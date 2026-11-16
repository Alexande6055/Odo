import 'dart:developer' as developer;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:traccar_client/geolocation_service.dart';
import 'package:traccar_client/main.dart';
import 'package:traccar_client/main_screen.dart';
import 'package:traccar_client/models/fleet_models.dart';
import 'package:traccar_client/preferences.dart';

class DriverLoginScreen extends StatefulWidget {
  const DriverLoginScreen({super.key});

  @override
  State<DriverLoginScreen> createState() => _DriverLoginScreenState();
}

class _DriverLoginScreenState extends State<DriverLoginScreen> {
  final _formKey = GlobalKey<FormState>();

  DriverInfo? _selectedDriver = FleetCatalog.drivers.first;
  BusInfo? _selectedBus = FleetCatalog.buses.first;
  RouteInfo? _selectedRoute = FleetCatalog.routes.first;

  final TextEditingController _pinController = TextEditingController(text: '1234');
  final TextEditingController _customDriverController = TextEditingController();
  final TextEditingController _customPlateController = TextEditingController();
  final TextEditingController _customImeiController = TextEditingController();
  final TextEditingController _customRouteController = TextEditingController();

  bool _isCustomDriver = false;
  bool _isCustomBus = false;
  bool _isCustomRoute = false;
  bool _loading = false;

  @override
  void dispose() {
    _pinController.dispose();
    _customDriverController.dispose();
    _customPlateController.dispose();
    _customImeiController.dispose();
    _customRouteController.dispose();
    super.dispose();
  }

