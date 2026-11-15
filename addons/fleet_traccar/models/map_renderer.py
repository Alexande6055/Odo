# -*- coding: utf-8 -*-
"""
Generador de Mapas Interactivos Leaflet / OpenStreetMap para Odoo 16.
Genera componentes HTML enriquecidos, 100% responsivos y sin dependencias de API Keys.
"""
import json

def render_leaflet_map(
    map_id: str,
    planned_stops: list = None,
    planned_path: list = None,
    actual_points: list = None,
    incidents: list = None,
    height_px: int = 480,
    title: str = "Trazado y Monitoreo del Recorrido"
) -> str:
    """
    Construye un contenedor HTML con Leaflet.js para renderizar:
    - Paradas planificadas (pins numerados coloreados según estado).
    - Trazado de ruta programado (línea discontinua azul).
    - Trazado GPS real registrado por el vehículo (línea sólida morada).
    - Última posición del bus con icono dinámico.
    - Marcadores de incidencias (alertas rojas en coordenadas exactas).
    """
    planned_stops = planned_stops or []
    planned_path = planned_path or []
    actual_points = actual_points or []
    incidents = incidents or []

    # Si no hay paradas ni puntos, mostrar placeholder amigable
    if not planned_stops and not planned_path and not actual_points:
        return f"""
        <div class="alert alert-info d-flex align-items-center my-2 p-3 shadow-sm rounded-3" role="alert">
            <i class="fa fa-map-o fa-2x me-3 text-primary"></i>
            <div>
                <strong>Mapa Interactivo:</strong> Seleccione una <strong>Ruta</strong> para visualizar el trazado oficial, las paradas geolocalizadas y el monitoreo GPS en tiempo real.
            </div>
        </div>
        """

    stops_json = json.dumps(planned_stops)
    planned_path_json = json.dumps(planned_path)
    actual_points_json = json.dumps(actual_points)
    incidents_json = json.dumps(incidents)

    html = f"""
    <div class="card shadow-sm border-0 my-3 rounded-3 overflow-hidden">
        <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center py-2 px-3">
            <span class="fw-bold"><i class="fa fa-map-marker text-danger me-2"></i>{title}</span>
            <div class="small">
                <span class="badge bg-primary me-1"><i class="fa fa-road me-1"></i>Ruta Planificada</span>
                <span class="badge bg-purple text-white me-1" style="background-color: #7c3aed;"><i class="fa fa-location-arrow me-1"></i>Rastro GPS Real</span>
                <span class="badge bg-success me-1"><i class="fa fa-check me-1"></i>Parada Cumplida</span>
                <span class="badge bg-danger"><i class="fa fa-exclamation-triangle me-1"></i>Incidencias</span>
            </div>
        </div>
        <div class="card-body p-0 position-relative">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <style>
                #{map_id} {{
                    height: {height_px}px;
                    width: 100%;
                    background: #f8fafc;
                }}
                .custom-stop-marker {{
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                    font-size: 11px;
                    border-radius: 50%;
                    border: 2px solid white;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.35);
                    width: 26px !important;
                    height: 26px !important;
                    margin-left: -13px;
                    margin-top: -13px;
                }}
                .stop-visited {{ background-color: #10b981; }}
                .stop-delayed {{ background-color: #f59e0b; }}
                .stop-missed {{ background-color: #ef4444; }}
                .stop-pending {{ background-color: #3b82f6; }}
                .bus-marker {{
                    background: #2563eb;
                    border: 2px solid #ffffff;
                    border-radius: 50%;
                    width: 32px !important;
                    height: 32px !important;
                    margin-left: -16px;
                    margin-top: -16px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 16px;
                    box-shadow: 0 0 10px rgba(37,99,235,0.7);
                    animation: pulse-bus 2s infinite;
                }}
                @keyframes pulse-bus {{
                    0% {{ box-shadow: 0 0 0 0 rgba(37,99,235,0.7); }}
                    70% {{ box-shadow: 0 0 0 10px rgba(37,99,235,0); }}
                    100% {{ box-shadow: 0 0 0 0 rgba(37,99,235,0); }}
                }}
                .incident-marker {{
                    background: #dc2626;
                    border: 2px solid #ffffff;
                    border-radius: 50%;
                    width: 24px !important;
                    height: 24px !important;
                    margin-left: -12px;
                    margin-top: -12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 11px;
                    box-shadow: 0 2px 6px rgba(220,38,38,0.5);
                }}
            </style>

            <div id="{map_id}"></div>

            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script>
            (function() {{
                var mapContainer = document.getElementById("{map_id}");
                if (!mapContainer) return;

                // Evitar reinicialización si ya existe
                if (mapContainer._leaflet_id) {{
                    mapContainer._leaflet_id = null;
                }}

                var map = L.map("{map_id}", {{
                    zoomControl: true,
                    attributionControl: true
                }}).setView([-1.2543, -78.6228], 14);

                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    maxZoom: 19,
                    attribution: '&copy; OpenStreetMap | UTA Calidad de Software'
                }}).addTo(map);

                var boundsGroup = L.featureGroup();

                var plannedStops = {stops_json};
                var plannedPath = {planned_path_json};
                var actualPoints = {actual_points_json};
                var incidents = {incidents_json};

                // 1. Trazado Planificado (Línea Azul punteada)
                if (plannedPath && plannedPath.length > 1) {{
                    var plannedLine = L.polyline(plannedPath, {{
                        color: '#2563eb',
                        weight: 4,
                        opacity: 0.7,
                        dashArray: '8, 8'
                    }}).addTo(map);
                    boundsGroup.addLayer(plannedLine);
                }}

                // 2. Trazado GPS Real (Línea Morada sólida)
                if (actualPoints && actualPoints.length > 1) {{
                    var trackCoords = actualPoints.map(function(p) {{ return [p.lat, p.lon]; }});
                    var trackLine = L.polyline(trackCoords, {{
                        color: '#7c3aed',
                        weight: 5,
                        opacity: 0.85
                    }}).addTo(map);
                    boundsGroup.addLayer(trackLine);

                    // Última posición del vehículo
                    var lastP = actualPoints[actualPoints.length - 1];
                    var busIcon = L.divIcon({{
                        className: 'bus-marker',
                        html: '🚌'
                    }});
                    var busMarker = L.marker([lastP.lat, lastP.lon], {{icon: busIcon}})
                        .bindPopup('<strong>Vehículo / Bus</strong><br>Velocidad: ' + (lastP.speed || 0) + ' km/h<br>Hora: ' + (lastP.time || ''));
                    busMarker.addTo(map);
                    boundsGroup.addLayer(busMarker);
                }}

                // 3. Puntos de Parada
                if (plannedStops && plannedStops.length > 0) {{
                    plannedStops.forEach(function(s, idx) {{
                        var statusClass = 'stop-pending';
                        var statusText = 'Pendiente';
                        if (s.status === 'visited') {{ statusClass = 'stop-visited'; statusText = 'Cumplida a Tiempo'; }}
                        else if (s.status === 'delayed') {{ statusClass = 'stop-delayed'; statusText = 'Cumplida con Retraso (' + s.delay + ' min)'; }}
                        else if (s.status === 'missed') {{ statusClass = 'stop-missed'; statusText = 'Parada Omitida / No Visitada'; }}

                        var stopIcon = L.divIcon({{
                            className: 'custom-stop-marker ' + statusClass,
                            html: (s.seq || (idx + 1))
                        }});

                        var popupContent = '<div style="min-width:180px;">' +
                            '<strong class="text-primary">' + (s.seq ? s.seq + '. ' : '') + s.name + '</strong><br>' +
                            '<span class="badge bg-secondary mb-1">' + statusText + '</span><br>' +
                            'Horario Previsto: <strong>' + (s.sched_time || 'N/A') + '</strong><br>' +
                            (s.actual_time ? 'Llegada Real: <strong>' + s.actual_time + '</strong><br>' : '') +
                            (s.dist ? 'Distancia Registrada: <strong>' + s.dist + ' m</strong>' : '') +
                            '</div>';

                        var marker = L.marker([s.lat, s.lon], {{icon: stopIcon}}).bindPopup(popupContent);
                        marker.addTo(map);
                        boundsGroup.addLayer(marker);
                    }});
                }}

                // 4. Incidencias Detectadas
                if (incidents && incidents.length > 0) {{
                    incidents.forEach(function(inc) {{
                        if (inc.lat && inc.lon) {{
                            var incIcon = L.divIcon({{
                                className: 'incident-marker',
                                html: '⚠️'
                            }});
                            var incPopup = '<div style="min-width:190px;">' +
                                '<strong class="text-danger">' + inc.name + '</strong><br>' +
                                '<span class="badge bg-danger mb-1">' + (inc.type || 'Incidencia') + '</span><br>' +
                                '<small class="text-muted">' + (inc.desc || '') + '</small><br>' +
                                (inc.delay ? 'Retraso: <strong>' + inc.delay + ' min</strong><br>' : '') +
                                (inc.dev ? 'Desvío: <strong>' + inc.dev + ' m</strong><br>' : '') +
                                '</div>';
                            var incMarker = L.marker([inc.lat, inc.lon], {{icon: incIcon}}).bindPopup(incPopup);
                            incMarker.addTo(map);
                            boundsGroup.addLayer(incMarker);
                        }}
                    }});
                }}

                // Ajustar zoom para abarcar todos los elementos
                if (boundsGroup.getLayers().length > 0) {{
                    map.fitBounds(boundsGroup.getBounds(), {{
                        padding: [30, 30],
                        maxZoom: 16
                    }});
                }}

                // Invalidate size al terminar la carga para evitar tiles cortados
                setTimeout(function() {{
                    map.invalidateSize();
                }}, 300);
            }})();
            </script>
        </div>
    </div>
    """
    return html
