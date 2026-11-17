/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { Component, onWillStart, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";

export class TransportDashboardClientAction extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.notification = useService("notification");

        this.mapRef = useRef("mapContainer");
        this.mapIframeRef = useRef("mapIframe");
        this.complianceChartRef = useRef("complianceChart");
        this.routesChartRef = useRef("routesChart");
        this.incidentsChartRef = useRef("incidentsChart");

        this.state = useState({
            loading: true,
            period: "today",
            kpis: {},
            buses: [],
            routes: [],
            recent_incidents: [],
            recent_trips: [],
            quality_metrics: {},
            mapWebUrl: "",
            mapWebRawUrl: "",
            lastUpdated: new Date().toLocaleTimeString(),
        });

        this.map = null;
        this.busMarkers = {};
        this.routeLayers = [];
        this.complianceChart = null;
        this.routesChart = null;
        this.incidentsChart = null;
        this.pollInterval = null;
        this._lastData = null;

        onWillStart(async () => {
            try {
                await loadJS("/web/static/lib/Chart/Chart.js");
            } catch (err) {
                console.error("Error al cargar biblioteca Chart.js en Odoo:", err);
            }
        });

        onMounted(async () => {
            await this.loadData(false);
            // Dar un tick para que los refs de canvas y mapa estén renderizados en el DOM
            setTimeout(() => {
                this.initMap();
                this.initCharts();
                if (this._lastData) {
                    this.updateCharts(this._lastData);
                }
            }, 100);

            // Refresco periódico cada 20 segundos
            this.pollInterval = setInterval(() => {
                this.loadData(true);
            }, 20000);
        });

        onWillUnmount(() => {
            if (this.pollInterval) {
                clearInterval(this.pollInterval);
            }
            if (this.map) {
                this.map.remove();
                this.map = null;
            }
            if (this.complianceChart) {
                this.complianceChart.destroy();
                this.complianceChart = null;
            }
            if (this.routesChart) {
                this.routesChart.destroy();
                this.routesChart = null;
            }
            if (this.incidentsChart) {
                this.incidentsChart.destroy();
                this.incidentsChart = null;
            }
        });
    }

    async setPeriod(period) {
        if (this.state.period === period) return;
        this.state.period = period;
        await this.loadData(false);
    }

    reloadMapIframe() {
        if (this.mapIframeRef.el && this.state.mapWebUrl) {
            const currentSrc = this.state.mapWebUrl;
            this.mapIframeRef.el.src = "";
            setTimeout(() => {
                if (this.mapIframeRef.el) {
                    this.mapIframeRef.el.src = currentSrc;
                }
            }, 50);
        }
    }

    async loadData(isSilent = false) {
        if (!isSilent) {
            this.state.loading = true;
        }
        try {
            const data = await this.rpc("/transport/dashboard/data", {
                period: this.state.period,
            });

            if (data && data.status === "ok") {
                this._lastData = data;
                this.state.kpis = data.kpis || {};
                this.state.buses = data.buses || [];
                this.state.routes = data.routes || [];
                this.state.recent_incidents = data.recent_incidents || [];
                this.state.recent_trips = data.recent_trips || [];
                this.state.quality_metrics = data.quality_metrics || {};
                this.state.mapWebUrl = data.map_web_url || "";
                this.state.mapWebRawUrl = data.map_web_raw_url || "";
                this.state.lastUpdated = data.timestamp ? data.timestamp.split(" ")[1] : new Date().toLocaleTimeString();

                this.updateMapRoutes(this.state.routes);
                this.updateMapBuses(this.state.buses);
                this.updateCharts(data);
            }
        } catch (err) {
            console.error("Error al cargar telemetría del dashboard:", err);
            if (!isSilent) {
                this.notification.add("No se pudo sincronizar la telemetría del transporte", {
                    type: "danger",
                });
            }
        } finally {
            this.state.loading = false;
        }
    }

    /* ----------------------------------------------------
       MAPA LEAFLET NATIVO
    ---------------------------------------------------- */
    initMap() {
        if (!this.mapRef.el || typeof L === "undefined") {
            return;
        }

        // Centro inicial: Ambato (Campus Huachi - Campus Ingahurco)
        this.map = L.map(this.mapRef.el, {
            center: [-1.258, -78.625],
            zoom: 13,
            zoomControl: true,
        });

        // Capa de mapas satelital/urbano nítida y moderna (OpenStreetMap)
        L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
            maxZoom: 19,
            attribution: "© OpenStreetMap contributors, © CARTO",
        }).addTo(this.map);

        this.updateMapRoutes(this.state.routes);
        this.updateMapBuses(this.state.buses);
    }

    resetMapView() {
        if (this.map) {
            this.map.setView([-1.258, -78.625], 13);
        }
    }

    updateMapRoutes(routes) {
        if (!this.map || !routes) return;

        // Limpiar rutas anteriores
        this.routeLayers.forEach(l => this.map.removeLayer(l));
        this.routeLayers = [];

        routes.forEach(r => {
            // Trazado de Ida (Azul)
            if (r.outbound_coords && r.outbound_coords.length > 1) {
                const poly = L.polyline(r.outbound_coords, {
                    color: "#0284c7",
                    weight: 4,
                    opacity: 0.8,
                    smoothFactor: 1,
                }).addTo(this.map);

                poly.bindTooltip(`<b>${r.code}</b>: ${r.name} (Ida: ${r.outbound_km} km)`, {
                    sticky: true,
                });
                this.routeLayers.push(poly);
            }

            // Trazado de Regreso (Naranja)
            if (r.return_coords && r.return_coords.length > 1) {
                const poly = L.polyline(r.return_coords, {
                    color: "#ea580c",
                    weight: 4,
                    opacity: 0.8,
                    dashArray: "6, 6",
                    smoothFactor: 1,
                }).addTo(this.map);

                poly.bindTooltip(`<b>${r.code}</b>: ${r.name} (Regreso: ${r.return_km} km)`, {
                    sticky: true,
                });
                this.routeLayers.push(poly);
            }
        });
    }

    updateMapBuses(buses) {
        if (!this.map || !buses) return;

        const currentIds = new Set(buses.map(b => b.id));

        // Eliminar buses que ya no existen
        for (const id in this.busMarkers) {
            if (!currentIds.has(parseInt(id))) {
                this.map.removeLayer(this.busMarkers[id]);
                delete this.busMarkers[id];
            }
        }

        buses.forEach(b => {
            if (!b.lat || !b.lon) return;

            const isOnline = b.status === "in_progress" || b.status === "online";
            const markerColor = b.status === "in_progress" ? "#38bdf8" : (isOnline ? "#22c55e" : "#94a3b8");

            const customIcon = L.divIcon({
                className: "custom-bus-icon-container",
                html: `
                    <div class="bus-pin-wrapper">
                        <div class="bus-pin ${isOnline ? 'pulse' : ''}" style="background-color: ${markerColor}">
                            <i class="fa fa-bus" style="color: #ffffff; font-size: 13px;"></i>
                        </div>
                        <div class="bus-plate-label">${b.license_plate}</div>
                    </div>
                `,
                iconSize: [42, 42],
                iconAnchor: [21, 21],
                popupAnchor: [0, -20],
            });

            if (this.busMarkers[b.id]) {
                // Actualizar posición existente
                this.busMarkers[b.id].setLatLng([b.lat, b.lon]);
                this.busMarkers[b.id].setIcon(customIcon);
            } else {
                // Crear nuevo marcador
                const marker = L.marker([b.lat, b.lon], { icon: customIcon }).addTo(this.map);
                this.busMarkers[b.id] = marker;
            }

            // Popup interactivo
            const popupContent = `
                <div class="bus-popup-content p-2" style="min-width: 200px;">
                    <div class="fw-bold fs-6 text-primary mb-1">${b.license_plate}</div>
                    <div class="text-muted small mb-1">${b.name}</div>
                    <div class="small mb-1"><b>Conductor:</b> ${b.driver}</div>
                    <div class="small mb-1"><b>Ruta:</b> ${b.current_route}</div>
                    <div class="small mb-1"><b>Velocidad:</b> <span class="badge bg-info text-white">${b.speed} km/h</span></div>
                    <div class="small mb-2"><b>Estado:</b> <span class="badge ${isOnline ? 'bg-success' : 'bg-secondary'}">${b.status_label}</span></div>
                    <button class="btn btn-sm btn-outline-primary w-100" onclick="window.__openBusVehicle(${b.id})">
                        <i class="fa fa-eye me-1"></i> Ver Ficha del Vehículo
                    </button>
                </div>
            `;
            this.busMarkers[b.id].bindPopup(popupContent);
        });

        // Registrar handler global para el popup
        window.__openBusVehicle = (id) => {
            this.openVehicle(id);
        };
    }

    /* ----------------------------------------------------
       GRÁFICOS ANALÍTICOS (CHART.JS v2.9.4 NATIVO EN ODOO)
    ---------------------------------------------------- */
    initCharts() {
        if (typeof Chart === "undefined") {
            console.warn("Chart.js aún no está disponible en window.Chart");
            return;
        }

        // 1. Gráfico de Cumplimiento de Viajes (Doughnut)
        if (this.complianceChartRef.el) {
            if (this.complianceChart) {
                this.complianceChart.destroy();
            }
            const ctx1 = this.complianceChartRef.el.getContext("2d");
            this.complianceChart = new Chart(ctx1, {
                type: "doughnut",
                data: {
                    labels: ["Puntual", "Retrasado", "No Conforme", "En Curso"],
                    datasets: [{
                        data: [0, 0, 0, 0],
                        backgroundColor: ["#22c55e", "#f59e0b", "#ef4444", "#38bdf8"],
                        borderWidth: 2,
                        borderColor: "#1e293b",
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    legend: {
                        position: "bottom",
                        labels: {
                            fontColor: "#e2e8f0",
                            boxWidth: 12,
                            padding: 8,
                            fontSize: 11,
                        },
                    },
                    tooltips: {
                        callbacks: {
                            label: function(tooltipItem, chartData) {
                                const dataset = chartData.datasets[tooltipItem.datasetIndex];
                                const val = dataset.data[tooltipItem.index] || 0;
                                const total = dataset.data.reduce((a, b) => a + b, 0);
                                const pct = total > 0 ? Math.round((val / total) * 100) : 0;
                                return ` ${chartData.labels[tooltipItem.index]}: ${val} (${pct}%)`;
                            },
                        },
                    },
                },
            });
        }

        // 2. Gráfico de Desempeño por Línea (Horizontal Bar)
        if (this.routesChartRef.el) {
            if (this.routesChart) {
                this.routesChart.destroy();
            }
            const ctx2 = this.routesChartRef.el.getContext("2d");
            this.routesChart = new Chart(ctx2, {
                type: "horizontalBar",
                data: {
                    labels: [],
                    datasets: [{
                        label: "Puntualidad (%)",
                        data: [],
                        backgroundColor: "#0284c7",
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    legend: { display: false },
                    scales: {
                        xAxes: [{
                            ticks: {
                                min: 0,
                                max: 100,
                                fontColor: "#94a3b8",
                                callback: (v) => v + "%",
                            },
                            gridLines: { color: "#334155" },
                        }],
                        yAxes: [{
                            ticks: { fontColor: "#e2e8f0", fontSize: 11 },
                            gridLines: { display: false },
                        }],
                    },
                    tooltips: {
                        callbacks: {
                            label: (item) => ` Puntualidad: ${item.xLabel}%`,
                        },
                    },
                },
            });
        }

        // 3. Gráfico de Desglose de Incidencias (Vertical Bar)
        if (this.incidentsChartRef.el) {
            if (this.incidentsChart) {
                this.incidentsChart.destroy();
            }
            const ctx3 = this.incidentsChartRef.el.getContext("2d");
            this.incidentsChart = new Chart(ctx3, {
                type: "bar",
                data: {
                    labels: ["Desvíos", "Retrasos", "P. Omitidas", "GPS Perdido"],
                    datasets: [{
                        label: "Total Registrado",
                        data: [0, 0, 0, 0],
                        backgroundColor: ["#ef4444", "#f59e0b", "#ec4899", "#8b5cf6"],
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    legend: { display: false },
                    scales: {
                        yAxes: [{
                            ticks: {
                                beginAtZero: true,
                                stepSize: 1,
                                fontColor: "#94a3b8",
                            },
                            gridLines: { color: "#334155" },
                        }],
                        xAxes: [{
                            ticks: { fontColor: "#e2e8f0", fontSize: 11 },
                            gridLines: { display: false },
                        }],
                    },
                    tooltips: {
                        callbacks: {
                            label: (item) => ` Total: ${item.yLabel} evento(s)`,
                        },
                    },
                },
            });
        }
    }

    updateCharts(data) {
        if (!data) return;

        // 1. Actualizar dona de cumplimiento
        if (this.complianceChart && data.trip_compliance_distribution) {
            const dist = data.trip_compliance_distribution;
            this.complianceChart.data.datasets[0].data = [
                dist.compliant || 0,
                dist.delayed || 0,
                dist.non_compliant || 0,
                dist.in_progress || 0,
            ];
            this.complianceChart.update();
        }

        // 2. Actualizar barras de puntualidad por línea
        if (this.routesChart && data.routes_performance && data.routes_performance.length) {
            const validRoutes = data.routes_performance.filter(r => r.route_code && (r.total_trips > 0 || r.route_code.startsWith("UTA")));
            this.routesChart.data.labels = validRoutes.map(r => r.route_code);
            this.routesChart.data.datasets[0].data = validRoutes.map(r => r.punctuality_rate);
            this.routesChart.update();
        }

        // 3. Actualizar barras de desglose de incidencias
        if (this.incidentsChart && data.incidents_breakdown) {
            const inc = data.incidents_breakdown;
            const totalDelays = (inc.delays_low || 0) + (inc.delays_med || 0);
            this.incidentsChart.data.datasets[0].data = [
                inc.deviations || 0,
                totalDelays,
                inc.missed_stops || 0,
                inc.gps_lost || 0,
            ];
            this.incidentsChart.update();
        }
    }

    /* ----------------------------------------------------
       NAVEGACIÓN INTERNA EN ODOO
    ---------------------------------------------------- */
    openTrip(tripId) {
        if (!tripId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "transport.trip",
            res_id: tripId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openIncident(incidentId) {
        if (!incidentId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "transport.trip.incident",
            res_id: incidentId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openVehicle(vehicleId) {
        if (!vehicleId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "fleet.vehicle",
            res_id: vehicleId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

TransportDashboardClientAction.template = "fleet_traccar.TransportDashboard";

// Registrar en la categoría de acciones de Odoo 16
registry.category("actions").add("transport_dashboard_client_action", TransportDashboardClientAction);
