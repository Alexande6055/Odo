import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;
const TRACCAR_URL = process.env.TRACCAR_URL || 'http://localhost:8082';

console.log(`[Bridge Server] Starting on port ${PORT}...`);
console.log(`[Bridge Server] Proxying /api and WebSockets to ${TRACCAR_URL}`);

// Proxy Traccar API and WebSocket requests while keeping /api prefix
const apiProxy = createProxyMiddleware({
  target: TRACCAR_URL,
  changeOrigin: true,
  ws: true,
  pathFilter: '/api',
  onError(err, _req, res) {
    console.error('[Proxy Error]', err.message);
    if (res && typeof res.status === 'function' && !res.headersSent) {
      res.status(502).json({ error: 'No se pudo conectar con el servidor Traccar', detail: err.message });
    }
  },
});

app.use(apiProxy);

// Serve compiled React build
app.use(express.static(path.join(__dirname, 'dist')));

// Fallback to index.html for SPA (compatible with Express 5)
app.use((_req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

const server = app.listen(PORT, '0.0.0.0', () => {
  console.log(`[Bridge Server] Listo y escuchando en http://0.0.0.0:${PORT}`);
});

server.on('upgrade', (req, socket, head) => {
  if (req.url?.startsWith('/api/socket')) {
    apiProxy.upgrade(req, socket, head);
  }
});
