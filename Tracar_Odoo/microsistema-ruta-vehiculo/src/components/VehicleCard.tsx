import React, { useState } from 'react';
import { 
  Car, 
  Battery, 
  Zap, 
  Clock, 
  Route as RouteIcon, 
  ChevronUp, 
  ChevronDown, 
  Focus
} from 'lucide-react';
import type { Device, Position } from '../types/traccar';
import { knotsToKmh } from '../services/traccarApi';

interface VehicleCardProps {
  device: Device;
  position?: Position;
  hasRoute: boolean;
  isLoadingRoute: boolean;
  onLoadRoute: () => void;
  onCenterMap: () => void;
}

export const VehicleCard: React.FC<VehicleCardProps> = ({
  device,
  position,
  hasRoute,
  isLoadingRoute,
  onLoadRoute,
  onCenterMap,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const speedKmh = position ? knotsToKmh(position.speed) : 0;
  const isOnline = device.status === 'online';
  const isMoving = speedKmh > 3;
  const battery = position?.attributes?.batteryLevel ?? device.attributes?.batteryLevel;
  const ignition = position?.attributes?.ignition ?? device.attributes?.ignition;

  return (
    <div className="absolute top-20 left-4 z-[990] w-80 glass-panel rounded-2xl p-4 shadow-2xl border border-slate-700/60 transition-all">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className={`p-2 rounded-xl ${
            isOnline 
              ? isMoving ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
              : 'bg-slate-700/40 text-slate-400 border border-slate-700'
          }`}>
            <Car className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-sm text-white tracking-wide leading-tight">
              {device.name}
            </h3>
            <p className="text-[11px] text-slate-400 font-mono">
              IMEI: {device.uniqueId}
            </p>
          </div>
        </div>

        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition cursor-pointer"
        >
          {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
        </button>
      </div>

      {!isCollapsed && (
        <>
          {/* Status Badge & Speed */}
          <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-slate-700/50">
            <div className="bg-slate-800/60 rounded-xl p-2.5 border border-slate-700/40">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block mb-0.5">
                Estado
              </span>
              <div className="flex items-center space-x-1.5">
                <span className={`w-2 h-2 rounded-full ${
                  isOnline 
                    ? isMoving ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                    : 'bg-slate-500'
                }`} />
                <span className="text-xs font-semibold text-white">
                  {isOnline ? (isMoving ? 'En movimiento' : 'Detenido') : 'Sin conexión'}
                </span>
              </div>
            </div>

            <div className="bg-slate-800/60 rounded-xl p-2.5 border border-slate-700/40">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block mb-0.5">
                Velocidad
              </span>
              <span className="text-sm font-bold text-cyan-400">
                {speedKmh} <span className="text-[10px] font-normal text-slate-400">km/h</span>
              </span>
            </div>
          </div>

          {/* Quick telemetry attributes */}
          <div className="mt-2.5 space-y-1.5 text-xs text-slate-300">
            {battery !== undefined && (
              <div className="flex items-center justify-between px-1">
                <span className="text-slate-400 flex items-center space-x-1">
                  <Battery className="w-3.5 h-3.5 text-slate-400" />
                  <span>Batería:</span>
                </span>
                <span className="font-semibold text-slate-200">{battery}%</span>
              </div>
            )}

            {ignition !== undefined && (
              <div className="flex items-center justify-between px-1">
                <span className="text-slate-400 flex items-center space-x-1">
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  <span>Ignición (Motor):</span>
                </span>
                <span className={`font-semibold ${ignition ? 'text-emerald-400' : 'text-slate-400'}`}>
                  {ignition ? 'Encendido' : 'Apagado'}
                </span>
              </div>
            )}

            {position?.fixTime && (
              <div className="flex items-center justify-between px-1">
                <span className="text-slate-400 flex items-center space-x-1">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>Última señal:</span>
                </span>
                <span className="text-slate-300 font-mono text-[11px]">
                  {new Date(position.fixTime).toLocaleTimeString()}
                </span>
              </div>
            )}
          </div>

          {/* Action buttons */}
          <div className="mt-4 pt-3 border-t border-slate-700/50 flex space-x-2">
            <button
              onClick={onCenterMap}
              className="flex-1 flex items-center justify-center space-x-1 py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white text-xs font-semibold border border-slate-700 transition cursor-pointer"
              title="Centrar mapa en el vehículo"
            >
              <Focus className="w-3.5 h-3.5" />
              <span>Centrar</span>
            </button>

            <button
              onClick={onLoadRoute}
              disabled={isLoadingRoute}
              className={`flex-1 flex items-center justify-center space-x-1 py-2 px-3 rounded-xl text-xs font-semibold transition cursor-pointer ${
                hasRoute
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40 hover:bg-amber-500/30'
                  : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-600/30'
              }`}
            >
              <RouteIcon className="w-3.5 h-3.5" />
              <span>{isLoadingRoute ? 'Cargando...' : hasRoute ? 'Ver Ruta' : 'Cargar Ruta'}</span>
            </button>
          </div>
        </>
      )}
    </div>
  );
};
