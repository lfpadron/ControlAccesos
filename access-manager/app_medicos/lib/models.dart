const doctorsSessionDuration = Duration(hours: 12);

int _accessRank(String? value) {
  switch (value) {
    case 'editar':
      return 2;
    case 'consultar':
      return 1;
    default:
      return 0;
  }
}

class SavedSession {
  const SavedSession({
    required this.apiBaseUrl,
    required this.token,
    required this.user,
    required this.expiresAt,
  });

  final String apiBaseUrl;
  final String token;
  final AuthUser user;
  final DateTime expiresAt;

  bool get isExpired => DateTime.now().toUtc().isAfter(expiresAt.toUtc());

  SavedSession withUser(AuthUser updatedUser) {
    return SavedSession(
      apiBaseUrl: apiBaseUrl,
      token: token,
      user: updatedUser,
      expiresAt: expiresAt,
    );
  }

  Map<String, Object?> toJson() {
    return {
      'apiBaseUrl': apiBaseUrl,
      'token': token,
      'user': user.toJson(),
      'expiresAt': expiresAt.toUtc().toIso8601String(),
    };
  }

  factory SavedSession.fromJson(Map<String, dynamic> json) {
    return SavedSession(
      apiBaseUrl: json['apiBaseUrl'] as String? ?? '',
      token: json['token'] as String? ?? '',
      user: AuthUser.fromJson(
        json['user'] as Map<String, dynamic>? ?? const {},
      ),
      expiresAt: DateTime.parse(json['expiresAt'] as String),
    );
  }
}

class AuthUser {
  const AuthUser({
    required this.id,
    required this.nombre,
    required this.apellidos,
    required this.email,
    required this.roles,
    required this.roleCodes,
    required this.permisos,
    required this.forcePasswordChange,
  });

  final String id;
  final String nombre;
  final String apellidos;
  final String email;
  final List<String> roles;
  final List<String> roleCodes;
  final Map<String, String> permisos;
  final bool forcePasswordChange;

  String get displayName {
    final fullName = '$nombre $apellidos'.trim();
    return fullName.isEmpty ? email : fullName;
  }

  bool canRead(String screen) => _accessRank(permisos[screen]) >= 1;

  bool canWrite(String screen) => _accessRank(permisos[screen]) >= 2;

  bool get canReadPatients => canRead('pacientes');

  bool get canReadAppointments => canRead('citas');

  bool get canWriteAppointments => canWrite('citas');

  bool get canCallPatients =>
      canWrite('turnos-llamados') || canWrite('citas-hoy');

  bool get canUseDoctorsApp => canReadAppointments && canReadPatients;

  Map<String, Object?> toJson() {
    return {
      'id': id,
      'nombre': nombre,
      'apellidos': apellidos,
      'email': email,
      'roles': roles,
      'roleCodes': roleCodes,
      'permisos': permisos,
      'forcePasswordChange': forcePasswordChange,
    };
  }

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    final rawPermissions =
        json['permisos'] as Map<String, dynamic>? ?? const {};
    return AuthUser(
      id: json['id'] as String? ?? '',
      nombre: json['nombre'] as String? ?? '',
      apellidos: json['apellidos'] as String? ?? '',
      email: json['email'] as String? ?? '',
      roles: (json['roles'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .toList(),
      roleCodes:
          ((json['role_codes'] as List<dynamic>?) ??
                  (json['roleCodes'] as List<dynamic>?) ??
                  const [])
              .map((item) => item.toString())
              .toList(),
      permisos: rawPermissions.map(
        (key, value) => MapEntry(key, value.toString()),
      ),
      forcePasswordChange:
          json['force_password_change'] as bool? ??
          json['forcePasswordChange'] as bool? ??
          false,
    );
  }
}

class Medico {
  const Medico({
    required this.id,
    required this.nombre,
    required this.apellidos,
    this.usuarioId,
    this.nombreVisible,
  });

  final String id;
  final String nombre;
  final String apellidos;
  final String? usuarioId;
  final String? nombreVisible;

  String get label {
    final visible = nombreVisible?.trim();
    if (visible != null && visible.isNotEmpty) return visible;
    return '$nombre $apellidos'.trim();
  }

