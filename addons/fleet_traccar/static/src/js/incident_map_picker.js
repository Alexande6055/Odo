/** @odoo-module **/

import { registry } from "@web/core/registry";
const { Component, onMounted, onWillUnmount, useEffect, useRef, xml } = owl;

const DEFAULT_LAT = -1.2687;
const DEFAULT_LNG = -78.6258;
const DEFAULT_ZOOM = 14;

export class IncidentMapPicker extends Component {
    setup() {
        this.mapContainerRef = useRef("mapContainer");
        this.map = null;
        this.marker = null;

        onMounted(() => {
            this._initMap();
        });

        // Sincronización bidireccional: si el usuario edita manualmente Latitud/Longitud, mover el marcador
        useEffect(
            (lat, lng) => {
                if (!this.map) {
                    return;
                }
                if (this._hasValidCoords(lat, lng)) {
                    this._placeMarker(lat, lng, false);
                } else if (this.marker) {
                    this.map.removeLayer(this.marker);
                    this.marker = null;
                }
            },
            () => [this.props.record.data.latitude, this.props.record.data.longitude]
        );

        onWillUnmount(() => {
            if (this.map) {
                this.map.remove();
                this.map = null;
                this.marker = null;
            }
        });
    }

    _hasValidCoords(lat, lng) {
        return (
            typeof lat === "number" &&
            typeof lng === "number" &&
            (lat !== 0 || lng !== 0) &&
            lat >= -90 &&
            lat <= 90 &&
            lng >= -180 &&
            lng <= 180
        );
    }

    _initMap() {
        const container = this.mapContainerRef.el;
        if (!container || typeof window.L === "undefined") {
            return;
        }

        const data = this.props.record.data || {};
        const hasCoords = this._hasValidCoords(data.latitude, data.longitude);
        const startLat = hasCoords ? data.latitude : DEFAULT_LAT;
        const startLng = hasCoords ? data.longitude : DEFAULT_LNG;

        this.map = window.L.map(container, {
            center: [startLat, startLng],
            zoom: hasCoords ? 16 : DEFAULT_ZOOM,
        });

        window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "&copy; OpenStreetMap",
        }).addTo(this.map);

        if (hasCoords) {
            this._placeMarker(startLat, startLng, false);
        }

        this.map.on("click", (ev) => {
            const lat = Number(ev.latlng.lat.toFixed(7));
            const lng = Number(ev.latlng.lng.toFixed(7));
            this._placeMarker(lat, lng, true);
        });

        setTimeout(() => {
            if (this.map) {
                this.map.invalidateSize();
            }
        }, 250);
    }

    _placeMarker(lat, lng, updateRecord) {
        if (!this.map || typeof window.L === "undefined") {
            return;
        }
        if (this.marker) {
            this.marker.setLatLng([lat, lng]);
        } else {
            this.marker = window.L.marker([lat, lng], { draggable: true }).addTo(this.map);
            this.marker.on("dragend", (ev) => {
                const pos = ev.target.getLatLng();
                this.props.record.update({
                    latitude: Number(pos.lat.toFixed(7)),
                    longitude: Number(pos.lng.toFixed(7)),
                });
            });
        }
        this.marker
            .bindPopup(`<b>Punto del evento</b><br/>Lat: ${lat}<br/>Lon: ${lng}`)
            .openPopup();
        this.map.panTo([lat, lng]);

        if (updateRecord) {
            this.props.record.update({
                latitude: lat,
                longitude: lng,
            });
        }
    }

    onCenterAmbato() {
        if (this.map) {
            this.map.setView([DEFAULT_LAT, DEFAULT_LNG], DEFAULT_ZOOM);
        }
    }

    onClearPoint() {
        if (this.marker && this.map) {
            this.map.removeLayer(this.marker);
            this.marker = null;
        }
        this.props.record.update({
            latitude: 0.0,
            longitude: 0.0,
        });
    }

    get formattedCoords() {
        const { latitude, longitude } = this.props.record.data || {};
        if (this._hasValidCoords(latitude, longitude)) {
            return `${Number(latitude).toFixed(6)}, ${Number(longitude).toFixed(6)}`;
        }
        return "Haz clic en el mapa para seleccionar la ubicación";
    }
}

IncidentMapPicker.template = xml`
    <div class="card border rounded-3 overflow-hidden shadow-sm my-2">
        <div class="card-header bg-dark text-white d-flex flex-wrap justify-content-between align-items-center py-2 px-3 gap-2">
            <div class="d-flex align-items-center gap-2 small">
                <i class="fa fa-map-marker text-danger"/>
                <span class="fw-semibold">Selector de Ubicación:</span>
                <span class="badge bg-secondary font-monospace" t-esc="formattedCoords"/>
            </div>
            <div class="d-flex gap-2">
                <button type="button" class="btn btn-sm btn-outline-light" t-on-click="onCenterAmbato">
                    <i class="fa fa-crosshairs me-1"/>Ambato / UTA
                </button>
                <button type="button" class="btn btn-sm btn-outline-warning" t-on-click="onClearPoint">
                    <i class="fa fa-eraser me-1"/>Limpiar
                </button>
            </div>
        </div>
        <div t-ref="mapContainer" style="width: 100%; height: 340px; z-index: 1;"/>
    </div>
`;

registry.category("view_widgets").add("incident_map_picker", IncidentMapPicker);
