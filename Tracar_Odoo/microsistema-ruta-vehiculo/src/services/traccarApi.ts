import type { Device, Position, RoutePoint } from '../types/traccar';

// Helper to convert knots to km/h
export const knotsToKmh = (knots: number = 0): number => {
  return Math.round(knots * 1.852 * 10) / 10;
};

// Default Traccar API base URL (via Vite proxy or direct)
const API_BASE = '/api';

export class TraccarService {
  private static authHeader: string = '';
  private static username: string = '';
  private static password: string = '';

  public static setCredentials(user: string, pass: string) {
    this.username = user || '';
    this.password = pass || '';
    if (user && pass) {
      this.authHeader = 'Basic ' + btoa(`${user}:${pass}`);
    } else {
      this.authHeader = '';
    }
  }

  public static getCredentials(): { authHeader: string } {
    return { authHeader: this.authHeader };
  }

  private static getHeaders(includeContentType = false): HeadersInit {
    const headers: Record<string, string> = {
      'Accept': 'application/json',
    };
    if (includeContentType) {
      headers['Content-Type'] = 'application/json';
    }
    if (this.authHeader) {
      headers['Authorization'] = this.authHeader;
    }
    return headers;
  }

  public static async ensureSession(): Promise<boolean> {
    try {
      if (this.username && this.password) {
        const body = new URLSearchParams({
          email: this.username,
          password: this.password,
        });
        const loginRes = await fetch(`${API_BASE}/session`, {
          method: 'POST',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: body.toString(),
          credentials: 'include',
        });
        if (loginRes.ok) {
          return true;
        }
      }
      const checkRes = await fetch(`${API_BASE}/session`, {
        headers: this.getHeaders(),
        credentials: 'include',
      });
      return checkRes.ok;
    } catch {
      return false;
    }
  }

  // Fetch all devices
  public static async getDevices(): Promise<Device[]> {
    try {
      const res = await fetch(`${API_BASE}/devices`, {
        headers: this.getHeaders(),
        credentials: 'include',
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
        credentials: 'include',
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
        credentials: 'include',
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

    const connect = async () => {
      if (isDisposed) return;
      try {
        await this.ensureSession();
        if (isDisposed) return;
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
    // Coordenadas base en Ambato, Ecuador (Campus Huachi UTA)
    const baseLat = -1.2687;
    const baseLon = -78.6258;

    const demoDevice: Device = {
      id: 9999,
      name: 'Bus Universitario UTA (Demo GPS)',
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
    let now = Date.now() - 35 * 60 * 1000;

    // Hacia Campus Ingahurco pasando por Mall de los Andes y Parque Cevallos
    const segments = [
      { dLat: 0.0010, dLon: 0.0002, speed: 32, course: 15, count: 8 },  // Salida Chasquis
      { dLat: 0.0012, dLon: -0.0001, speed: 42, course: 355, count: 10 }, // Hacia Mall de los Andes
      { dLat: 0.0015, dLon: -0.0003, speed: 28, course: 340, count: 12 }, // Hacia Parque Cevallos
      { dLat: 0.0002, dLon: 0.0009, speed: 38, course: 75, count: 10 },  // Hacia Campus Ingahurco
    ];

    for (const seg of segments) {
      for (let i = 0; i < seg.count; i++) {
        curLat += seg.dLat + (Math.random() - 0.5) * 0.00005;
        curLon += seg.dLon + (Math.random() - 0.5) * 0.00005;
        const currentSpeed = Math.max(0, seg.speed + (Math.random() - 0.5) * 6);
        now += 60 * 1000;

        route.push({
          latitude: Number(curLat.toFixed(6)),
          longitude: Number(curLon.toFixed(6)),
          speed: Math.round(currentSpeed),
          course: seg.course + Math.round((Math.random() - 0.5) * 8),
          fixTime: new Date(now).toISOString(),
          ignition: currentSpeed > 0,
          batteryLevel: 95,
          address: `Ambato - Av. Universitaria Km ${(route.length * 0.2).toFixed(1)}`,
        });
      }
    }

    return { device: demoDevice, route };
  }
}
