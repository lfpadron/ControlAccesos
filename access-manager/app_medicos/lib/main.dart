import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:qr_flutter/qr_flutter.dart';

import 'api_client.dart';
import 'models.dart';
import 'session_store.dart';

const defaultApiBaseUrl = String.fromEnvironment(
  'DOCTORS_API_BASE_URL',
  defaultValue: 'https://control-acceso-qr.com.mx/api',
);

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const DoctorsMobileApp());
}

class DoctorsMobileApp extends StatefulWidget {
  const DoctorsMobileApp({super.key});

  @override
  State<DoctorsMobileApp> createState() => _DoctorsMobileAppState();
}

class _DoctorsMobileAppState extends State<DoctorsMobileApp> {
  final SessionStore _sessionStore = SessionStore();
  SavedSession? _session;
  ApiClient? _api;
  Timer? _expirationTimer;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  @override
  void dispose() {
    _expirationTimer?.cancel();
    super.dispose();
  }

  Future<void> _bootstrap() async {
    final saved = await _sessionStore.load();
    if (saved == null) {
      if (!mounted) return;
      setState(() => _loading = false);
      return;
    }

    final api = ApiClient(saved.apiBaseUrl, token: saved.token);
    try {
      final user = await api.currentUser();
      _ensureDoctorAppAccess(user);
      final refreshed = saved.withUser(user);
      await _sessionStore.save(refreshed);
      if (!mounted) return;
      setState(() {
        _session = refreshed;
        _api = api;
        _loading = false;
      });
      _scheduleExpiration(refreshed);
    } catch (_) {
      await _sessionStore.clear();
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  Future<void> _login(String apiBaseUrl, String email, String password) async {
    final api = ApiClient(apiBaseUrl);
    final token = await api.login(email, password);
    api.token = token;
    final user = await api.currentUser();
    _ensureDoctorAppAccess(user);
    final session = SavedSession(
      apiBaseUrl: api.baseUrl,
      token: token,
      user: user,
      expiresAt: DateTime.now().toUtc().add(doctorsSessionDuration),
    );
    await _sessionStore.save(session);
    if (!mounted) return;
    setState(() {
      _session = session;
      _api = api;
    });
    _scheduleExpiration(session);
  }

  Future<void> _logout() async {
    _expirationTimer?.cancel();
    await _sessionStore.clear();
    if (!mounted) return;
    setState(() {
      _session = null;
      _api = null;
    });
  }

  void _ensureDoctorAppAccess(AuthUser user) {
    if (user.forcePasswordChange) {
      throw const ApiException(
        'Debe cambiar su contraseña desde la plataforma web antes de usar la app.',
      );
    }
    if (!user.canUseDoctorsApp) {
      throw const ApiException(
        'El usuario no tiene permisos de pacientes y citas para usar la app de médicos.',
      );
    }
  }

  void _scheduleExpiration(SavedSession session) {
    _expirationTimer?.cancel();
    final delay = session.expiresAt.toUtc().difference(DateTime.now().toUtc());
    if (delay <= Duration.zero) {
      unawaited(_logout());
      return;
    }
    _expirationTimer = Timer(delay, () => unawaited(_logout()));
  }

  @override
  Widget build(BuildContext context) {
    final session = _session;
    final api = _api;
    return MaterialApp(
      title: 'App de Médicos',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF0F766E)),
        useMaterial3: true,
        cardTheme: const CardThemeData(
          margin: EdgeInsets.zero,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(8)),
          ),
        ),
        inputDecorationTheme: const InputDecorationTheme(
          border: OutlineInputBorder(),
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          ),
        ),
      ),
      home: _loading
          ? const LoadingScreen()
          : session == null || api == null
          ? LoginScreen(onLogin: _login)
          : HomeScreen(session: session, api: api, onLogout: _logout),
    );
  }
}

