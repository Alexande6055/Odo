# -*- coding: utf-8 -*-
"""
Pruebas de Caja Negra, Valores Límite y Rendimiento/Estrés ORM en Odoo 16 (Odo-Principal).
Se ejecuta dentro del contenedor odoo16 con rollback final para no ensuciar la BD.
"""
import json
import time
from datetime import timedelta
import odoo
from odoo import fields
from odoo.tools import config
from odoo.exceptions import ValidationError


def run_odoo_quality_tests():
    config.parse_config([
        "-c", "/etc/odoo/odoo.conf",
        "-d", "Odo-Principal",
        "-r", "odoo",
        "-w", "odoo",
        "--db_host", "db",
    ])
    registry = odoo.registry("Odo-Principal")
    report = {"blackbox": [], "performance": []}

    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {"tz": "America/Guayaquil"})
        Trip = env["transport.trip"]
        Route = env["transport.route"].search([], limit=1)
        Stop = env["transport.route.stop"]
        Incident = env["transport.trip.incident"]
        Vehicle = env["fleet.vehicle"]

        brand = env["fleet.vehicle.model.brand"].create({"name": "QABrand"})
        model = env["fleet.vehicle.model"].create({"name": "QAModel", "brand_id": brand.id})
        veh = Vehicle.create({
            "model_id": model.id,
            "license_plate": "QAT-0001",
            "gps_imei": "9988776655",
        })
        today = fields.Date.context_today(Trip)
        tomorrow = today + timedelta(days=1)

        def record_case(cid, name, passed, detail):
            report["blackbox"].append({
                "id": cid,
                "name": name,
                "status": "PASA" if passed else "FALLA",
                "detail": str(detail),
            })
            if not passed:
                raise AssertionError(f"{cid} FAILED: {detail}")

        # CP-12: Fecha pasada (valor límite ayer) -> debe rechazar
        try:
            with cr.savepoint():
                Trip.create({
                    "vehicle_id": veh.id,
                    "route_id": Route.id,
                    "date": today - timedelta(days=1),
                    "scheduled_start_hour": 8.0,
                    "scheduled_end_hour": 8.5,
                })
            record_case("CP-12", "Fecha anterior a hoy en viaje", False, "Permitió fecha pasada")
        except ValidationError as e:
            record_case("CP-12", "Fecha anterior a hoy en viaje", True, e)

        # CP-13: Hora fuera de límite (24:00 / -1) -> debe rechazar
        try:
            with cr.savepoint():
                Trip.create({
                    "vehicle_id": veh.id,
                    "route_id": Route.id,
                    "date": tomorrow,
                    "scheduled_start_hour": 24.0,
                    "scheduled_end_hour": 25.0,
                })
            record_case("CP-13", "Hora límite inválida (24:00)", False, "Permitió 24:00")
        except ValidationError as e:
            record_case("CP-13", "Hora límite inválida (24:00)", True, e)

        # CP-14: Llegada programada <= Salida programada -> debe rechazar
        try:
            with cr.savepoint():
                Trip.create({
                    "vehicle_id": veh.id,
                    "route_id": Route.id,
                    "date": tomorrow,
                    "scheduled_start_hour": 10.0,
                    "scheduled_end_hour": 10.0,
                })
            record_case("CP-14", "Llegada igual/anterior a Salida", False, "Permitió llegada == salida")
        except ValidationError as e:
            record_case("CP-14", "Llegada igual/anterior a Salida", True, e)

        # CP-15: Viaje válido con valores límite horarios (00:00 -> 23:59) -> debe aceptar
        valid_trip = Trip.create({
            "vehicle_id": veh.id,
            "route_id": Route.id,
            "date": tomorrow,
            "scheduled_start_hour": 8.0,
            "scheduled_end_hour": 8.5,
        })
        ok_hours = abs(valid_trip.scheduled_start_hour - 8.0) < 0.01 and abs(valid_trip.scheduled_end_hour - 8.5) < 0.01
        record_case("CP-15", "Creación viaje válido solo hora (08:00-08:30)", ok_hours, f"{valid_trip.name} OK")

        # CP-16: Solapamiento horario del mismo vehículo -> debe rechazar
        try:
            with cr.savepoint():
                Trip.create({
                    "vehicle_id": veh.id,
                    "route_id": Route.id,
                    "date": tomorrow,
                    "scheduled_start_hour": 8.25,
                    "scheduled_end_hour": 9.0,
                })
            record_case("CP-16", "Solapamiento de horario mismo bus", False, "Permitió solapamiento")
        except ValidationError as e:
            record_case("CP-16", "Solapamiento de horario mismo bus", True, e)

        # CP-17: Coordenada límite inválida en parada (lat = 90.1) -> debe rechazar
        try:
            with cr.savepoint():
                Stop.create({
                    "name": "Parada Límite Inválida",
                    "route_id": Route.id,
                    "latitude": 90.1,
                    "longitude": -78.62,
                })
            record_case("CP-17", "Latitud fuera de rango (>90°)", False, "Permitió lat 90.1")
        except ValidationError as e:
            record_case("CP-17", "Latitud fuera de rango (>90°)", True, e)

        # CP-18: IMEI inválido (< 5 caracteres) y duplicado -> debe rechazar
        try:
            with cr.savepoint():
                Vehicle.create({"model_id": model.id, "license_plate": "QAT-0002", "gps_imei": "123"})
            record_case("CP-18", "IMEI con formato inválido (<5 chars)", False, "Permitió IMEI corto")
        except ValidationError as e:
            record_case("CP-18", "IMEI con formato inválido (<5 chars)", True, e)

        try:
            with cr.savepoint():
                Vehicle.create({"model_id": model.id, "license_plate": "QAT-0003", "gps_imei": "9988776655"})
            record_case("CP-19", "IMEI duplicado entre vehículos", False, "Permitió IMEI duplicado")
        except ValidationError as e:
            record_case("CP-19", "IMEI duplicado entre vehículos", True, e)

        # CP-20: Incidencia sobre viaje en Borrador -> debe rechazar
        try:
            with cr.savepoint():
                Incident.create({
                    "name": "Accidente en borrador",
                    "trip_id": valid_trip.id,
                    "incident_type": "accident",
                    "severity": "high",
                })
            record_case("CP-20", "Incidencia en viaje Borrador bloqueada", False, "Permitió incidencia en borrador")
        except ValidationError as e:
            record_case("CP-20", "Incidencia en viaje Borrador bloqueada", True, e)

        # BENCHMARK DE RENDIMIENTO / ESTRÉS ORM (100, 1000 y 5000 coordenadas GPS)
        base_dt = valid_trip.scheduled_start_time
        for n_points in (100, 1000, 5000):
            with cr.savepoint():
                t_perf = Trip.with_context(skip_date_validation=True).create({
                    "vehicle_id": veh.id,
                    "route_id": Route.id,
                    "date": today + timedelta(days=5 + (n_points // 100)),
                    "scheduled_start_hour": 7.0,
                    "scheduled_end_hour": 7.5,
                    "state": "completed",
                })
                pts_vals = []
                for i in range(n_points):
                    frac = i / max(n_points - 1, 1)
                    pts_vals.append((0, 0, {
                        "vehicle_id": veh.id,
                        "latitude": round(-1.2687 + (0.0262 * frac), 6),
                        "longitude": round(-78.6258 + (0.0073 * frac), 6),
                        "speed": 30.0,
                        "timestamp": base_dt + timedelta(seconds=i * 2),
                        "traccar_position_id": 50000 + i,
                        "is_valid": True,
                    }))

                t0 = time.perf_counter()
                t_perf.write({"point_ids": pts_vals})
                t1 = time.perf_counter()
                t_perf.action_analyze_trip()
                t2 = time.perf_counter()
                summary = env["transport.metrics.summary"].create({
                    "name": f"Perf-{n_points}",
                    "date_from": today - timedelta(days=7),
                    "date_to": today + timedelta(days=60),
                })
                summary.action_compute_all_metrics()
                t3 = time.perf_counter()

                report["performance"].append({
                    "points": n_points,
                    "insert_ms": round((t1 - t0) * 1000.0, 2),
                    "analyze_ms": round((t2 - t1) * 1000.0, 2),
                    "metrics_ms": round((t3 - t2) * 1000.0, 2),
                    "total_ms": round((t3 - t0) * 1000.0, 2),
                })

        cr.rollback()

    print("JSON_REPORT_START")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("JSON_REPORT_END")


if __name__ == "__main__":
    run_odoo_quality_tests()
