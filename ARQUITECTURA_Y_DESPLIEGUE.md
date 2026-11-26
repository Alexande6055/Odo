# Arquitectura, Conexión y Despliegue del Sistema de Transporte Universitario (UTA)

Este documento describe cómo están interconectadas las aplicaciones del ecosistema de monitoreo GPS y gestión de flota universitaria (**Traccar**, **Odoo 16** y el **Microsistema React de Mapas**), junto con los pasos completos para levantar, configurar y verificar todo el stack en local o servidor.

---

## 1. Arquitectura General e Interconexión de las 3 Aplicaciones

El sistema integra tres aplicaciones principales respaldadas por dos bases de datos PostgreSQL aisladas y una red Docker compartida (`tracar_odoo_default`):

```
[Dispositivos GPS / App Traccar Client]
        │  (TCP / UDP puertos 5000–5150, ej. OsmAnd 5055)
        ▼
┌──────────────────────────────────────────────────────────┐
│  1. TRACCAR GPS SERVER (Puerto HTTP 8082)                │
│     • Contenedor: traccar (traccar/traccar:latest)       │
│     • Base de datos: traccar-db (postgres:15-alpine)     │
│     • Config: Tracar_Odoo/traccar.xml                    │
└───────────────┬──────────────────────────┬───────────────┘
                │                          │
   API REST /api/devices,     Proxy HTTP /api y WebSocket
   /api/positions,            /api/socket (Vite o server.js)
   /api/reports/route                      │
                │                          ▼
                │         ┌────────────────────────────────┐
                │         │  2. MICROSISTEMA DE MAPAS      │
                │         │     (React 19 + Vite + Leaflet)│
                │         │     • Dev local: :3001         │
                │         │     • Docker bridge: :3050     │
                │         └────────────────┬───────────────┘
                │                          │
                ▼                          │ (Embebido vía URL en
┌──────────────────────────────────────────▼───────────────┐
│  3. ODOO 16 — MÓDULO fleet_traccar (Puerto HTTP 8069)    │
│     • Contenedor: odoo16 (odoo:16.0)                     │
│     • Base de datos: odoo16-db (postgres:15)             │
│     • Panel OWL 2, Flota, Rutas, Paradas, Viajes e       │
│       Incidencias automáticas                            │
└──────────────────────────────────────────────────────────┘
```

### ¿Cómo se conectan entre sí?

1. **Dispositivos GPS → Traccar (`:5000–5150` TCP/UDP):**
   Los rastreadores físicos o la app móvil **Traccar Client** envían coordenadas, velocidad e ignición hacia los puertos de escucha de Traccar (por ejemplo, protocolo OsmAnd en el puerto `5055`). Traccar persiste posiciones e historial en PostgreSQL (`traccar-db`).

2. **Odoo 16 ↔ Traccar (`http://localhost:8082` / `http://traccar:8082`):**
   * En [docker-compose.yml](docker-compose.yml), el contenedor `odoo16` se conecta tanto a su red interna (`default`) como a la red externa `tracar_odoo_default` (`traccar_net`).
   * El archivo de configuración centralizado [.env](.env) expone `TRACCAR_SERVER_URL`, `TRACCAR_INTERNAL_URL`, `TRACCAR_USER` y `TRACCAR_PASSWORD` dentro del contenedor (`env_file: .env` y montaje `/etc/odoo/.env`).
   * Desde `addons/fleet_traccar/models/fleet_vehicle.py` y `addons/fleet_traccar/models/geo_utils.py`, la función `get_effective_traccar_url()` resuelve automáticamente si Odoo debe consultar a Traccar mediante la pasarela Docker (`172.17.0.1:8082`) o el nombre del servicio interno (`http://traccar:8082`).
   * Odoo sincroniza dispositivos, estados (`online`/`offline`) y posiciones (`cron_sync_all_traccar_positions` y botones manuales), y sobre esos puntos calcula cumplimiento de rutas, omisión de paradas, desvíos e incidencias en `transport.trip`.