class LoadingScreen extends StatelessWidget {
  const LoadingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const Scaffold(body: Center(child: CircularProgressIndicator()));
  }
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.onLogin});

  final Future<void> Function(String apiBaseUrl, String email, String password)
  onLogin;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _serverController = TextEditingController(text: defaultApiBaseUrl);
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _loading = false;
  bool _obscure = true;
  String? _error;

  @override
  void dispose() {
    _serverController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await widget.onLogin(
        _serverController.text,
        _emailController.text,
        _passwordController.text,
      );
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 460),
            child: ListView(
              padding: const EdgeInsets.all(20),
              shrinkWrap: true,
              children: [
                Icon(
                  Icons.medical_services_outlined,
                  size: 58,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(height: 14),
                Text(
                  'App de Médicos',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 6),
                Text(
                  'Agenda clínica y llamados',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                const SizedBox(height: 24),
                Form(
                  key: _formKey,
                  child: Column(
                    children: [
                      TextFormField(
                        controller: _serverController,
                        keyboardType: TextInputType.url,
                        decoration: const InputDecoration(
                          labelText: 'Servidor API',
                        ),
                        validator: (value) {
                          final uri = Uri.tryParse(value?.trim() ?? '');
                          if (uri == null ||
                              !uri.hasScheme ||
                              uri.host.isEmpty) {
                            return 'Indique una URL válida.';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 14),
                      TextFormField(
                        controller: _emailController,
                        keyboardType: TextInputType.emailAddress,
                        autofillHints: const [AutofillHints.username],
                        decoration: const InputDecoration(labelText: 'Correo'),
                        validator: (value) => (value?.trim().isEmpty ?? true)
                            ? 'Capture el correo.'
                            : null,
                      ),
                      const SizedBox(height: 14),
                      TextFormField(
                        controller: _passwordController,
                        obscureText: _obscure,
                        autofillHints: const [AutofillHints.password],
                        decoration: InputDecoration(
                          labelText: 'Contraseña',
                          suffixIcon: IconButton(
                            tooltip: _obscure ? 'Mostrar' : 'Ocultar',
                            icon: Icon(
                              _obscure
                                  ? Icons.visibility_outlined
                                  : Icons.visibility_off_outlined,
                            ),
                            onPressed: () =>
                                setState(() => _obscure = !_obscure),
                          ),
                        ),
                        validator: (value) => (value?.isEmpty ?? true)
                            ? 'Capture la contraseña.'
                            : null,
                        onFieldSubmitted: (_) => _submit(),
                      ),
                      const SizedBox(height: 18),
                      FilledButton.icon(
                        onPressed: _loading ? null : _submit,
                        icon: _loading
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.login),
                        label: const Text('Iniciar sesión'),
                      ),
                    ],
                  ),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 16),
                  ErrorBanner(message: _error!),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({
    super.key,
    required this.session,
    required this.api,
    required this.onLogout,
  });

  final SavedSession session;
  final ApiClient api;
  final Future<void> Function() onLogout;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _agendaKey = GlobalKey<_AgendaScreenState>();
  final _patientsKey = GlobalKey<_PatientsScreenState>();
  int _selectedIndex = 0;

  String get _title {
    return switch (_selectedIndex) {
      0 => 'Agenda',
      1 => 'Pacientes',
      2 => 'Nueva cita',
      _ => 'Perfil',
    };
  }

  void _refreshCurrentTab() {
    if (_selectedIndex == 0) {
      _agendaKey.currentState?.refresh();
    } else if (_selectedIndex == 1) {
      _patientsKey.currentState?.refresh();
    }
  }

  Future<void> _openAppointmentForm({
    Paciente? patient,
    String? medicoId,
  }) async {
    final created = await Navigator.of(context).push<Cita>(
      MaterialPageRoute(
        builder: (_) => AppointmentFormPage(
          api: widget.api,
          session: widget.session,
          initialPatient: patient,
          initialMedicoId: medicoId,
        ),
      ),
    );
    if (created != null) {
      _agendaKey.currentState?.refresh();
      if (mounted) setState(() => _selectedIndex = 0);
    }
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      AgendaScreen(key: _agendaKey, api: widget.api, session: widget.session),
      PatientsScreen(
        key: _patientsKey,
        api: widget.api,
        session: widget.session,
        onCreateAppointment: (patient, medicoId) =>
            _openAppointmentForm(patient: patient, medicoId: medicoId),
      ),
      AppointmentFormContent(
        api: widget.api,
        session: widget.session,
        onCreated: (cita) {
          _agendaKey.currentState?.refresh();
          setState(() => _selectedIndex = 0);
        },
      ),
      ProfileScreen(session: widget.session, onLogout: widget.onLogout),
    ];

    return Scaffold(
      appBar: AppBar(
        title: Text(_title),
        actions: [
          if (_selectedIndex <= 1)
            IconButton(
              tooltip: 'Actualizar',
              onPressed: _refreshCurrentTab,
              icon: const Icon(Icons.refresh),
            ),
          IconButton(
            tooltip: 'Cerrar sesión',
            onPressed: widget.onLogout,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: SafeArea(
        child: IndexedStack(index: _selectedIndex, children: pages),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) =>
            setState(() => _selectedIndex = index),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.calendar_today_outlined),
            selectedIcon: Icon(Icons.calendar_today),
            label: 'Agenda',
          ),
          NavigationDestination(
            icon: Icon(Icons.groups_outlined),
            selectedIcon: Icon(Icons.groups),
            label: 'Pacientes',
          ),
          NavigationDestination(
            icon: Icon(Icons.add_circle_outline),
            selectedIcon: Icon(Icons.add_circle),
            label: 'Nueva',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Perfil',
          ),
        ],
      ),
    );
  }
}

class AgendaScreen extends StatefulWidget {
  const AgendaScreen({super.key, required this.api, required this.session});

  final ApiClient api;
  final SavedSession session;

  @override
  State<AgendaScreen> createState() => _AgendaScreenState();
}

class _AgendaScreenState extends State<AgendaScreen> {
  final _patientSearchController = TextEditingController();
  List<Medico> _medicos = const [];
  List<Cita> _citas = const [];
  DateTime _selectedDate = DateTime.now();
  String? _selectedMedicoId;
  String _selectedEstado = 'TODAS';
  String _selectedTipo = 'TODAS';
  bool _loading = true;
  bool _catalogLoading = true;
  String? _error;
  String? _busyCitaId;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _loadInitial();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => unawaited(refresh(silent: true)),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _patientSearchController.dispose();
    super.dispose();
  }

  Future<void> _loadInitial() async {
    setState(() {
      _catalogLoading = true;
      _loading = true;
      _error = null;
    });
    try {
      final medicos = await widget.api.listMedicos();
      if (!mounted) return;
      setState(() {
        _medicos = medicos;
        _selectedMedicoId = medicos.length == 1 ? medicos.first.id : null;
        _catalogLoading = false;
      });
      await refresh();
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
        _catalogLoading = false;
        _loading = false;
      });
    }
  }

  Future<void> refresh({bool silent = false}) async {
    if (!silent) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final rows = await widget.api.listCitas(
        fecha: dateOnly(_selectedDate),
        paciente: _patientSearchController.text,
        medicoId: _selectedMedicoId,
        estado: _selectedEstado,
        tipo: _selectedTipo,
      );
      if (!mounted) return;
      setState(() {
        _citas = rows;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      if (!silent) {
        setState(() {
          _error = error.toString();
          _loading = false;
        });
      }
    }
  }

  Future<void> _pickDate() async {
    final selected = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime.now().subtract(const Duration(days: 365)),
      lastDate: DateTime.now().add(const Duration(days: 730)),
    );
    if (selected == null) return;
    setState(() => _selectedDate = selected);
    await refresh();
  }

  Future<void> _showQr(Cita cita) async {
    setState(() => _busyCitaId = cita.id);
    try {
      final qr = await widget.api.generarQr(cita.id);
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => QrDialog(cita: cita, qr: qr),
      );
      await refresh(silent: true);
    } catch (error) {
      if (!mounted) return;
      showSnack(context, error.toString());
    } finally {
      if (mounted) setState(() => _busyCitaId = null);
    }
  }

  Future<void> _callPatient(Cita cita) async {
    setState(() => _busyCitaId = cita.id);
    try {
      final response = await widget.api.llamarCita(cita.id);
      if (!mounted) return;
      showSnack(
        context,
        'Turno ${response.turno} llamado (${response.llamadoNumero}/3).',
      );
      await refresh(silent: true);
    } catch (error) {
      if (!mounted) return;
      showSnack(context, error.toString());
    } finally {
      if (mounted) setState(() => _busyCitaId = null);
    }
  }

  Future<void> _cancelCita(Cita cita) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Cancelar cita'),
        content: Text(
          'Se cancelará la cita ${cita.folioTurno} de ${cita.patientLabel}.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Conservar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Cancelar cita'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    setState(() => _busyCitaId = cita.id);
    try {
      await widget.api.cancelarCita(cita.id);
      if (!mounted) return;
      showSnack(context, 'Cita ${cita.folioTurno} cancelada.');
      await refresh(silent: true);
    } catch (error) {
      if (!mounted) return;
      showSnack(context, error.toString());
    } finally {
      if (mounted) setState(() => _busyCitaId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_catalogLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    return RefreshIndicator(
      onRefresh: refresh,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          FilterPanel(
            children: [
              DropdownButtonFormField<String?>(
                initialValue: _selectedMedicoId,
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Médico'),
                items: [
                  const DropdownMenuItem<String?>(
                    value: null,
                    child: Text('Todos los médicos accesibles'),
                  ),
                  ..._medicos.map(
                    (medico) => DropdownMenuItem<String?>(
                      value: medico.id,
                      child: Text(medico.label),
                    ),
                  ),
                ],
                onChanged: (value) {
                  setState(() => _selectedMedicoId = value);
                  unawaited(refresh());
                },
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _pickDate,
                      icon: const Icon(Icons.event),
                      label: Text(formatDate(_selectedDate)),
                    ),
                  ),
                  const SizedBox(width: 10),
                  IconButton.filledTonal(
                    tooltip: 'Hoy',
                    onPressed: () {
                      setState(() => _selectedDate = DateTime.now());
                      unawaited(refresh());
                    },
                    icon: const Icon(Icons.today),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _patientSearchController,
                textInputAction: TextInputAction.search,
                decoration: InputDecoration(
                  labelText: 'Buscar paciente',
                  suffixIcon: IconButton(
                    tooltip: 'Buscar',
                    onPressed: refresh,
                    icon: const Icon(Icons.search),
                  ),
                ),
                onSubmitted: (_) => refresh(),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      initialValue: _selectedEstado,
                      decoration: const InputDecoration(labelText: 'Estado'),
                      items: appointmentStates
                          .map(
                            (estado) => DropdownMenuItem(
                              value: estado,
                              child: Text(appointmentStateLabel(estado)),
                            ),
                          )
                          .toList(),
                      onChanged: (value) {
                        setState(() => _selectedEstado = value ?? 'TODAS');
                        unawaited(refresh());
                      },
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      initialValue: _selectedTipo,
                      decoration: const InputDecoration(labelText: 'Tipo'),
                      items: appointmentTypes
                          .map(
                            (tipo) => DropdownMenuItem(
                              value: tipo,
                              child: Text(appointmentTypeLabel(tipo)),
                            ),
                          )
                          .toList(),
                      onChanged: (value) {
                        setState(() => _selectedTipo = value ?? 'TODAS');
                        unawaited(refresh());
                      },
                    ),
                  ),
                ],
              ),
            ],
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            ErrorBanner(message: _error!),
          ],
          const SizedBox(height: 16),
          if (_loading)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: CircularProgressIndicator(),
              ),
            )
          else if (_citas.isEmpty)
            const EmptyState(
              icon: Icons.event_busy,
              text: 'No hay citas con estos filtros.',
            )
          else
            ..._citas.map(
              (cita) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: AppointmentCard(
                  cita: cita,
                  busy: _busyCitaId == cita.id,
                  canWrite: widget.session.user.canWriteAppointments,
                  canCall: widget.session.user.canCallPatients,
                  onGenerateQr: () => _showQr(cita),
                  onCall: () => _callPatient(cita),
                  onCancel: () => _cancelCita(cita),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class PatientsScreen extends StatefulWidget {
  const PatientsScreen({
    super.key,
    required this.api,
    required this.session,
    required this.onCreateAppointment,
  });

  final ApiClient api;
  final SavedSession session;
  final void Function(Paciente patient, String? medicoId) onCreateAppointment;

  @override
  State<PatientsScreen> createState() => _PatientsScreenState();
}

class _PatientsScreenState extends State<PatientsScreen> {
  final _searchController = TextEditingController();
  List<Medico> _medicos = const [];
  List<Paciente> _patients = const [];
  String? _selectedMedicoId;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadInitial();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadInitial() async {
    try {
      final medicos = await widget.api.listMedicos();
      if (!mounted) return;
      setState(() {
        _medicos = medicos;
        _selectedMedicoId = medicos.length == 1 ? medicos.first.id : null;
      });
      await refresh();
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
        _loading = false;
      });
    }
  }

  Future<void> refresh() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final query = _searchController.text.trim();
      final rows = query.isEmpty
          ? await widget.api.listPacientes(medicoId: _selectedMedicoId)
          : await widget.api.searchPacientes(
              query,
              medicoId: _selectedMedicoId,
            );
      if (!mounted) return;
      setState(() {
        _patients = rows;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.session.user.canReadPatients) {
      return const PermissionMessage(
        message: 'El usuario no tiene permiso para consultar pacientes.',
      );
    }
    return RefreshIndicator(
      onRefresh: refresh,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          FilterPanel(
            children: [
              DropdownButtonFormField<String?>(
                initialValue: _selectedMedicoId,
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Médico'),
                items: [
                  const DropdownMenuItem<String?>(
                    value: null,
                    child: Text('Todos los médicos accesibles'),
                  ),
                  ..._medicos.map(
                    (medico) => DropdownMenuItem<String?>(
                      value: medico.id,
                      child: Text(medico.label),
                    ),
                  ),
                ],
                onChanged: (value) {
                  setState(() => _selectedMedicoId = value);
                  unawaited(refresh());
                },
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _searchController,
                textInputAction: TextInputAction.search,
                decoration: InputDecoration(
                  labelText: 'Buscar por nombre, celular o folio',
                  suffixIcon: IconButton(
                    tooltip: 'Buscar',
                    onPressed: refresh,
                    icon: const Icon(Icons.search),
                  ),
                ),
                onSubmitted: (_) => refresh(),
              ),
            ],
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            ErrorBanner(message: _error!),
          ],
          const SizedBox(height: 16),
          if (_loading)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: CircularProgressIndicator(),
              ),
            )
          else if (_patients.isEmpty)
            const EmptyState(
              icon: Icons.groups_outlined,
              text: 'No hay pacientes para mostrar.',
            )
          else
            ..._patients.map(
              (patient) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: PatientCard(
                  patient: patient,
                  canCreateAppointment:
                      widget.session.user.canWriteAppointments,
                  onCreateAppointment: () =>
                      widget.onCreateAppointment(patient, _selectedMedicoId),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class AppointmentFormPage extends StatelessWidget {
  const AppointmentFormPage({
    super.key,
    required this.api,
    required this.session,
    this.initialPatient,
    this.initialMedicoId,
  });

  final ApiClient api;
  final SavedSession session;
  final Paciente? initialPatient;
  final String? initialMedicoId;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Nueva cita')),
      body: SafeArea(
        child: AppointmentFormContent(
          api: api,
          session: session,
          initialPatient: initialPatient,
          initialMedicoId: initialMedicoId,
          onCreated: (cita) => Navigator.of(context).pop(cita),
        ),
      ),
    );
  }
}

class AppointmentFormContent extends StatefulWidget {
  const AppointmentFormContent({
    super.key,
    required this.api,
    required this.session,
    required this.onCreated,
    this.initialPatient,
    this.initialMedicoId,
  });

  final ApiClient api;
  final SavedSession session;
  final ValueChanged<Cita> onCreated;
  final Paciente? initialPatient;
  final String? initialMedicoId;

  @override
  State<AppointmentFormContent> createState() => _AppointmentFormContentState();
}

class _AppointmentFormContentState extends State<AppointmentFormContent> {
  final _formKey = GlobalKey<FormState>();
  final _patientSearchController = TextEditingController();
  final _durationController = TextEditingController(text: '30');
  final _notesController = TextEditingController();
  List<Medico> _medicos = const [];
  List<Consultorio> _consultorios = const [];
  List<Paciente> _patientResults = const [];
  String? _selectedMedicoId;
  Consultorio? _selectedConsultorio;
  Paciente? _selectedPatient;
  DateTime _selectedDate = DateTime.now();
  TimeOfDay _selectedTime = roundToNextFiveMinutes(TimeOfDay.now());
  String _selectedType = 'PROGRAMADA';
  bool _loadingCatalogs = true;
  bool _loadingPatients = false;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _selectedPatient = widget.initialPatient;
    _selectedMedicoId = widget.initialMedicoId;
    _loadCatalogs();
  }

  @override
  void dispose() {
    _patientSearchController.dispose();
    _durationController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _loadCatalogs() async {
    setState(() {
      _loadingCatalogs = true;
      _error = null;
    });
    try {
      final medicos = await widget.api.listMedicos();
      final selectedMedicoId =
          _selectedMedicoId ?? (medicos.length == 1 ? medicos.first.id : null);
      final consultorios = await widget.api.listConsultorios(
        medicoId: selectedMedicoId,
      );
      if (!mounted) return;
      setState(() {
        _medicos = medicos;
        _selectedMedicoId = selectedMedicoId;
        _consultorios = consultorios;
        _selectedConsultorio = consultorios.length == 1
            ? consultorios.first
            : null;
        _loadingCatalogs = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
        _loadingCatalogs = false;
      });
    }
  }

  Future<void> _changeMedico(String? medicoId) async {
    setState(() {
      _selectedMedicoId = medicoId;
      _selectedConsultorio = null;
      _selectedPatient = null;
      _patientResults = const [];
      _loadingCatalogs = true;
      _error = null;
    });
    try {
      final consultorios = await widget.api.listConsultorios(
        medicoId: medicoId,
      );
      if (!mounted) return;
      setState(() {
        _consultorios = consultorios;
        _selectedConsultorio = consultorios.length == 1
            ? consultorios.first
            : null;
        _loadingCatalogs = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
        _loadingCatalogs = false;
      });
    }
  }

  Future<void> _searchPatients() async {
    final query = _patientSearchController.text.trim();
    if (query.isEmpty) {
      setState(
        () => _error = 'Capture un nombre, celular o folio de paciente.',
      );
      return;
    }
    setState(() {
      _loadingPatients = true;
      _error = null;
    });
    try {
      final rows = await widget.api.searchPacientes(
        query,
        medicoId: _selectedMedicoId,
      );
      if (!mounted) return;
      setState(() {
        _patientResults = rows;
        _loadingPatients = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
        _loadingPatients = false;
      });
    }
  }

  Future<void> _pickDate() async {
    final selected = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime.now().subtract(const Duration(days: 30)),
      lastDate: DateTime.now().add(const Duration(days: 730)),
    );
    if (selected != null) setState(() => _selectedDate = selected);
  }

  Future<void> _pickTime() async {
    final selected = await showTimePicker(
      context: context,
      initialTime: _selectedTime,
    );
    if (selected != null) setState(() => _selectedTime = selected);
  }

  void _setType(String type) {
    setState(() {
      _selectedType = type;
      if (type == 'ESPONTANEA') {
        _selectedDate = DateTime.now();
        _selectedTime = roundToNextFiveMinutes(TimeOfDay.now());
      }
    });
  }

  Future<void> _submit({bool confirmarDuplicado = false}) async {
    if (!_formKey.currentState!.validate()) return;
    final patient = _selectedPatient;
    final medicoId = _selectedMedicoId;
    final consultorio = _selectedConsultorio;
    if (patient == null) {
      setState(() => _error = 'Seleccione un paciente.');
      return;
    }
    if (medicoId == null || medicoId.isEmpty) {
      setState(() => _error = 'Seleccione un médico.');
      return;
    }
    if (consultorio == null) {
      setState(() => _error = 'Seleccione un consultorio.');
      return;
    }

    setState(() {
      _submitting = true;
      _error = null;
    });
    final duration = int.tryParse(_durationController.text.trim());
    final notes = _notesController.text.trim();
    final payload = <String, Object?>{
      'tipo': _selectedType,
      'estado': 'AGENDADA',
      'paciente_id': patient.id,
      'medico_id': medicoId,
      'consultorio_id': consultorio.id,
      'complejo_id': consultorio.complejoId,
      'piso_id': consultorio.pisoId,
      'fecha_cita': dateOnly(_selectedDate),
      'hora_cita': timeOnly(_selectedTime),
      'origen': 'APP_MEDICOS',
    };
    if (duration != null) payload['duracion_estimada'] = duration;
    if (notes.isNotEmpty) payload['notas_operativas'] = notes;

    try {
      final cita = await widget.api.createCita(
        payload,
        confirmarDuplicado: confirmarDuplicado,
      );
      if (!mounted) return;
      showSnack(context, 'Cita ${cita.folioTurno} creada.');
      _resetForm(keepMedico: true);
      widget.onCreated(cita);
    } on ApiException catch (error) {
      if (!mounted) return;
      if (error.isDuplicateAppointment && !confirmarDuplicado) {
        final confirmed = await _confirmDuplicate(error);
        if (confirmed && mounted) {
          await _submit(confirmarDuplicado: true);
        }
      } else {
        setState(() => _error = error.toString());
      }
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<bool> _confirmDuplicate(ApiException error) async {
    final duplicates = error.duplicateSummaries;
    final text = duplicates.isEmpty
        ? 'Existe una posible cita duplicada. ¿Desea crearla de todos modos?'
        : 'Existe una posible cita duplicada:\n\n${duplicates.join('\n')}\n\n¿Desea crearla de todos modos?';
    final result = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Posible duplicado'),
        content: Text(text),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Revisar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Crear de todos modos'),
          ),
        ],
      ),
    );
    return result == true;
  }

  void _resetForm({required bool keepMedico}) {
    setState(() {
      if (!keepMedico) _selectedMedicoId = null;
      _selectedPatient = null;
      _patientResults = const [];
      _patientSearchController.clear();
      _notesController.clear();
      _durationController.text = '30';
      _selectedType = 'PROGRAMADA';
      _selectedDate = DateTime.now();
      _selectedTime = roundToNextFiveMinutes(TimeOfDay.now());
    });
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.session.user.canWriteAppointments) {
      return const PermissionMessage(
        message: 'El usuario no tiene permiso de edición para crear citas.',
      );
    }
    if (_loadingCatalogs && _medicos.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SegmentedButton<String>(
                segments: const [
                  ButtonSegment(
                    value: 'PROGRAMADA',
                    icon: Icon(Icons.event_available),
                    label: Text('Programada'),
                  ),
                  ButtonSegment(
                    value: 'ESPONTANEA',
                    icon: Icon(Icons.flash_on_outlined),
                    label: Text('Espontánea'),
                  ),
                ],
                selected: {_selectedType},
                onSelectionChanged: (value) => _setType(value.first),
              ),
              const SizedBox(height: 14),
              DropdownButtonFormField<String?>(
                initialValue: _selectedMedicoId,
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Médico'),
                items: [
                  const DropdownMenuItem<String?>(
                    value: null,
                    child: Text('Seleccione médico'),
                  ),
                  ..._medicos.map(
                    (medico) => DropdownMenuItem<String?>(
                      value: medico.id,
                      child: Text(medico.label),
                    ),
                  ),
                ],
                validator: (value) => value == null || value.isEmpty
                    ? 'Seleccione médico.'
                    : null,
                onChanged: _submitting
                    ? null
                    : (value) => unawaited(_changeMedico(value)),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<Consultorio>(
                key: ValueKey(_selectedMedicoId ?? 'sin-medico'),
                initialValue: _selectedConsultorio,
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Consultorio'),
                items: _consultorios
                    .map(
                      (consultorio) => DropdownMenuItem(
                        value: consultorio,
                        child: Text(consultorio.label),
                      ),
                    )
                    .toList(),
                validator: (value) =>
                    value == null ? 'Seleccione consultorio.' : null,
                onChanged: _submitting
                    ? null
                    : (value) => setState(() => _selectedConsultorio = value),
              ),
              const SizedBox(height: 14),
              SelectedPatientPanel(
                patient: _selectedPatient,
                onClear: _submitting
                    ? null
                    : () => setState(() => _selectedPatient = null),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _patientSearchController,
                enabled: !_submitting,
                textInputAction: TextInputAction.search,
                decoration: InputDecoration(
                  labelText: 'Buscar paciente',
                  suffixIcon: IconButton(
                    tooltip: 'Buscar',
                    onPressed: _loadingPatients ? null : _searchPatients,
                    icon: _loadingPatients
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.search),
                  ),
                ),
                onSubmitted: (_) => _searchPatients(),
              ),
              if (_patientResults.isNotEmpty) ...[
                const SizedBox(height: 10),
                ..._patientResults
                    .take(6)
                    .map(
                      (patient) => ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.person_outline),
                        title: Text(patient.displayName),
                        subtitle: Text(patient.detail),
                        trailing: const Icon(Icons.check_circle_outline),
                        onTap: () => setState(() {
                          _selectedPatient = patient;
                          _patientResults = const [];
                          _patientSearchController.clear();
                        }),
                      ),
                    ),
              ],
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _selectedType == 'ESPONTANEA'
                          ? null
                          : _pickDate,
                      icon: const Icon(Icons.event),
                      label: Text(formatDate(_selectedDate)),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _pickTime,
                      icon: const Icon(Icons.schedule),
                      label: Text(formatTimeOfDay(_selectedTime)),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _durationController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Duración estimada (min)',
                ),
                validator: (value) {
                  final parsed = int.tryParse(value?.trim() ?? '');
                  if (parsed == null || parsed <= 0 || parsed > 720) {
                    return 'Capture una duración entre 1 y 720.';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _notesController,
                minLines: 2,
                maxLines: 4,
                decoration: const InputDecoration(
                  labelText: 'Notas operativas',
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                ErrorBanner(message: _error!),
              ],
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _submitting ? null : _submit,
                icon: _submitting
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.save_outlined),
                label: const Text('Crear cita'),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({
    super.key,
    required this.session,
    required this.onLogout,
  });

  final SavedSession session;
  final Future<void> Function() onLogout;

  @override
  Widget build(BuildContext context) {
    final user = session.user;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  user.displayName,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 4),
                Text(user.email),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: user.roles
                      .map(
                        (role) => Chip(
                          label: Text(role),
                          visualDensity: VisualDensity.compact,
                        ),
                      )
                      .toList(),
                ),
                const SizedBox(height: 12),
                InfoRow(
                  icon: Icons.timer_outlined,
                  text: 'Sesión hasta ${formatDateTime(session.expiresAt)}',
                ),
                const SizedBox(height: 6),
                InfoRow(icon: Icons.dns_outlined, text: session.apiBaseUrl),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Permisos',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 10),
                PermissionRow(
                  label: 'Pacientes',
                  granted: user.canReadPatients,
                ),
                PermissionRow(
                  label: 'Consultar citas',
                  granted: user.canReadAppointments,
                ),
                PermissionRow(
                  label: 'Crear y cancelar citas',
                  granted: user.canWriteAppointments,
                ),
                PermissionRow(
                  label: 'Llamar pacientes',
                  granted: user.canCallPatients,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        OutlinedButton.icon(
          onPressed: onLogout,
          icon: const Icon(Icons.logout),
          label: const Text('Cerrar sesión'),
        ),
      ],
    );
  }
}

