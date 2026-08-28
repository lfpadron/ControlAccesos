import 'dart:convert';

import 'package:http/http.dart' as http;

import 'models.dart';

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode, this.detail});

  final String message;
  final int? statusCode;
  final Object? detail;

  bool get isDuplicateAppointment {
    return statusCode == 409 &&
        detail is Map &&
        (detail as Map).containsKey('duplicados');
  }

  List<String> get duplicateSummaries {
    if (detail is! Map) return const [];
    final raw = (detail as Map)['duplicados'];
    if (raw is! List) return const [];
    return raw.map((item) {
      if (item is Map) {
        final folio = item['folio_turno']?.toString() ?? '-';
        final estado = item['estado']?.toString() ?? '-';
        return 'Turno $folio · $estado';
      }
      return item.toString();
    }).toList();
  }

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient(String baseUrl, {this.token})
    : baseUrl = _normalizeBaseUrl(baseUrl);

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

  Future<AuthUser> currentUser() async {
    final payload = await _request<Map<String, dynamic>>('GET', '/auth/me');
    return AuthUser.fromJson(payload);
  }

  Future<List<Medico>> listMedicos() async {
    final payload = await _request<List<dynamic>>(
      'GET',
      '/catalogos-operativos/medicos',
    );
    return payload
        .map((item) => Medico.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<List<MedicoEstado>> listMedicosEstado() async {
    final payload = await _request<List<dynamic>>(
      'GET',
      '/estado-medico/medicos',
    );
    return payload
        .map((item) => MedicoEstado.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<MedicoEstado> updateMedicoEstado(
    String medicoId, {
    required String estadoAtencion,
    String? notasEstado,
  }) async {
    final payload = await _request<Map<String, dynamic>>(
      'PATCH',
      '/estado-medico/medicos/$medicoId',
      body: {'estado_atencion': estadoAtencion, 'notas_estado': notasEstado},
    );
    return MedicoEstado.fromJson(payload);
  }

  Future<List<Consultorio>> listConsultorios({String? medicoId}) async {
    final payload = await _request<List<dynamic>>(
      'GET',
      '/catalogos-operativos/consultorios',
      query: {
        if (medicoId != null && medicoId.isNotEmpty) 'medico_id': medicoId,
      },
    );
    return payload
        .map((item) => Consultorio.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<List<Paciente>> listPacientes({String? medicoId}) async {
    final payload = await _request<List<dynamic>>(
      'GET',
      '/pacientes',
      query: {
        if (medicoId != null && medicoId.isNotEmpty) 'medico_id': medicoId,
      },
    );
    return payload
        .map((item) => Paciente.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<List<Paciente>> searchPacientes(String q, {String? medicoId}) async {
    final payload = await _request<List<dynamic>>(
      'GET',
      '/pacientes/buscar',
      query: {
        'q': q.trim(),
        if (medicoId != null && medicoId.isNotEmpty) 'medico_id': medicoId,
      },
    );
    return payload
        .map((item) => Paciente.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<List<Cita>> listCitas({
    String? fecha,
    String? fechaInicio,
    String? paciente,
    String? medicoId,
    String? estado,
    String? tipo,
    int limit = 200,
  }) async {
    final query = <String, String>{'limit': limit.toString()};
    if (fecha != null) query['fecha'] = fecha;
    if (fechaInicio != null) query['fecha_inicio'] = fechaInicio;
    if (paciente != null && paciente.trim().isNotEmpty) {
      query['paciente'] = paciente.trim();
    }
    if (medicoId != null && medicoId.isNotEmpty) query['medico_id'] = medicoId;
    if (estado != null && estado.isNotEmpty && estado != 'TODAS') {
      query['estado'] = estado;
    }
    if (tipo != null && tipo.isNotEmpty && tipo != 'TODAS') {
      query['tipo'] = tipo;
    }
    final payload = await _request<List<dynamic>>(
      'GET',
      '/citas',
      query: query,
    );
    return payload
        .map((item) => Cita.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<Cita> createCita(
    Map<String, Object?> payload, {
    bool confirmarDuplicado = false,
  }) async {
    final response = await _request<Map<String, dynamic>>(
      'POST',
      '/citas',
      query: {if (confirmarDuplicado) 'confirmar_duplicado': 'true'},
      body: payload,
    );
    return Cita.fromJson(response);
  }

  Future<CitaActionResponse> cancelarCita(String citaId) async {
    final payload = await _request<Map<String, dynamic>>(
      'PATCH',
      '/citas/$citaId/cancelar',
    );
    return CitaActionResponse.fromJson(payload);
  }

  Future<QrAccess> generarQr(String citaId) async {
    final payload = await _request<Map<String, dynamic>>(
      'POST',
      '/citas/$citaId/qr',
    );
    return QrAccess.fromJson(payload);
  }

  Future<CitaCallResponse> llamarCita(String citaId) async {
    final payload = await _request<Map<String, dynamic>>(
      'POST',
      '/citas/$citaId/llamar',
    );
    return CitaCallResponse.fromJson(payload);
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
    final response = await http.Request(method, uri)
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
      final detail = decoded is Map<String, dynamic>
          ? decoded['detail'] ?? decoded
          : decoded;
      throw ApiException(
        _errorMessage(detail),
        statusCode: response.statusCode,
        detail: detail,
      );
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

  String _errorMessage(Object? detail) {
    if (detail is String) return detail;
    if (detail is List) {
      final messages = detail
          .map((item) {
            if (item is Map<String, dynamic>) {
              final location = (item['loc'] as List<dynamic>? ?? const [])
                  .where((part) => part != 'body')
                  .join('.');
              final message = (item['msg'] as String? ?? 'Entrada inválida')
                  .replaceFirst('Value error, ', '');
              return location.isEmpty ? message : '$location: $message';
            }
            return item.toString();
          })
          .where((item) => item.isNotEmpty);
      return messages.isEmpty
          ? 'No fue posible completar la solicitud.'
          : messages.join(' · ');
    }
    if (detail is Map<String, dynamic>) {
      final message = detail['mensaje'];
      if (message is String) return message;
      final nestedDetail = detail['detail'];
      if (nestedDetail != null) return _errorMessage(nestedDetail);
      return detail.toString();
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
