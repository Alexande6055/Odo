import 'dart:io';
import 'dart:math';

import 'package:shared_preferences/shared_preferences.dart';
import 'package:shared_preferences_android/shared_preferences_android.dart';
import 'package:traccar_client_sdk/traccar_client_sdk.dart';

class Preferences {
  static Future<void>? _initFuture;
  static late SharedPreferencesWithCache instance;

  static const String defaultServerIp = '100.77.129.90';
  static const int defaultServerPort = 5055;
  static const String defaultUrl = 'http://$defaultServerIp:$defaultServerPort';

  static const String id = 'id';
  static const String url = 'url';
  static const String accuracy = 'accuracy';
  static const String distance = 'distance';
  static const String interval = 'interval';
  static const String angle = 'angle';
  static const String heartbeat = 'heartbeat';
  static const String buffer = 'buffer';
  static const String wakelock = 'wakelock';
  static const String stopDetection = 'stop_detection';
  static const String preferPlatformProviders = 'prefer_platform_providers';
  static const String password = 'password';
  static const String autoStart = 'auto_start';

  // Driver & Fleet Session Keys
  static const String driverName = 'driver_name';
  static const String driverCode = 'driver_code';
  static const String busPlate = 'bus_plate';
  static const String busModel = 'bus_model';
  static const String routeCode = 'route_code';
  static const String routeName = 'route_name';
  static const String shiftStartTime = 'shift_start_time';

  static bool get isDriverLoggedIn =>
      (instance.getString(driverName)?.isNotEmpty ?? false) &&
      (instance.getString(busPlate)?.isNotEmpty ?? false);

  static Future<void> saveDriverSession({
    required String driver,
    required String code,
    required String plate,
    required String model,
    required String imei,
    required String rCode,
    required String rName,
  }) async {
    await instance.setString(driverName, driver);
    await instance.setString(driverCode, code);
    await instance.setString(busPlate, plate);
    await instance.setString(busModel, model);
    await instance.setString(id, imei);
    await instance.setString(routeCode, rCode);
    await instance.setString(routeName, rName);
    await instance.setString(shiftStartTime, DateTime.now().toIso8601String());
  }

  static Future<void> clearDriverSession() async {
    await instance.remove(driverName);
    await instance.remove(driverCode);
    await instance.remove(busPlate);
    await instance.remove(busModel);
    await instance.remove(routeCode);
    await instance.remove(routeName);
    await instance.remove(shiftStartTime);
  }

  static Future<void> init() async {
    _initFuture ??= _createInstance();
    await _initFuture;
  }

  static Future<void> _createInstance() async {
    instance = await SharedPreferencesWithCache.create(
      sharedPreferencesOptions: Platform.isAndroid
          ? SharedPreferencesAsyncAndroidOptions(backend: SharedPreferencesAndroidBackendLibrary.SharedPreferences)
          : SharedPreferencesOptions(),
      cacheOptions: SharedPreferencesWithCacheOptions(
        allowList: {
          id, url, accuracy, distance, interval, angle, heartbeat, buffer, wakelock, stopDetection, preferPlatformProviders, password, autoStart,
          driverName, driverCode, busPlate, busModel, routeCode, routeName, shiftStartTime,
        },
      ),
    );
    if (Platform.isAndroid) {
      for (final key in {interval, distance, angle, heartbeat}) {
        if (instance.get(key) is String) {
          await instance.setInt(key, int.tryParse(instance.getString(key) ?? '') ?? 0);
        }
      }
    }
    if (instance.getString(id) == null) {
      await instance.setString(id, (Random().nextInt(90000000) + 10000000).toString());
      await instance.setString(url, defaultUrl);
      await instance.setString(accuracy, 'highest');
      await instance.setInt(interval, 5);
      await instance.setInt(distance, 0);
      await instance.setBool(buffer, true);
      await instance.setBool(stopDetection, false);
      await instance.setBool(wakelock, true);
      await instance.setBool(autoStart, true);
    } else {
      // Auto-migrate if it's the demo server or empty so it immediately points to the configured server
      final currentUrl = instance.getString(url);
      if (currentUrl == null || currentUrl.isEmpty || currentUrl.contains('demo.traccar.org')) {
        await instance.setString(url, defaultUrl);
      }
      // Ensure real-time interval if it was still on the slow 300s default
      final currentInterval = instance.getInt(interval);
      if (currentInterval == null || currentInterval > 30) {
        await instance.setInt(interval, 5);
      }
      final currentDistance = instance.getInt(distance);
      if (currentDistance == null || currentDistance > 20) {
        await instance.setInt(distance, 0);
      }
      await instance.setString(accuracy, 'highest');
      await instance.setBool(wakelock, true);
      await instance.setBool(stopDetection, false);
    }
  }

  static Future<void> resetToDefaultServer() async {
    await instance.setString(url, defaultUrl);
  }

  static Config buildConfig() {
    return Config(
      serverUrl: instance.getString(url) ?? defaultUrl,
      deviceId: instance.getString(id) ?? '',
      location: LocationConfig(
        accuracy: switch (instance.getString(accuracy)) {
          'highest' => Accuracy.highest,
          'high' => Accuracy.high,
          'low' => Accuracy.low,
          _ => Accuracy.highest,
        },
        distanceMeters: instance.getInt(distance) ?? 0,
        intervalSeconds: instance.getInt(interval) ?? 5,
        angleDegrees: instance.getInt(angle) ?? 0,
        heartbeatIntervalSeconds: instance.getInt(heartbeat) ?? 0,
        stopDetection: instance.getBool(stopDetection) ?? false,
      ),
      wakeLock: instance.getBool(wakelock) ?? true,
      buffer: instance.getBool(buffer) ?? true,
      preferPlatformProviders: instance.getBool(preferPlatformProviders) ?? false,
    );
  }
}
