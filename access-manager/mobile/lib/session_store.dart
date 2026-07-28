import 'package:shared_preferences/shared_preferences.dart';

import 'models.dart';

class SessionStore {
  static const _apiBaseUrl = 'apiBaseUrl';
  static const _token = 'token';
  static const _email = 'email';
  static const _name = 'name';
  static const _roles = 'roles';
  static const _expiresAt = 'expiresAt';
  static const _canCheckin = 'canCheckin';
  static const _canViewLogs = 'canViewLogs';
  static const _deviceId = 'deviceId';

  Future<SavedSession?> load() async {
    final prefs = await SharedPreferences.getInstance();
    final apiBaseUrl = prefs.getString(_apiBaseUrl);
    final token = prefs.getString(_token);
    final email = prefs.getString(_email);
    final name = prefs.getString(_name);
    final expiresAtText = prefs.getString(_expiresAt);
    if ([apiBaseUrl, token, email, name, expiresAtText].any((item) => item == null || item.isEmpty)) {
      return null;
    }
    final session = SavedSession(
      apiBaseUrl: apiBaseUrl!,
      token: token!,
      email: email!,
      name: name!,
      roles: prefs.getStringList(_roles) ?? const [],
      expiresAt: DateTime.parse(expiresAtText!),
      canCheckin: prefs.getBool(_canCheckin) ?? false,
      canViewLogs: prefs.getBool(_canViewLogs) ?? false,
    );
    if (session.isExpired) {
      await clear();
      return null;
    }
    return session;
  }

  Future<void> save(SavedSession session) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_apiBaseUrl, session.apiBaseUrl);
    await prefs.setString(_token, session.token);
    await prefs.setString(_email, session.email);
    await prefs.setString(_name, session.name);
    await prefs.setStringList(_roles, session.roles);
    await prefs.setString(_expiresAt, session.expiresAt.toUtc().toIso8601String());
    await prefs.setBool(_canCheckin, session.canCheckin);
    await prefs.setBool(_canViewLogs, session.canViewLogs);
  }

  Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_token);
    await prefs.remove(_email);
    await prefs.remove(_name);
    await prefs.remove(_roles);
    await prefs.remove(_expiresAt);
    await prefs.remove(_canCheckin);
    await prefs.remove(_canViewLogs);
  }

  Future<String> deviceId() async {
    final prefs = await SharedPreferences.getInstance();
    final existing = prefs.getString(_deviceId);
    if (existing != null && existing.isNotEmpty) return existing;
    final generated = 'android-${DateTime.now().microsecondsSinceEpoch}';
    await prefs.setString(_deviceId, generated);
    return generated;
  }
}
