import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import type { Device, Position, RoutePoint, MapTileLayer, StopPoint } from '../types/traccar';
import { knotsToKmh } from '../services/traccarApi';

interface MapProps {
  devices: Device[];
  positions: Position[];
  selectedDeviceId: number | null;
  route: RoutePoint[];
  playbackIndex: number | null;
  tileLayer: MapTileLayer;
  autoCenter: boolean;
  stops?: StopPoint[];
  selectedStop?: StopPoint | null;
  fitAllTrigger?: number;
  onSelectDevice: (deviceId: number) => void;
}

// 100% Free OpenStreetMap tile layers (No Google Maps, No API keys required)
const TILE_SERVERS: Record<MapTileLayer, { url: string; attribution: string }> = {
  streets: {
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  },
  dark: {
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; OpenStreetMap &copy; CARTO',
  },
  light: {
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; OpenStreetMap &copy; CARTO',
  },
  satellite: {
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; Esri World Imagery',
  },
};

export const Map: React.FC<MapProps> = ({
  devices,
  positions,
  selectedDeviceId,
  route,
  playbackIndex,
  tileLayer,
  autoCenter,
  stops = [],
  selectedStop,
  fitAllTrigger,
  onSelectDevice,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const markersGroupRef = useRef<L.LayerGroup | null>(null);
  const routeLayerRef = useRef<L.LayerGroup | null>(null);
  const stopsLayerRef = useRef<L.LayerGroup | null>(null);
  const playbackMarkerRef = useRef<L.Marker | null>(null);

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    // Coordenadas iniciales por defecto: Ambato, Ecuador (Universidad Técnica de Ambato)
    const map = L.map(mapContainerRef.current, {
      center: [-1.2543, -78.6228],
      zoom: 14,
      zoomControl: false,
    });

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    const initialTiles = L.tileLayer(TILE_SERVERS[tileLayer].url, {
      attribution: TILE_SERVERS[tileLayer].attribution,
      maxZoom: 19,
    }).addTo(map);

    tileLayerRef.current = initialTiles;
    markersGroupRef.current = L.layerGroup().addTo(map);
    routeLayerRef.current = L.layerGroup().addTo(map);
    stopsLayerRef.current = L.layerGroup().addTo(map);

    mapInstanceRef.current = map;

    // Trigger invalidateSize to ensure tiles render immediately
    const initialTimer = setTimeout(() => {
      if (mapInstanceRef.current && mapContainerRef.current) {
        try {
          mapInstanceRef.current.invalidateSize();
        } catch {
          // ignore when unmounting
        }
      }
    }, 150);

    const resizeObserver = new ResizeObserver(() => {
      if (mapInstanceRef.current && mapContainerRef.current) {
        try {
          mapInstanceRef.current.invalidateSize();
        } catch {
          // ignore when unmounting or container detached
        }
      }
    });

    if (mapContainerRef.current) {
      resizeObserver.observe(mapContainerRef.current);
    }

    return () => {
      clearTimeout(initialTimer);
      resizeObserver.disconnect();
      if (mapInstanceRef.current) {
        try {
          mapInstanceRef.current.remove();
        } catch {
          // ignore unmount errors
        }
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update Tile Layer
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (tileLayerRef.current) {
      map.removeLayer(tileLayerRef.current);
    }

    const newTiles = L.tileLayer(TILE_SERVERS[tileLayer].url, {
      attribution: TILE_SERVERS[tileLayer].attribution,
      maxZoom: 19,
    }).addTo(map);

    tileLayerRef.current = newTiles;
    map.invalidateSize();
  }, [tileLayer]);

  // Update Devices & Realtime Markers
  useEffect(() => {
    const map = mapInstanceRef.current;
    const markersGroup = markersGroupRef.current;
    if (!map || !markersGroup) return;

    markersGroup.clearLayers();

    const deviceMap: Record<number, Device> = {};
    devices.forEach((d) => {
      deviceMap[d.id] = d;
    });

    const bounds: L.LatLngExpression[] = [];

    const activePositions = selectedDeviceId
      ? positions.filter((p) => p.deviceId === selectedDeviceId)
      : positions;

    activePositions.forEach((pos) => {
      if (!pos.latitude || !pos.longitude) return;

      const device = deviceMap[pos.deviceId];
      const isSelected = selectedDeviceId === pos.deviceId;
      const speedKmh = knotsToKmh(pos.speed);
      const isMoving = speedKmh > 3;
      const isOnline = device?.status === 'online';
      const course = pos.course || 0;

      bounds.push([pos.latitude, pos.longitude]);

      const iconHtml = `
        <div class="relative flex items-center justify-center cursor-pointer group">
          ${isOnline && isMoving ? '<div class="absolute w-12 h-12 rounded-full bg-emerald-500/30 gps-radar-pulse"></div>' : ''}
          ${isSelected ? '<div class="absolute w-14 h-14 rounded-full border-2 border-cyan-400 animate-ping opacity-40"></div>' : ''}
          
          <div class="relative flex items-center justify-center w-10 h-10 rounded-full shadow-xl transition-transform duration-200 group-hover:scale-110 ${
            isSelected 
              ? 'bg-cyan-500 border-2 border-white ring-4 ring-cyan-500/40 text-white' 
              : isOnline
                ? isMoving 
                  ? 'bg-emerald-600 border-2 border-white text-white' 
                  : 'bg-amber-500 border-2 border-white text-white'
                : 'bg-slate-700 border-2 border-slate-500 text-slate-300'
          }">
            <svg class="w-5 h-5" style="transform: rotate(${course}deg);" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 19V5m0 0l-4 4m4-4l4 4" />
            </svg>
          </div>

          <div class="absolute -bottom-6 left-1/2 -translate-x-1/2 whitespace-nowrap px-2 py-0.5 rounded-md bg-slate-900/90 text-[11px] font-semibold text-slate-100 shadow border border-slate-700 pointer-events-none">
            ${device?.name || `Dispositivo ${pos.deviceId}`}
          </div>
        </div>
      `;

      const customIcon = L.divIcon({
        html: iconHtml,
        className: 'vehicle-marker-wrapper',
        iconSize: [40, 40],
        iconAnchor: [20, 20],
      });

      const marker = L.marker([pos.latitude, pos.longitude], { icon: customIcon });

      marker.on('click', () => {
        onSelectDevice(pos.deviceId);
      });

      const popupContent = `
        <div class="p-3.5 text-slate-100 font-sans min-w-[210px]">
          <div class="flex items-center justify-between pb-2 mb-2 border-b border-slate-700">
            <span class="font-bold text-sm tracking-wide text-white">${device?.name || 'Vehículo'}</span>
            <span class="px-2 py-0.5 text-[10px] font-semibold rounded-full ${
              isOnline ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-slate-700 text-slate-400'
            }">
              ${isOnline ? (isMoving ? 'En Movimiento' : 'Detenido') : 'Offline'}
            </span>
          </div>
          <div class="space-y-1.5 text-xs text-slate-300">
            <div class="flex justify-between">
              <span class="text-slate-400">Velocidad:</span>
              <span class="font-semibold text-cyan-400 text-sm">${speedKmh} km/h</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">Rumbo:</span>
              <span>${course}°</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">IMEI:</span>
              <span class="font-mono text-[11px]">${device?.uniqueId || 'N/A'}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">Última señal:</span>
              <span class="text-[11px]">${pos.fixTime ? new Date(pos.fixTime).toLocaleTimeString() : 'Reciente'}</span>
            </div>
          </div>
        </div>
      `;

      marker.bindPopup(popupContent, { className: 'custom-leaflet-popup' });
      markersGroup.addLayer(marker);
    });

    if (autoCenter && bounds.length > 0 && playbackIndex === null) {
      if (bounds.length === 1) {
        map.panTo(bounds[0]);
      } else {
        map.fitBounds(L.latLngBounds(bounds), { padding: [50, 50], maxZoom: 16 });
      }
    }
  }, [devices, positions, selectedDeviceId, autoCenter, playbackIndex]);

  // Render Route Polyline & Endpoints
  useEffect(() => {
    const map = mapInstanceRef.current;
    const routeLayer = routeLayerRef.current;
    if (!map || !routeLayer) return;

    routeLayer.clearLayers();

    if (!route || route.length === 0) return;

    const latLngs: L.LatLngExpression[] = route.map((pt) => [pt.latitude, pt.longitude]);

    const routeOutline = L.polyline(latLngs, {
      color: '#0891b2',
      weight: 7,
      opacity: 0.5,
      lineCap: 'round',
      lineJoin: 'round',
    });

    const routeLine = L.polyline(latLngs, {
      color: '#06b6d4',
      weight: 4,
      opacity: 0.9,
      lineCap: 'round',
      lineJoin: 'round',
    });

    routeLayer.addLayer(routeOutline);
    routeLayer.addLayer(routeLine);

    // Start Pin (Green)
    const startPt = route[0];
    const startIcon = L.divIcon({
      html: `
        <div class="w-6 h-6 rounded-full bg-emerald-500 border-2 border-white flex items-center justify-center shadow-lg text-[10px] font-bold text-white">
          A
        </div>
      `,
      className: 'route-start-marker',
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });
    const startMarker = L.marker([startPt.latitude, startPt.longitude], { icon: startIcon });
    startMarker.bindPopup('<b class="text-xs">Punto Inicial del Recorrido</b>', { className: 'custom-leaflet-popup' });
    routeLayer.addLayer(startMarker);

    // End Pin (Red/Flag)
    const endPt = route[route.length - 1];
    const endIcon = L.divIcon({
      html: `
        <div class="w-6 h-6 rounded-full bg-rose-500 border-2 border-white flex items-center justify-center shadow-lg text-[10px] font-bold text-white">
          B
        </div>
      `,
      className: 'route-end-marker',
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });
    const endMarker = L.marker([endPt.latitude, endPt.longitude], { icon: endIcon });
    endMarker.bindPopup('<b class="text-xs">Punto Final del Recorrido</b>', { className: 'custom-leaflet-popup' });
    routeLayer.addLayer(endMarker);

    if (autoCenter && playbackIndex === null) {
      map.fitBounds(L.latLngBounds(latLngs), { padding: [60, 60], maxZoom: 16 });
    }
  }, [route]);

  // Render University Route Stops (Puntos de Control UTA)
  useEffect(() => {
    const map = mapInstanceRef.current;
    const stopsLayer = stopsLayerRef.current;
    if (!map || !stopsLayer) return;

    stopsLayer.clearLayers();
    if (!stops || stops.length === 0) return;

    const bounds: L.LatLngExpression[] = [];

    stops.forEach((stop, index) => {
      if (!stop.lat || !stop.lon) return;
      bounds.push([stop.lat, stop.lon]);

      const seqNum = stop.seq || index + 1;
      let statusColor = 'bg-cyan-500';
      let statusBadge = 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';
      let statusText = 'Programada';

      if (stop.status === 'visited') {
        statusColor = 'bg-emerald-500';
        statusBadge = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
        statusText = 'Cumplida a Tiempo';
      } else if (stop.status === 'delayed') {
        statusColor = 'bg-amber-500';
        statusBadge = 'bg-amber-500/20 text-amber-300 border-amber-500/40';
        statusText = `Con Retraso (${stop.delay || 0} min)`;
      } else if (stop.status === 'missed') {
        statusColor = 'bg-rose-500';
        statusBadge = 'bg-rose-500/20 text-rose-300 border-rose-500/40';
        statusText = 'Parada Omitida';
      }

      const stopIcon = L.divIcon({
        html: `
          <div class="relative flex items-center justify-center">
            <div class="w-7 h-7 rounded-full ${statusColor} border-2 border-white shadow-xl flex items-center justify-center text-xs font-bold text-white hover:scale-125 transition-transform duration-200">
              ${seqNum}
            </div>
            <div class="absolute -bottom-5 left-1/2 -translate-x-1/2 whitespace-nowrap px-1.5 py-0.2 rounded bg-slate-900/90 text-[10px] text-slate-200 border border-slate-700 shadow pointer-events-none">
              ${stop.name}
            </div>
          </div>
        `,
        className: 'university-stop-marker',
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });

      const marker = L.marker([stop.lat, stop.lon], { icon: stopIcon });

      const popupHtml = `
        <div class="p-3 text-slate-100 font-sans min-w-[200px]">
          <div class="flex items-center justify-between pb-1.5 mb-1.5 border-b border-slate-700">
            <span class="font-bold text-sm text-cyan-400">${seqNum}. ${stop.name}</span>
          </div>
          <div class="space-y-1 text-xs">
            <span class="inline-block px-2 py-0.5 text-[10px] font-semibold rounded-full border ${statusBadge} mb-1">
              ${statusText}
            </span>
            ${stop.schedTime ? `<div class="text-slate-300">Horario previsto: <b class="text-white">${stop.schedTime}</b></div>` : ''}
            ${stop.actualTime ? `<div class="text-slate-300">Llegada real: <b class="text-emerald-400">${stop.actualTime}</b></div>` : ''}
          </div>
        </div>
      `;

      marker.bindPopup(popupHtml, { className: 'custom-leaflet-popup' });
      stopsLayer.addLayer(marker);
    });

    if (autoCenter && bounds.length > 0 && (!route || route.length === 0)) {
      map.fitBounds(L.latLngBounds(bounds), { padding: [60, 60], maxZoom: 16 });
    }
  }, [stops, autoCenter, route]);

  // Handle Playback Marker Animation
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (playbackIndex === null || !route || route.length === 0 || !route[playbackIndex]) {
      if (playbackMarkerRef.current) {
        map.removeLayer(playbackMarkerRef.current);
        playbackMarkerRef.current = null;
      }
      return;
    }

    const currentPoint = route[playbackIndex];
    const latLng: L.LatLngExpression = [currentPoint.latitude, currentPoint.longitude];

    const playbackIconHtml = `
      <div class="relative flex items-center justify-center">
        <div class="absolute w-14 h-14 rounded-full bg-amber-400/30 animate-ping"></div>
        <div class="relative w-11 h-11 rounded-full bg-gradient-to-tr from-amber-500 to-yellow-400 border-2 border-white shadow-2xl flex items-center justify-center text-slate-900">
          <svg class="w-6 h-6 transform transition-transform duration-100" style="transform: rotate(${currentPoint.course}deg);" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2L4.5 20.29l.71.71L12 18l6.79 3 .71-.71z"/>
          </svg>
        </div>
        <div class="absolute -top-7 px-2 py-0.5 rounded-full bg-amber-500 text-[11px] font-bold text-slate-950 shadow-md">
          ${currentPoint.speed} km/h
        </div>
      </div>
    `;

    const playbackIcon = L.divIcon({
      html: playbackIconHtml,
      className: 'playback-active-marker',
      iconSize: [44, 44],
      iconAnchor: [22, 22],
    });

    if (!playbackMarkerRef.current) {
      playbackMarkerRef.current = L.marker(latLng, { icon: playbackIcon, zIndexOffset: 1000 }).addTo(map);
    } else {
      playbackMarkerRef.current.setLatLng(latLng);
      playbackMarkerRef.current.setIcon(playbackIcon);
    }

    map.panTo(latLng, { animate: true, duration: 0.3 });
  }, [playbackIndex, route]);

  // Smoothly pan & zoom to selected stop
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !selectedStop || !selectedStop.lat || !selectedStop.lon) return;
    map.flyTo([selectedStop.lat, selectedStop.lon], 17, {
      duration: 1.2,
      easeLinearity: 0.25,
    });
  }, [selectedStop]);

  // Fit all bounds (stops + vehicles + route)
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !fitAllTrigger) return;
    const allBounds: L.LatLngExpression[] = [];
    stops.forEach((s) => {
      if (s.lat && s.lon) allBounds.push([s.lat, s.lon]);
    });
    positions.forEach((p) => {
      if (p.latitude && p.longitude) allBounds.push([p.latitude, p.longitude]);
    });
    route.forEach((r) => {
      if (r.latitude && r.longitude) allBounds.push([r.latitude, r.longitude]);
    });
    if (allBounds.length > 0) {
      map.fitBounds(L.latLngBounds(allBounds), { padding: [60, 60], maxZoom: 16 });
    }
  }, [fitAllTrigger]);

  return (
    <div className="relative w-full h-full flex-1 min-h-[350px]">
      <div ref={mapContainerRef} className="absolute inset-0 w-full h-full" />

      {/* Floating Modern Map Legend */}
      <div className="absolute bottom-4 left-4 z-[900] glass-panel px-3 py-1.5 rounded-xl text-[10px] text-slate-300 border border-slate-700/60 shadow-lg flex flex-wrap items-center gap-2.5 pointer-events-auto backdrop-blur-md select-none">
        <span className="font-bold text-slate-200 uppercase tracking-wider text-[9px] text-cyan-400">Leyenda:</span>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-sm" />
          <span>Bus Online / Ok</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-amber-400 shadow-sm" />
          <span>Retraso (&gt;5m)</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-rose-500 shadow-sm" />
          <span>Omitida</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-1 rounded bg-cyan-400 shadow-sm" />
          <span>Ruta</span>
        </div>
      </div>
    </div>
  );
};
