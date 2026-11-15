import React, { useState } from 'react';
import { 
  Flag, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  Clock, 
  ChevronRight, 
  ChevronDown, 
  ChevronUp,
  Compass
} from 'lucide-react';
import type { StopPoint } from '../types/traccar';

interface StopsListOverlayProps {
  stops: StopPoint[];
  routeName?: string;
  onSelectStop: (stop: StopPoint) => void;
  onFitAllStops: () => void;
}

export const StopsListOverlay: React.FC<StopsListOverlayProps> = ({
  stops,
  routeName,
  onSelectStop,
  onFitAllStops,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!stops || stops.length === 0) return null;

  const visitedCount = stops.filter((s) => s.status === 'visited').length;
  const delayedCount = stops.filter((s) => s.status === 'delayed').length;
  const missedCount = stops.filter((s) => s.status === 'missed').length;
  const completionRate = Math.round((visitedCount / stops.length) * 100);

  return (
    <div className="absolute top-16 right-4 z-[990] w-80 max-w-[calc(100vw-2rem)] glass-panel rounded-2xl shadow-2xl border border-slate-700/60 overflow-hidden transition-all duration-300">
      {/* Panel Header */}
      <div 
        onClick={() => setIsExpanded(!isExpanded)}
        className="px-4 py-3 bg-slate-800/80 hover:bg-slate-800 border-b border-slate-700/60 flex items-center justify-between cursor-pointer transition select-none"
      >
        <div className="flex items-center space-x-2.5 min-w-0">
          <div className="p-1.5 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 shrink-0">
            <Flag className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <h4 className="text-xs font-bold text-white tracking-wide truncate">
              {routeName || 'Puntos de Control / Paradas'}
            </h4>
            <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
              <span className="text-cyan-300 font-semibold">{stops.length} paradas</span>
              <span>•</span>
              <span className="text-emerald-400 font-semibold">{completionRate}% cumplido</span>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-1 shrink-0">
          <button 
            type="button"
            className="p-1 text-slate-400 hover:text-white transition"
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="max-h-[360px] overflow-y-auto divide-y divide-slate-800/60 p-2 space-y-1 scrollbar-thin">
          {stops.map((stop, idx) => {
            const seq = stop.seq || idx + 1;
            let statusIcon = <Clock className="w-3.5 h-3.5 text-slate-400" />;
            let badgeBg = 'bg-slate-800 text-slate-300 border-slate-700';
            let statusText = 'Pendiente';
            let dotColor = 'bg-slate-400';

            if (stop.status === 'visited') {
              statusIcon = <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
              badgeBg = 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
              statusText = 'A tiempo';
              dotColor = 'bg-emerald-400';
            } else if (stop.status === 'delayed') {
              statusIcon = <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />;
              badgeBg = 'bg-amber-500/15 text-amber-300 border-amber-500/30';
              statusText = `+${stop.delay || 0}m retraso`;
              dotColor = 'bg-amber-400';
            } else if (stop.status === 'missed') {
              statusIcon = <XCircle className="w-3.5 h-3.5 text-rose-400" />;
              badgeBg = 'bg-rose-500/15 text-rose-300 border-rose-500/30';
              statusText = 'Omitida';
              dotColor = 'bg-rose-400';
            }

            return (
              <div
                key={idx}
                onClick={() => onSelectStop(stop)}
                className="group p-2 rounded-xl hover:bg-slate-800/70 border border-transparent hover:border-slate-700/60 transition cursor-pointer flex items-center justify-between gap-2"
                title="Hacer clic para enfocar esta parada en el mapa"
              >
                <div className="flex items-center space-x-2.5 min-w-0">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0 shadow-sm ${dotColor}`}>
                    {seq}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-slate-200 group-hover:text-cyan-300 transition truncate">
                      {stop.name}
                    </p>
                    <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
                      {stop.schedTime && (
                        <span>Horario: <b className="text-slate-300">{stop.schedTime}</b></span>
                      )}
                      {stop.actualTime && (
                        <span className="text-emerald-400 font-semibold">Llegada: {stop.actualTime}</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-1.5 shrink-0">
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border flex items-center gap-1 ${badgeBg}`}>
                    {statusIcon}
                    <span>{statusText}</span>
                  </span>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-cyan-400 group-hover:translate-x-0.5 transition" />
                </div>
              </div>
            );
          })}

          {/* Bottom Actions & Summary */}
          <div className="pt-2 px-1 flex items-center justify-between border-t border-slate-700/60 text-[11px] text-slate-400">
            <div className="flex items-center space-x-2">
              <span className="flex items-center gap-1 text-emerald-400 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> {visitedCount}
              </span>
              <span className="flex items-center gap-1 text-amber-400 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" /> {delayedCount}
              </span>
              <span className="flex items-center gap-1 text-rose-400 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-400" /> {missedCount}
              </span>
            </div>

            <button
              onClick={(e) => {
                e.stopPropagation();
                onFitAllStops();
              }}
              className="px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-400 hover:text-cyan-300 font-medium border border-slate-700/80 transition flex items-center gap-1 cursor-pointer"
            >
              <Compass className="w-3 h-3" />
              <span>Ver todas</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
