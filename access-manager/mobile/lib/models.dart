const mobileSessionDuration = Duration(hours: 12);

class SavedSession {
  const SavedSession({
    required this.apiBaseUrl,
    required this.token,
    required this.email,
    required this.name,
    required this.roles,
    required this.expiresAt,
    required this.canCheckin,
    required this.canViewLogs,
  });

  final String apiBaseUrl;
  final String token;
  final String email;
  final String name;
  final List<String> roles;
  final DateTime expiresAt;
  final bool canCheckin;
  final bool canViewLogs;

  bool get isExpired => DateTime.now().toUtc().isAfter(expiresAt.toUtc());

  SavedSession withServerSession(MobileSession session) {
    return SavedSession(
      apiBaseUrl: apiBaseUrl,
      token: token,
      email: session.email,
      name: session.name,
      roles: session.roles,
      expiresAt: expiresAt,
      canCheckin: session.canCheckin,
      canViewLogs: session.canViewLogs,
    );
  }
}

class MobileSession {
  const MobileSession({
    required this.userId,
    required this.name,
    required this.email,
    required this.roles,
    required this.canCheckin,
    required this.canViewLogs,
  });

  final String userId;
  final String name;
  final String email;
  final List<String> roles;
  final bool canCheckin;
  final bool canViewLogs;

  factory MobileSession.fromJson(Map<String, dynamic> json) {
    return MobileSession(
      userId: json['usuario_id'] as String? ?? '',
      name: json['nombre'] as String? ?? '',
      email: json['email'] as String? ?? '',
      roles: (json['roles'] as List<dynamic>? ?? const []).map((item) => item.toString()).toList(),
      canCheckin: json['can_checkin'] as bool? ?? false,
      canViewLogs: json['can_view_logs'] as bool? ?? false,
    );
  }

  factory MobileSession.fromLegacyUser(Map<String, dynamic> json) {
    return MobileSession(
      userId: json['id'] as String? ?? '',
      name: json['nombre'] as String? ?? '',
      email: json['email'] as String? ?? '',
      roles: const ['API_REAL'],
      canCheckin: true,
      canViewLogs: false,
    );
  }
}

class CitaSearchResult {
  const CitaSearchResult({
    required this.id,
    required this.folioTurno,
    required this.horaCita,
    required this.estado,
    this.consultorio,
    this.piso,
  });

  final String id;
  final String folioTurno;
  final String horaCita;
  final String estado;
  final String? consultorio;
  final String? piso;

  factory CitaSearchResult.fromJson(Map<String, dynamic> json) {
    return CitaSearchResult(
      id: json['id'] as String? ?? '',
      folioTurno: json['folio_turno'] as String? ?? '',
      horaCita: json['hora_cita'] as String? ?? '',
      estado: json['estado'] as String? ?? '',
      consultorio: json['consultorio'] as String?,
      piso: json['piso'] as String?,
    );
  }
}

class CheckinResponse {
  const CheckinResponse({
    required this.resultado,
    required this.mensaje,
    this.citaId,
    this.folioTurno,
    this.estadoCita,
  });

  final String resultado;
  final String mensaje;
  final String? citaId;
  final String? folioTurno;
  final String? estadoCita;

  factory CheckinResponse.fromJson(Map<String, dynamic> json) {
    return CheckinResponse(
      resultado: json['resultado'] as String? ?? '',
      mensaje: json['mensaje'] as String? ?? '',
      citaId: json['cita_id'] as String?,
      folioTurno: json['folio_turno'] as String?,
      estadoCita: json['estado_cita'] as String?,
    );
  }
}

class TicketResponse {
  const TicketResponse({
    required this.encabezadoFecha,
    required this.leyenda,
    required this.turno,
    required this.qrPayload,
    required this.consultorio,
    required this.piso,
    required this.hora,
  });

  final String encabezadoFecha;
  final String leyenda;
  final String turno;
  final String qrPayload;
  final String consultorio;
  final String piso;
  final String hora;

  factory TicketResponse.fromJson(Map<String, dynamic> json) {
    return TicketResponse(
      encabezadoFecha: json['encabezado_fecha'] as String? ?? '',
      leyenda: json['leyenda'] as String? ?? '',
      turno: json['turno'] as String? ?? '',
      qrPayload: json['qr_payload'] as String? ?? '',
      consultorio: json['consultorio'] as String? ?? '',
      piso: json['piso'] as String? ?? '',
      hora: json['hora'] as String? ?? '',
    );
  }
}

class ActivityLogEntry {
  const ActivityLogEntry({
    required this.id,
    required this.qrToken,
    required this.folioTurno,
    required this.createdAt,
    required this.recepcionistaLogin,
  });

  final int id;
  final String? qrToken;
  final String? folioTurno;
  final DateTime createdAt;
  final String recepcionistaLogin;

  factory ActivityLogEntry.fromMap(Map<String, Object?> map) {
    return ActivityLogEntry(
      id: map['id'] as int,
      qrToken: map['qr_token'] as String?,
      folioTurno: map['folio_turno'] as String?,
      createdAt: DateTime.parse(map['created_at'] as String),
      recepcionistaLogin: map['recepcionista_login'] as String,
    );
  }
}
