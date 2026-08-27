import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import 'models.dart';

class SessionStore {
  static const _sessionKey = 'doctorsAppSession';

  Future<SavedSession?> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_sessionKey);
    if (raw == null || raw.isEmpty) return null;
    try {
      final session = SavedSession.fromJson(
        jsonDecode(raw) as Map<String, dynamic>,
      );
      if (session.isExpired ||
          session.token.isEmpty ||
          session.apiBaseUrl.isEmpty) {
        await clear();
        return null;
      }
      return session;
    } catch (_) {
      await clear();
      return null;
    }
  }

  Future<void> save(SavedSession session) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_sessionKey, jsonEncode(session.toJson()));
  }

  Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_sessionKey);
  }
}
