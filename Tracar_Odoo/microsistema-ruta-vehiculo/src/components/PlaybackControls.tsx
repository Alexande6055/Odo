import React from 'react';
import { Play, Pause, RotateCcw, FastForward, Navigation, Clock, Gauge } from 'lucide-react';
import type { RoutePoint } from '../types/traccar';

interface PlaybackControlsProps {
  route: RoutePoint[];
  currentIndex: number;
  isPlaying: boolean;
  speedMultiplier: number;
  onPlayPause: () => void;
  onReset: () => void;
  onSeek: (index: number) => void;
  onSpeedChange: (speed: number) => void;
  onClose: () => void;
}

export const PlaybackControls: React.FC<PlaybackControlsProps> = ({
  route,
  currentIndex,
  isPlaying,
  speedMultiplier,
  onPlayPause,
  onReset,
  onSeek,
  onSpeedChange,
  onClose,
}) => {
  if (!route || route.length === 0) return null;

  const currentPoint = route[currentIndex] || route[0];

  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 w-11/12 max-w-2xl z-[1000] glass-panel rounded-2xl p-4 shadow-2xl border border-slate-700/60 transition-all">
      {/* Top row: Current Point Info & Close Button */}
      <div className="flex items-center justify-between pb-3 mb-2 border-b border-slate-700/50">
        <div className="flex items-center space-x-3 text-xs sm:text-sm">
          <div className="flex items-center space-x-1.5 text-cyan-400 font-medium">
            <Gauge className="w-4 h-4 text-cyan-400" />
            <span>{currentPoint.speed} km/h</span>
          </div>

          <span className="text-slate-600">|</span>

          <div className="flex items-center space-x-1.5 text-slate-300">
            <Clock className="w-4 h-4 text-amber-400" />
            <span>
              {currentPoint.fixTime ? new Date(currentPoint.fixTime).toLocaleTimeString() : 'N/A'}
            </span>
          </div>

          <span className="text-slate-600">|</span>

          <div className="flex items-center space-x-1 text-slate-400 text-xs">
            <Navigation className="w-3.5 h-3.5" />
            <span>{currentPoint.course}°</span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-xs text-slate-400 font-mono">
            {currentIndex + 1} / {route.length}
          </span>
          <button
            onClick={onClose}
            className="text-xs px-2 py-1 rounded bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition"
            title="Cerrar reproductor de ruta"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Scrubber timeline */}
      <div className="relative mb-3 flex items-center">
        <input
          type="range"
          min={0}
          max={route.length - 1}
          value={currentIndex}
          onChange={(e) => onSeek(Number(e.target.value))}
          className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-400 focus:outline-none"
        />
      </div>

      {/* Bottom row: Playback Buttons & Speed Selector */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {/* Reset */}
          <button
            onClick={onReset}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition shadow"
            title="Reiniciar ruta"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* Play/Pause */}
          <button
            onClick={onPlayPause}
            className="flex items-center space-x-1 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-sm transition shadow-lg shadow-cyan-500/25 cursor-pointer"
          >
            {isPlaying ? (
              <>
                <Pause className="w-4 h-4 fill-white" />
                <span>Pausar</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white" />
                <span>Reproducir</span>
              </>
            )}
          </button>
        </div>

        {/* Speed multiplier buttons */}
        <div className="flex items-center space-x-1 bg-slate-800/80 p-1 rounded-xl border border-slate-700/60">
          <FastForward className="w-3.5 h-3.5 text-slate-400 ml-1.5 mr-0.5" />
          {[1, 2, 5, 10].map((speed) => (
            <button
              key={speed}
              onClick={() => onSpeedChange(speed)}
              className={`px-2 py-1 text-xs font-semibold rounded-lg transition cursor-pointer ${
                speedMultiplier === speed
                  ? 'bg-cyan-500 text-white shadow'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
              }`}
            >
              {speed}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