class AppointmentCard extends StatelessWidget {
  const AppointmentCard({
    super.key,
    required this.cita,
    required this.busy,
    required this.canWrite,
    required this.canCall,
    required this.onGenerateQr,
    required this.onCall,
    required this.onCancel,
  });

  final Cita cita;
  final bool busy;
  final bool canWrite;
  final bool canCall;
  final VoidCallback onGenerateQr;
  final VoidCallback onCall;
  final VoidCallback onCancel;

  @override
  Widget build(BuildContext context) {
    final detail = [
      shortTime(cita.horaCita),
      if ((cita.consultorio ?? '').isNotEmpty) cita.consultorio!,
      if ((cita.piso ?? '').isNotEmpty) cita.piso!,
      appointmentTypeLabel(cita.tipo),
    ].join(' · ');
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        cita.patientLabel,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 3),
                      Text('Turno ${cita.folioTurno} · $detail'),
                    ],
                  ),
                ),
                StatusChip(estado: cita.estado),
              ],
            ),
            if (cita.hasArrived) ...[
              const SizedBox(height: 10),
              ArrivalBanner(estado: cita.estado),
            ],
            if (busy) ...[
              const SizedBox(height: 10),
              const LinearProgressIndicator(),
            ],
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton.icon(
                  onPressed: busy || !canWrite || cita.isTerminal
                      ? null
                      : onGenerateQr,
                  icon: const Icon(Icons.qr_code_2),
                  label: const Text('QR'),
                ),
                FilledButton.tonalIcon(
                  onPressed: busy || !canCall || cita.isTerminal
                      ? null
                      : onCall,
                  icon: const Icon(Icons.campaign_outlined),
                  label: const Text('Llamar'),
                ),
                OutlinedButton.icon(
                  onPressed: busy || !canWrite || cita.isTerminal
                      ? null
                      : onCancel,
                  icon: const Icon(Icons.event_busy),
                  label: const Text('Cancelar'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class PatientCard extends StatelessWidget {
  const PatientCard({
    super.key,
    required this.patient,
    required this.canCreateAppointment,
    required this.onCreateAppointment,
  });

  final Paciente patient;
  final bool canCreateAppointment;
  final VoidCallback onCreateAppointment;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: const Icon(Icons.person_outline),
        title: Text(patient.displayName),
        subtitle: Text(patient.detail),
        trailing: IconButton(
          tooltip: 'Crear cita',
          onPressed: canCreateAppointment ? onCreateAppointment : null,
          icon: const Icon(Icons.add_circle_outline),
        ),
      ),
    );
  }
}

