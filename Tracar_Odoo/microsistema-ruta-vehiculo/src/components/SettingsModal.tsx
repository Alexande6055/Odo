import React, { useState } from 'react';
import { X, Server, RefreshCw, CheckCircle, AlertTriangle } from 'lucide-react';
import { TraccarService } from '../services/traccarApi';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (user: string, pass: string) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  onSave,
}) => {
  if (!isOpen) return null;

  const [user, setUser] = useState(localStorage.getItem('traccar_user') || 'juanperzezss@gmail.com');
  const [password, setPassword] = useState(localStorage.getItem('traccar_pass') || '');
  const [testStatus, setTestStatus] = useState<{ type: 'idle' | 'testing' | 'success' | 'error'; message: string }>({
    type: 'idle',
    message: '',
  });

  const handleTestConnection = async () => {
    setTestStatus({ type: 'testing', message: 'Probando conexión...' });
    TraccarService.setCredentials(user, password);
    try {
      const devices = await TraccarService.getDevices();
      setTestStatus({
        type: 'success',
        message: `¡Conexión exitosa! Se encontraron ${devices.length} dispositivos en Traccar.`,
      });
    } catch (err: any) {
      setTestStatus({
        type: 'error',
        message: `Error al conectar: ${err.message || 'Verifica credenciales o que Traccar esté encendido.'}`,
      });
    }
  };

  const handleSave = () => {
    localStorage.setItem('traccar_user', user);
    localStorage.setItem('traccar_pass', password);
    TraccarService.setCredentials(user, password);
    onSave(user, password);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-md glass-panel rounded-2xl p-6 border border-slate-700/70 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-700">
          <div className="flex items-center space-x-2">
            <Server className="w-5 h-5 text-cyan-400" />
            <h2 className="text-base font-bold text-white">Ajustes de Conexión</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Usuario / Correo de Traccar
            </label>
            <input
              type="text"
              value={user}
              onChange={(e) => setUser(e.target.value)}
              placeholder="juanperzezss@gmail.com"
              className="w-full px-3 py-2 bg-slate-800/90 rounded-xl border border-slate-700 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Contraseña de Traccar
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Tu contraseña de Traccar"
              className="w-full px-3 py-2 bg-slate-800/90 rounded-xl border border-slate-700 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
            />
          </div>

          <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/40 text-xs text-slate-400">
            <p>
              💡 <b>Nota:</b> El micro-servicio se comunica con el contenedor Traccar mediante el proxy interno configurado en <code>/api</code>.
            </p>
          </div>

          {testStatus.type !== 'idle' && (
            <div
              className={`p-3 rounded-xl text-xs flex items-center space-x-2 ${
                testStatus.type === 'testing'
                  ? 'bg-slate-800 text-slate-300 border border-slate-700'
                  : testStatus.type === 'success'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
              }`}
            >
              {testStatus.type === 'testing' && <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />}
              {testStatus.type === 'success' && <CheckCircle className="w-4 h-4 text-emerald-400" />}
              {testStatus.type === 'error' && <AlertTriangle className="w-4 h-4 text-rose-400" />}
              <span>{testStatus.message}</span>
            </div>
          )}
        </div>

        <div className="mt-6 pt-4 border-t border-slate-700 flex justify-between space-x-3">
          <button
            onClick={handleTestConnection}
            disabled={testStatus.type === 'testing'}
            className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition cursor-pointer"
          >
            Probar Conexión
          </button>

          <div className="flex space-x-2">
            <button
              onClick={onClose}
              className="px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition cursor-pointer"
            >
              Cancelar
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-lg shadow-cyan-600/30 transition cursor-pointer"
            >
              Guardar Cambios
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
