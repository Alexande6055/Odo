import type { Device, Position, RoutePoint } from '../types/traccar';

// Helper to convert knots to km/h
export const knotsToKmh = (knots: number = 0): number => {
  return Math.round(knots * 1.852 * 10) / 10;
};

// Default Traccar API base URL (via Vite proxy or direct)
const API_BASE = '/api';

export class TraccarService {
  private static authHeader: string = '';

  public static setCredentials(user: string, pass: string) {
    if (user && pass) {
      this.authHeader = 'Basic ' + btoa(`${user}:${pass}`);
    } else {
      this.authHeader = '';
    }
  }

  private static getHeaders(): HeadersInit {
    const headers: Record<string, string> = {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    };
    if (this.authHeader) {
      headers['Authorization'] = this.authHeader;
    }
    return headers;
  }

  // Fetch all devices
  public static async getDevices(): Promise<Device[]> {
    try {
      const res = await fetch(`${API_BASE}/devices`, {
        headers: this.getHeaders(),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      return await res.json();
    } catch (err) {
      console.warn('Error fetching devices from Traccar:', err);
      return [];
    }
  }

  // Fetch current positions (all or specific device)
  public static async getPositions(deviceId?: number): Promise<Position[]> {
    try {
      const url = deviceId 
        ? `${API_BASE}/positions?deviceId=${deviceId}`
        : `${API_BASE}/positions`;
      const res = await fetch(url, {
        headers: this.getHeaders(),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      return await res.json();
    } catch (err) {
      console.warn('Error fetching positions from Traccar:', err);
      return [];
    }
  }

  // Fetch route history for route playback
  public static async getRoute(
    deviceId: number,
    from: string,
    to: string
  ): Promise<RoutePoint[]> {
    try {
      const url = `${API_BASE}/reports/route?deviceId=${deviceId}&from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`;
      const res = await fetch(url, {
        headers: this.getHeaders(),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      const rawPositions: Position[] = await res.json();
      return rawPositions.map((p) => ({
        latitude: p.latitude,
        longitude: p.longitude,
        speed: knotsToKmh(p.speed),
        fixTime: p.fixTime,
        course: p.course || 0,
        ignition: p.attributes?.ignition,
        batteryLevel: p.attributes?.batteryLevel,
        address: p.address,
      }));
    } catch (err) {
      console.warn('Error fetching route from Traccar:', err);
      return [];
    }
  }

  // Connect to Traccar WebSocket for instant live events
  public static connectWebSocket(
    onPositions: (positions: Position[]) => void,
    onDevices: (devices: Device[]) => void
  ): () => void {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/socket`;

    let socket: WebSocket | null = null;
    let reconnectTimeout: any = null;
    let isDisposed = false;

    const connect = () => {
      if (isDisposed) return;
      try {
        socket = new WebSocket(wsUrl);

        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.positions && Array.isArray(data.positions)) {
              onPositions(data.positions);
            }
            if (data.devices && Array.isArray(data.devices)) {
              onDevices(data.devices);
            }
          } catch (e) {
            console.error('Error parsing WS message:', e);
          }
        };

        socket.onerror = (e) => {
          console.log('Traccar WebSocket error, will retry...', e);
        };

        socket.onclose = () => {
          if (!isDisposed) {
            reconnectTimeout = setTimeout(connect, 5000);
          }
        };
      } catch (err) {
        console.warn('Could not establish WebSocket connection:', err);
        if (!isDisposed) {
          reconnectTimeout = setTimeout(connect, 5000);
        }
      }
    };

    connect();

    return () => {
      isDisposed = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (socket) socket.close();
    };
  }

  // Generate realistic route simulation for instant demo and testing
  public static generateDemoRoute(): { device: Device; route: RoutePoint[] } {
    const baseLat = -12.046374;
    const baseLon = -77.042793;

    const demoDevice: Device = {
      id: 9999,
      name: 'Vehículo Demo (Simulado GPS)',
      uniqueId: 'DEMO-863001234',
      status: 'online',
      lastUpdate: new Date().toISOString(),
      attributes: {
        batteryLevel: 98,
        ignition: true,
      },
    };

    const route: RoutePoint[] = [];
    let curLat = baseLat;
    let curLon = baseLon;
    let now = Date.now() - 45 * 60 * 1000;

    const segments = [
      { dLat: 0.0005, dLon: 0.0002, speed: 35, course: 22, count: 8 },
      { dLat: 0.0002, dLon: 0.0008, speed: 52, course: 75, count: 12 },
      { dLat: -0.0004, dLon: 0.0006, speed: 45, course: 125, count: 10 },
      { dLat: -0.0006, dLon: -0.0002, speed: 60, course: 200, count: 8 },
      { dLat: 0.0001, dLon: -0.0005, speed: 28, course: 280, count: 7 },
    ];

    for (const seg of segments) {
      for (let i = 0; i < seg.count; i++) {
        curLat += seg.dLat + (Math.random() - 0.5) * 0.00005;
        curLon += seg.dLon + (Math.random() - 0.5) * 0.00005;
        const currentSpeed = Math.max(0, seg.speed + (Math.random() - 0.5) * 8);
        now += 60 * 1000;

        route.push({
          latitude: Number(curLat.toFixed(6)),
          longitude: Number(curLon.toFixed(6)),
          speed: Math.round(currentSpeed),
          course: seg.course + Math.round((Math.random() - 0.5) * 10),
          fixTime: new Date(now).toISOString(),
          ignition: currentSpeed > 0,
          batteryLevel: 95,
          address: `Av. Principal Km ${(route.length * 0.4).toFixed(1)}`,
        });
      }
    }

    return { device: demoDevice, route };
  }
}