  factory Medico.fromJson(Map<String, dynamic> json) {
    return Medico(
      id: json['id'] as String? ?? '',
      nombre: json['nombre'] as String? ?? '',
      apellidos: json['apellidos'] as String? ?? '',
      usuarioId: json['usuario_id'] as String?,
      nombreVisible: json['nombre_visible'] as String?,
    );
  }
}

class MedicoEstado {
  const MedicoEstado({
    required this.id,
    required this.nombre,
    required this.apellidos,
    required this.estadoAtencion,
    required this.updatedAt,
    this.usuarioId,
    this.nombreVisible,
    this.notasEstado,
  });

  final String id;
  final String nombre;
  final String apellidos;
  final String estadoAtencion;
  final String updatedAt;
  final String? usuarioId;
  final String? nombreVisible;
  final String? notasEstado;

  String get label {
    final visible = nombreVisible?.trim();
    if (visible != null && visible.isNotEmpty) return visible;
    return '$nombre $apellidos'.trim();
  }

  factory MedicoEstado.fromJson(Map<String, dynamic> json) {
    return MedicoEstado(
      id: json['id'] as String? ?? '',
      nombre: json['nombre'] as String? ?? '',
      apellidos: json['apellidos'] as String? ?? '',
      estadoAtencion: json['estado_atencion'] as String? ?? 'DISPONIBLE',
      updatedAt: json['updated_at'] as String? ?? '',
      usuarioId: json['usuario_id'] as String?,
      nombreVisible: json['nombre_visible'] as String?,
      notasEstado: json['notas_estado'] as String?,
    );
  }
}

class Consultorio {
  const Consultorio({
    required this.id,
    required this.complejoId,
    required this.pisoId,
    required this.codigo,
    this.nombreVisible,
  });

  final String id;
  final String complejoId;
  final String pisoId;
  final String codigo;
  final String? nombreVisible;

  String get label {
    final visible = nombreVisible?.trim();
    if (visible != null && visible.isNotEmpty) return visible;
    return codigo;
  }

  factory Consultorio.fromJson(Map<String, dynamic> json) {
    return Consultorio(
      id: json['id'] as String? ?? '',
      complejoId: json['complejo_id'] as String? ?? '',
      pisoId: json['piso_id'] as String? ?? '',
      codigo: json['codigo'] as String? ?? '',
      nombreVisible: json['nombre_visible'] as String?,
    );
  }
}

class Paciente {
  const Paciente({
    required this.id,
    required this.folioPaciente,
    this.nombre,
    this.nombrePreferido,
    this.apellidoPaterno,
    this.apellidoMaterno,
    this.celular,
    this.fechaNacimiento,
  });

  final String id;
  final String folioPaciente;
  final String? nombre;
  final String? nombrePreferido;
  final String? apellidoPaterno;
  final String? apellidoMaterno;
  final String? celular;
  final String? fechaNacimiento;

  String get displayName {
    final preferred = nombrePreferido?.trim();
    if (preferred != null && preferred.isNotEmpty) return preferred;
    final parts = [nombre, apellidoPaterno, apellidoMaterno]
        .where((value) => value != null && value.trim().isNotEmpty)
        .map((value) => value!.trim());
    final fullName = parts.join(' ');
    return fullName.isEmpty ? folioPaciente : fullName;
  }

  String get detail {
    final parts = [
      if (folioPaciente.isNotEmpty) folioPaciente,
      if ((celular ?? '').isNotEmpty) celular!,
      if ((fechaNacimiento ?? '').isNotEmpty) fechaNacimiento!,
    ];
    return parts.join(' · ');
  }

  factory Paciente.fromJson(Map<String, dynamic> json) {
    return Paciente(
      id: json['id'] as String? ?? '',
      folioPaciente: json['folio_paciente'] as String? ?? '',
      nombre: json['nombre'] as String?,
      nombrePreferido: json['nombre_preferido'] as String?,
      apellidoPaterno: json['apellido_paterno'] as String?,
      apellidoMaterno: json['apellido_materno'] as String?,
      celular: json['celular'] as String?,
      fechaNacimiento: json['fecha_nacimiento'] as String?,
    );
  }
}

class Cita {
  const Cita({
    required this.id,
    required this.tipo,
    required this.estado,
    required this.pacienteId,
    required this.medicoId,
    required this.consultorioId,
    required this.complejoId,
    required this.pisoId,
    required this.fechaCita,
    required this.horaCita,
    required this.folioTurno,
    this.duracionEstimada,
    this.paciente,
    this.pacienteNombreCompleto,
    this.consultorio,
    this.piso,
    this.medico,
  });