3. **Microsistema React de Mapas ↔ Traccar:**
   * Código fuente en `Tracar_Odoo/microsistema-ruta-vehiculo/`.
   * En **modo desarrollo** (`pnpm run dev` con Vite), `Tracar_Odoo/microsistema-ruta-vehiculo/vite.config.ts` redirige las peticiones `/api` hacia `http://localhost:8082` y `/api/socket` hacia `ws://localhost:8082`.
   * En **modo producción / Docker** (`traccar-map-bridge` en el puerto `3050`), `Tracar_Odoo/microsistema-ruta-vehiculo/server.js` (Express 5 + `http-proxy-middleware`) sirve el compilado estático de `dist/` y reenvía `/api` y WebSockets hacia `TRACCAR_URL=http://traccar:8082`.
   * El cliente React (`src/services/traccarApi.ts`) consulta `/api/devices`, `/api/positions`, `/api/reports/route` y escucha eventos en vivo por WebSocket (`/api/socket`).

4. **Odoo 16 → Microsistema React (`.env` / `MAP_WEB_URL`):**
   * `addons/fleet_traccar/models/geo_utils.py` (`get_configured_map_web_url()`) lee en orden de prioridad:
     1. Variables de entorno `MAP_WEB_URL` / `MAP_WEB_PORT`.
     2. El archivo `.env` (`/etc/odoo/.env`, `/mnt/extra-addons/.env`, o raíz del proyecto).
     3. Parámetro de sistema en Odoo (`fleet_traccar.map_url`, configurable en **Flota y Configuración → Ajustes Traccar**).
   * Tanto el Dashboard nativo OWL 2 (`controllers/transport_dashboard.py` + `static/src/xml/transport_dashboard.xml`) como la ficha de detalle del vehículo (`fleet_vehicle.py`) y la vista de rutas incrustan el visor del microsistema usando esta URL con `?compact=true`, o la abren en pantalla completa mediante los botones de acceso directo.

---

## 2. Variables de Entorno (`.env`)

En la raíz del proyecto (`/home/alexander/MEGA/Documentos/Gestion de Clidad/Odo/.env`):

```env
# Puerto y URL del Microservicio Web de Mapas (React / Vite)
MAP_WEB_PORT=3001
MAP_WEB_URL=http://localhost:3001

# Conexión con el servidor Traccar GPS
TRACCAR_SERVER_URL=http://localhost:8082
TRACCAR_INTERNAL_URL=http://traccar:8082
TRACCAR_USER=tu_usuario_traccar@correo.com
TRACCAR_PASSWORD=tu_password_traccar
```

> **Nota sobre puertos del mapa:**
> * Si levantas el microsistema React en modo desarrollo con `pnpm run dev`, Vite intenta usar el puerto `3000` y, si está ocupado, pasa automáticamente a `3001`. Asegúrate de que `MAP_WEB_PORT` y `MAP_WEB_URL` coincidan con el puerto activo (`http://localhost:3001`).
> * Si prefieres usar el contenedor compilado `traccar-map-bridge`, apunta `MAP_WEB_URL=http://localhost:3050` y `MAP_WEB_PORT=3050`.

---

## 3. Paso a Paso: Cómo Levantar Toda la Aplicación

### Requisitos previos
* Docker y Docker Compose v2 (`docker compose`)
* Node.js (v20+) y `pnpm` (para ejecutar el microsistema de mapas en modo desarrollo)

### Paso 1: Levantar Traccar, su base de datos y el Bridge Docker
Este stack debe levantarse **primero**, ya que crea la red compartida `tracar_odoo_default` que utiliza el contenedor de Odoo:

```bash
cd Tracar_Odoo
docker compose up -d
```

Esto inicia:
* `traccar-db` (PostgreSQL para Traccar)
* `traccar` (Servidor GPS en `http://localhost:8082` y puertos GPS `5000-5150`)
* `traccar-map-bridge` (Versión compilada del visor de mapas en `http://localhost:3050`)

