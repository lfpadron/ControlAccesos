import 'dart:convert';

import 'package:http/http.dart' as http;

import 'models.dart';

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient(String baseUrl, {this.token}) : baseUrl = _normalizeBaseUrl(baseUrl);

  final String baseUrl;
  String? token;

  static String _normalizeBaseUrl(String value) {
    final trimmed = value.trim();
    if (trimmed.endsWith('/')) {
      return trimmed.substring(0, trimmed.length - 1);
    }
    return trimmed;
  }

  Future<String> login(String email, String password) async {
    final payload = await _request<Map<String, dynamic>>(
      'POST',
      '/auth/login',
      body: {'email': email.trim(), 'password': password},
      authenticated: false,
    );
    return payload['access_token'] as String;
  }

  Future<MobileSession> mobileSession() async {
    try {
      final payload = await _request<Map<String, dynamic>>('GET', '/mobile/session');
      return MobileSession.fromJson(payload);
    } on ApiException catch (error) {
      if (!_isMissingMobileRoute(error)) rethrow;
      final payload = await _request<Map<String, dynamic>>('GET', '/auth/me');
      return MobileSession.fromLegacyUser(payload);
    }
  }

  Future<List<CitaSearchResult>> searchCitas({
    required String paciente,
    String? celular,
    DateTime? fechaNacimiento,
  }) async {
    final query = {
      'paciente': paciente.trim(),
      if ((celular ?? '').trim().isNotEmpty) 'celular': celular!.trim(),
      if (fechaNacimiento != null) 'fecha_nacimiento': _dateOnly(fechaNacimiento),
    };
    List<dynamic> payload;
    try {
      payload = await _request<List<dynamic>>('GET', '/mobile/citas/buscar', query: query);
    } on ApiException catch (error) {
      if (!_isMissingMobileRoute(error)) rethrow;
      payload = await _request<List<dynamic>>('GET', '/citas/buscar', query: query);
    }
    return payload.map((item) => CitaSearchResult.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<CheckinResponse> checkinQr(String qrToken, String deviceId) async {
    final body = {
      'token': qrToken,
      'canal': 'APP_MOVIL',
      'dispositivo_id': deviceId,
    };
    Map<String, dynamic> payload;
    try {
      payload = await _request<Map<String, dynamic>>('POST', '/mobile/qr/checkin', body: body);
    } on ApiException catch (error) {
      if (!_isMissingMobileRoute(error)) rethrow;
      payload = await _request<Map<String, dynamic>>('POST', '/qr/checkin', body: body);
    }
    return CheckinResponse.fromJson(payload);
  }

  Future<CheckinResponse> checkinManual(String citaId, String deviceId) async {
    final body = {
      'canal': 'APP_MOVIL',
      'dispositivo_id': deviceId,
    };
    Map<String, dynamic> payload;
    try {
      payload = await _request<Map<String, dynamic>>('POST', '/mobile/citas/$citaId/checkin-lobby', body: body);
    } on ApiException catch (error) {
      if (!_isMissingMobileRoute(error)) rethrow;
      payload = await _request<Map<String, dynamic>>('POST', '/citas/$citaId/checkin-lobby', body: body);
    }
    return CheckinResponse.fromJson(payload);
  }

  Future<TicketResponse> fetchTicket(String citaId) async {
    Map<String, dynamic> payload;
    try {
      payload = await _request<Map<String, dynamic>>('GET', '/mobile/citas/$citaId/ticket');
    } on ApiException catch (error) {
      if (!_isMissingMobileRoute(error)) rethrow;
      payload = await _request<Map<String, dynamic>>('GET', '/citas/$citaId/ticket');
    }
    return TicketResponse.fromJson(payload);
  }

  bool _isMissingMobileRoute(ApiException error) {
    return error.statusCode == 404 && error.message == 'Not Found';
  }

  Future<T> _request<T>(
    String method,
    String path, {
    Map<String, String>? query,
    Map<String, Object?>? body,
    bool authenticated = true,
  }) async {
    final uri = _uri(path, query);
    final requestHeaders = <String, String>{
      'Content-Type': 'application/json',
      if (authenticated && token != null) 'Authorization': 'Bearer $token',
    };
    final response = await http
        .Request(method, uri)
        .apply((request) {
          request.headers.addAll(requestHeaders);
          if (body != null) {
            request.body = jsonEncode(body);
          }
        })
        .send()
        .then(http.Response.fromStream);

    final decoded = response.body.isEmpty ? null : jsonDecode(response.body);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(_errorMessage(decoded), statusCode: response.statusCode);
    }
    return decoded as T;
  }

  Uri _uri(String path, Map<String, String>? query) {
    final normalizedPath = path.startsWith('/') ? path : '/$path';
    final cleanQuery = Map<String, String>.from(query ?? const {});
    cleanQuery.removeWhere((_, value) => value.trim().isEmpty);
    final uri = Uri.parse('$baseUrl$normalizedPath');
    return cleanQuery.isEmpty ? uri : uri.replace(queryParameters: cleanQuery);
  }

  String _dateOnly(DateTime value) {
    final local = DateTime(value.year, value.month, value.day);
    return local.toIso8601String().split('T').first;
  }

  String _errorMessage(Object? decoded) {
    if (decoded is Map<String, dynamic>) {
      final detail = decoded['detail'];
      if (detail is String) return detail;
      if (detail is Map<String, dynamic> && detail['mensaje'] is String) {
        return detail['mensaje'] as String;
      }
      if (detail != null) return detail.toString();
    }
    return 'No fue posible completar la solicitud.';
  }
}

extension on http.Request {
  http.Request apply(void Function(http.Request request) block) {
    block(this);
    return this;
  }
}
