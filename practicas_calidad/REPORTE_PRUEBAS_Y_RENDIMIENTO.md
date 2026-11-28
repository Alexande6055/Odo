# Reporte de Pruebas Automatizadas, Integración y Rendimiento

**Proyecto:** Sistema de Monitoreo y Evaluación de Rutas de Transporte Universitario UTA (Odoo 16 + Traccar)  
**Fecha de ejecución:** 2026-11-28  
**Scripts ejecutados:**
- `python3 practicas_calidad/test_suite_completo.py` (Caja Blanca, Integración y Benchmark Geodésico)
- `docker exec -i odoo16 python3 - < practicas_calidad/test_odoo_blackbox_and_perf.py` (Caja Negra, Valores Límite y Rendimiento ORM en PostgreSQL)

---

## 1. Matriz Formal de Casos de Prueba (20 / 20 Aprobados — 100%)

| ID | Tipo | Caso de Prueba | Entrada / Escenario | Resultado Esperado | Resultado Obtenido | Estado |
| :-: | :--- | :--- | :--- | :--- | :--- | :-: |
| **CP-01** | Caja Blanca | Distancia Haversine identidad y simetría | Huachi↔Huachi y Huachi↔Ingahurco | `0.0 m`, `d(A,B)==d(B,A)`, rango 2.9–3.5 km | `0.0 m`, simetría exacta, ~3.03 km | ✅ PASA |
| **CP-02** | Caja Blanca | Geocerca / radio de proximidad | Punto a ~15 m vs >3.000 m (radio 50 m) | `True` dentro, `False` fuera | `True` / `False` | ✅ PASA |
| **CP-03** | Caja Blanca | Distancia mínima a corredor de ruta | Punto en Mall de los Andes vs punto desviado | `< 1 m` en ruta, `> 1000 m` fuera | `< 1 m` / `> 1000 m` | ✅ PASA |
| **CP-04** | Caja Blanca | Distancia acumulada de trayecto | 4 paradas consecutivas Ruta 1 | Entre `3.0` y `8.0 km` | `3.024 km` | ✅ PASA |
| **CP-05** | Caja Blanca | Coordenadas corruptas / no numéricas | `lat="abc"` | Lanza `ValueError` | `ValueError` lanzado | ✅ PASA |
| **CP-06** | Caja Blanca | Reglas de retraso y parada omitida | 23 vs 32 min (tol. 5 min); 120 m vs 50 m | A tiempo / retraso / omitida | Validado correctamente | ✅ PASA |
| **CP-07** | Integración | API REST Servidor Traccar | `GET http://localhost:8082/api/server` | `HTTP 200` + JSON con `version` | `HTTP 200` con versión | ✅ PASA |
| **CP-08** | Integración | Microsistema Mapas React + Proxy | `GET :3050` y `GET :3050/api/server` | `HTTP 200` en ambos | `HTTP 200` / `HTTP 200` | ✅ PASA |
| **CP-09** | Integración | Servidor Web Odoo 16 | `GET http://localhost:8069/web/login` | `HTTP 200` | `HTTP 200` | ✅ PASA |
| **CP-10** | Integración | Ingesta protocolo GPS OsmAnd | `GET http://localhost:5055/?id=8632940401001&lat=...` | Puerto 5055 escucha y procesa HTTP | Respuesta HTTP válida | ✅ PASA |
| **CP-11** | Rendimiento | Escalado geodésico 100 / 1.000 / 5.000 pts | Series sintéticas Huachi→Ingahurco | `< 1.000 ms` hasta 5.000 pts | `1.34 ms` / `13.25 ms` / `64.71 ms` | ✅ PASA |
| **CP-12** | Caja Negra | Fecha anterior a hoy en viaje nuevo | `date = hoy - 1 día` | Bloquea con `ValidationError` | Bloqueado con mensaje claro | ✅ PASA |
| **CP-13** | Valores Límite | Hora fuera de rango (`24:00`) | `scheduled_start_hour = 24.0` | Bloquea (`00:00` a `23:59`) | Bloqueado con mensaje claro | ✅ PASA |
| **CP-14** | Valores Límite | Llegada igual/anterior a Salida | `10:00` → `10:00` | Bloquea con `ValidationError` | Bloqueado con mensaje claro | ✅ PASA |
| **CP-15** | Caja Negra | Viaje válido con campos solo hora | `mañana`, `08:00` → `08:30` | Crea viaje y conserva `8.0` / `8.5` | `VIAJE/2026/0023` creado | ✅ PASA |
| **CP-16** | Caja Negra | Solapamiento horario mismo vehículo | Mismo bus `08:15` → `09:00` | Bloquea solapamiento | Bloqueado con `ValidationError` | ✅ PASA |
| **CP-17** | Valores Límite | Latitud fuera de rango en parada | `latitude = 90.1°` | Bloquea (`-90` a `90`) | Bloqueado con `ValidationError` | ✅ PASA |
| **CP-18** | Caja Negra | IMEI con formato inválido | `gps_imei = "123"` (< 5 chars) | Bloquea formato inválido | Bloqueado con `ValidationError` | ✅ PASA |
| **CP-19** | Caja Negra | IMEI duplicado entre buses | Mismo IMEI en 2 vehículos | Bloquea duplicado | Bloqueado con `ValidationError` | ✅ PASA |
| **CP-20** | Caja Negra | Incidencia sobre viaje en Borrador | Incidencia en viaje `draft` | Bloquea (solo `En Curso`/`Completado`) | Bloqueado con `ValidationError` | ✅ PASA |

