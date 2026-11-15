import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import type { Device, Position, RoutePoint, MapTileLayer } from '../types/traccar';
import { knotsToKmh } from '../services/traccarApi';

interface MapProps {
  devices: Device[];
  positions: Position[];
  selectedDeviceId: number | null;
  route: RoutePoint[];
  playbackIndex: number | null;
  tileLayer: MapTileLayer;
  autoCenter: boolean;
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
  onSelectDevice,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const markersGroupRef = useRef<L.LayerGroup | null>(null);
  const routeLayerRef = useRef<L.LayerGroup | null>(null);
  const playbackMarkerRef = useRef<L.Marker | null>(null);

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [-12.046374, -77.042793],
      zoom: 13,
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

    mapInstanceRef.current = map;

    // Trigger invalidateSize to ensure tiles render immediately
    setTimeout(() => {
      map.invalidateSize();
    }, 100);

    const resizeObserver = new ResizeObserver(() => {
      map.invalidateSize();
    });
    resizeObserver.observe(mapContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      map.remove();
      mapInstanceRef.current = null;
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

  return (
    <div className="relative w-full h-full flex-1 min-h-[350px]">
      <div ref={mapContainerRef} className="absolute inset-0 w-full h-full" />
    </div>
  );
};
