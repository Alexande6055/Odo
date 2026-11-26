# Orden de Ejecución del Sistema en Local

Guía rápida con la **secuencia exacta de comandos** para levantar, verificar, actualizar y detener todo el entorno local (**Traccar**, **Odoo 16** y el **Microsistema React de Mapas**).

> **Regla crítica de orden:** `Tracar_Odoo` **siempre debe arrancarse primero**, porque crea la red Docker `tracar_odoo_default` que necesita `docker-compose.yml` de Odoo para conectar ambos stacks.

---

## Orden de Arranque Completo (Paso a Paso)

### 1. Verificar el archivo `.env` en la raíz del proyecto
En `/home/alexander/MEGA/Documentos/Gestion de Clidad/Odo/.env` confirma el puerto del microsistema de mapas y las credenciales de Traccar:

```env
MAP_WEB_PORT=3001
MAP_WEB_URL=http://localhost:3001

TRACCAR_SERVER_URL=http://localhost:8082
TRACCAR_INTERNAL_URL=http://traccar:8082
TRACCAR_USER=juanperzezss@gmail.com
TRACCAR_PASSWORD=asd1230A
```

---

### 2. Levantar el Stack de Traccar GPS + Bridge Docker (1.º)
Crea la red compartida `tracar_odoo_default` e inicia `traccar-db`, `traccar` (`:8082` y puertos GPS `:5000-5150`) y `traccar-map-bridge` (`:3050`):

```bash
cd "/home/alexander/MEGA/Documentos/Gestion de Clidad/Odo/Tracar_Odoo"
docker compose up -d
```

Verificar que Traccar esté arriba antes de pasar al paso 3:

```bash
docker ps --filter "name=traccar" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

---

### 3. Levantar Odoo 16 y PostgreSQL de Odoo (2.º)
Desde la carpeta raíz del proyecto, inicia `odoo16-db` y `odoo16` (`:8069`), conectándose automáticamente a `tracar_odoo_default`:

```bash
cd "/home/alexander/MEGA/Documentos/Gestion de Clidad/Odo"
docker compose up -d
```

Verificar logs de arranque de Odoo (opcional):

```bash
docker logs -f --tail 40 odoo16
```

*(Pulsa `Ctrl + C` para salir de los logs; el contenedor seguirá corriendo).*

---

### 4. Levantar el Microsistema React de Mapas en Modo Dev (3.º)
Si en `.env` está configurado `MAP_WEB_PORT=3001` (`http://localhost:3001`), levanta Vite en otra terminal:

```bash
cd "/home/alexander/MEGA/Documentos/Gestion de Clidad/Odo/Tracar_Odoo/microsistema-ruta-vehiculo"
pnpm install
pnpm run dev -- --port 3001
```

> **Nota sobre el puerto (`3000` vs `3001`):**
> * `vite.config.ts` intenta usar el puerto `3000` por defecto; si está ocupado, Vite salta automáticamente al `3001`. Pasando `-- --port 3001` garantizas que coincida siempre con `MAP_WEB_PORT=3001` en `.env`.
> * Si no quieres ejecutar `pnpm run dev` aparte y prefieres usar el contenedor compilado `traccar-map-bridge` (`:3050`), cambia `MAP_WEB_PORT=3050` y `MAP_WEB_URL=http://localhost:3050` en `.env` y reinicia `odoo16` (`docker restart odoo16`).

---

## Comprobación Rápida (Checklist Post-Arranque)

1. **Ver todos los contenedores activos:**
   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
   ```
   Deben figurar en estado `Up`: `traccar-db`, `traccar`, `traccar-map-bridge`, `odoo16-db` y `odoo16`.

2. **Accesos en el navegador:**
   * **Odoo 16 (Sistema Principal):** `http://localhost:8069/web`
   * **Directorio de Vehículos:** `http://localhost:8069/web#action=175&model=fleet.vehicle&view_type=kanban&cids=1&menu_id=127`
   * **Microsistema Mapa (Vite Dev):** `http://localhost:3001`
   * **Microsistema Mapa (Docker Bridge):** `http://localhost:3050`
   * **Traccar Web Admin:** `http://localhost:8082`

---

## Comandos Frecuentes de Mantenimiento

### Actualizar el módulo `fleet_traccar` tras editar XML, Python o SCSS
```bash
docker exec odoo16 odoo -d Odo-Principal -r odoo -w odoo --db_host=db -u fleet_traccar --stop-after-init
docker restart odoo16
```

### Limpiar caché de CSS/JS en Odoo (si un cambio SCSS/JS no se refleja)
```bash
docker exec odoo16 python3 -c "
import odoo
from odoo.tools import config
config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'Odo-Principal', '-r', 'odoo', '-w', 'odoo', '--db_host', 'db'])
registry = odoo.registry('Odo-Principal')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    env['ir.attachment'].sudo().search([('name', 'like', 'web.assets_%')]).unlink()
    cr.commit()
"
docker restart odoo16
```

### Reconstruir el contenedor `traccar-map-bridge` tras cambios en React (`src/`)
```bash
cd "/home/alexander/MEGA/Documentos/Gestion de Clidad/Odo/Tracar_Odoo"
docker compose up -d --build map-bridge
```

---

## Orden de Apagado Completo (Detener Todo)

1. **Detener Vite (en la terminal del microsistema React):** pulsa `Ctrl + C`.
2. **Detener Odoo (1.º al apagar):**
   ```bash
   cd "/home/alexander/MEGA/Documentos/Gestion de Clidad/Odo"
   docker compose down
   ```
3. **Detener Traccar y su red compartida (2.º al apagar):**
   ```bash
   cd "/home/alexander/MEGA/Documentos/Gestion de Clidad/Odo/Tracar_Odoo"
   docker compose down
   ```
   *(No uses `-v` en `docker compose down` para conservar las bases de datos de Odoo y Traccar).*
