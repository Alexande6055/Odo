# Plan de Proyecto y Checklist de Cumplimiento
## Proyecto Final Integrador: Sistema de Monitoreo y Evaluación de Rutas de Transporte Universitario (Odoo 16 + Traccar)
**Asignatura:** Gestión de Calidad del Software — UTA

---

## 1. Estado Actual: ¿Qué está ya desarrollado en el repositorio?

Actualmente, el proyecto cuenta con la infraestructura base de contenedores y una primera versión de integración entre Odoo y Traccar centrada en el vehículo:

### Infraestructura y Contenedores
- **Odoo 16 y PostgreSQL 15 ([docker-compose.yml](file:///home/alexander/MEGA/Documentos/Gestion%20de%20Clidad/Odo/docker-compose.yml)):**
  - Contenedor `odoo16` y base de datos `odoo16-db`.
  - Enlazado con la red externa de Traccar (`traccar_net` / `tracar_odoo_default`).
  - Mapeo de addons locales en `./addons`.
- **Traccar Server y Base de Datos ([Tracar_Odoo/docker-compose.yml](file:///home/alexander/MEGA/Documentos/Gestion%20de%20Clidad/Odo/Tracar_Odoo/docker-compose.yml)):**
  - Contenedor `traccar` oficial con puertos expuestos (`8082` web, `5055` protocolo OsmAnd/Traccar Client, rango de puertos GPS).
  - Base de datos dedicada `traccar-db` (Postgres 15-alpine).
  - Archivo de configuración [Tracar_Odoo/traccar.xml](file:///home/alexander/MEGA/Documentos/Gestion%20de%20Clidad/Odo/Tracar_Odoo/traccar.xml).
- **Microservicio Puente de Mapas ([Tracar_Odoo/microsistema-ruta-vehiculo/](file:///home/alexander/MEGA/Documentos/Gestion%20de%20Clidad/Odo/Tracar_Odoo/microsistema-ruta-vehiculo/)):**
  - Aplicación React + TypeScript + Vite con servidor Express `server.js` (puerto `3050`).
  - Proxy para llamadas `/api` y WebSockets hacia Traccar.
  - Interfaz de mapa interactivo (Leaflet/OSM) con soporte de visualización en vivo y reproducción (playback).

### Módulo Odoo: `fleet_traccar` ([addons/fleet_traccar/](file:///home/alexander/MEGA/Documentos/Gestion%20de%20Clidad/Odo/addons/fleet_traccar/))
- **Extensión de Flota ([fleet_vehicle.py](file:///home/alexander/MEGA/Documentos/Gestion%20de%20Clidad/Odo/addons/fleet_traccar/models/fleet_vehicle.py)):**
  - Campos agregados: `gps_imei`, `traccar_device_id`, `traccar_status`, `last_latitude`, `last_longitude`, `last_speed`, `last_gps_update`.
  - Métodos de vinculación y registro automático de dispositivos en la API de Traccar (`_create_device_in_traccar` y `action_register_traccar_device`).
  - Consulta manual de la última posición (`action_sync_traccar_positions`).
  - Tarea cron programada para actualización periódica ([ir_cron_data.xml](file:///home/alexander/MEGA/Documentos/Gestion%20de%20Clidad/Odo/addons/fleet_traccar/data/ir_cron_data.xml)).
  - Enlaces directos a OpenStreetMap y mapa embebido vía iframe.
- **Configuración ([res_config_settings.py](file:///home/alexander/MEGA/Documentos/Gestion%20de%20Clidad/Odo/addons/fleet_traccar/models/res_config_settings.py)):**
  - Parámetros del sistema para URL del servidor Traccar, usuario, contraseña y URL del mapa.

---

## 2. Checklist Exhaustivo de Tareas Pendientes (Rúbrica 100 Puntos)

### Actividad 1: Análisis del Problema y Requisitos (10 Pts)
- [ ] **1.1.** Redactar documento de Requisitos Funcionales (RF) con identificador y descripción:
  - [ ] RF-01: Gestión de Vehículos y vinculación GPS.
  - [ ] RF-02: Administración de múltiples rutas universitarias.
  - [ ] RF-03: Registro y secuenciación de paradas/puntos de control y horarios previstos.
  - [ ] RF-04: Asignación y programación de recorridos (viajes por fecha y vehículo).
  - [ ] RF-05: Captura y almacenamiento del historial de coordenadas GPS.
  - [ ] RF-06: Detección automática de retrasos respecto al horario oficial.
  - [ ] RF-07: Detección automática de omisión de paradas (puntos de control).
  - [ ] RF-08: Detección automática de desviaciones de la ruta establecida.
  - [ ] RF-09: Registro y clasificación de incidencias del transporte.
  - [ ] RF-10: Cálculo dinámico de métricas de transporte y de calidad de software.
  - [ ] RF-11: Visualización de mapas y dashboard analítico en Odoo.
- [ ] **1.2.** Redactar Requisitos No Funcionales (RNF):
  - [ ] RNF-01: Rendimiento y tiempo de respuesta ante consultas de posiciones.
  - [ ] RNF-02: Integridad y no duplicidad de coordenadas GPS.
  - [ ] RNF-03: Seguridad en credenciales API y acceso por túnel HTTPS.
  - [ ] RNF-04: Mantenibilidad y cumplimiento de buenas prácticas (SonarQube).
- [ ] **1.3.** Definir **Criterios de Aceptación** claros y medibles para cada requisito funcional.

---

### Actividad 2: Infraestructura y Conectividad Externa (10 Pts)
- [ ] **2.1. Cloudflare Tunnel:**
  - [ ] Instalar y configurar `cloudflared` (o túnel HTTPS autorizado) para publicar el puerto de recepción de Traccar (`5055` o `8082`) a Internet sin requerir IP pública fija.
- [ ] **2.2. Traccar Client en Datos Móviles:**
  - [ ] Configurar la app Traccar Client en al menos un smartphone apuntando al subdominio público del túnel Cloudflare.
  - [ ] Realizar prueba de transmisión con **datos móviles (4G/5G)** con el Wi-Fi apagado.
- [ ] **2.3. Evidencias requeridas:**
  - [ ] Captura de los contenedores Docker en ejecución.
  - [ ] Captura de la configuración y estado activo de Cloudflare Tunnel.
  - [ ] Captura de Traccar Server recibiendo posiciones en tiempo real desde la red móvil.

---

### Actividad 3 & 4: Módulo de Gestión de Transporte en Odoo (25 Pts)
*(El núcleo del sistema en Odoo: modelos creados en `addons/fleet_traccar/`)*

- [x] **3.1. Modelo de Rutas (`transport.route`):**
  - [x] Campos: Nombre, código, origen, destino, distancia estimada ($km$), tiempo estimado (minutos).
  - [x] Trazado de referencia (coordenadas de la ruta para detección de desvíos).
  - [x] *Requisito mínimo cumplido:* Creadas **3 rutas diferentes** de la UTA en `transport_demo_data.xml`.
- [x] **3.2. Modelo de Puntos de Control / Paradas (`transport.route.stop`):**
  - [x] Campos: Nombre de parada, secuencia/orden, latitud, longitud.
  - [x] Horario previsto de paso (offset en minutos desde inicio).
  - [x] Radio de tolerancia de proximidad en metros (50 a 60 metros).
  - [x] Margen de tolerancia de tiempo en minutos ($\pm 5$ min).
  - [x] *Requisito mínimo cumplido:* Creadas **4 paradas por cada ruta** (12 paradas geolocalizadas en total en Ambato).
- [x] **3.3. Modelo de Asignación de Recorridos / Viajes (`transport.trip`):**
  - [x] Campos: Vehículo asignado, ruta asignada, fecha, horas programadas vs reales, distancia real, estado (`draft`, `in_progress`, `completed`, `cancelled`).
  - [x] Soporte para que un mismo vehículo realice diferentes rutas en distintos horarios.
  - [x] Secuencia automática única `VIAJE/YYYY/XXXX`.
- [x] **3.4. Modelo de Histórico de Posiciones (`transport.trip.point`):**
  - [x] Relación con el viaje (`trip_id`) y vehículo (`vehicle_id`).
  - [x] Campos: latitud, longitud, velocidad, fecha/hora GPS, ID Traccar.
  - [x] Control de no duplicidad de registros mediante `_sql_constraints` y filtro por timestamp.
- [x] **3.5. Interfaz de Usuario (Vistas Odoo):**
  - [x] Vistas formulario, lista, kanban, calendario y búsqueda para Rutas, Paradas y Recorridos.
  - [x] Menús de acceso organizados en Odoo bajo la aplicación **Transporte Universitario**.
  - [x] Reglas de seguridad CRUD configuradas en `security/ir.model.access.csv`.

---

### Actividad 5: Monitoreo y Ejecución de 10 Recorridos de Prueba (10 Pts)
- [x] **5.1.** Registrar y documentar **al menos 10 recorridos de prueba** distribuidos en las 3 rutas:
  - [x] Recorrido 1 (Ruta 1 - Bus 1): Caso Normal / Puntual (conforme).
  - [x] Recorrido 2 (Ruta 1 - Bus 2): Caso con Retraso (14 min en Av. Atahualpa).
  - [x] Recorrido 3 (Ruta 1 - Bus 1): Caso con Parada omitida (Parque Cevallos).
  - [x] Recorrido 4 (Ruta 2 - Bus 2): Caso Normal / Puntual (conforme a Querochaca).
  - [x] Recorrido 5 (Ruta 2 - Bus 1): Caso con Desviación geográfica de ruta (380m fuera).
  - [x] Recorrido 6 (Ruta 2 - Bus 2): Caso con Retraso significativo (18 min).
  - [x] Recorrido 7 (Ruta 3 - Bus 1): Caso Normal / Puntual (conforme circuito Ficoa).
  - [x] Recorrido 8 (Ruta 3 - Bus 2): Caso con Desviación + Retraso.
  - [x] Recorrido 9 (Ruta 3 - Bus 1): Caso de Recorrido con corte/pérdida de señal GPS (16 min).
  - [x] Recorrido 10 (Ruta 1 - Bus 2): Caso con múltiples incidencias (retraso 12 min + parada Mall omitida).
- [x] **5.2.** Trazados GPS, marcas de tiempo y auditoría completa generados y validados en la base de datos de Odoo.

---

### Actividad 6: Motor de Detección de Incumplimientos e Incidencias (10 Pts)
- [x] **6.1. Modelo de Incidencias (`transport.trip.incident`):**
  - [x] Relación con viaje (`trip_id`), vehículo, ruta y parada afectada (si aplica).
  - [x] Tipo de incidencia: `retraso`, `parada_omitida`, `desvio_ruta`, `recorrido_incompleto`, `gps_lost`.
  - [x] Severidad, fecha/hora, valor detectado (minutos de retraso, metros de desvío).
- [x] **6.2. Algoritmos de Detección Automática implementados:**
  - [x] Algoritmo de verificación de paradas por proximidad geodésica (fórmula Haversine en `geo_utils.py`).
  - [x] Algoritmo de detección de retrasos comparando `timestamp_llegada` vs `hora_programada + tolerancia`.
  - [x] Algoritmo de detección de desviación de ruta (`min_distance_to_path` comparado con `allowed_deviation_meters`).
  - [x] Algoritmo de detección de pérdida de señal (brechas temporales $> 10$ minutos).
- [ ] **6.3. Justificación de Tolerancias:**
  - [ ] Tabla documentada con los valores umbral empleados (radio 50-60 m, tolerancia de retraso 5 min, desvío 150 m) y su justificación operativa para el informe final.

---

### Actividad 7: Métricas e Indicadores Obligatorios (15 Pts)
*Modelo relacional `transport.metrics.summary` con métodos de cálculo dinámicos implementado.*

- [x] **7.1. Métricas de Transporte (8 Obligatorias implementadas en el modelo):**
  - [x] **M1:** Porcentaje de cumplimiento de rutas.
  - [x] **M2:** Porcentaje de puntualidad.
  - [x] **M3:** Retraso promedio (minutos).
  - [x] **M4:** Porcentaje de paradas cumplidas.
  - [x] **M5:** Desviación respecto a la ruta programada.
  - [x] **M6:** Diferencia entre distancia estimada y recorrida ($\Delta d$).
  - [x] **M7:** Tiempo promedio de recorrido.
  - [x] **M8:** Número y frecuencia de incidencias.
- [x] **7.2. Métricas de Calidad de Software (4 Obligatorias implementadas en el modelo):**
  - [x] **CS1: Integridad de los registros GPS.**
  - [x] **CS2: Exactitud de datos sincronizados Traccar $\leftrightarrow$ Odoo.**
  - [x] **CS3: Tiempo de respuesta del sistema (latencia de cómputo en ms).**
  - [x] **CS4: Porcentaje de detección correcta de incidencias.**
- [x] **7.3.** Métricas calculadas dinámicamente mediante queries ORM sobre la BD en Odoo (sin valores estáticos).

---

### Actividad 8: Dashboard y Visualización en Odoo (15 Pts)
- [x] **8.1.** Implementar panel de indicadores en Odoo:
  - [x] Vistas de tarjetas KPI para cumplimiento, puntualidad, retraso y paradas.
  - [x] Fichas técnicas HTML integradas con fórmulas e interpretación operativa.
  - [x] Vistas Graph (barras) y Pivot para análisis de incidencias por ruta y severidad.
  - [ ] *(Opcional)* Embeber informe de Power BI interactivo adicional si se requiere.

---

### Actividad 9: Aseguramiento de la Calidad y Pruebas (10 Pts)
- [ ] **9.1. Pruebas Funcionales y Caja Negra:**
  - [ ] Pruebas de clases de equivalencia y valores límite (horarios válidos/inválidos, coordenadas límite, IMEI con formato erróneo).
- [ ] **9.2. Pruebas de Caja Blanca:**
  - [ ] Pruebas unitarias sobre las funciones matemáticas (Haversine, cálculo de retraso, lógica condicional de incidencias).
- [ ] **9.3. Pruebas de Integración:**
  - [ ] Pruebas de conexión API Traccar $\leftrightarrow$ Odoo (manejo de caídas de conexión, timeouts, autenticación fallida).
- [ ] **9.4. Pruebas de Rendimiento:**
  - [ ] Medición de tiempos de carga y respuesta con consultas de $100$, $1000$ y $5000$ coordenadas GPS.
- [ ] **9.5. Pruebas Automatizadas con Pytest:**
  - [ ] Crear script `test_transport_system.py` que valide automáticamente la lógica de cálculo e incidencias.
- [ ] **9.6. Análisis Estático con SonarQube:**
  - [ ] Analizar el código de `fleet_traccar` en SonarQube.
  - [ ] Obtener reporte de bugs, vulnerabilidades, code smells y duplicaciones.
  - [ ] Realizar refactorización para subsanar los principales hallazgos.
- [ ] **9.7. Matriz Formal de Casos de Prueba:**
  - [ ] Documentar al menos **10 casos de prueba** detallados (ID, Objetivo, Entradas, Resultado Esperado, Resultado Obtenido, Estado Pasa/Falla).
- [ ] **9.8. Mapeo ISO/IEC 25010:**
  - [ ] Relacionar resultados con características: Adecuación funcional, Fiabilidad, Eficiencia de desempeño, Mantenibilidad y Seguridad.

---

### Actividad 10: Mejora Continua (5 Pts)
- [ ] **10.1. Selección del Problema Real:**
  - [ ] Elegir un fallo técnico real detectado durante el desarrollo (ej: duplicación de puntos GPS en la sincronización, error en la tolerancia de detección de parada, desfase horario UTC/local).
- [ ] **10.2. Aplicación de Herramientas de Calidad:**
  - [ ] **Diagrama de Ishikawa (Causa-Efecto):** Analizar causas del problema en las 6M / dimensiones de software.
  - [ ] **Diagrama de Pareto:** Priorizar las causas o defectos según su frecuencia.
  - [ ] **Ciclo PDCA (Deming):**
    - *Plan:* Planificar la corrección.
    - *Do:* Implementar la solución técnica en el código.
    - *Check:* Verificar con pruebas la resolución del defecto.
    - *Act:* Estandarizar la solución y documentar lecciones aprendidas.
- [ ] **10.3. Comparación ANTES vs. DESPUÉS:**
  - [ ] Mostrar métricas cuantitativas que demuestren la mejora lograda tras la corrección.

---

### Entregables Finales y Defensa (5 Pts)
- [ ] **Informe Final Consolidado (LaTeX $\to$ PDF en `informes/`):**
  - [ ] Portada, introducción y contexto del problema.
  - [ ] Documento de requisitos (RF, RNF y criterios de aceptación).
  - [ ] Arquitectura del sistema y Modelo Entidad-Relación (ER).
  - [ ] Evidencias de infraestructura (Docker, Cloudflare Tunnel, Traccar Client).
  - [ ] Detalle del módulo desarrollado (modelos, vistas, reglas).
  - [ ] Documentación de los 10 recorridos de prueba.
  - [ ] Tabla completa de las 12 métricas calculadas.
  - [ ] Capturas del Dashboard funcional en Odoo.
  - [ ] Matriz de pruebas, resultados Pytest y reporte SonarQube.
  - [ ] Sección de Mejora Continua (Ishikawa, Pareto, PDCA).
  - [ ] Conclusiones y recomendaciones.
- [ ] **Preparación de la Defensa Técnica:**
  - [ ] Disponer de demostración en vivo con 1 caso de cumplimiento y 1 de incumplimiento.
  - [ ] Responder con solvencia técnica a las preguntas de diseño, calidad y algoritmos.

---

## 3. La Mejor Ruta de Desarrollo (Hoja de Ruta Estratégica)

Para avanzar de forma ordenada y sin bloqueos, se recomienda seguir esta ruta secuencial de 5 fases:

```
┌────────────────────────────────────────────────────────┐
│  FASE 1: Modelo de Datos y Vistas en Odoo              │
│  - Rutas, Paradas, Asignación de Viajes, Incidencias   │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│  FASE 2: Conectividad Externa y Datos de Prueba        │
│  - Cloudflare Tunnel + Traccar Client móvil            │
│  - Grabación/Simulación de los 10 Recorridos           │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│  FASE 3: Lógica de Detección, Métricas y Dashboard     │
│  - Reglas de retrasos, desvíos y paradas saltadas      │
│  - 8 métricas transporte + 4 métricas software         │
│  - Vistas Graph/Pivot o Dashboard en Odoo              │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│  FASE 4: Calidad de Software, Pruebas y SonarQube      │
│  - Pytest automatizado + 10 Casos de prueba            │
│  - Escaneo SonarQube del módulo + Mapeo ISO 25010      │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│  FASE 5: Mejora Continua e Informe Final en LaTeX      │
│  - Ishikawa, Pareto, PDCA (Antes vs Después)           │
│  - Redacción y compilación del informe final           │
└────────────────────────────────────────────────────────┘
```

### Fase 1: Arquitectura de Datos en Odoo (1-2 días)
1. Extender `fleet_traccar` con los modelos relacionales:
   - `transport.route`: Catálogo de 3 rutas de la UTA (ej. Campus Huachi - Campus Ingahurco, etc.).
   - `transport.route.stop`: 4 paradas geolocalizadas por ruta.
   - `transport.trip`: Viaje programado con vehículo, ruta, conductor y horario.
   - `transport.trip.point`: Historial de puntos GPS del viaje sincronizados desde Traccar.
   - `transport.trip.incident`: Registro de incidencias.
2. Definir vistas en Odoo (`form`, `tree`, `search`) y menús de acceso.

### Fase 2: Conectividad Externa y Generación de Recorridos (1 día)
1. Levantar túnel seguro con `cloudflared` apuntando al puerto `5055` de Traccar.
2. Instalar Traccar Client en el teléfono y verificar recepción con datos móviles fuera de la red local.
3. Generar los **10 recorridos de prueba** (combinando recorridos reales en la ciudad con simulaciones precisas para forzar desvíos o paradas omitidas).

### Fase 3: Motor de Reglas, Métricas y Dashboard (2 días)
1. Implementar método Python en `transport.trip`: `action_analyze_trip()` que analice los puntos GPS del viaje contra las paradas y el trazado de la ruta.
2. Registrar automáticamente las incidencias detectadas.
3. Implementar métodos de cálculo para las 8 métricas de transporte y las 4 métricas de software.
4. Construir las vistas gráficas y métricas KPI en Odoo.

### Fase 4: Pruebas, SonarQube e ISO/IEC 25010 (1-2 días)
1. Escribir tests en Pytest (`practicas_calidad/test_transport_system.py`) validando distancias Haversine, tolerancias de tiempo y detección de desvíos.
2. Documentar la matriz de 10 casos de prueba.
3. Ejecutar SonarQube sobre `addons/fleet_traccar/` y generar capturas de métricas de calidad.

### Fase 5: Mejora Continua y Documentación Final (1-2 días)
1. Documentar un caso de mejora técnica usando Ishikawa, Pareto y ciclo PDCA.
2. Redactar el informe integrador final en LaTeX (aprovechando la plantilla existente en `informes/`) e incluir todas las evidencias solicitadas en la rúbrica.
3. Preparar el guión de la defensa técnica demostrando 1 caso de cumplimiento y 1 de incumplimiento.

