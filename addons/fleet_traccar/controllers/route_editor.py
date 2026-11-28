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
        Gestiona simultáneamente el Trazado de Ida (Azul) y el Trazado de Regreso (Naranja),
        calcula distancias independientes y determina el punto de origen (1er vértice) y
        destino (último vértice) de cada sentido de forma automática.
        """
        route = request.env['transport.route'].browse(route_id)
        if not route.exists():
            return request.not_found()

        # Coordenadas de Ida
        existing_outbound = []
        if route.reference_coordinates:
            try:
                parsed = json.loads(route.reference_coordinates)
                if isinstance(parsed, list):
                    existing_outbound = parsed
            except Exception:
                existing_outbound = []

        # Coordenadas de Regreso
        existing_return = []
        if route.return_coordinates:
            try:
                parsed = json.loads(route.return_coordinates)
                if isinstance(parsed, list):
                    existing_return = parsed
            except Exception:
                existing_return = []

        # Paradas registradas
        stops_list = []
        for s in route.stop_ids.sorted('sequence'):
            stops_list.append({
                'id': s.id,
                'name': s.name,
                'seq': s.sequence,
                'lat': s.latitude,
                'lon': s.longitude,
                'radius': s.proximity_radius or 50.0,
                'direction': getattr(s, 'stop_direction', 'outbound'),
                'mandatory': s.is_mandatory,
            })

        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Diseñador de Ruta Bidireccional: {route.name}</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; height: 100vh; display: flex; flex-direction: column; background: #0f172a; color: #f8fafc; overflow: hidden; }}
        #toolbar {{
            background: #1e293b;
            padding: 8px 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 8px;
            border-bottom: 1px solid #334155;
            flex-shrink: 0;
            position: relative;
            z-index: 1000;
        }}
        .tool-group {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 7px 12px;
            font-size: 12px;
            font-weight: 600;
            border-radius: 8px;
            border: 1px solid transparent;
            cursor: pointer;
            transition: all 0.2s ease;
            user-select: none;
        }}
        .btn-outbound {{ background: #1e3a8a; color: #93c5fd; border-color: #3b82f6; }}
        .btn-outbound:hover {{ background: #1d4ed8; color: white; }}
        .btn-outbound.active {{ background: #2563eb !important; color: white !important; border-color: #60a5fa !important; box-shadow: 0 0 10px rgba(37,99,235,0.7); }}

        .btn-return {{ background: #7c2d12; color: #fdba74; border-color: #f97316; }}
        .btn-return:hover {{ background: #c2410c; color: white; }}
        .btn-return.active {{ background: #ea580c !important; color: white !important; border-color: #fb923c !important; box-shadow: 0 0 10px rgba(234,88,12,0.7); }}

        .btn-success {{ background: #059669; color: white; }}
        .btn-success:hover {{ background: #047857; }}
        .btn-outline {{ background: #334155; color: #e2e8f0; border-color: #475569; }}
        .btn-outline:hover {{ background: #475569; }}
        .btn-danger {{ background: #dc2626; color: white; }}
        .btn-danger:hover {{ background: #b91c1c; }}

        .badge {{ padding: 3px 7px; border-radius: 6px; font-size: 11px; font-weight: bold; background: #334155; color: #cbd5e1; }}
        .badge-blue {{ background: #1d4ed8; color: white; }}
        .badge-orange {{ background: #c2410c; color: white; }}
        .switch-container {{ display: flex; align-items: center; gap: 5px; font-size: 11px; color: #cbd5e1; cursor: pointer; user-select: none; }}

        #subbar {{
            background: #0f172a;
            padding: 5px 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 11px;
            color: #94a3b8;
            border-bottom: 1px solid #1e293b;
            gap: 15px;
            flex-wrap: wrap;
            flex-shrink: 0;
            position: relative;
            z-index: 999;
        }}
        .route-summary-box {{ display: flex; align-items: center; gap: 8px; }}

        #map {{ flex: 1; min-height: 0; width: 100%; position: relative; z-index: 1; }}
        .toast-msg {{
            position: fixed;
            top: 75px;
            right: 20px;
            z-index: 2000;
            padding: 10px 16px;
            border-radius: 8px;
            color: white;
            font-size: 12px;
            font-weight: bold;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
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
            font-size: 10px;
            border-radius: 50%;
            border: 2px solid white;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 6px rgba(0,0,0,0.4);
            width: 22px;
            height: 22px;
        }}
        .endpoint-icon {{
            width: 26px;
            height: 26px;
            border-radius: 50%;
            border: 2px solid white;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 11px;
            box-shadow: 0 3px 8px rgba(0,0,0,0.4);
        }}
        .out-start {{ background: #16a34a; }}
        .out-end {{ background: #2563eb; }}
        .ret-start {{ background: #ea580c; }}
        .ret-end {{ background: #9333ea; }}
    </style>
</head>
<body>
    <div id="toolbar">
        <div class="tool-group">
            <span class="badge badge-blue"><i class="fa fa-route me-1"></i>{route.code}</span>
            <span style="font-weight: bold; font-size: 13px;">{route.name}</span>
        </div>

        <div class="tool-group">
            <!-- Selector de Sentido de Trazado -->
            <button id="btnTrackOutbound" class="btn btn-outbound active" title="Editar el trazado del tramo de Ida (Salida)">
                <i class="fa fa-arrow-right"></i> Trazar IDA (Azul)
            </button>
            <button id="btnTrackReturn" class="btn btn-return" title="Editar el trazado del tramo de Regreso (Retorno)">
                <i class="fa fa-arrow-left"></i> Trazar REGRESO (Naranja)
            </button>

            <label class="switch-container ms-2">
                <input type="checkbox" id="chkAutoRoute" checked style="cursor: pointer;">
                <span><i class="fa fa-road"></i> Seguir Calles</span>
            </label>
            <button id="btnAutoTraceStops" class="btn btn-outline" title="Trazar automáticamente por calles reales (OSRM) pasando por todas las paradas">
                <i class="fa fa-magic"></i> Trazar por Calles
            </button>
            <button id="btnAddStop" class="btn btn-outline" title="Haz clic en el mapa para registrar una parada">
                <i class="fa fa-flag"></i> Nueva Parada
            </button>
            <button id="btnUndo" class="btn btn-outline" title="Deshacer el último tramo trazado (Ctrl+Z)">
                <i class="fa fa-undo"></i> Deshacer
            </button>
            <button id="btnRevert" class="btn btn-outline" title="Restaurar los trazados al último estado guardado en Odoo">
                <i class="fa fa-history"></i> Restaurar
            </button>
            <button id="btnClear" class="btn btn-danger" title="Borrar el trazado del sentido activo">
                <i class="fa fa-trash"></i> Limpiar
            </button>
            <button id="btnSave" class="btn btn-success" title="Guardar ambos trazados, distancias y puntos de origen/destino en Odoo">
                <i class="fa fa-save"></i> Guardar Rutas
            </button>
        </div>
    </div>

    <!-- Barra de Origen / Destino / Distancias de ambos sentidos -->
    <div id="subbar">
        <div class="route-summary-box">
            <span class="badge badge-blue">🔵 IDA:</span>
            <span>Origen: <strong id="lblOriginOut" class="text-white">--</strong></span>
            <span>➔</span>
            <span>Destino: <strong id="lblDestOut" class="text-white">--</strong></span>
            <span class="badge"><span id="txtDistOut">0.00</span> km (<span id="txtPtsOut">0</span> pts)</span>
        </div>

        <div class="route-summary-box">
            <span class="badge badge-orange">🟠 REGRESO:</span>
            <span>Origen: <strong id="lblOriginRet" class="text-white">--</strong></span>
            <span>➔</span>
            <span>Destino: <strong id="lblDestRet" class="text-white">--</strong></span>
            <span class="badge"><span id="txtDistRet">0.00</span> km (<span id="txtPtsRet">0</span> pts)</span>
        </div>
    </div>

    <div id="map"></div>
    <div id="toast" class="toast-msg"></div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const routeId = {route.id};
        const savedOutboundBackup = {json.dumps(existing_outbound)};
        const savedReturnBackup = {json.dumps(existing_return)};
        let pointsOutbound = savedOutboundBackup.map(p => [p[0], p[1]]);
        let pointsReturn = savedReturnBackup.map(p => [p[0], p[1]]);
        const stops = {json.dumps(stops_list)};

        let activeTrack = 'outbound'; // 'outbound' or 'return'
        let mode = 'trace'; // 'trace' or 'stop'

        let polylineOut = null;
        let polylineRet = null;
        let markersOut = [];
        let markersRet = [];
        let stopMarkers = [];

        let originNameOut = "{route.origin or ''}";
        let destNameOut = "{route.destination or ''}";
        let originNameRet = "{getattr(route, 'origin_return', '') or ''}";
        let destNameRet = "{getattr(route, 'destination_return', '') or ''}";

        // Evitar que Chromium/Brave desplace el iframe y oculte la cabecera al enfocar el mapa
        const mapEl = document.getElementById('map');
        const origMapFocus = mapEl.focus.bind(mapEl);
        mapEl.focus = function() {{ origMapFocus({{ preventScroll: true }}); }};
        mapEl.addEventListener('mousedown', () => {{ window.scrollTo(0, 0); }});

        // Inicializar Mapa centrado en Ambato
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

        // Haversine
        function haversine(lat1, lon1, lat2, lon2) {{
            const R = 6371; // km
            const dLat = (lat2 - lat1) * Math.PI / 180;
            const dLon = (lon2 - lon1) * Math.PI / 180;
            const a = Math.sin(dLat/2)*Math.sin(dLat/2) +
                      Math.cos(lat1*Math.PI/180) * Math.cos(lat2*Math.PI/180) *
                      Math.sin(dLon/2)*Math.sin(dLon/2);
            return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        }}

        function calcDistance(pts) {{
            if (pts.length < 2) return 0.0;
            let total = 0.0;
            for (let i = 0; i < pts.length - 1; i++) {{
                total += haversine(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1]);
            }}
            return total;
        }}

        // Geocodificación inversa para obtener nombres de calles del 1er y último vértice
        async function reverseGeocode(lat, lon) {{
            try {{
                const res = await fetch('https://nominatim.openstreetmap.org/reverse?format=json&lat=' + lat + '&lon=' + lon);
                const data = await res.json();
                if (data && data.address) {{
                    const road = data.address.road || data.address.neighbourhood || data.address.suburb || data.address.city || '';
                    if (road) return road;
                }}
            }} catch (e) {{
                // Red local / offline
            }}
            return 'Punto (' + lat.toFixed(4) + ', ' + lon.toFixed(4) + ')';
        }}

        async function updateVertexLocations() {{
            // Actualizar Origen y Destino de Ida
            if (pointsOutbound.length > 0) {{
                const p0 = pointsOutbound[0];
                const pLast = pointsOutbound[pointsOutbound.length - 1];
                if (!originNameOut || originNameOut.includes('Tomado') || originNameOut.includes('Determinado')) {{
                    originNameOut = await reverseGeocode(p0[0], p0[1]);
                }}
                if (pointsOutbound.length > 1) {{
                    destNameOut = await reverseGeocode(pLast[0], pLast[1]);
                }} else {{
                    destNameOut = originNameOut;
                }}
            }}
            // Actualizar Origen y Destino de Regreso
            if (pointsReturn.length > 0) {{
                const p0 = pointsReturn[0];
                const pLast = pointsReturn[pointsReturn.length - 1];
                if (!originNameRet || originNameRet.includes('Tomado') || originNameRet.includes('Determinado')) {{
                    originNameRet = await reverseGeocode(p0[0], p0[1]);
                }}
                if (pointsReturn.length > 1) {{
                    destNameRet = await reverseGeocode(pLast[0], pLast[1]);
                }} else {{
                    destNameRet = originNameRet;
                }}
            }}
            renderSubbar();
        }}

        function renderSubbar() {{
            const distOut = calcDistance(pointsOutbound);
            const distRet = calcDistance(pointsReturn);

            document.getElementById('txtPtsOut').innerText = pointsOutbound.length;
            document.getElementById('txtDistOut').innerText = distOut.toFixed(2);
            document.getElementById('lblOriginOut').innerText = originNameOut || (pointsOutbound.length > 0 ? (pointsOutbound[0][0].toFixed(4) + ', ' + pointsOutbound[0][1].toFixed(4)) : '--');
            document.getElementById('lblDestOut').innerText = destNameOut || (pointsOutbound.length > 1 ? (pointsOutbound[pointsOutbound.length-1][0].toFixed(4) + ', ' + pointsOutbound[pointsOutbound.length-1][1].toFixed(4)) : '--');

            document.getElementById('txtPtsRet').innerText = pointsReturn.length;
            document.getElementById('txtDistRet').innerText = distRet.toFixed(2);
            document.getElementById('lblOriginRet').innerText = originNameRet || (pointsReturn.length > 0 ? (pointsReturn[0][0].toFixed(4) + ', ' + pointsReturn[0][1].toFixed(4)) : '--');
            document.getElementById('lblDestRet').innerText = destNameRet || (pointsReturn.length > 1 ? (pointsReturn[pointsReturn.length-1][0].toFixed(4) + ', ' + pointsReturn[pointsReturn.length-1][1].toFixed(4)) : '--');
        }}

        // Dibujar Trazado de Ida (Azul)
        function redrawOutbound() {{
            markersOut.forEach(m => map.removeLayer(m));
            markersOut = [];
            if (polylineOut) map.removeLayer(polylineOut);

            if (pointsOutbound.length === 0) return;

            polylineOut = L.polyline(pointsOutbound, {{
                color: '#2563eb',
                weight: 5,
                opacity: 0.85,
                lineCap: 'round',
                lineJoin: 'round'
            }}).addTo(map);

            // Marcador Inicio Ida (Verde)
            const iconStart = L.divIcon({{
                className: 'endpoint-icon out-start',
                html: '<i class="fa fa-play" style="font-size: 9px;"></i>',
                iconSize: [26, 26],
                iconAnchor: [13, 13]
            }});
            const mStart = L.marker(pointsOutbound[0], {{ icon: iconStart }})
                .bindPopup('<b>🔵 Origen Ida:</b><br>' + originNameOut)
                .addTo(map);
            markersOut.push(mStart);

            // Marcador Fin Ida (Azul oscuro / Bandera)
            if (pointsOutbound.length > 1) {{
                const iconEnd = L.divIcon({{
                    className: 'endpoint-icon out-end',
                    html: '<i class="fa fa-flag-checkered" style="font-size: 10px;"></i>',
                    iconSize: [26, 26],
                    iconAnchor: [13, 13]
                }});
                const mEnd = L.marker(pointsOutbound[pointsOutbound.length - 1], {{ icon: iconEnd }})
                    .bindPopup('<b>🔵 Destino Ida:</b><br>' + destNameOut)
                    .addTo(map);
                markersOut.push(mEnd);
            }}
        }}

        // Dibujar Trazado de Regreso (Naranja)
        function redrawReturn() {{
            markersRet.forEach(m => map.removeLayer(m));
            markersRet = [];
            if (polylineRet) map.removeLayer(polylineRet);

            if (pointsReturn.length === 0) return;

            polylineRet = L.polyline(pointsReturn, {{
                color: '#ea580c',
                weight: 5,
                opacity: 0.85,
                dashArray: '8, 6', // Distintivo para visualizar fácilmente superposiciones
                lineCap: 'round',
                lineJoin: 'round'
            }}).addTo(map);

            // Marcador Inicio Regreso (Naranja)
            const iconStart = L.divIcon({{
                className: 'endpoint-icon ret-start',
                html: '<i class="fa fa-play" style="font-size: 9px;"></i>',
                iconSize: [26, 26],
                iconAnchor: [13, 13]
            }});
            const mStart = L.marker(pointsReturn[0], {{ icon: iconStart }})
                .bindPopup('<b>🟠 Origen Regreso:</b><br>' + originNameRet)
                .addTo(map);
            markersRet.push(mStart);

            // Marcador Fin Regreso (Morado / Bandera)
            if (pointsReturn.length > 1) {{
                const iconEnd = L.divIcon({{
                    className: 'endpoint-icon ret-end',
                    html: '<i class="fa fa-flag-checkered" style="font-size: 10px;"></i>',
                    iconSize: [26, 26],
                    iconAnchor: [13, 13]
                }});
                const mEnd = L.marker(pointsReturn[pointsReturn.length - 1], {{ icon: iconEnd }})
                    .bindPopup('<b>🟠 Destino Regreso:</b><br>' + destNameRet)
                    .addTo(map);
                markersRet.push(mEnd);
            }}
        }}

        // Renderizar Paradas
        function renderStops() {{
            stopMarkers.forEach(m => map.removeLayer(m));
            stopMarkers = [];
            stops.forEach(s => {{
                const icon = L.divIcon({{
                    className: 'stop-marker-icon',
                    html: '<span>' + (s.seq ? s.seq/10 : 'P') + '</span>',
                    iconSize: [22, 22],
                    iconAnchor: [11, 11]
                }});
                const m = L.marker([s.lat, s.lon], {{ icon: icon }})
                    .bindPopup('<b>Parada #' + (s.seq/10) + ':</b> ' + s.name + '<br>Radio: ' + s.radius + 'm')
                    .addTo(map);
                stopMarkers.push(m);
            }});
        }}

        // Inicializar vistas
        redrawOutbound();
        redrawReturn();
        renderStops();
        renderSubbar();

        // Ajustar zoom inicial
        const allBounds = [];
        if (polylineOut) allBounds.push(polylineOut.getBounds());
        if (polylineRet) allBounds.push(polylineRet.getBounds());
        if (allBounds.length > 0) {{
            const combined = allBounds[0];
            if (allBounds.length > 1) combined.extend(allBounds[1]);
            map.fitBounds(combined, {{ padding: [40, 40] }});
        }}

        // Botones de Selector de Sentido
        const btnTrackOut = document.getElementById('btnTrackOutbound');
        const btnTrackRet = document.getElementById('btnTrackReturn');
        const btnAddStop = document.getElementById('btnAddStop');

        btnTrackOut.addEventListener('click', () => {{
            activeTrack = 'outbound';
            mode = 'trace';
            btnTrackOut.className = 'btn btn-outbound active';
            btnTrackRet.className = 'btn btn-return';
            btnAddStop.className = 'btn btn-outline';
            map.getContainer().style.cursor = 'crosshair';
            showToast('Modo Activo: 🔵 Trazado de IDA (Línea Azul)');
        }});

        btnTrackRet.addEventListener('click', () => {{
            activeTrack = 'return';
            mode = 'trace';
            btnTrackRet.className = 'btn btn-return active';
            btnTrackOut.className = 'btn btn-outbound';
            btnAddStop.className = 'btn btn-outline';
            map.getContainer().style.cursor = 'crosshair';
            showToast('Modo Activo: 🟠 Trazado de REGRESO (Línea Naranja)');
        }});

        btnAddStop.addEventListener('click', () => {{
            mode = 'stop';
            btnAddStop.className = 'btn btn-outline active';
            map.getContainer().style.cursor = 'pointer';
            showToast('Modo Parada: Haz clic en el mapa para registrar una parada');
        }});

        // Clic en el Mapa
        map.on('click', async (e) => {{
            const lat = e.latlng.lat;
            const lon = e.latlng.lng;

            if (mode === 'stop') {{
                const stopName = prompt('Nombre de la Parada:', 'Parada #' + (stops.length + 1));
                if (!stopName) return;

                showToast('Guardando parada...');
                try {{
                    const res = await fetch('/transport/route/add_stop', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            route_id: routeId,
                            name: stopName,
                            lat: lat,
                            lon: lon,
                            direction: activeTrack
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
                        showToast('✅ Parada ' + data.name + ' guardada');
                    }} else {{
                        showToast('Error: ' + data.message, true);
                    }}
                }} catch (err) {{
                    showToast('Error de conexión al crear parada', true);
                }}
                mode = 'trace';
                btnAddStop.className = 'btn btn-outline';
                return;
            }}

            // Modo Trazado (Ida o Regreso)
            const targetArray = (activeTrack === 'outbound') ? pointsOutbound : pointsReturn;
            const targetHistory = (activeTrack === 'outbound') ? historyOutbound : historyReturn;
            targetHistory.push(targetArray.length);
            const autoRoute = document.getElementById('chkAutoRoute').checked;

            if (autoRoute && targetArray.length > 0) {{
                const last = targetArray[targetArray.length - 1];
                showToast('Enrutando por calles con OpenStreetMap...');
                try {{
                    const url = 'https://router.project-osrm.org/route/v1/driving/' +
                                last[1] + ',' + last[0] + ';' + lon + ',' + lat +
                                '?overview=full&geometries=geojson';
                    const res = await fetch(url);
                    const data = await res.json();
                    if (data.routes && data.routes.length > 0) {{
                        const coords = data.routes[0].geometry.coordinates; // [lon, lat]
                        for (let i = 1; i < coords.length; i++) {{
                            targetArray.push([coords[i][1], coords[i][0]]);
                        }}
                        if (activeTrack === 'outbound') redrawOutbound();
                        else redrawReturn();
                        updateVertexLocations();
                        return;
                    }}
                }} catch (err) {{
                    console.warn('OSRM error, usando línea recta:', err);
                }}
            }}

            targetArray.push([lat, lon]);
            if (activeTrack === 'outbound') redrawOutbound();
            else redrawReturn();
            updateVertexLocations();
        }});

        const historyOutbound = [];
        const historyReturn = [];

        // Botón Auto-Trazar por Calles desde Paradas (OSRM)
        document.getElementById('btnAutoTraceStops').addEventListener('click', async () => {{
            let routeStops = [];
            if (activeTrack === 'outbound') {{
                routeStops = stops.filter(s => s.direction === 'outbound' || s.direction === 'both');
                if (routeStops.length < 2) routeStops = [...stops];
            }} else {{
                routeStops = stops.filter(s => s.direction === 'inbound' || s.direction === 'both');
                if (routeStops.length < 2) routeStops = [...stops].reverse();
            }}
            if (routeStops.length < 2) {{
                showToast('Se necesitan al menos 2 paradas para trazar por calles.', true);
                return;
            }}
            const trackLabel = (activeTrack === 'outbound') ? 'IDA' : 'REGRESO';
            showToast('Calculando ruta real por calles (' + trackLabel + ') con OSRM...');
            try {{
                const waypoints = routeStops.map(s => s.lon + ',' + s.lat).join(';');
                const url = 'https://router.project-osrm.org/route/v1/driving/' + waypoints + '?overview=full&geometries=geojson';
                const res = await fetch(url);
                const data = await res.json();
                if (data.routes && data.routes.length > 0) {{
                    const geom = data.routes[0].geometry.coordinates.map(c => [Number(c[1].toFixed(6)), Number(c[0].toFixed(6))]);
                    if (activeTrack === 'outbound') {{
                        historyOutbound.push(pointsOutbound.length);
                        pointsOutbound = geom;
                        redrawOutbound();
                    }} else {{
                        historyReturn.push(pointsReturn.length);
                        pointsReturn = geom;
                        redrawReturn();
                    }}
                    updateVertexLocations();
                    const km = calcDistance(geom).toFixed(2);
                    showToast('✅ ' + trackLabel + ' trazada por calles reales (' + geom.length + ' pts, ' + km + ' km). Pulsa Guardar Rutas.');
                }} else {{
                    showToast('OSRM no devolvió una ruta válida para estas paradas.', true);
                }}
            }} catch (err) {{
                console.warn('OSRM auto-trace error:', err);
                showToast('No se pudo conectar con OSRM para trazar por calles.', true);
            }}
        }});

        // Botón Deshacer (deshace el tramo completo del último clic) + Atajo Ctrl+Z
        function performUndo() {{
            const targetArray = (activeTrack === 'outbound') ? pointsOutbound : pointsReturn;
            const targetHistory = (activeTrack === 'outbound') ? historyOutbound : historyReturn;
            if (targetArray.length === 0) return;
            if (targetHistory.length > 0) {{
                const prevLen = targetHistory.pop();
                targetArray.splice(prevLen);
            }} else {{
                targetArray.pop();
            }}
            if (activeTrack === 'outbound') redrawOutbound();
            else redrawReturn();
            updateVertexLocations();
            showToast('↩️ Último tramo deshecho en ' + (activeTrack === 'outbound' ? 'Ida' : 'Regreso'));
        }}
        document.getElementById('btnUndo').addEventListener('click', performUndo);
        document.addEventListener('keydown', (ev) => {{
            if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === 'z') {{
                ev.preventDefault();
                performUndo();
            }}
        }});

        // Botón Restaurar al último estado guardado en Odoo
        document.getElementById('btnRevert').addEventListener('click', () => {{
            if (confirm('¿Restaurar los trazados de Ida y Regreso al último estado guardado en Odoo?')) {{
                pointsOutbound = savedOutboundBackup.map(p => [p[0], p[1]]);
                pointsReturn = savedReturnBackup.map(p => [p[0], p[1]]);
                historyOutbound.length = 0;
                historyReturn.length = 0;
                redrawOutbound();
                redrawReturn();
                updateVertexLocations();
                showToast('🔄 Trazados restaurados al último estado guardado');
            }}
        }});

        // Botón Limpiar
        document.getElementById('btnClear').addEventListener('click', () => {{
            const name = (activeTrack === 'outbound') ? 'IDA' : 'REGRESO';
            if (confirm('¿Deseas reiniciar el trazado de ' + name + '?')) {{
                if (activeTrack === 'outbound') {{
                    pointsOutbound = [];
                    historyOutbound.length = 0;
                    redrawOutbound();
                }} else {{
                    pointsReturn = [];
                    historyReturn.length = 0;
                    redrawReturn();
                }}
                updateVertexLocations();
                showToast('Trazado de ' + name + ' reiniciado');
            }}
        }});

        // Botón Guardar Trazados (Ida y Regreso)
        document.getElementById('btnSave').addEventListener('click', async () => {{
            if (pointsOutbound.length === 0 && pointsReturn.length === 0) {{
                alert('No has trazado ningún punto todavía. Haz clic sobre el mapa para trazar la ruta de ida o regreso.');
                return;
            }}

            const distOut = calcDistance(pointsOutbound);
            const distRet = calcDistance(pointsReturn);

            showToast('Guardando ambos trazados en Odoo...');
            try {{
                const res = await fetch('/transport/route/save_coordinates', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        route_id: routeId,
                        outbound_coordinates: pointsOutbound,
                        return_coordinates: pointsReturn,
                        outbound_distance: distOut,
                        return_distance: distRet,
                        origin_out: originNameOut,
                        dest_out: destNameOut,
                        origin_ret: originNameRet,
                        dest_ret: destNameRet
                    }})
                }});
                const data = await res.json();
                if (data.status === 'ok') {{
                    showToast('✅ ¡Rutas guardadas con éxito! Ida: ' + data.outbound_km + ' km | Regreso: ' + data.return_km + ' km');
                }} else {{
                    showToast('Error: ' + data.message, true);
                }}
            }} catch (err) {{
                showToast('Error de conexión al guardar trazados', true);
            }}
        }});
    </script>
</body>
</html>"""
        return html_content

    @http.route('/transport/route/save_coordinates', type='http', auth='user', methods=['POST'], csrf=False)
    def save_coordinates(self, **kwargs):
        """
        Guarda las coordenadas de Ida y de Regreso, actualiza distancias y
        asigna automáticamente el Punto de Origen (1er vértice) y
        Punto de Destino (último vértice) de cada sentido.
        """
        try:
            raw_data = request.httprequest.data
            if raw_data:
                data = json.loads(raw_data.decode('utf-8'))
            else:
                data = kwargs

            route_id = data.get('route_id')
            outbound_coords = data.get('outbound_coordinates', data.get('coordinates', []))
            return_coords = data.get('return_coordinates', [])
            outbound_dist = data.get('outbound_distance', data.get('distance_km', 0.0))
            return_dist = data.get('return_distance', 0.0)

            origin_out = data.get('origin_out', '').strip()
            dest_out = data.get('dest_out', '').strip()
            origin_ret = data.get('origin_ret', '').strip()
            dest_ret = data.get('dest_ret', '').strip()

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
                'reference_coordinates': json.dumps(outbound_coords),
                'return_coordinates': json.dumps(return_coords),
                'outbound_distance': round(float(outbound_dist), 2) if outbound_dist else 0.0,
                'return_distance': round(float(return_dist), 2) if return_dist else 0.0,
            }

            # Asignación automática de Origen y Destino de Ida desde los vértices
            if outbound_coords and len(outbound_coords) > 0:
                p0 = outbound_coords[0]
                pLast = outbound_coords[-1]
                vals['origin'] = origin_out or f"Lat: {p0[0]:.5f}, Lon: {p0[1]:.5f}"
                vals['destination'] = dest_out or f"Lat: {pLast[0]:.5f}, Lon: {pLast[1]:.5f}"

            # Asignación automática de Origen y Destino de Regreso desde los vértices
            if return_coords and len(return_coords) > 0:
                p0_ret = return_coords[0]
                pLast_ret = return_coords[-1]
                vals['origin_return'] = origin_ret or f"Lat: {p0_ret[0]:.5f}, Lon: {p0_ret[1]:.5f}"
                vals['destination_return'] = dest_ret or f"Lat: {pLast_ret[0]:.5f}, Lon: {pLast_ret[1]:.5f}"

            route.write(vals)

            return request.make_response(
                json.dumps({
                    'status': 'ok',
                    'outbound_pts': len(outbound_coords),
                    'return_pts': len(return_coords),
                    'outbound_km': vals.get('outbound_distance', 0.0),
                    'return_km': vals.get('return_distance', 0.0),
                    'origin': route.origin,
                    'destination': route.destination
                }),
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            _logger.exception("Error guardando trazados bidireccionales: %s", e)
            return request.make_response(
                json.dumps({'status': 'error', 'message': str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

    @http.route('/transport/route/add_stop', type='http', auth='user', methods=['POST'], csrf=False)
    def add_stop(self, **kwargs):
        """
        Crea un nuevo punto de parada georreferenciado para la ruta.
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
            direction = data.get('direction', 'outbound')

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

            stop_vals = {
                'route_id': route.id,
                'name': name,
                'sequence': next_seq,
                'latitude': float(lat),
                'longitude': float(lon),
                'proximity_radius': 50.0,
                'is_mandatory': True,
            }
            if hasattr(request.env['transport.route.stop'], 'stop_direction'):
                stop_vals['stop_direction'] = direction

            stop = request.env['transport.route.stop'].create(stop_vals)

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
