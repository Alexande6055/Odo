# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class RouteEditorController(http.Controller):

    @http.route('/transport/route/map_editor/<int:route_id>', type='http', auth='user', methods=['GET'])
    def map_editor(self, route_id, **kwargs):
        """
        Renderiza el Diseñador Interactivo de Rutas en Leaflet.
        Permite hacer clic sobre el mapa para trazar la línea oficial por donde
        debe circular el bus, calcular distancias y registrar paradas.
        """
        route = request.env['transport.route'].browse(route_id)
        if not route.exists():
            return request.not_found()

        # Parsear coordenadas de trazado existentes
        existing_coords = []
        if route.reference_coordinates:
            try:
                parsed = json.loads(route.reference_coordinates)
                if isinstance(parsed, list):
                    existing_coords = parsed
            except Exception:
                existing_coords = []

        # Paradas de la ruta
        stops_list = []
        for s in route.stop_ids.sorted('sequence'):
            stops_list.append({
                'id': s.id,
                'name': s.name,
                'seq': s.sequence,
                'lat': s.latitude,
                'lon': s.longitude,
                'radius': s.proximity_radius or 50.0,
                'mandatory': s.is_mandatory,
            })

        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Diseñador de Ruta: {route.name}</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; height: 100vh; display: flex; flex-direction: column; background: #0f172a; color: #f8fafc; overflow: hidden; }}
        #toolbar {{
            background: #1e293b;
            padding: 10px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 10px;
            border-bottom: 1px solid #334155;
            z-index: 1000;
        }}
        .tool-group {{ display: flex; align-items: center; gap: 8px; }}
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 14px;
            font-size: 13px;
            font-weight: 600;
            border-radius: 8px;
            border: 1px solid transparent;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        .btn-primary {{ background: #2563eb; color: white; }}
        .btn-primary:hover {{ background: #1d4ed8; }}
        .btn-success {{ background: #059669; color: white; }}
        .btn-success:hover {{ background: #047857; }}
        .btn-outline {{ background: #334155; color: #e2e8f0; border-color: #475569; }}
        .btn-outline:hover {{ background: #475569; }}
        .btn-danger {{ background: #dc2626; color: white; }}
        .btn-danger:hover {{ background: #b91c1c; }}
        .btn-active {{ background: #3b82f6 !important; border-color: #60a5fa !important; box-shadow: 0 0 10px rgba(59,130,246,0.6); }}
        .badge {{ padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; background: #334155; color: #94a3b8; }}
        .badge-info {{ background: #0284c7; color: white; }}
        .badge-success {{ background: #10b981; color: white; }}
        .switch-container {{ display: flex; align-items: center; gap: 6px; font-size: 12px; color: #cbd5e1; user-select: none; cursor: pointer; }}
        #map {{ flex: 1; width: 100%; }}
        .toast-msg {{
            position: fixed;
            top: 65px;
            right: 20px;
            z-index: 2000;
            padding: 12px 18px;
            border-radius: 8px;
            color: white;
            font-size: 13px;
            font-weight: bold;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            display: none;
            animation: slideIn 0.3s ease;
        }}
        .toast-success {{ background: #059669; }}
        .toast-error {{ background: #dc2626; }}
        @keyframes slideIn {{ from {{ transform: translateX(100%); opacity: 0; }} to {{ transform: translateX(0); opacity: 1; }} }}
        .stop-marker-icon {{
            background: #10b981;
            color: white;
            font-weight: bold;
            font-size: 11px;
            border-radius: 50%;
            border: 2px solid white;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 6px rgba(0,0,0,0.4);
            width: 24px;
            height: 24px;
        }}
        .endpoint-icon {{
            width: 28px;
            height: 28px;
            border-radius: 50%;
            border: 3px solid white;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 12px;
            box-shadow: 0 3px 8px rgba(0,0,0,0.4);
        }}
        .start-point {{ background: #16a34a; }}
        .end-point {{ background: #dc2626; }}
        .waypoint-dot {{
            background: #2563eb;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            border: 1px solid white;
        }}
    </style>
</head>
<body>
    <div id="toolbar">
        <div class="tool-group">
            <span class="badge badge-info"><i class="fa fa-route me-1"></i>{route.code}</span>
            <span style="font-weight: bold; font-size: 13px;">{route.name}</span>
            <span class="badge"><i class="fa fa-shield me-1"></i>Desvío máx: {route.allowed_deviation_meters or 150}m</span>
        </div>

        <div class="tool-group">
            <button id="btnTrace" class="btn btn-outline btn-active" title="Haz clic en el mapa para ir marcando el trazado de la ruta">
                <i class="fa fa-pencil"></i> Trazar Ruta (Clic)
            </button>
            <label class="switch-container">
                <input type="checkbox" id="chkAutoRoute" checked style="cursor: pointer;">
                <span><i class="fa fa-road"></i> Seguir Calles (Auto)</span>
            </label>
            <button id="btnAddStop" class="btn btn-outline" title="Haz clic en el mapa para registrar una parada oficial">
                <i class="fa fa-flag"></i> Nueva Parada
            </button>
            <button id="btnUndo" class="btn btn-outline" title="Deshacer el último punto marcado">
                <i class="fa fa-undo"></i> Deshacer
            </button>
            <button id="btnClear" class="btn btn-danger" title="Limpiar todo el trazado actual">
                <i class="fa fa-trash"></i> Limpiar
            </button>
            <button id="btnSave" class="btn btn-success" title="Guardar este trazado en la base de datos de Odoo">
                <i class="fa fa-save"></i> Guardar Trazado
            </button>
        </div>

        <div class="tool-group">
            <span class="badge badge-success"><i class="fa fa-map-pin me-1"></i><span id="txtPoints">0</span> Vértices</span>
            <span class="badge badge-info"><i class="fa fa-tachometer-alt me-1"></i><span id="txtDist">0.00</span> km</span>
        </div>
    </div>

    <div id="map"></div>
    <div id="toast" class="toast-msg"></div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const routeId = {route.id};
        let points = {json.dumps(existing_coords)};
        const stops = {json.dumps(stops_list)};

        let currentMode = 'trace'; // 'trace' or 'stop'
        let polyline = null;
        let pointMarkers = [];
        let stopMarkers = [];

        // Inicializar mapa (Centrado en Ambato por defecto)
        const map = L.map('map', {{
            center: [-1.2543, -78.6229],
            zoom: 14,
            zoomControl: true
        }});

        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19,
            attribution: '© OpenStreetMap Flota Universitaria'
        }}).addTo(map);

        function showToast(msg, isError = false) {{
            const t = document.getElementById('toast');
            t.className = 'toast-msg ' + (isError ? 'toast-error' : 'toast-success');
            t.innerHTML = msg;
            t.style.display = 'block';
            setTimeout(() => {{ t.style.display = 'none'; }}, 3500);
        }}

        // Fórmula Haversine para distancia acumulada
        function haversine(lat1, lon1, lat2, lon2) {{
            const R = 6371; // km
            const dLat = (lat2 - lat1) * Math.PI / 180;
            const dLon = (lon2 - lon1) * Math.PI / 180;
            const a = Math.sin(dLat/2)*Math.sin(dLat/2) + 
                      Math.cos(lat1*Math.PI/180) * Math.cos(lat2*Math.PI/180) * 
                      Math.sin(dLon/2)*Math.sin(dLon/2);
            return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        }}

        function calculateTotalDistance(pts) {{
            if (pts.length < 2) return 0.0;
            let total = 0.0;
            for (let i = 0; i < pts.length - 1; i++) {{
                total += haversine(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1]);
            }}
            return total;
        }}

        function updateStats() {{
            document.getElementById('txtPoints').innerText = points.length;
            const dist = calculateTotalDistance(points);
            document.getElementById('txtDist').innerText = dist.toFixed(2);
        }}

        function redrawRoute() {{
            // Limpiar marcadores de trazado previos
            pointMarkers.forEach(m => map.removeLayer(m));
            pointMarkers = [];
            if (polyline) map.removeLayer(polyline);

            if (points.length === 0) {{
                updateStats();
                return;
            }}

            // Dibujar polilínea continua
            polyline = L.polyline(points, {{
                color: '#2563eb',
                weight: 5,
                opacity: 0.85,
                lineCap: 'round',
                lineJoin: 'round'
            }}).addTo(map);

            // Marcador de Inicio (Verde)
            const startIcon = L.divIcon({{
                className: 'endpoint-icon start-point',
                html: '<i class="fa fa-play" style="font-size: 10px;"></i>',
                iconSize: [28, 28],
                iconAnchor: [14, 14]
            }});
            const startMarker = L.marker(points[0], {{ icon: startIcon }})
                .bindPopup('<b>Inicio de Ruta</b><br>' + points[0][0].toFixed(5) + ', ' + points[0][1].toFixed(5))
                .addTo(map);
            pointMarkers.push(startMarker);

            // Marcador de Fin (Rojo) si hay más de 1 punto
            if (points.length > 1) {{
                const endIcon = L.divIcon({{
                    className: 'endpoint-icon end-point',
                    html: '<i class="fa fa-flag-checkered" style="font-size: 11px;"></i>',
                    iconSize: [28, 28],
                    iconAnchor: [14, 14]
                }});
                const endMarker = L.marker(points[points.length - 1], {{ icon: endIcon }})
                    .bindPopup('<b>Destino / Final de Ruta</b><br>' + points[points.length - 1][0].toFixed(5) + ', ' + points[points.length - 1][1].toFixed(5))
                    .addTo(map);
                pointMarkers.push(endMarker);
            }}

            updateStats();
        }}

        // Renderizar paradas registradas
        function renderStops() {{
            stopMarkers.forEach(m => map.removeLayer(m));
            stopMarkers = [];

            stops.forEach(s => {{
                const icon = L.divIcon({{
                    className: 'stop-marker-icon',
                    html: '<span>' + (s.seq ? s.seq/10 : 'P') + '</span>',
                    iconSize: [24, 24],
                    iconAnchor: [12, 12]
                }});
                const m = L.marker([s.lat, s.lon], {{ icon: icon }})
                    .bindPopup('<b>Parada Oficial #' + (s.seq/10) + ':</b> ' + s.name + '<br>Radio de Proximidad: ' + s.radius + 'm')
                    .addTo(map);
                stopMarkers.push(m);
            }});
        }}

        // Inicializar trazado existente y ajustar zoom
        redrawRoute();
        renderStops();

        if (points.length > 0) {{
            map.fitBounds(polyline.getBounds(), {{ padding: [40, 40] }});
        }} else if (stops.length > 0) {{
            const group = new L.featureGroup(stopMarkers);
            map.fitBounds(group.getBounds(), {{ padding: [40, 40] }});
        }}

        // Alternar modos de la barra de herramientas
        const btnTrace = document.getElementById('btnTrace');
        const btnAddStop = document.getElementById('btnAddStop');

        btnTrace.addEventListener('click', () => {{
            currentMode = 'trace';
            btnTrace.className = 'btn btn-outline btn-active';
            btnAddStop.className = 'btn btn-outline';
            map.getContainer().style.cursor = 'crosshair';
            showToast('Modo Trazado Activo: Haz clic en el mapa para marcar la línea del bus');
        }});

        btnAddStop.addEventListener('click', () => {{
            currentMode = 'stop';
            btnAddStop.className = 'btn btn-outline btn-active';
            btnTrace.className = 'btn btn-outline';
            map.getContainer().style.cursor = 'pointer';
            showToast('Modo Parada: Haz clic en el mapa para registrar una parada oficial');
        }});

        // Clic en el mapa para añadir punto o parada
        map.on('click', async (e) => {{
            const lat = e.latlng.lat;
            const lon = e.latlng.lng;

            if (currentMode === 'trace') {{
                const autoRoute = document.getElementById('chkAutoRoute').checked;

                // Si autoRoute está activo y ya hay un punto previo, intentar seguir las calles con OSRM
                if (autoRoute && points.length > 0) {{
                    const last = points[points.length - 1];
                    showToast('Enrutando por calles con OpenStreetMap...');
                    try {{
                        const url = 'https://router.project-osrm.org/route/v1/driving/' + 
                                    last[1] + ',' + last[0] + ';' + lon + ',' + lat + 
                                    '?overview=full&geometries=geojson';
                        const res = await fetch(url);
                        const data = await res.json();
                        if (data.routes && data.routes.length > 0) {{
                            const coords = data.routes[0].geometry.coordinates; // [lon, lat]
                            // Añadir los puntos intermedios omitiendo el primero repetido
                            for (let i = 1; i < coords.length; i++) {{
                                points.push([coords[i][1], coords[i][0]]);
                            }}
                            redrawRoute();
                            return;
                        }}
                    }} catch (err) {{
                        console.warn('OSRM error, fallback a línea recta:', err);
                    }}
                }}

                // Línea directa o primer punto
                points.push([lat, lon]);
                redrawRoute();

            }} else if (currentMode === 'stop') {{
                const stopName = prompt('Nombre de la nueva Parada:', 'Parada #' + (stops.length + 1));
                if (!stopName) return;

                showToast('Guardando nueva parada...');
                try {{
                    const res = await fetch('/transport/route/add_stop', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            route_id: routeId,
                            name: stopName,
                            lat: lat,
                            lon: lon
                        }})
                    }});
                    const data = await res.json();
                    if (data.status === 'ok') {{
                        stops.push({{
                            id: data.stop_id,
                            name: data.name,
                            seq: data.sequence,
                            lat: lat,
                            lon: lon,
                            radius: 50.0
                        }});
                        renderStops();
                        showToast('✅ Parada ' + data.name + ' registrada correctamente');
                    }} else {{
                        showToast('Error: ' + data.message, true);
                    }}
                }} catch (err) {{
                    showToast('Error de conexión al crear parada', true);
                }}
            }}
        }});

        // Botón Deshacer
        document.getElementById('btnUndo').addEventListener('click', () => {{
            if (points.length === 0) return;
            points.pop();
            redrawRoute();
            showToast('Último punto eliminado');
        }});

        // Botón Limpiar
        document.getElementById('btnClear').addEventListener('click', () => {{
            if (confirm('¿Deseas borrar todo el trazado actual para empezar de nuevo?')) {{
                points = [];
                redrawRoute();
                showToast('Trazado reiniciado');
            }}
        }});

        // Botón Guardar Trazado en Odoo
        document.getElementById('btnSave').addEventListener('click', async () => {{
            if (points.length === 0) {{
                alert('No has marcado ningún punto aún. Haz clic sobre el mapa para trazar la ruta antes de guardar.');
                return;
            }}

            const dist = calculateTotalDistance(points);
            showToast('Guardando trazado oficial en Odoo...');

            try {{
                const res = await fetch('/transport/route/save_coordinates', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        route_id: routeId,
                        coordinates: points,
                        distance_km: dist
                    }})
                }});
                const data = await res.json();
                if (data.status === 'ok') {{
                    showToast('✅ ¡Trazado oficial guardado! (' + data.points_count + ' puntos, ' + data.distance_km + ' km). Detección de desvíos activa.');
                }} else {{
                    showToast('Error al guardar: ' + data.message, true);
                }}
            }} catch (err) {{
                showToast('Error al conectar con Odoo para guardar trazado', true);
            }}
        }});
    </script>
</body>
</html>"""
        return html_content

    @http.route('/transport/route/save_coordinates', type='http', auth='user', methods=['POST'], csrf=False)
    def save_coordinates(self, **kwargs):
        """
        Guarda las coordenadas del trazado oficial y la distancia calculada
        en el modelo transport.route.
        """
        try:
            raw_data = request.httprequest.data
            if raw_data:
                data = json.loads(raw_data.decode('utf-8'))
            else:
                data = kwargs

            route_id = data.get('route_id')
            coordinates = data.get('coordinates', [])
            distance_km = data.get('distance_km', 0.0)

            if not route_id:
                return request.make_response(
                    json.dumps({'status': 'error', 'message': 'Falta el ID de la ruta'}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            route = request.env['transport.route'].browse(int(route_id))
            if not route.exists():
                return request.make_response(
                    json.dumps({'status': 'error', 'message': 'Ruta no encontrada'}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            vals = {
                'reference_coordinates': json.dumps(coordinates),
            }
            if distance_km:
                vals['estimated_distance'] = round(float(distance_km), 2)

            route.write(vals)

            return request.make_response(
                json.dumps({
                    'status': 'ok',
                    'points_count': len(coordinates),
                    'distance_km': vals.get('estimated_distance', route.estimated_distance)
                }),
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            _logger.exception("Error guardando trazado de ruta: %s", e)
            return request.make_response(
                json.dumps({'status': 'error', 'message': str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

    @http.route('/transport/route/add_stop', type='http', auth='user', methods=['POST'], csrf=False)
    def add_stop(self, **kwargs):
        """
        Crea un nuevo punto de parada para la ruta directamente desde el mapa.
        """
        try:
            raw_data = request.httprequest.data
            if raw_data:
                data = json.loads(raw_data.decode('utf-8'))
            else:
                data = kwargs

            route_id = data.get('route_id')
            name = (data.get('name') or 'Nueva Parada').strip()
            lat = data.get('lat')
            lon = data.get('lon')

            if not route_id or lat is None or lon is None:
                return request.make_response(
                    json.dumps({'status': 'error', 'message': 'Parámetros incompletos (route_id, lat, lon)'}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            route = request.env['transport.route'].browse(int(route_id))
            if not route.exists():
                return request.make_response(
                    json.dumps({'status': 'error', 'message': 'Ruta no encontrada'}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            existing_seqs = [s.sequence for s in route.stop_ids]
            next_seq = (max(existing_seqs) + 10) if existing_seqs else 10

            stop = request.env['transport.route.stop'].create({
                'route_id': route.id,
                'name': name,
                'sequence': next_seq,
                'latitude': float(lat),
                'longitude': float(lon),
                'proximity_radius': 50.0,
                'is_mandatory': True,
            })

            return request.make_response(
                json.dumps({
                    'status': 'ok',
                    'stop_id': stop.id,
                    'name': stop.name,
                    'sequence': stop.sequence,
                    'lat': stop.latitude,
                    'lon': stop.longitude,
                }),
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            _logger.exception("Error creando parada desde mapa: %s", e)
            return request.make_response(
                json.dumps({'status': 'error', 'message': str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