---

## 2. Resultados de Pruebas de Rendimiento y Estrés (100 / 1.000 / 5.000 puntos GPS)

### A. Rendimiento algorítmico puro (`geo_utils.py`)
| Cantidad de Puntos GPS | Cálculo Distancia Total (ms) | Detección de Desvíos (ms) | Tiempo Total Algoritmo (ms) |
| :---: | :---: | :---: | :---: |
| **100** | `0.31 ms` | `1.03 ms` | **`1.34 ms`** |
| **1.000** | `2.40 ms` | `10.85 ms` | **`13.25 ms`** |
| **5.000** | `12.74 ms` | `51.97 ms` | **`64.71 ms`** |

### B. Rendimiento End-to-End en Odoo 16 + PostgreSQL (`Odo-Principal`)
| Cantidad de Puntos GPS | Inserción ORM/BD (ms) | Análisis de Incidencias (`action_analyze_trip`) | Cálculo 12 Métricas (`action_compute_all_metrics`) | Tiempo Total (ms) |
| :---: | :---: | :---: | :---: | :---: |
| **100** | `21.08 ms` | `11.76 ms` | `21.03 ms` | **`53.88 ms`** |
| **1.000** | `162.88 ms` | `55.47 ms` | `16.63 ms` | **`234.98 ms`** |
| **5.000** | `815.23 ms` | `257.76 ms` | `56.01 ms` | **`1.129,00 ms`** |

> **Interpretación (ISO/IEC 25010 — Eficiencia de Desempeño):** El sistema escala de forma lineal ($O(n)$). Un recorrido universitario típico de 30 minutos a 1 punto cada 5 segundos genera ~360 puntos GPS, procesándose completo (inserción + análisis + métricas) en **~100 ms**; incluso bajo estrés de **5.000 puntos** (más de 6 horas continuas de telemetría), el análisis de incidencias tarda solo **257.76 ms** y el cálculo global de métricas **56.01 ms**.


---

## 3. Resultados de Análisis Estático con SonarQube (`sonarqube:lts-community`)

- **Proyecto analizado:** `addons/fleet_traccar` (`uta-fleet-traccar-odoo`)
- **Dashboard local:** `http://localhost:9000/dashboard?id=uta-fleet-traccar-odoo` (usuario `admin` / `admin`)

| Métrica SonarQube | Resultado Inicial | Resultado Final (Post-Ajuste) | Calificación |
| :--- | :---: | :---: | :---: |
| **Quality Gate** | **PASSED (`OK`)** | **PASSED (`OK`)** | ✅ Aprobado |
| **Líneas de Código (`ncloc`)** | `7.017` | `7.017` | — |
| **Vulnerabilidades** | `0` | `0` | **A** |
| **Bugs** | `1` *(falso positivo `python:S905` en `__manifest__.py`)* | **`0`** | **A** (subió de C → A) |
| **Security Hotspots** | `4` | `4` | Revisión recomendada |
| **Code Smells** | `40` | `40` | **A** (Mantenibilidad) |
| **Duplicación de Código** | `0.0%` | `0.0%` | **Óptimo** |

---

## 4. Conectividad Externa mediante Cloudflare Tunnel (`cloudflared`)

- **Servicio Docker:** `traccar-cloudflared` agregado en `Tracar_Odoo/docker-compose.yml` apuntando a `http://traccar:5055`.
- **URL Pública HTTPS activa:** `https://spin-operate-lexmark-statutory.trycloudflare.com`
- **Verificación externa:** Petición OsmAnd enviada por Internet hacia el túnel HTTPS respondió directamente desde el puerto `5055` de Traccar (`HTTP 400` para IMEI no registrado, confirmando entrega extremo a extremo sin requerir Wi-Fi local ni IP pública fija).
