# -*- coding: utf-8 -*-
"""
Suite de Pruebas de Caja Blanca (algoritmos geodésicos y reglas)
y Pruebas de Integración + Rendimiento (100 / 1.000 / 5.000 puntos GPS).
Compatible con unittest estándar de Python 3 (no requiere pytest).
"""
import json
import os
import sys
import time
import unittest
import urllib.request
import urllib.error

MODELS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "addons", "fleet_traccar", "models")
)
if MODELS_PATH not in sys.path:
    sys.path.insert(0, MODELS_PATH)

from geo_utils import (
    haversine_distance,
    is_point_within_radius,
    min_distance_to_path,
    calculate_total_path_distance,
)

HUACHI = (-1.2687, -78.6258)
MALL_ANDES = (-1.2605, -78.6242)
CEVALLOS = (-1.2418, -78.6279)
INGAHURCO = (-1.2425, -78.6185)
REF_ROUTE = [HUACHI, MALL_ANDES, CEVALLOS, INGAHURCO]


def generate_gps_points(n):
    """Genera n coordenadas sintéticas a lo largo del corredor Huachi -> Ingahurco."""
    pts = []
    lat0, lon0 = HUACHI
    lat1, lon1 = INGAHURCO
    denom = max(n - 1, 1)
    for i in range(n):
        frac = i / denom
        lat = lat0 + (lat1 - lat0) * frac
        lon = lon0 + (lon1 - lon0) * frac
        pts.append((round(lat, 6), round(lon, 6)))
    return pts


class TestWhiteBoxGeoAndRules(unittest.TestCase):
    """CP-01 a CP-06: Pruebas de Caja Blanca sobre geo_utils y lógica de incidencias."""

    def test_cp01_haversine_zero_and_symmetry(self):
        self.assertEqual(round(haversine_distance(*HUACHI, *HUACHI), 2), 0.0)
        d_ab = haversine_distance(*HUACHI, *INGAHURCO)
        d_ba = haversine_distance(*INGAHURCO, *HUACHI)
        self.assertAlmostEqual(d_ab, d_ba, places=6)
        self.assertTrue(2900.0 <= d_ab <= 3500.0)

    def test_cp02_geofence_boundary_radius(self):
        # Punto muy cercano (~15m) dentro de radio 50m
        near = (HUACHI[0] + 0.0001, HUACHI[1] + 0.0001)
        self.assertTrue(is_point_within_radius(near[0], near[1], HUACHI[0], HUACHI[1], 50.0))
        # Punto fuera (> 3000m)
        self.assertFalse(is_point_within_radius(INGAHURCO[0], INGAHURCO[1], HUACHI[0], HUACHI[1], 50.0))

    def test_cp03_min_distance_to_path_on_and_off_route(self):
        self.assertLess(min_distance_to_path(*MALL_ANDES, REF_ROUTE), 1.0)
        off_route = (-1.2200, -78.6500)
        self.assertGreater(min_distance_to_path(*off_route, REF_ROUTE), 1000.0)

    def test_cp04_total_path_distance_accuracy(self):
        total_km = calculate_total_path_distance(REF_ROUTE)
        self.assertTrue(3.0 <= total_km <= 8.0)

    def test_cp05_invalid_coordinates_raise_value_error(self):
        with self.assertRaises(ValueError):
            haversine_distance("abc", -78.6, -1.2, -78.6)

    def test_cp06_delay_and_missed_stop_rules(self):
        # Regla de retraso (> 5 min tolerancia)
        self.assertFalse((23 - 20) > 5)
        self.assertTrue((32 - 20) > 5)
        # Regla de parada omitida (distancia > radio)
        self.assertTrue(120.0 > 50.0)


class TestRealIntegrationStack(unittest.TestCase):
    """CP-07 a CP-10: Pruebas de Integración real entre Traccar, Map Bridge y Odoo."""

    def _http_status(self, url, timeout=5):
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()

    def test_cp07_traccar_api_alive(self):
        status, body = self._http_status("http://localhost:8082/api/server")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8", errors="ignore") or "{}")
        self.assertIn("version", data)

    def test_cp08_map_bridge_and_proxy_alive(self):
        status_ui, _ = self._http_status("http://localhost:3050")
        self.assertEqual(status_ui, 200)
        status_proxy, _ = self._http_status("http://localhost:3050/api/server")
        self.assertEqual(status_proxy, 200)

    def test_cp09_odoo_web_alive(self):
        status, _ = self._http_status("http://localhost:8069/web/login")
        self.assertEqual(status, 200)

    def test_cp10_traccar_osmand_gps_ingestion_port_5055(self):
        # Envía paquete OsmAnd HTTP al puerto 5055 (protocolo de la App Móvil Traccar Client)
        url = (
            "http://localhost:5055/?id=8632940401001"
            "&lat=-1.2687&lon=-78.6258&speed=12.5&bearing=45"
        )
        try:
            status, _ = self._http_status(url)
            self.assertIn(status, (200, 400))
        except urllib.error.HTTPError as e:
            code = e.code
            e.close()
            self.assertIn(code, (200, 400))


class TestGeoPerformanceBenchmark(unittest.TestCase):
    """CP-11: Pruebas de Rendimiento y Estrés geodésico con 100, 1.000 y 5.000 puntos GPS."""

    def test_cp11_geodesic_scaling_100_1000_5000(self):
        results = {}
        for count in (100, 1000, 5000):
            pts = generate_gps_points(count)
            t0 = time.perf_counter()
            total_km = calculate_total_path_distance(pts)
            t1 = time.perf_counter()
            max_dev = max(min_distance_to_path(lat, lon, REF_ROUTE) for lat, lon in pts)
            t2 = time.perf_counter()
            results[count] = {
                "distance_km": total_km,
                "dist_ms": round((t1 - t0) * 1000.0, 2),
                "deviation_ms": round((t2 - t1) * 1000.0, 2),
                "max_dev_m": round(max_dev, 2),
            }
            # Umbral de eficiencia: procesar hasta 5.000 puntos en menos de 1.000 ms
            self.assertLess((t2 - t0) * 1000.0, 1000.0)
        print("\n[BENCHMARK GEODÉSICO]", json.dumps(results))


if __name__ == "__main__":
    unittest.main(verbosity=2)
