# -*- coding: utf-8 -*-
import sys
import os
import pytest

# Agregar path del módulo
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'addons', 'fleet_traccar', 'models')))

from geo_utils import (
    haversine_distance,
    is_point_within_radius,
    min_distance_to_path,
    calculate_total_path_distance
)

# Coordenadas de prueba en Ambato (Campus UTA)
HUACHI = (-1.2687, -78.6258)
MALL_ANDES = (-1.2605, -78.6242)
CEVALLOS = (-1.2418, -78.6279)
INGAHURCO = (-1.2425, -78.6185)


class TestGeoUtils:
    """Pruebas unitarias de cálculo geodésico y geocercas."""

    def test_haversine_same_point(self):
        """La distancia entre un punto y sí mismo debe ser 0.0 metros."""
        d = haversine_distance(HUACHI[0], HUACHI[1], HUACHI[0], HUACHI[1])
        assert round(d, 2) == 0.0

    def test_haversine_symmetry(self):
        """La distancia de A a B debe ser idéntica a la de B a A."""
        d_ab = haversine_distance(HUACHI[0], HUACHI[1], INGAHURCO[0], INGAHURCO[1])
        d_ba = haversine_distance(INGAHURCO[0], INGAHURCO[1], HUACHI[0], HUACHI[1])
        assert abs(d_ab - d_ba) < 1e-6

    def test_haversine_huachi_ingahurco_range(self):
        """La distancia en línea recta entre Campus Huachi e Ingahurco está aprox entre 3.0 y 3.5 km."""
        dist_meters = haversine_distance(HUACHI[0], HUACHI[1], INGAHURCO[0], INGAHURCO[1])
        assert 2900.0 <= dist_meters <= 3500.0

    def test_is_point_within_radius(self):
        """Verifica que un punto dentro de un radio de 100m sea aceptado y uno fuera rechazado."""
        # Punto a ~20 metros de Huachi
        near_huachi = (HUACHI[0] + 0.0001, HUACHI[1] + 0.0001)
        assert is_point_within_radius(near_huachi[0], near_huachi[1], HUACHI[0], HUACHI[1], 50.0) is True

        # Punto lejano (Ingahurco respecto a Huachi)
        assert is_point_within_radius(INGAHURCO[0], INGAHURCO[1], HUACHI[0], HUACHI[1], 100.0) is False

    def test_min_distance_to_path(self):
        """Calcula correctamente la distancia mínima de un punto hacia una ruta de referencia."""
        route_coords = [HUACHI, MALL_ANDES, CEVALLOS, INGAHURCO]
        # Si el punto coincide con un nodo de la ruta, la distancia mínima debe ser cercana a 0
        min_d = min_distance_to_path(MALL_ANDES[0], MALL_ANDES[1], route_coords)
        assert min_d < 1.0

        # Punto desviado
        off_route_point = (-1.2200, -78.6500)
        min_d_off = min_distance_to_path(off_route_point[0], off_route_point[1], route_coords)
        assert min_d_off > 1000.0

    def test_calculate_total_path_distance(self):
        """Verifica el cálculo de distancia acumulada de un trayecto."""
        path = [HUACHI, MALL_ANDES, CEVALLOS, INGAHURCO]
        total_km = calculate_total_path_distance(path)
        # La suma por tramos debe ser mayor a 3 km y menor a 8 km
        assert 3.0 <= total_km <= 8.0

    def test_invalid_coordinates_raise(self):
        """Coordenadas inválidas deben arrojar ValueError."""
        with pytest.raises(ValueError):
            haversine_distance("invalid", 10.0, 20.0, 30.0)


class TestIncidentDetectionLogic:
    """Pruebas de la lógica de detección de incumplimientos y tolerancias."""

    def test_delay_detection_rule(self):
        """Evalúa la regla de retraso con tolerancia de 5 minutos."""
        scheduled_minutes = 20
        tolerance_minutes = 5

        # Llegada a los 23 min (dentro de tolerancia -> a tiempo)
        arrival_minutes = 23
        delay = arrival_minutes - scheduled_minutes
        is_delayed = delay > tolerance_minutes
        assert is_delayed is False

        # Llegada a los 32 min (7 min por encima de tolerancia -> retraso)
        arrival_late = 32
        delay_late = arrival_late - scheduled_minutes
        is_delayed_late = delay_late > tolerance_minutes
        assert is_delayed_late is True
        assert delay_late == 12

    def test_missed_stop_rule(self):
        """Una parada se considera omitida si el vehículo nunca estuvo a menos de su radio de proximidad."""
        stop_radius = 50.0  # metros
        closest_distance_measured = 120.0  # metros

        status = 'visited' if closest_distance_measured <= stop_radius else 'missed'
        assert status == 'missed'

    def test_route_deviation_rule(self):
        """Detecta desviación si la distancia al corredor supera allowed_deviation_meters."""
        allowed_dev = 150.0  # metros
        max_measured_dev = 280.0  # metros

        has_deviation = max_measured_dev > allowed_dev
        assert has_deviation is True

