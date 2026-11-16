class DriverInfo {
  final String code;
  final String name;
  final String pin;

  const DriverInfo({
    required this.code,
    required this.name,
    required this.pin,
  });
}

class BusInfo {
  final String plate;
  final String model;
  final String imei;

  const BusInfo({
    required this.plate,
    required this.model,
    required this.imei,
  });
}

class RouteInfo {
  final String code;
  final String name;
  final String origin;
  final String destination;
  final double distanceKm;
  final int durationMin;

  const RouteInfo({
    required this.code,
    required this.name,
    required this.origin,
    required this.destination,
    required this.distanceKm,
    required this.durationMin,
  });
}

class FleetCatalog {
  static const List<DriverInfo> drivers = [
    DriverInfo(code: 'CH-001', name: 'Juan Carlos Pérez', pin: '1234'),
    DriverInfo(code: 'CH-002', name: 'Segundo Manuel Morales', pin: '1234'),
    DriverInfo(code: 'CH-003', name: 'Luis Alberto Sánchez', pin: '1234'),
  ];

  static const List<BusInfo> buses = [
    BusInfo(plate: 'TBA-1001', model: 'Hino AK Urbano (Bus 1)', imei: '8632940401001'),
    BusInfo(plate: 'TBA-2002', model: 'Hino AK Urbano (Bus 2)', imei: '8632940402002'),
    BusInfo(plate: 'TBA-3003', model: 'Mercedes-Benz OF (Bus 3)', imei: '8632940403003'),
  ];

  static const List<RouteInfo> routes = [
    RouteInfo(
      code: 'UTA-R01',
      name: 'Ruta 1: Troncal Campus Huachi - Campus Ingahurco',
      origin: 'Campus Huachi (Av. Los Chasquis)',
      destination: 'Campus Ingahurco (Av. Colombia)',
      distanceKm: 5.8,
      durationMin: 25,
    ),
    RouteInfo(
      code: 'UTA-R02',
      name: 'Ruta 2: Intercampus Huachi - Querochaca',
      origin: 'Campus Huachi (Estación Sur)',
      destination: 'Campus Querochaca (Cevallos)',
      distanceKm: 11.5,
      durationMin: 35,
    ),
    RouteInfo(
      code: 'UTA-R03',
      name: 'Ruta 3: Circuito Periférico Ficoa - Huachi',
      origin: 'Redondel Miraflores',
      destination: 'Campus Huachi',
      distanceKm: 4.6,
      durationMin: 20,
    ),
  ];
}
