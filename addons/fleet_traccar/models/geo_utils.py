# -*- coding: utf-8 -*-
import math

# Radio medio de la Tierra en metros
EARTH_RADIUS_METERS = 6371000.0

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula la distancia geodésica del gran círculo entre dos puntos en la Tierra
    utilizando la fórmula de Haversine.

    :param lat1: Latitud del primer punto en grados decimales.
    :param lon1: Longitud del primer punto en grados decimales.
    :param lat2: Latitud del segundo punto en grados decimales.
    :param lon2: Longitud del segundo punto en grados decimales.
    :return: Distancia en metros entre ambos puntos.
    """
    if not all(isinstance(v, (int, float)) for v in [lat1, lon1, lat2, lon2]):
        raise ValueError("Las coordenadas deben ser números válidos.")

    # Convertir de grados decimales a radianes
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)

    # Clamping a [0, 1] para evitar errores por redondeo de coma flotante
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return EARTH_RADIUS_METERS * c


def is_point_within_radius(point_lat: float, point_lon: float,
                           target_lat: float, target_lon: float,
                           radius_meters: float) -> bool:
    """
    Determina si un punto se encuentra dentro de un radio geocercado respecto a un objetivo.
    """
    distance = haversine_distance(point_lat, point_lon, target_lat, target_lon)
    return distance <= radius_meters


def min_distance_to_path(point_lat: float, point_lon: float,
                         path_coords: list) -> float:
    """
    Calcula la distancia mínima en metros entre un punto y una serie de puntos
    que representan el trazado oficial de una ruta.
    :param path_coords: Lista de tuplas o listas [(lat, lon), ...]
    :return: Distancia mínima en metros al punto más cercano de la ruta.
    """
    if not path_coords:
        return 0.0

    min_dist = float('inf')
    for coord in path_coords:
        if len(coord) >= 2:
            d = haversine_distance(point_lat, point_lon, coord[0], coord[1])
            if d < min_dist:
                min_dist = d
    return min_dist if min_dist != float('inf') else 0.0


def calculate_total_path_distance(points: list) -> float:
    """
    Calcula la distancia acumulada total en kilómetros de una lista de puntos GPS [(lat, lon), ...].
    """
    if len(points) < 2:
        return 0.0

    total_meters = 0.0
    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]
        total_meters += haversine_distance(p1[0], p1[1], p2[0], p2[1])

    return round(total_meters / 1000.0, 3)


def get_effective_traccar_url(url: str) -> str:
    """
    En entornos de desarrollo con Docker / localhost, si la URL configurada
    en Odoo apunta a localhost o 127.0.0.1, el contenedor Odoo debe resolverla
    hacia la pasarela del host (172.17.0.1) o al contenedor 'traccar' para que
    las peticiones backend funcionen mientras el navegador del usuario sigue
    usando 'http://localhost:8082'.
    """
    if not url:
        return url
    import urllib.parse
    import requests
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname in ('localhost', '127.0.0.1'):
        # 1. Probar pasarela Docker estándar (172.17.0.1)
        gateway_url = urllib.parse.urlunparse(parsed._replace(netloc=parsed.netloc.replace(parsed.hostname, '172.17.0.1')))
        try:
            r = requests.get(f"{gateway_url}/api/server", timeout=1)
            if r.status_code == 200:
                return gateway_url
        except Exception:
            pass

        # 2. Probar contenedor interno 'traccar'
        port = parsed.port or 8082
        traccar_url = urllib.parse.urlunparse(parsed._replace(netloc=f"traccar:{port}"))
        try:
            r = requests.get(f"{traccar_url}/api/server", timeout=1)
            if r.status_code == 200:
                return traccar_url
        except Exception:
            pass

        return gateway_url
    return url

