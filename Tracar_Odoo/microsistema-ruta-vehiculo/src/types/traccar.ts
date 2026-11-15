export interface Device {
  id: number;
  name: string;
  uniqueId: string;
  status: 'online' | 'offline' | 'unknown' | string;
  lastUpdate?: string;
  positionId?: number;
  phone?: string;
  model?: string;
  contact?: string;
  category?: string;
  disabled?: boolean;
  attributes?: Record<string, any>;
}

export interface Position {
  id: number;
  deviceId: number;
  protocol?: string;
  deviceTime: string;
  fixTime: string;
  serverTime?: string;
  outdated?: boolean;
  valid?: boolean;
  latitude: number;
  longitude: number;
  altitude?: number;
  speed: number; // in knots in Traccar (1 knot = 1.852 km/h)
  course?: number; // 0-360 degrees
  address?: string;
  accuracy?: number;
  network?: any;
  attributes?: {
    batteryLevel?: number;
    ignition?: boolean;
    motion?: boolean;
    distance?: number;
    totalDistance?: number;
    hours?: number;
    [key: string]: any;
  };
}

export interface RoutePoint {
  latitude: number;
  longitude: number;
  speed: number; // km/h
  fixTime: string;
  course: number;
  ignition?: boolean;
  batteryLevel?: number;
  address?: string;
}

export interface StopPoint {
  name: string;
  lat: number;
  lon: number;
  seq?: number;
  status?: 'visited' | 'delayed' | 'missed' | 'pending' | string;
  schedTime?: string;
  actualTime?: string;
  delay?: number;
}

export type MapTileLayer = 'dark' | 'light' | 'streets' | 'satellite';

export interface AppConfig {
  traccarUrl: string;
  authHeader: string;
  odooSyncEnabled: boolean;
  refreshIntervalSeconds: number;
}
