import 'dart:async';
import 'dart:developer' as developer;
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:traccar_client/main.dart';
import 'package:traccar_client/password_service.dart';
import 'package:traccar_client/preferences.dart';

import 'driver_login_screen.dart';
import 'geolocation_service.dart';
import 'l10n/app_localizations.dart';
import 'settings_screen.dart';
import 'status_screen.dart';

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => MainScreenState();
}

class MainScreenState extends State<MainScreen> with WidgetsBindingObserver {
  bool trackingEnabled = false;
  bool checkingServer = false;
  bool? serverReachable;
  String? serverResponseTime;
  DateTime? lastPositionSent;
  Timer? _realtimeStreamTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _refreshState();

    WidgetsBinding.instance.addPostFrameCallback((_) async {
      await _checkServerConnection(showFeedback: false);
      await _autoStartTrackingIfEnabled();
    });
  }

  void _startRealtimeStreamTimer() {
    _realtimeStreamTimer?.cancel();
    _realtimeStreamTimer = Timer.periodic(const Duration(seconds: 5), (_) async {
      if (trackingEnabled && mounted) {
        try {
          await GeolocationService.tracker.requestPosition();
          if (mounted) {
            setState(() {
              lastPositionSent = DateTime.now();
            });
          }
        } catch (_) {}
      }
    });
  }

  void _stopRealtimeStreamTimer() {
    _realtimeStreamTimer?.cancel();
    _realtimeStreamTimer = null;
  }

  @override
  void dispose() {
    _stopRealtimeStreamTimer();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _refreshState();
      _checkServerConnection(showFeedback: false);
    }
  }

  Future<void> _refreshState() async {
    final tracking = await GeolocationService.tracker.isTracking();
    if (!mounted) return;
    setState(() {
      trackingEnabled = tracking;
    });
    if (tracking) {
      if (_realtimeStreamTimer == null) {
        _startRealtimeStreamTimer();
      }
    } else {
      _stopRealtimeStreamTimer();
    }
  }

  void refresh() {
    _refreshState();
    _checkServerConnection(showFeedback: false);
  }

  Future<void> _autoStartTrackingIfEnabled() async {
    final autoStart = Preferences.instance.getBool(Preferences.autoStart) ?? true;
    if (!autoStart) return;

    try {
      final isCurrentlyTracking = await GeolocationService.tracker.isTracking();
      if (!isCurrentlyTracking && mounted) {
        await GeolocationService.tracker.start();
        if (mounted) {
          setState(() => trackingEnabled = true);
        }
      }
    } on PlatformException catch (e) {
      developer.log('Auto-start skipped or permissions required: ${e.message}');
    }
  }

  Future<void> _checkServerConnection({bool showFeedback = true}) async {
    if (!mounted) return;
    setState(() => checkingServer = true);

    final currentUrl = Preferences.instance.getString(Preferences.url) ?? Preferences.defaultUrl;
    bool reachable = false;
    final stopwatch = Stopwatch()..start();

    try {
      final uri = Uri.parse(currentUrl);
      final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
      final request = await client.getUrl(uri);
      final response = await request.close();
      stopwatch.stop();
      // Any HTTP response means port 5055 is listening and reachable
      reachable = (response.statusCode >= 200 && response.statusCode < 500);
      client.close();
    } catch (e) {
      reachable = false;
    }

    if (!mounted) return;
    setState(() {
      checkingServer = false;
      serverReachable = reachable;
      serverResponseTime = reachable ? '${stopwatch.elapsedMilliseconds} ms' : null;
    });

    if (showFeedback && mounted) {
      messengerKey.currentState?.showSnackBar(
        SnackBar(
          content: Row(
            children: [
              Icon(
                reachable ? Icons.check_circle_outline : Icons.error_outline,
                color: Colors.white,
                size: 20,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  reachable
                      ? 'Conexión exitosa a $currentUrl ($serverResponseTime)'
                      : 'No se pudo conectar a $currentUrl. Revisa tu VPN Tailscale o el servidor.',
                ),
              ),
            ],
          ),
          backgroundColor: reachable ? const Color(0xFF0F766E) : Theme.of(context).colorScheme.error,
          duration: const Duration(seconds: 4),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  Future<void> _toggleTracking(bool value) async {
    if (await PasswordService.authenticate(context) && mounted) {
      if (value) {
        developer.log('tracking_toggle_start');
        var started = false;
        try {
          await GeolocationService.tracker.start();
          started = true;
        } on PlatformException {
          // permission denied or startup error
        }
        if (!mounted) return;
        if (!started) {
          messengerKey.currentState?.showSnackBar(
            const SnackBar(
              content: Text('No se pudo iniciar el rastreo. Verifica los permisos de ubicación en segundo plano.'),
              duration: Duration(seconds: 4),
              behavior: SnackBarBehavior.floating,
            ),
          );
        } else {
          messengerKey.currentState?.showSnackBar(
            SnackBar(
              content: Text('🟢 Rastreo GPS activado. Conectando a ${Preferences.instance.getString(Preferences.url) ?? Preferences.defaultUrl}'),
              duration: const Duration(seconds: 3),
              behavior: SnackBarBehavior.floating,
            ),
          );
        }
        setState(() => trackingEnabled = started);
        if (started) {
          _startRealtimeStreamTimer();
        }
      } else {
        developer.log('tracking_toggle_stop');
        await GeolocationService.tracker.stop();
        _stopRealtimeStreamTimer();
        if (mounted) {
          setState(() => trackingEnabled = false);
          messengerKey.currentState?.showSnackBar(
            const SnackBar(
              content: Text('Rastreo en pausa.'),
              duration: Duration(seconds: 2),
              behavior: SnackBarBehavior.floating,
            ),
          );
        }
      }
    }
  }

  Future<void> _sendManualPosition() async {
    try {
      await GeolocationService.tracker.requestPosition();
      if (!mounted) return;
      setState(() => lastPositionSent = DateTime.now());
      messengerKey.currentState?.showSnackBar(
        SnackBar(
          content: Text('📍 Ubicación enviada a ${Preferences.instance.getString(Preferences.url) ?? Preferences.defaultUrl}'),
          backgroundColor: const Color(0xFF0F766E),
          duration: const Duration(seconds: 3),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } on PlatformException catch (e) {
      if (!mounted) return;
      messengerKey.currentState?.showSnackBar(
        SnackBar(
          content: Text('Error al enviar ubicación: ${e.message ?? e.code}'),
          backgroundColor: Theme.of(context).colorScheme.error,
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  Future<void> _sendSosAlarm() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.warning_amber_rounded, color: Colors.redAccent, size: 28),
            SizedBox(width: 8),
            Text('Alarma SOS'),
          ],
        ),
        content: const Text(
          '¿Deseas enviar una alarma de emergencia SOS con tu ubicación inmediata al servidor Traccar?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: Colors.red.shade700,
              foregroundColor: Colors.white,
            ),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Enviar Alerta SOS'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      try {
        await GeolocationService.tracker.requestPosition(alarm: 'sos');
        if (!mounted) return;
        messengerKey.currentState?.showSnackBar(
          const SnackBar(
            content: Text('🚨 ¡Alarma SOS enviada al servidor de monitoreo!'),
            backgroundColor: Colors.red,
            duration: Duration(seconds: 5),
            behavior: SnackBarBehavior.floating,
          ),
        );
      } on PlatformException catch (e) {
        if (!mounted) return;
        messengerKey.currentState?.showSnackBar(
          SnackBar(
            content: Text('Error al enviar SOS: ${e.message ?? e.code}'),
            backgroundColor: Theme.of(context).colorScheme.error,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  Future<void> _copyDeviceId() async {
    final id = Preferences.instance.getString(Preferences.id) ?? '';
    await Clipboard.setData(ClipboardData(text: id));
    if (!mounted) return;
    messengerKey.currentState?.showSnackBar(
      SnackBar(
        content: Text('ID $id copiado al portapapeles. Regístralo en Traccar / Odoo Flota.'),
        duration: const Duration(seconds: 3),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  Future<void> _resetToDefaultServer() async {
    await Preferences.resetToDefaultServer();
    await GeolocationService.tracker.setConfig(Preferences.buildConfig());
    if (!mounted) return;
    await _checkServerConnection(showFeedback: true);
    setState(() {});
  }

  Future<void> _handleFinishShift() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.logout_rounded, color: Colors.orange, size: 26),
            SizedBox(width: 8),
            Text('Finalizar Turno'),
          ],
        ),
        content: const Text(
          '¿Estás seguro de finalizar el turno de conducción?\n\n'
          'Se detendrá la transmisión de GPS de este bus y se cerrará la sesión del chofer.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red.shade700),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Finalizar y Salir'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      _stopRealtimeStreamTimer();
      try {
        await GeolocationService.tracker.stop();
      } catch (_) {}
      await Preferences.clearDriverSession();

      if (!mounted) return;
      messengerKey.currentState?.showSnackBar(
        const SnackBar(
          content: Text('Turno finalizado. Rastreo detenido.'),
          behavior: SnackBarBehavior.floating,
        ),
      );

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const DriverLoginScreen()),
      );
    }
  }

  Widget _buildDriverShiftCard() {
    final theme = Theme.of(context);
    final driverName = Preferences.instance.getString(Preferences.driverName) ?? 'Sin Conductor';
    final driverCode = Preferences.instance.getString(Preferences.driverCode) ?? '';
    final busPlate = Preferences.instance.getString(Preferences.busPlate) ?? 'Sin Bus';
    final busModel = Preferences.instance.getString(Preferences.busModel) ?? '';
    final routeCode = Preferences.instance.getString(Preferences.routeCode) ?? '';
    final routeName = Preferences.instance.getString(Preferences.routeName) ?? 'Sin Ruta Asignada';
    final imei = Preferences.instance.getString(Preferences.id) ?? '';

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: BorderSide(color: theme.colorScheme.primary.withValues(alpha: 0.4), width: 1.5),
      ),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              theme.colorScheme.primaryContainer.withValues(alpha: 0.35),
              theme.colorScheme.surface,
            ],
          ),
        ),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  backgroundColor: theme.colorScheme.primary,
                  radius: 20,
                  child: const Icon(Icons.person_rounded, color: Colors.white, size: 22),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        driverName,
                        style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                      ),
                      Text(
                        'Conductor Oficial • $driverCode',
                        style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                      ),
                    ],
                  ),
                ),
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.red.shade700,
                    side: BorderSide(color: Colors.red.shade300),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  icon: const Icon(Icons.logout_rounded, size: 16),
                  label: const Text('Salir', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                  onPressed: _handleFinishShift,
                ),
              ],
            ),
            const SizedBox(height: 12),
            const Divider(height: 1),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.45),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(Icons.directions_bus_rounded, size: 15, color: theme.colorScheme.primary),
                            const SizedBox(width: 5),
                            Text('Unidad / Bus', style: theme.textTheme.bodySmall?.copyWith(fontWeight: FontWeight.bold)),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          busPlate,
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, fontFamily: 'monospace'),
                        ),
                        Text(
                          busModel,
                          style: theme.textTheme.bodySmall?.copyWith(fontSize: 10),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'IMEI: $imei',
                          style: const TextStyle(
                            fontSize: 9,
                            fontFamily: 'monospace',
                            color: Colors.green,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.45),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(Icons.alt_route_rounded, size: 15, color: theme.colorScheme.secondary),
                            const SizedBox(width: 5),
                            Text('Ruta Activa', style: theme.textTheme.bodySmall?.copyWith(fontWeight: FontWeight.bold)),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          routeCode,
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                        ),
                        Text(
                          routeName,
                          style: theme.textTheme.bodySmall?.copyWith(fontSize: 10),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLiveStatusBadge() {
    if (checkingServer) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              width: 10,
              height: 10,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            SizedBox(width: 6),
            Text('Verificando...', style: TextStyle(fontSize: 12)),
          ],
        ),
      );
    }

    if (serverReachable == true) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.green.withOpacity(0.15),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.green.withOpacity(0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: const BoxDecoration(
                color: Colors.green,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 6),
            Text(
              'En línea ${serverResponseTime != null ? "($serverResponseTime)" : ""}',
              style: const TextStyle(
                color: Colors.green,
                fontWeight: FontWeight.bold,
                fontSize: 12,
              ),
            ),
          ],
        ),
      );
    }

    if (serverReachable == false) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.red.withOpacity(0.12),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.red.withOpacity(0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: const BoxDecoration(
                color: Colors.red,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 6),
            const Text(
              'Sin conexión',
              style: TextStyle(
                color: Colors.red,
                fontWeight: FontWeight.bold,
                fontSize: 12,
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
      ),
      child: const Text('Sin verificar', style: TextStyle(fontSize: 12)),
    );
  }

  Widget _buildTrackingHeroCard() {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    final activeColor = const Color(0xFF0D9488); // Teal
    final activeBg = isDark ? activeColor.withOpacity(0.2) : activeColor.withOpacity(0.1);

    return Card(
      elevation: 0,
      color: trackingEnabled ? activeBg : null,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: BorderSide(
          color: trackingEnabled ? activeColor.withOpacity(0.4) : theme.colorScheme.outlineVariant,
          width: trackingEnabled ? 1.5 : 1,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: trackingEnabled ? activeColor.withOpacity(0.2) : theme.colorScheme.surfaceContainerHighest,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    trackingEnabled ? Icons.sensors_rounded : Icons.location_off_rounded,
                    color: trackingEnabled ? activeColor : theme.colorScheme.onSurfaceVariant,
                    size: 26,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        trackingEnabled ? 'TRANSMISIÓN EN VIVO' : 'TRANSMISIÓN EN PAUSA',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: trackingEnabled ? activeColor : theme.colorScheme.onSurface,
                          letterSpacing: 0.5,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        trackingEnabled
                            ? 'Transmitiendo coordenadas a ${Preferences.instance.getString(Preferences.url) ?? Preferences.defaultUrl}'
                            : 'Presiona el interruptor para activar el rastreo GPS',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
                Switch.adaptive(
                  value: trackingEnabled,
                  activeColor: activeColor,
                  activeTrackColor: activeColor.withValues(alpha: 0.5),
                  onChanged: _toggleTracking,
                ),
              ],
            ),
            const SizedBox(height: 14),
            const Divider(height: 1),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _buildParameterChip(
                  Icons.timer_outlined,
                  '${Preferences.instance.getInt(Preferences.interval) ?? 300}s',
                ),
                _buildParameterChip(
                  Icons.straighten_outlined,
                  '${Preferences.instance.getInt(Preferences.distance) ?? 75}m',
                ),
                _buildParameterChip(
                  Icons.gps_fixed_rounded,
                  'Precisión: ${(Preferences.instance.getString(Preferences.accuracy) ?? 'media').toUpperCase()}',
                ),
                _buildParameterChip(
                  Icons.storage_rounded,
                  (Preferences.instance.getBool(Preferences.buffer) ?? true) ? 'Buffer Activo' : 'Sin Buffer',
                ),
              ],
            ),
            if (Platform.isAndroid) ...[
              const SizedBox(height: 10),
              Text(
                AppLocalizations.of(context)!.disclosureMessage,
                style: theme.textTheme.bodySmall?.copyWith(
                  fontSize: 11,
                  color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.8),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildParameterChip(IconData icon, String label) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: theme.colorScheme.primary),
          const SizedBox(width: 5),
          Text(
            label,
            style: theme.textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }

  Widget _buildServerCard() {
    final theme = Theme.of(context);
    final currentUrl = Preferences.instance.getString(Preferences.url) ?? Preferences.defaultUrl;
    final isCustomUrl = currentUrl != Preferences.defaultUrl;

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: BorderSide(color: theme.colorScheme.outlineVariant),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.dns_rounded, color: theme.colorScheme.primary, size: 22),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Servidor Traccar',
                    style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                  ),
                ),
                _buildLiveStatusBadge(),
              ],
            ),
            const SizedBox(height: 14),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceContainerHighest.withOpacity(0.4),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: theme.colorScheme.outlineVariant.withOpacity(0.5)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.primary.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          'IP: ${Preferences.defaultServerIp}',
                          style: TextStyle(
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                            color: theme.colorScheme.primary,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.secondary.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          'Puerto: ${Preferences.defaultServerPort}',
                          style: TextStyle(
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                            color: theme.colorScheme.secondary,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'URL de Envío: $currentUrl',
                    style: const TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 12,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Protocolo: OsmAnd Client (HTTP)',
                    style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    icon: checkingServer
                        ? const SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.network_check_rounded, size: 18),
                    label: const Text('Probar Conexión'),
                    onPressed: checkingServer ? null : () => _checkServerConnection(showFeedback: true),
                  ),
                ),
                if (isCustomUrl) ...[
                  const SizedBox(width: 8),
                  FilledButton.tonalIcon(
                    style: FilledButton.styleFrom(
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    icon: const Icon(Icons.replay_rounded, size: 18),
                    label: const Text('Usar 100.77.129.90'),
                    onPressed: _resetToDefaultServer,
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDeviceIdCard() {
    final theme = Theme.of(context);
    final id = Preferences.instance.getString(Preferences.id) ?? '';

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: BorderSide(color: theme.colorScheme.outlineVariant),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.directions_car_rounded, color: theme.colorScheme.primary, size: 22),
                const SizedBox(width: 8),
                Text(
                  'Identificador del Dispositivo',
                  style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceContainerHighest.withOpacity(0.5),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      id,
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 2,
                      ),
                    ),
                  ),
                  FilledButton.tonalIcon(
                    style: FilledButton.styleFrom(
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    ),
                    icon: const Icon(Icons.copy_rounded, size: 18),
                    label: const Text('Copiar'),
                    onPressed: _copyDeviceId,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Regístralo en el panel web de Traccar (100.77.129.90:8082) o en Odoo Flota para vincular el vehículo.',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickActionsGrid() {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Text(
            'Acciones Rápidas',
            style: theme.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.bold,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ),
        Row(
          children: [
            Expanded(
              child: _buildActionTile(
                icon: Icons.near_me_rounded,
                title: 'Enviar Ubicación',
                subtitle: 'Puntual ahora',
                color: theme.colorScheme.primary,
                onTap: _sendManualPosition,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildActionTile(
                icon: Icons.warning_amber_rounded,
                title: 'Alarma SOS',
                subtitle: 'Alerta de emergencia',
                color: Colors.red.shade700,
                onTap: _sendSosAlarm,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _buildActionTile(
                icon: Icons.receipt_long_rounded,
                title: 'Ver Registros',
                subtitle: 'Historial y logs',
                color: theme.colorScheme.secondary,
                onTap: () {
                  Navigator.push(context, MaterialPageRoute(builder: (_) => const StatusScreen()));
                },
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildActionTile(
                icon: Icons.tune_rounded,
                title: 'Ajustes',
                subtitle: 'Parámetros y GPS',
                color: theme.colorScheme.tertiary,
                onTap: () async {
                  if (await PasswordService.authenticate(context) && mounted) {
                    await Navigator.push(context, MaterialPageRoute(builder: (_) => const SettingsScreen()));
                    setState(() {});
                  }
                },
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildActionTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required Color color,
    required VoidCallback onTap,
  }) {
    final theme = Theme.of(context);
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: theme.colorScheme.outlineVariant),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, color: color, size: 22),
              ),
              const SizedBox(height: 10),
              Text(
                title,
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              Text(
                subtitle,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                  fontSize: 11,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Icon(Icons.gps_fixed_rounded, size: 22),
            SizedBox(width: 8),
            Text('Traccar Flota'),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Finalizar Turno',
            icon: const Icon(Icons.logout_rounded),
            onPressed: _handleFinishShift,
          ),
          IconButton(
            tooltip: 'Comprobar Servidor',
            icon: const Icon(Icons.sync_rounded),
            onPressed: () => _checkServerConnection(showFeedback: true),
          ),
          IconButton(
            tooltip: 'Ajustes',
            icon: const Icon(Icons.tune_rounded),
            onPressed: () async {
              if (await PasswordService.authenticate(context) && mounted) {
                if (!context.mounted) return;
                await Navigator.push(context, MaterialPageRoute(builder: (_) => const SettingsScreen()));
                setState(() {});
              }
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          _refreshState();
          await _checkServerConnection(showFeedback: true);
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
          child: Column(
            children: [
              _buildDriverShiftCard(),
              const SizedBox(height: 14),
              _buildTrackingHeroCard(),
              const SizedBox(height: 14),
              _buildServerCard(),
              const SizedBox(height: 14),
              _buildDeviceIdCard(),
              const SizedBox(height: 14),
              _buildQuickActionsGrid(),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}