  final String id;
  final String tipo;
  final String estado;
  final String pacienteId;
  final String medicoId;
  final String consultorioId;
  final String complejoId;
  final String pisoId;
  final String fechaCita;
  final String horaCita;
  final int? duracionEstimada;
  final String folioTurno;
  final String? paciente;
  final String? pacienteNombreCompleto;
  final String? consultorio;
  final String? piso;
  final String? medico;

  bool get hasArrived => {
    'LLEGO_LOBBY',
    'AUTORIZADO_PASAR',
    'EN_CONSULTA',
    'FINALIZADA',
  }.contains(estado);

  bool get isTerminal =>
      {'CANCELADA', 'EXPIRADA', 'FINALIZADA', 'NO_LLEGO'}.contains(estado);

  String get patientLabel => pacienteNombreCompleto ?? paciente ?? pacienteId;

  factory Cita.fromJson(Map<String, dynamic> json) {
    return Cita(
      id: json['id'] as String? ?? '',
      tipo: json['tipo'] as String? ?? '',
      estado: json['estado'] as String? ?? '',
      pacienteId: json['paciente_id'] as String? ?? '',
      medicoId: json['medico_id'] as String? ?? '',
      consultorioId: json['consultorio_id'] as String? ?? '',
      complejoId: json['complejo_id'] as String? ?? '',
      pisoId: json['piso_id'] as String? ?? '',
      fechaCita: json['fecha_cita'] as String? ?? '',
      horaCita: json['hora_cita'] as String? ?? '',
      duracionEstimada: json['duracion_estimada'] as int?,
      folioTurno: json['folio_turno'] as String? ?? '',
      paciente: json['paciente'] as String?,
      pacienteNombreCompleto: json['paciente_nombre_completo'] as String?,
      consultorio: json['consultorio'] as String?,
      piso: json['piso'] as String?,
      medico: json['medico'] as String?,
    );
  }
}

class QrAccess {
  const QrAccess({
    required this.id,
    required this.citaId,
    required this.estado,
    required this.fechaExpiracion,
    required this.qrPayload,
  });

  final String id;
  final String citaId;
  final String estado;
  final String fechaExpiracion;
  final String qrPayload;

  factory QrAccess.fromJson(Map<String, dynamic> json) {
    return QrAccess(
      id: json['id'] as String? ?? '',
      citaId: json['cita_id'] as String? ?? '',
      estado: json['estado'] as String? ?? '',
      fechaExpiracion: json['fecha_expiracion'] as String? ?? '',
      qrPayload: json['qr_payload'] as String? ?? '',
    );
  }
}

class CitaActionResponse {
  const CitaActionResponse({
    required this.id,
    required this.estado,
    required this.folioTurno,
  });

  final String id;
  final String estado;
  final String folioTurno;

  factory CitaActionResponse.fromJson(Map<String, dynamic> json) {
    return CitaActionResponse(
      id: json['id'] as String? ?? '',
      estado: json['estado'] as String? ?? '',
      folioTurno: json['folio_turno'] as String? ?? '',
    );
  }
}

class CitaCallResponse {
  const CitaCallResponse({
    required this.turno,
    required this.consultorio,
    required this.estadoCita,
    required this.llamadoNumero,
  });

  final String turno;
  final String consultorio;
  final String estadoCita;
  final int llamadoNumero;

  factory CitaCallResponse.fromJson(Map<String, dynamic> json) {
    return CitaCallResponse(
      turno: json['turno'] as String? ?? '',
      consultorio: json['consultorio'] as String? ?? '',
      estadoCita: json['estado_cita'] as String? ?? '',
      llamadoNumero: json['llamado_numero'] as int? ?? 1,
    );
  }
}