  Future<void> _handleStartShift() async {
    if (!_formKey.currentState!.validate()) return;

    final driverName = _isCustomDriver
        ? _customDriverController.text.trim()
        : _selectedDriver?.name ?? '';
    final driverCode = _isCustomDriver
        ? 'CH-PERS'
        : _selectedDriver?.code ?? '';

    // PIN check for catalog drivers
    if (!_isCustomDriver && _selectedDriver != null) {
      if (_pinController.text.trim() != _selectedDriver!.pin) {
        messengerKey.currentState?.showSnackBar(
          const SnackBar(
            content: Text('PIN incorrecto. (PIN por defecto: 1234)'),
            backgroundColor: Colors.red,
            behavior: SnackBarBehavior.floating,
          ),
        );
        return;
      }
    }

    final busPlate = _isCustomBus
        ? _customPlateController.text.trim().toUpperCase()
        : _selectedBus?.plate ?? '';
    final busModel = _isCustomBus
        ? 'Bus Personalizado'
        : _selectedBus?.model ?? '';
    final busImei = _isCustomBus
        ? _customImeiController.text.trim()
        : _selectedBus?.imei ?? '';

    final routeCode = _isCustomRoute
        ? 'RUTA-ESP'
        : _selectedRoute?.code ?? '';
    final routeName = _isCustomRoute
        ? _customRouteController.text.trim()
        : _selectedRoute?.name ?? '';

    setState(() => _loading = true);

    try {
      // 0. Ensure real-time continuous streaming parameters (5s interval, 0m distance, wakeLock ON)
      await Preferences.instance.setInt(Preferences.interval, 5);
      await Preferences.instance.setInt(Preferences.distance, 0);
      await Preferences.instance.setString(Preferences.accuracy, 'highest');
      await Preferences.instance.setBool(Preferences.wakelock, true);
      await Preferences.instance.setBool(Preferences.stopDetection, false);

      // 1. Save session and configure specific Bus IMEI
      await Preferences.saveDriverSession(
        driver: driverName,
        code: driverCode,
        plate: busPlate,
        model: busModel,
        imei: busImei,
        rCode: routeCode,
        rName: routeName,
      );

      // 2. Apply new config to Traccar Tracker
      await GeolocationService.tracker.setConfig(Preferences.buildConfig());

      // 3. Start continuous GPS tracking exclusively for this bus and route
      var trackingStarted = false;
      try {
        await GeolocationService.tracker.start();
        trackingStarted = true;
        await GeolocationService.tracker.requestPosition();
      } on PlatformException catch (e) {
        developer.log('Error starting tracking: ${e.message}');
      }

      if (!mounted) return;

      messengerKey.currentState?.showSnackBar(
        SnackBar(
          content: Text(
            trackingStarted
                ? '🟢 Turno iniciado: $busPlate en $routeCode. Rastreo activo.'
                : 'Turno registrado. Revisa los permisos de ubicación en tu teléfono.',
          ),
          backgroundColor: const Color(0xFF0F766E),
          behavior: SnackBarBehavior.floating,
          duration: const Duration(seconds: 4),
        ),
      );

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => MainScreen(key: mainScreenKey)),
      );
    } catch (e) {
      if (!mounted) return;
      messengerKey.currentState?.showSnackBar(
        SnackBar(
          content: Text('Error al iniciar turno: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Ingreso de Chofer'),
        centerTitle: true,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Branding Header
                Center(
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.primary.withValues(alpha: 0.12),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      Icons.directions_bus_rounded,
                      size: 48,
                      color: theme.colorScheme.primary,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'Monitoreo de Flota UTA',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Identifícate y selecciona tu unidad para iniciar el recorrido',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: 8),
                Center(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.green.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.green.withValues(alpha: 0.3)),
                    ),
                    child: Text(
                      '📡 Servidor: ${Preferences.defaultServerIp}:${Preferences.defaultServerPort}',
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        color: Colors.green,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 24),

                // 1. SELECCIÓN DE CONDUCTOR
                _buildSectionTitle('1. Identificación del Chofer', Icons.person_rounded),
                Card(
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                    side: BorderSide(color: theme.colorScheme.outlineVariant),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        DropdownButtonFormField<DriverInfo?>(
                          value: _isCustomDriver ? null : _selectedDriver,
                          decoration: InputDecoration(
                            labelText: 'Conductor Registrado',
                            prefixIcon: const Icon(Icons.badge_rounded),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                          items: [
                            ...FleetCatalog.drivers.map(
                              (driver) => DropdownMenuItem(
                                value: driver,
                                child: Text('${driver.name} (${driver.code})'),
                              ),
                            ),
                            const DropdownMenuItem(
                              value: null,
                              child: Text('Otro Conductor...'),
                            ),
                          ],
                          onChanged: (val) {
                            setState(() {
                              if (val == null) {
                                _isCustomDriver = true;
                                _selectedDriver = null;
                              } else {
                                _isCustomDriver = false;
                                _selectedDriver = val;
                              }
                            });
                          },
                        ),
                        if (_isCustomDriver) ...[
                          const SizedBox(height: 12),
                          TextFormField(
                            controller: _customDriverController,
                            decoration: InputDecoration(
                              labelText: 'Nombre y Apellido del Chofer',
                              prefixIcon: const Icon(Icons.person_outline),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                            ),
                            validator: (val) =>
                                (val == null || val.trim().isEmpty) ? 'Ingresa el nombre del chofer' : null,
                          ),
                        ],
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _pinController,
                          keyboardType: TextInputType.number,
                          obscureText: true,
                          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                          decoration: InputDecoration(
                            labelText: 'PIN de Seguridad',
                            prefixIcon: const Icon(Icons.lock_outline_rounded),
                            helperText: 'PIN predeterminado: 1234',
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                          validator: (val) =>
                              (val == null || val.isEmpty) ? 'Ingresa tu PIN de acceso' : null,
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 18),

                // 2. SELECCIÓN DE BUS
                _buildSectionTitle('2. Asignación de Unidad (Bus)', Icons.directions_bus_filled_rounded),
                Card(
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                    side: BorderSide(color: theme.colorScheme.outlineVariant),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        DropdownButtonFormField<BusInfo?>(
                          value: _isCustomBus ? null : _selectedBus,
                          decoration: InputDecoration(
                            labelText: 'Bus / Vehículo',
                            prefixIcon: const Icon(Icons.commute_rounded),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                          items: [
                            ...FleetCatalog.buses.map(
                              (bus) => DropdownMenuItem(
                                value: bus,
                                child: Text('${bus.plate} • ${bus.model}'),
                              ),
                            ),
                            const DropdownMenuItem(
                              value: null,
                              child: Text('Otro Bus / IMEI personalizado...'),
                            ),
                          ],
                          onChanged: (val) {
                            setState(() {
                              if (val == null) {
                                _isCustomBus = true;
                                _selectedBus = null;
                              } else {
                                _isCustomBus = false;
                                _selectedBus = val;
                              }
                            });
                          },
                        ),
                        if (_isCustomBus) ...[
                          const SizedBox(height: 12),
                          TextFormField(
                            controller: _customPlateController,
                            textCapitalization: TextCapitalization.characters,
                            decoration: InputDecoration(
                              labelText: 'Placa del Bus (ej: TBA-4004)',
                              prefixIcon: const Icon(Icons.credit_card_rounded),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                            ),
                            validator: (val) =>
                                (val == null || val.trim().isEmpty) ? 'Ingresa la placa del bus' : null,
                          ),
                          const SizedBox(height: 12),
                          TextFormField(
                            controller: _customImeiController,
                            keyboardType: TextInputType.number,
                            decoration: InputDecoration(
                              labelText: 'IMEI / ID de Traccar',
                              prefixIcon: const Icon(Icons.fingerprint_rounded),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                            ),
                            validator: (val) =>
                                (val == null || val.trim().isEmpty) ? 'Ingresa el IMEI de Traccar' : null,
                          ),
                        ] else if (_selectedBus != null) ...[
                          const SizedBox(height: 10),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                            decoration: BoxDecoration(
                              color: theme.colorScheme.primaryContainer.withValues(alpha: 0.4),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Row(
                              children: [
                                Icon(Icons.verified_user_outlined, size: 18, color: theme.colorScheme.primary),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    'ID en Traccar: ${_selectedBus!.imei}',
                                    style: TextStyle(
                                      fontFamily: 'monospace',
                                      fontWeight: FontWeight.bold,
                                      fontSize: 12,
                                      color: theme.colorScheme.primary,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 18),

                // 3. SELECCIÓN DE RUTA
                _buildSectionTitle('3. Ruta Programada', Icons.alt_route_rounded),
                Card(
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                    side: BorderSide(color: theme.colorScheme.outlineVariant),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        DropdownButtonFormField<RouteInfo?>(
                          isExpanded: true,
                          value: _isCustomRoute ? null : _selectedRoute,
                          decoration: InputDecoration(
                            labelText: 'Ruta Universitaria',
                            prefixIcon: const Icon(Icons.map_rounded),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                          items: [
                            ...FleetCatalog.routes.map(
                              (route) => DropdownMenuItem(
                                value: route,
                                child: Text(
                                  '${route.code}: ${route.name}',
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ),
                            const DropdownMenuItem(
                              value: null,
                              child: Text('Otra Ruta / Servicio Especial...'),
                            ),
                          ],
                          onChanged: (val) {
                            setState(() {
                              if (val == null) {
                                _isCustomRoute = true;
                                _selectedRoute = null;
                              } else {
                                _isCustomRoute = false;
                                _selectedRoute = val;
                              }
                            });
                          },
                        ),
                        if (_isCustomRoute) ...[
                          const SizedBox(height: 12),
                          TextFormField(
                            controller: _customRouteController,
                            decoration: InputDecoration(
                              labelText: 'Nombre o Código de Ruta',
                              prefixIcon: const Icon(Icons.edit_road_rounded),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                            ),
                            validator: (val) =>
                                (val == null || val.trim().isEmpty) ? 'Ingresa la ruta' : null,
                          ),
                        ] else if (_selectedRoute != null) ...[
                          const SizedBox(height: 10),
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    const Icon(Icons.trip_origin_rounded, size: 14, color: Colors.green),
                                    const SizedBox(width: 6),
                                    Expanded(
                                      child: Text(
                                        'Origen: ${_selectedRoute!.origin}',
                                        style: theme.textTheme.bodySmall,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 4),
                                Row(
                                  children: [
                                    const Icon(Icons.location_on_rounded, size: 14, color: Colors.red),
                                    const SizedBox(width: 6),
                                    Expanded(
                                      child: Text(
                                        'Destino: ${_selectedRoute!.destination}',
                                        style: theme.textTheme.bodySmall,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'Distancia: ${_selectedRoute!.distanceKm} km • Duración est.: ${_selectedRoute!.durationMin} min',
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: theme.colorScheme.onSurfaceVariant,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 28),

                // BOTÓN INICIAR TURNO
                FilledButton.icon(
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                  icon: _loading
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.play_circle_fill_rounded, size: 24),
                  label: Text(
                    _loading ? 'Iniciando Turno...' : 'INICIAR TURNO Y RASTREO',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  onPressed: _loading ? null : _handleStartShift,
                ),
                const SizedBox(height: 16),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSectionTitle(String title, IconData icon) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 6),
      child: Row(
        children: [
          Icon(icon, size: 18, color: theme.colorScheme.primary),
          const SizedBox(width: 6),
          Text(
            title,
            style: theme.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.bold,
              color: theme.colorScheme.primary,
            ),
          ),
        ],
      ),
    );
  }
}
