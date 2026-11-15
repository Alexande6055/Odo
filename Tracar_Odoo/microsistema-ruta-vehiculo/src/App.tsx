import { useState, useEffect, useRef } from 'react';
import { Map } from './components/Map';
import { Header } from './components/Header';
import { VehicleCard } from './components/VehicleCard';
import { PlaybackControls } from './components/PlaybackControls';
import { SettingsModal } from './components/SettingsModal';
import type { Device, Position, RoutePoint, MapTileLayer } from './types/traccar';
import { TraccarService } from './services/traccarApi';

export function App() {
  const queryParams = new URLSearchParams(window.location.search);
  const paramDeviceId = queryParams.get('deviceId');
  const paramImei = queryParams.get('imei');
  const isIframe = window.self !== window.top || queryParams.get('compact') === 'true';

  const [devices, setDevices] = useState<Device[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(
    paramDeviceId ? Number(paramDeviceId) : null
  );

  const [route, setRoute] = useState<RoutePoint[]>([]);
  const [playbackIndex, setPlaybackIndex] = useState<number | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speedMultiplier, setSpeedMultiplier] = useState(1);
  const [isLoadingRoute, setIsLoadingRoute] = useState(false);

  const [tileLayer, setTileLayer] = useState<MapTileLayer>(
    (localStorage.getItem('map_tile_layer') as MapTileLayer) || 'streets'
  );
  const [autoCenter, setAutoCenter] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [isDemoMode, setIsDemoMode] = useState(queryParams.get('demo') === 'true');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const playbackTimerRef = useRef<any>(null);

  useEffect(() => {
    const savedUser = localStorage.getItem('traccar_user') || 'juanperzezss@gmail.com';
    const savedPass = localStorage.getItem('traccar_pass') || '';
    TraccarService.setCredentials(savedUser, savedPass);
  }, []);

  const fetchLiveTrackingData = async () => {
    if (isDemoMode) return;

    try {
      const [fetchedDevices, fetchedPositions] = await Promise.all([
        TraccarService.getDevices(),
        TraccarService.getPositions(),
      ]);

      if (fetchedDevices && fetchedDevices.length > 0) {
        setDevices(fetchedDevices);
        setIsConnected(true);

        if (paramImei && !selectedDeviceId) {
          const matched = fetchedDevices.find((d) => d.uniqueId === paramImei);
          if (matched) {
            setSelectedDeviceId(matched.id);
          }
        }
      } else {
        setIsConnected(false);
      }

      if (fetchedPositions) {
        setPositions(fetchedPositions);
      }
    } catch (err) {
      console.warn('Error fetching live Traccar data:', err);
      setIsConnected(false);
    }
  };

  useEffect(() => {
    if (isDemoMode) {
      loadDemoData();
      return;
    }

    fetchLiveTrackingData();
    const interval = setInterval(fetchLiveTrackingData, 5000);

    const unsubscribeWs = TraccarService.connectWebSocket(
      (newPositions) => {
        setPositions((prev) => {
          const posMap: Record<number, Position> = {};
          prev.forEach((p) => {
            posMap[p.deviceId] = p;
          });
          newPositions.forEach((p) => {
            posMap[p.deviceId] = p;
          });
          return Object.values(posMap);
        });
        setIsConnected(true);
      },
      (newDevices) => {
        setDevices(newDevices);
      }
    );

    return () => {
      clearInterval(interval);
      unsubscribeWs();
    };
  }, [isDemoMode, paramImei]);

  const loadDemoData = () => {
    const { device, route: demoRoute } = TraccarService.generateDemoRoute();
    setDevices([device]);
    setSelectedDeviceId(device.id);

    const latestPt = demoRoute[demoRoute.length - 1];
    setPositions([
      {
        id: 99991,
        deviceId: device.id,
        latitude: latestPt.latitude,
        longitude: latestPt.longitude,
        speed: latestPt.speed / 1.852,
        course: latestPt.course,
        fixTime: latestPt.fixTime,
        deviceTime: latestPt.fixTime,
        attributes: {
          batteryLevel: latestPt.batteryLevel,
          ignition: latestPt.ignition,
        },
      },
    ]);

    setRoute(demoRoute);
    setPlaybackIndex(0);
    setIsPlaying(true);
    setIsConnected(true);
  };

  const handleToggleDemoMode = () => {
    if (!isDemoMode) {
      setIsDemoMode(true);
      loadDemoData();
    } else {
      setIsDemoMode(false);
      setRoute([]);
      setPlaybackIndex(null);
      setIsPlaying(false);
      fetchLiveTrackingData();
    }
  };

  const handleLoadRoute = async () => {
    if (!selectedDeviceId) return;

    if (isDemoMode) {
      const { route: demoRoute } = TraccarService.generateDemoRoute();
      setRoute(demoRoute);
      setPlaybackIndex(0);
      setIsPlaying(true);
      return;
    }

    setIsLoadingRoute(true);
    try {
      const now = new Date();
      const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
      const points = await TraccarService.getRoute(
        selectedDeviceId,
        yesterday.toISOString(),
        now.toISOString()
      );

      if (points && points.length > 0) {
        setRoute(points);
        setPlaybackIndex(0);
      } else {
        alert('No se encontraron registros de recorrido para este vehículo en las últimas 24 horas.');
      }
    } catch (err) {
      console.error('Error loading route:', err);
      alert('Error al consultar el recorrido desde Traccar.');
    } finally {
      setIsLoadingRoute(false);
    }
  };

  useEffect(() => {
    if (!isPlaying || playbackIndex === null || route.length === 0) {
      if (playbackTimerRef.current) clearInterval(playbackTimerRef.current);
      return;
    }

    const intervalMs = Math.max(80, 1000 / speedMultiplier);

    playbackTimerRef.current = setInterval(() => {
      setPlaybackIndex((prev) => {
        if (prev === null) return 0;
        if (prev >= route.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, intervalMs);

    return () => {
      if (playbackTimerRef.current) clearInterval(playbackTimerRef.current);
    };
  }, [isPlaying, speedMultiplier, route.length]);

  const selectedDevice = devices.find((d) => d.id === selectedDeviceId);
  const selectedPosition = positions.find((p) => p.deviceId === selectedDeviceId);

  return (
    <div className="relative w-screen h-screen flex flex-col bg-slate-900 overflow-hidden font-sans">
      <Header
        devices={devices}
        selectedDeviceId={selectedDeviceId}
        tileLayer={tileLayer}
        isConnected={isConnected}
        isDemoMode={isDemoMode}
        isCompact={isIframe}
        onSelectDevice={(id) => {
          setSelectedDeviceId(id);
          setRoute([]);
          setPlaybackIndex(null);
          setIsPlaying(false);
        }}
        onTileLayerChange={(layer) => {
          setTileLayer(layer);
          localStorage.setItem('map_tile_layer', layer);
        }}
        onToggleDemoMode={handleToggleDemoMode}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      <div className="relative flex-1 w-full h-full">
        <Map
          devices={devices}
          positions={positions}
          selectedDeviceId={selectedDeviceId}
          route={route}
          playbackIndex={playbackIndex}
          tileLayer={tileLayer}
          autoCenter={autoCenter}
          onSelectDevice={(deviceId) => {
            setSelectedDeviceId(deviceId);
          }}
        />

        {selectedDevice && (
          <VehicleCard
            device={selectedDevice}
            position={selectedPosition}
            hasRoute={route.length > 0}
            isLoadingRoute={isLoadingRoute}
            onLoadRoute={handleLoadRoute}
            onCenterMap={() => setAutoCenter((prev) => !prev)}
          />
        )}

        {route.length > 0 && playbackIndex !== null && (
          <PlaybackControls
            route={route}
            currentIndex={playbackIndex}
            isPlaying={isPlaying}
            speedMultiplier={speedMultiplier}
            onPlayPause={() => setIsPlaying(!isPlaying)}
            onReset={() => {
              setPlaybackIndex(0);
              setIsPlaying(false);
            }}
            onSeek={(idx) => setPlaybackIndex(idx)}
            onSpeedChange={(speed) => setSpeedMultiplier(speed)}
            onClose={() => {
              setRoute([]);
              setPlaybackIndex(null);
              setIsPlaying(false);
            }}
          />
        )}
      </div>

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onSave={(user, pass) => {
          TraccarService.setCredentials(user, pass);
          fetchLiveTrackingData();
        }}
      />
    </div>
  );
}

export default App;
