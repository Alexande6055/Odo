# -*- coding: utf-8 -*-
"""
Script de Generación y Ejecución de los 10 Recorridos de Prueba Documentados
para el Proyecto Final de Gestión de Calidad de Software (Odoo 16 + Traccar).
"""
from datetime import datetime, timedelta

def run_simulation(env):
    print("=== INICIANDO CONFIGURACIÓN Y EJECUCIÓN DE LOS 10 RECORRIDOS ===")

    # 1. Asegurar al menos 2 vehículos de prueba
    Fleet = env['fleet.vehicle']
    Model = env['fleet.vehicle.model']
    Brand = env['fleet.vehicle.model.brand']

    brand = Brand.search([('name', '=', 'Hino')], limit=1)
    if not brand:
        brand = Brand.create({'name': 'Hino'})

    model = Model.search([('name', '=', 'Bus Urbano AK')], limit=1)
    if not model:
        model = Model.create({'name': 'Bus Urbano AK', 'brand_id': brand.id})

    v1 = Fleet.search([('license_plate', '=', 'TBA-1001')], limit=1)
    if not v1:
        v1 = Fleet.create({
            'model_id': model.id,
            'license_plate': 'TBA-1001',
            'gps_imei': '8632940401001',
            'traccar_device_id': 101,
            'traccar_status': 'online',
        })
    print(f"-> Vehículo 1: {v1.display_name} (IMEI: {v1.gps_imei})")

    v2 = Fleet.search([('license_plate', '=', 'TBA-2002')], limit=1)
    if not v2:
        v2 = Fleet.create({
            'model_id': model.id,
            'license_plate': 'TBA-2002',
            'gps_imei': '8632940402002',
            'traccar_device_id': 102,
            'traccar_status': 'online',
        })
    print(f"-> Vehículo 2: {v2.display_name} (IMEI: {v2.gps_imei})")

    # 2. Obtener las 3 rutas
    Route = env['transport.route']
    r1 = Route.search([('code', '=', 'UTA-R01')], limit=1)
    r2 = Route.search([('code', '=', 'UTA-R02')], limit=1)
    r3 = Route.search([('code', '=', 'UTA-R03')], limit=1)

    if not (r1 and r2 and r3):
        print("ERROR: Rutas no encontradas.")
        return

    # Limpiar viajes simulados anteriores para idempotencia
    Trip = env['transport.trip']
    old_trips = Trip.search([('name', 'like', 'VIAJE/SIM/%')])
    if old_trips:
        old_trips.unlink()
        print(f"-> Eliminados {len(old_trips)} viajes anteriores de prueba.")

    # Definición de los 10 escenarios requeridos por la Rúbrica
    # Fecha base: Hoy
    base_date = datetime.now().date()
    today_dt = datetime.combine(base_date, datetime.min.time())

    scenarios = [
        # 1. Ruta 1 - Bus 1: Normal y Puntual (Conforme)
        {
            'name': 'VIAJE/SIM/0001',
            'route': r1,
            'vehicle': v1,
            'start_h': 7, 'start_m': 0,
            'expected_duration': 25,
            'scenario': 'compliant',
            'notes': 'Recorrido 1 (Ruta 1): Conforme y puntual. Cumplió las 4 paradas a tiempo sin desvíos.'
        },
        # 2. Ruta 1 - Bus 2: Con Retraso por congestión
        {
            'name': 'VIAJE/SIM/0002',
            'route': r1,
            'vehicle': v2,
            'start_h': 8, 'start_m': 0,
            'expected_duration': 25,
            'scenario': 'delay',
            'delay_minutes': 14,
            'notes': 'Recorrido 2 (Ruta 1): Con retraso de 14 min por tráfico pesado en Av. Atahualpa.'
        },
        # 3. Ruta 1 - Bus 1: Parada Omitida
        {
            'name': 'VIAJE/SIM/0003',
            'route': r1,
            'vehicle': v1,
            'start_h': 9, 'start_m': 30,
            'expected_duration': 25,
            'scenario': 'missed_stop',
            'missed_stop_index': 2, # Parada 3 (Parque Cevallos)
            'notes': 'Recorrido 3 (Ruta 1): Parada Parque Cevallos omitida por cierre temporal de vía.'
        },
        # 4. Ruta 2 - Bus 2: Normal y Puntual (Conforme)
        {
            'name': 'VIAJE/SIM/0004',
            'route': r2,
            'vehicle': v2,
            'start_h': 7, 'start_m': 15,
            'expected_duration': 35,
            'scenario': 'compliant',
            'notes': 'Recorrido 4 (Ruta 2): Conforme intercampus Querochaca con velocidad estable de 45 km/h.'
        },
        # 5. Ruta 2 - Bus 1: Desviación de Ruta
        {
            'name': 'VIAJE/SIM/0005',
            'route': r2,
            'vehicle': v1,
            'start_h': 11, 'start_m': 0,
            'expected_duration': 35,
            'scenario': 'deviation',
            'notes': 'Recorrido 5 (Ruta 2): Desvío a 380m del corredor oficial por trabajo de asfaltado.'
        },
        # 6. Ruta 2 - Bus 2: Con Retraso Significativo
        {
            'name': 'VIAJE/SIM/0006',
            'route': r2,
            'vehicle': v2,
            'start_h': 13, 'start_m': 0,
            'expected_duration': 35,
            'scenario': 'delay',
            'delay_minutes': 18,
            'notes': 'Recorrido 6 (Ruta 2): Retraso de 18 min en Panamericana Sur.'
        },
        # 7. Ruta 3 - Bus 1: Normal y Puntual (Conforme)
        {
            'name': 'VIAJE/SIM/0007',
            'route': r3,
            'vehicle': v1,
            'start_h': 8, 'start_m': 30,
            'expected_duration': 20,
            'scenario': 'compliant',
            'notes': 'Recorrido 7 (Ruta 3): Circuito Ficoa-Huachi fluido y a tiempo.'
        },
        # 8. Ruta 3 - Bus 2: Desviación de Ruta + Retraso
        {
            'name': 'VIAJE/SIM/0008',
            'route': r3,
            'vehicle': v2,
            'start_h': 12, 'start_m': 15,
            'expected_duration': 20,
            'scenario': 'deviation_delay',
            'delay_minutes': 9,
            'notes': 'Recorrido 8 (Ruta 3): Desvío en Parque de las Flores y retraso de 9 minutos.'
        },
        # 9. Ruta 3 - Bus 1: Interrupción / Pérdida de señal GPS
        {
            'name': 'VIAJE/SIM/0009',
            'route': r3,
            'vehicle': v1,
            'start_h': 15, 'start_m': 0,
            'expected_duration': 20,
            'scenario': 'gps_lost',
            'notes': 'Recorrido 9 (Ruta 3): Pérdida de conectividad GPS durante 15 minutos.'
        },
        # 10. Ruta 1 - Bus 2: Incidencias Múltiples (Parada omitida + Retraso)
        {
            'name': 'VIAJE/SIM/0010',
            'route': r1,
            'vehicle': v2,
            'start_h': 17, 'start_m': 0,
            'expected_duration': 25,
            'scenario': 'multi_incident',
            'delay_minutes': 12,
            'missed_stop_index': 1, # Mall de los Andes
            'notes': 'Recorrido 10 (Ruta 1): Congestión pico vespertina, retraso de 12 min y omisión de parada Mall.'
        },
    ]

    trips_created = []

    for sc in scenarios:
        route = sc['route']
        vehicle = sc['vehicle']
        sched_start = today_dt.replace(hour=sc['start_h'], minute=sc['start_m'])
        sched_end = sched_start + timedelta(minutes=sc['expected_duration'])

        actual_delay = sc.get('delay_minutes', 0)
        actual_start = sched_start + timedelta(minutes=2 if actual_delay > 0 else 0)
        actual_end = sched_end + timedelta(minutes=actual_delay)

        trip = Trip.create({
            'name': sc['name'],
            'vehicle_id': vehicle.id,
            'route_id': route.id,
            'date': base_date,
            'scheduled_start_time': sched_start,
            'scheduled_end_time': sched_end,
            'actual_start_time': actual_start,
            'actual_end_time': actual_end,
            'state': 'completed',
            'notes': sc['notes'],
        })

        # Generar puntos GPS sintéticos consistentes
        stops = route.stop_ids.sorted('sequence')
        points = []
        cur_time = actual_start
        step_minutes = 2.0

        for idx, stop in enumerate(stops):
            # Si el escenario es omitir esta parada, desviamos el punto a 300m
            is_missed = (sc['scenario'] in ('missed_stop', 'multi_incident') and idx == sc.get('missed_stop_index'))
            
            if is_missed:
                # Coordenada desviada de la parada
                p_lat = stop.latitude + 0.0030
                p_lon = stop.longitude + 0.0030
            else:
                p_lat = stop.latitude
                p_lon = stop.longitude

            # Puntos intermedios hacia la parada
            cur_time += timedelta(minutes=3)
            points.append((0, 0, {
                'vehicle_id': vehicle.id,
                'latitude': p_lat,
                'longitude': p_lon,
                'speed': 35.0,
                'timestamp': cur_time,
                'is_valid': True,
                'traccar_position_id': 1000 + len(points),
            }))

            # Si es desvío forzado en este trayecto
            if 'deviation' in sc['scenario'] and idx == 1:
                cur_time += timedelta(minutes=2)
                points.append((0, 0, {
                    'vehicle_id': vehicle.id,
                    'latitude': stop.latitude + 0.0045, # ~500m fuera
                    'longitude': stop.longitude + 0.0045,
                    'speed': 28.0,
                    'timestamp': cur_time,
                    'is_valid': True,
                    'traccar_position_id': 1000 + len(points),
                }))

            # Si es pérdida de señal GPS
            if sc['scenario'] == 'gps_lost' and idx == 1:
                cur_time += timedelta(minutes=16) # Salto de 16 min sin reportar

        trip.write({
            'point_ids': points,
            'actual_distance': round(route.estimated_distance * (1.15 if 'deviation' in sc['scenario'] else 1.0), 2)
        })

        # Ejecutar análisis automático de reglas en el viaje
        trip.action_analyze_trip()
        trips_created.append(trip)
        print(f"-> {trip.name} [{route.code} - {vehicle.license_plate}]: Evaluado como '{trip.compliance_status}', Incidencias: {trip.incident_count}")

    # 3. Generar y calcular el Dashboard Global de Métricas
    Summary = env['transport.metrics.summary']
    summary = Summary.create({
        'name': f'Auditoría Oficial del Sistema de Transporte UTA - {base_date}',
        'date_from': base_date,
        'date_to': base_date,
    })
    summary.action_compute_all_metrics()

    print("\n================ RESULTADOS DE LA AUDITORÍA DE MÉTRICAS ================")
    print(f"Total Recorridos Analizados: {summary.total_trips}")
    print(f"1. % Cumplimiento de Rutas: {summary.m1_route_compliance_rate}%")
    print(f"2. % Puntualidad: {summary.m2_punctuality_rate}%")
    print(f"3. Retraso Promedio: {summary.m3_avg_delay_minutes} minutos")
    print(f"4. % Paradas Cumplidas: {summary.m4_stops_compliance_rate}%")
    print(f"5. % Desviación de Ruta: {summary.m5_deviation_rate}%")
    print(f"6. Diferencia Media Distancia: {summary.m6_avg_distance_diff} km")
    print(f"7. Tiempo Promedio de Recorrido: {summary.m7_avg_duration_minutes} min")
    print(f"8. Total Incidencias: {summary.m8_total_incidents} (Frecuencia: {summary.m8_incident_frequency} inc/viaje)")
    print("------------------------------------------------------------------------")
    print(f"CS1. Integridad de Registros GPS: {summary.cs1_gps_integrity_rate}%")
    print(f"CS2. Exactitud Sincronización Traccar-Odoo: {summary.cs2_sync_accuracy_rate}%")
    print(f"CS3. Latencia del Sistema: {summary.cs3_response_time_ms} ms")
    print(f"CS4. Precisión de Detección: {summary.cs4_incident_detection_accuracy}%")
    print("========================================================================\n")
    print("¡10 Recorridos de prueba y métricas creados con éxito!")

if __name__ == '__main__':
    pass