Verifica que Traccar esté activo abriendo `http://localhost:8082` o ejecutando `docker ps`.

### Paso 2: Levantar Odoo 16 y su base de datos
Desde la carpeta raíz del proyecto (`/home/alexander/MEGA/Documentos/Gestion de Clidad/Odo`):

```bash
docker compose up -d
```

Esto inicia:
* `odoo16-db` (PostgreSQL 15)
* `odoo16` (Odoo 16 en `http://localhost:8069`, montando `./addons` en `/mnt/extra-addons` y `./.env` en `/etc/odoo/.env`)

> Si realizas cambios en el código XML, Python o SCSS de `addons/fleet_traccar`, actualiza el módulo y reinicia Odoo con:
> ```bash
> docker exec odoo16 odoo -d Odo-Principal -r odoo -w odoo --db_host=db -u fleet_traccar --stop-after-init
> docker restart odoo16
> ```

### Paso 3: Levantar el Microsistema React de Mapas (Modo Desarrollo en `:3001`)
Si estás desarrollando sobre `Tracar_Odoo/microsistema-ruta-vehiculo` o quieres servirlo desde Vite según el `.env` (`http://localhost:3001`):

```bash
cd Tracar_Odoo/microsistema-ruta-vehiculo
pnpm install
pnpm run dev
```

Si modificas el frontend React y deseas actualizar también la imagen Docker de `traccar-map-bridge` (`:3050`):

```bash
cd Tracar_Odoo
docker compose up -d --build map-bridge
```

---

## 4. Resumen de URLs y Puertos

| Servicio | Contenedor / Proceso | Puerto Host | URL de Acceso |
| :--- | :--- | :---: | :--- |
| **Odoo 16 (Transporte UTA)** | `odoo16` | `8069` | `http://localhost:8069/web` |
| **PostgreSQL Odoo** | `odoo16-db` | interno `5432` | Solo red Docker |
| **Servidor Traccar Web / API** | `traccar` | `8082` | `http://localhost:8082` |
| **Ingesta GPS Traccar (OsmAnd / otros)** | `traccar` | `5000–5150` | TCP/UDP (ej. `5055`) |
| **PostgreSQL Traccar** | `traccar-db` | interno `5432` | Solo red Docker |
| **Microsistema Mapa (Vite Dev)** | `pnpm run dev` | `3001` (o `3000`) | `http://localhost:3001` |
| **Microsistema Mapa (Docker Bridge)** | `traccar-map-bridge` | `3050` | `http://localhost:3050` |

---

## 5. Verificación Rápida Tras el Arranque

1. **Verificar contenedores activos:**
   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
   ```
   Debes ver en estado `Up`: `odoo16`, `odoo16-db`, `traccar`, `traccar-db` y `traccar-map-bridge`.

2. **Verificar conexión Odoo ↔ Traccar:**
   * Ingresa a `http://localhost:8069/web`.
   * Ve a **Transporte Universitario → Flota y Configuración → Ajustes Traccar**.
   * Verifica la URL, usuario, contraseña y URL del microsistema de mapas, y pulsa **Probar Conexión con Traccar**.

3. **Verificar Dashboard y Mapa en Vivo:**
   * En **Transporte Universitario → Panel de Control (Dashboard)** deben cargarse los KPIs, el mapa satelital del microsistema React, los 3 gráficos analíticos (Cumplimiento de Recorridos, Puntualidad por Línea, Desglose de Incidencias) y la tabla de Monitoreo.

4. **Verificar Directorio de Vehículos:**
   * En **Transporte Universitario → Flota y Configuración → Directorio de Vehículos**, registra el `Código IMEI GPS (Traccar)` en cada bus; al vincular o guardar, el vehículo quedará asociado en Traccar y mostrará su ubicación y velocidad en tiempo real.
