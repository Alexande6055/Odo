import React from 'react';
import { 
  Compass, 
  Layers, 
  Settings, 
  Sparkles, 
  Car,
  ChevronDown
} from 'lucide-react';
import type { Device, MapTileLayer } from '../types/traccar';

interface HeaderProps {
  devices: Device[];
  selectedDeviceId: number | null;
  tileLayer: MapTileLayer;
  isConnected: boolean;
  isDemoMode: boolean;
  isCompact: boolean;
  onSelectDevice: (deviceId: number | null) => void;
  onTileLayerChange: (layer: MapTileLayer) => void;
  onToggleDemoMode: () => void;
  onOpenSettings: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  devices,
  selectedDeviceId,
  tileLayer,
  isConnected,
  isDemoMode,
  isCompact,
  onSelectDevice,
  onTileLayerChange,
  onToggleDemoMode,
  onOpenSettings,
}) => {
  return (
    <header className="relative z-[1000] w-full px-4 py-2.5 glass-panel border-b border-slate-700/60 flex items-center justify-between">
      {/* Brand & Vehicle Selector */}
      <div className="flex items-center space-x-3 sm:space-x-4">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-md shadow-cyan-500/20">
            <Compass className="w-5 h-5 animate-spin-slow" />
          </div>
          {!isCompact && (
            <div>
              <h1 className="text-sm font-bold tracking-tight text-white flex items-center space-x-1.5">
                <span>Traccar &amp; Odoo GPS</span>
                {isDemoMode && (
                  <span className="text-[10px] bg-amber-500/20 text-amber-300 px-1.5 py-0.2 rounded border border-amber-500/30">
                    DEMO
                  </span>
                )}
              </h1>
              <p className="text-[10px] text-slate-400">Monitoreo en Tiempo Real</p>
            </div>
          )}
        </div>

        {/* Vehicle Selector Dropdown */}
        <div className="relative">
          <select
            value={selectedDeviceId ?? ''}
            onChange={(e) => {
              const val = e.target.value;
              onSelectDevice(val ? Number(val) : null);
            }}
            className="appearance-none bg-slate-800 hover:bg-slate-750 text-white text-xs font-semibold pl-8 pr-8 py-1.5 rounded-xl border border-slate-700 shadow focus:outline-none focus:ring-2 focus:ring-cyan-500/50 cursor-pointer transition max-w-[200px] truncate"
          >
            <option value="">Todos los vehículos ({devices.length})</option>
            {devices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} {d.status === 'online' ? '🟢' : '⚪'}
              </option>
            ))}
          </select>
          <Car className="w-3.5 h-3.5 text-cyan-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>
      </div>

      {/* Controls & Tools */}
      <div className="flex items-center space-x-2">
        {/* Live indicator */}
        <div className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-slate-800/80 border border-slate-700/60 text-[11px]">
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
          <span className="text-slate-300 hidden sm:inline">
            {isConnected ? 'En Vivo' : 'Desconectado'}
          </span>
        </div>

        {/* Tile layer selector */}
        <div className="relative">
          <select
            value={tileLayer}
            onChange={(e) => onTileLayerChange(e.target.value as MapTileLayer)}
            className="appearance-none bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-medium pl-7 pr-6 py-1.5 rounded-xl border border-slate-700 focus:outline-none cursor-pointer"
            title="Cambiar capa del mapa"
          >
            <option value="dark">Mapa Oscuro</option>
            <option value="light">Mapa Claro</option>
            <option value="streets">Calles OSM</option>
            <option value="satellite">Satélite Esri</option>
          </select>
          <Layers className="w-3.5 h-3.5 text-slate-400 absolute left-2 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>

        {/* Demo Mode Button */}
        <button
          onClick={onToggleDemoMode}
          className={`flex items-center space-x-1 px-2.5 py-1.5 rounded-xl text-xs font-semibold border transition cursor-pointer ${
            isDemoMode
              ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 hover:bg-amber-500/30'
              : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
          }`}
          title="Alternar recorrido simulado para pruebas"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span className="hidden md:inline">{isDemoMode ? 'Modo Real' : 'Simular Ruta'}</span>
        </button>

        {/* Settings Button */}
        <button
          onClick={onOpenSettings}
          className="p-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition cursor-pointer"
          title="Ajustes de conexión Traccar & Odoo"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