class SelectedPatientPanel extends StatelessWidget {
  const SelectedPatientPanel({
    super.key,
    required this.patient,
    required this.onClear,
  });

  final Paciente? patient;
  final VoidCallback? onClear;

  @override
  Widget build(BuildContext context) {
    final selected = patient;
    if (selected == null) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(8),
        ),
        child: const Row(
          children: [
            Icon(Icons.person_search),
            SizedBox(width: 8),
            Expanded(child: Text('Seleccione un paciente para la cita.')),
          ],
        ),
      );
    }
    return Card(
      child: ListTile(
        leading: const Icon(Icons.check_circle_outline),
        title: Text(selected.displayName),
        subtitle: Text(selected.detail),
        trailing: IconButton(
          tooltip: 'Quitar paciente',
          onPressed: onClear,
          icon: const Icon(Icons.close),
        ),
      ),
    );
  }
}

class QrDialog extends StatelessWidget {
  const QrDialog({super.key, required this.cita, required this.qr});

  final Cita cita;
  final QrAccess qr;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('QR ${cita.folioTurno}'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            QrImageView(
              data: qr.qrPayload,
              version: QrVersions.auto,
              size: 250,
              backgroundColor: Colors.white,
            ),
            const SizedBox(height: 12),
            Text(
              cita.patientLabel,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 4),
            Text(
              'Expira: ${formatDateTimeFromText(qr.fechaExpiracion)}',
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
      actions: [
        TextButton.icon(
          onPressed: () async {
            await Clipboard.setData(ClipboardData(text: qr.qrPayload));
            if (context.mounted) showSnack(context, 'Token QR copiado.');
          },
          icon: const Icon(Icons.copy),
          label: const Text('Copiar'),
        ),
        FilledButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cerrar'),
        ),
      ],
    );
  }
}

