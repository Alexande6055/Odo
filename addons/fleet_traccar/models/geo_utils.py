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


def get_configured_map_web_url(env=None) -> str:
    """
    Obtiene la URL del microservicio web de mapas (React / Vite).
    Prioridad:
    1. Variables de entorno (MAP_WEB_URL o MAP_WEB_PORT)
    2. Archivo .env (/etc/odoo/.env, /mnt/extra-addons/../.env, o raíz)
    3. Parámetro de sistema en Odoo (fleet_traccar.map_url)
    4. Valor por defecto: http://localhost:30001
    """
    import os
    from pathlib import Path

    # 1. Variables de entorno en el SO / contenedor
    env_url = os.environ.get('MAP_WEB_URL')
    if env_url:
        return env_url.strip().rstrip('/')

    env_port = os.environ.get('MAP_WEB_PORT')
    if env_port:
        return f"http://localhost:{env_port.strip()}".rstrip('/')

    # 2. Leer archivo .env si existe en las rutas conocidas
    env_paths = [
        Path('/mnt/extra-addons/.env'),
        Path('/mnt/extra-addons/fleet_traccar/.env'),
        Path('/etc/odoo/.env'),
        Path('/home/alexander/MEGA/Documentos/Gestion de Clidad/Odo/.env'),
        Path('.env'),
    ]
    for p in env_paths:
        try:
            if p.exists():
                with open(p, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k == 'MAP_WEB_URL' and v:
                                return v.rstrip('/')
                            elif k == 'MAP_WEB_PORT' and v:
                                return f"http://localhost:{v}".rstrip('/')
        except Exception:
            pass

    # 3. Parámetro ir.config_parameter en base de datos si se provee env
    if env:
        try:
            icp_url = env['ir.config_parameter'].sudo().get_param('fleet_traccar.map_url')
            if icp_url:
                return icp_url.strip().rstrip('/')
        except Exception:
            pass

    # 4. Fallback por defecto según requerimiento
    return 'http://localhost:30001'