class FilterPanel extends StatelessWidget {
  const FilterPanel({super.key, required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(children: children),
      ),
    );
  }
}

class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.estado});

  final String estado;

  @override
  Widget build(BuildContext context) {
    final color = statusColor(estado);
    return Chip(
      visualDensity: VisualDensity.compact,
      avatar: Icon(Icons.circle, size: 12, color: color),
      label: Text(appointmentStateLabel(estado)),
    );
  }
}

class ArrivalBanner extends StatelessWidget {
  const ArrivalBanner({super.key, required this.estado});

  final String estado;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFFEAF7EF),
        borderRadius: BorderRadius.circular(8),
      ),
      padding: const EdgeInsets.all(10),
      child: Row(
        children: [
          const Icon(Icons.how_to_reg, color: Color(0xFF11845B), size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text(arrivalLabel(estado))),
        ],
      ),
    );
  }
}

class PermissionMessage extends StatelessWidget {
  const PermissionMessage({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.lock_outline,
              size: 42,
              color: Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(height: 10),
            Text(message, textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}

class PermissionRow extends StatelessWidget {
  const PermissionRow({super.key, required this.label, required this.granted});

  final String label;
  final bool granted;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Icon(
            granted ? Icons.check_circle : Icons.cancel_outlined,
            color: granted ? const Color(0xFF11845B) : Colors.grey,
          ),
          const SizedBox(width: 8),
          Expanded(child: Text(label)),
        ],
      ),
    );
  }
}

class InfoRow extends StatelessWidget {
  const InfoRow({super.key, required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 18),
        const SizedBox(width: 8),
        Expanded(child: Text(text)),
      ],
    );
  }
}

class EmptyState extends StatelessWidget {
  const EmptyState({super.key, required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 30),
        child: Column(
          children: [
            Icon(icon, size: 42, color: Theme.of(context).colorScheme.outline),
            const SizedBox(height: 10),
            Text(text, textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}

class ErrorBanner extends StatelessWidget {
  const ErrorBanner({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.errorContainer,
        borderRadius: BorderRadius.circular(8),
      ),
      padding: const EdgeInsets.all(12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.error_outline,
            color: Theme.of(context).colorScheme.onErrorContainer,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: TextStyle(
                color: Theme.of(context).colorScheme.onErrorContainer,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

const appointmentStates = [
  'TODAS',
  'AGENDADA',
  'QR_GENERADO',
  'LLEGO_LOBBY',
  'AUTORIZADO_PASAR',
  'EN_CONSULTA',
  'FINALIZADA',
  'NO_LLEGO',
  'CANCELADA',
  'EXPIRADA',
];

const appointmentTypes = ['TODAS', 'PROGRAMADA', 'ESPONTANEA'];

String appointmentStateLabel(String value) {
  return switch (value) {
    'TODAS' => 'Todas',
    'AGENDADA' => 'Agendada',
    'QR_GENERADO' => 'QR generado',
    'LLEGO_LOBBY' => 'Llegó',
    'AUTORIZADO_PASAR' => 'Autorizado',
    'EN_CONSULTA' => 'En consulta',
    'FINALIZADA' => 'Finalizada',
    'NO_LLEGO' => 'No llegó',
    'CANCELADA' => 'Cancelada',
    'EXPIRADA' => 'Expirada',
    _ => value,
  };
}

String appointmentTypeLabel(String value) {
  return switch (value) {
    'TODAS' => 'Todas',
    'PROGRAMADA' => 'Programada',
    'ESPONTANEA' => 'Espontánea',
    _ => value,
  };
}

String arrivalLabel(String estado) {
  return switch (estado) {
    'LLEGO_LOBBY' => 'El paciente ya llegó e hizo check-in en recepción.',
    'AUTORIZADO_PASAR' => 'El paciente ya llegó y está autorizado para pasar.',
    'EN_CONSULTA' => 'El paciente ya está en consulta.',
    'FINALIZADA' => 'Consulta finalizada.',
    _ => 'El paciente ya registró llegada.',
  };
}

Color statusColor(String status) {
  return switch (status) {
    'AGENDADA' => const Color(0xFF2563EB),
    'QR_GENERADO' => const Color(0xFF7C3AED),
    'LLEGO_LOBBY' => const Color(0xFF11845B),
    'AUTORIZADO_PASAR' => const Color(0xFF0F766E),
    'EN_CONSULTA' => const Color(0xFFB7791F),
    'FINALIZADA' => const Color(0xFF4B5563),
    'NO_LLEGO' => const Color(0xFFC2410C),
    'CANCELADA' => const Color(0xFFC53030),
    'EXPIRADA' => const Color(0xFF6B7280),
    _ => const Color(0xFF4B5563),
  };
}

String dateOnly(DateTime value) {
  final local = DateTime(value.year, value.month, value.day);
  return local.toIso8601String().split('T').first;
}

String timeOnly(TimeOfDay value) {
  return '${_pad(value.hour)}:${_pad(value.minute)}:00';
}

String shortTime(String value) {
  if (value.length >= 5) return value.substring(0, 5);
  return value;
}

String formatDate(DateTime value) {
  final local = value.toLocal();
  return '${_pad(local.day)}/${_pad(local.month)}/${local.year}';
}

String formatDateTime(DateTime value) {
  final local = value.toLocal();
  return '${formatDate(local)} ${_pad(local.hour)}:${_pad(local.minute)}';
}

String formatDateTimeFromText(String value) {
  final parsed = DateTime.tryParse(value);
  if (parsed == null) return value;
  return formatDateTime(parsed);
}

String formatTimeOfDay(TimeOfDay value) {
  return '${_pad(value.hour)}:${_pad(value.minute)}';
}

String _pad(int value) => value.toString().padLeft(2, '0');

TimeOfDay roundToNextFiveMinutes(TimeOfDay value) {
  final total = value.hour * 60 + value.minute;
  final rounded = ((total + 4) ~/ 5) * 5;
  return TimeOfDay(hour: (rounded ~/ 60) % 24, minute: rounded % 60);
}

void showSnack(BuildContext context, String message) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(message)));
}
