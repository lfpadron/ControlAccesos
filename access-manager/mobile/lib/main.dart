import 'dart:async';

import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import 'api_client.dart';
import 'local_log_store.dart';
import 'models.dart';
import 'session_store.dart';
import 'ticket_pdf.dart';

const defaultApiBaseUrl = String.fromEnvironment(
  'ACCESS_API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8080/api',
);

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const AccessMobileApp());
}

class AccessMobileApp extends StatefulWidget {
  const AccessMobileApp({super.key});

  @override
  State<AccessMobileApp> createState() => _AccessMobileAppState();
}

class _AccessMobileAppState extends State<AccessMobileApp> {
  final SessionStore _sessionStore = SessionStore();
  final LocalLogStore _logStore = LocalLogStore();
  SavedSession? _session;
  ApiClient? _api;
  Timer? _expirationTimer;
  String? _deviceId;
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
    final deviceId = await _sessionStore.deviceId();
    final saved = await _sessionStore.load();
    if (saved == null) {
      if (!mounted) return;
      setState(() {
        _deviceId = deviceId;
        _loading = false;
      });
      return;
    }

    final api = ApiClient(saved.apiBaseUrl, token: saved.token);
    try {
      final serverSession = await api.mobileSession();
      final refreshed = saved.withServerSession(serverSession);
      await _sessionStore.save(refreshed);
      if (!mounted) return;
      setState(() {
        _session = refreshed;
        _api = api;
        _deviceId = deviceId;
        _loading = false;
      });
      _scheduleExpiration(refreshed);
    } catch (_) {
      await _sessionStore.clear();
      if (!mounted) return;
      setState(() {
        _deviceId = deviceId;
        _loading = false;
      });
    }
  }

  Future<void> _login(String apiBaseUrl, String email, String password) async {
    final api = ApiClient(apiBaseUrl);
    final token = await api.login(email, password);
    api.token = token;
    final serverSession = await api.mobileSession();
    if (!serverSession.canCheckin && !serverSession.canViewLogs) {
      throw const ApiException('El usuario no tiene permisos para usar la app móvil.');
    }
    final session = SavedSession(
      apiBaseUrl: api.baseUrl,
      token: token,
      email: serverSession.email,
      name: serverSession.name,
      roles: serverSession.roles,
      expiresAt: DateTime.now().toUtc().add(mobileSessionDuration),
      canCheckin: serverSession.canCheckin,
      canViewLogs: serverSession.canViewLogs,
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

  void _scheduleExpiration(SavedSession session) {
    _expirationTimer?.cancel();
    final delay = session.expiresAt.toUtc().difference(DateTime.now().toUtc());
    if (delay <= Duration.zero) {
      unawaited(_logout());
      return;
    }
    _expirationTimer = Timer(delay, () {
      unawaited(_logout());
    });
  }

  @override
  Widget build(BuildContext context) {
    final session = _session;
    final api = _api;
    final deviceId = _deviceId;

    return MaterialApp(
      title: 'Llegada de pacientes',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF145C8F)),
        useMaterial3: true,
        cardTheme: const CardThemeData(
          margin: EdgeInsets.zero,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.all(Radius.circular(8))),
        ),
        inputDecorationTheme: const InputDecorationTheme(border: OutlineInputBorder()),
      ),
      home: _loading
          ? const LoadingScreen()
          : session == null || api == null || deviceId == null
              ? LoginScreen(onLogin: _login)
              : HomeScreen(
                  session: session,
                  api: api,
                  logStore: _logStore,
                  deviceId: deviceId,
                  onLogout: _logout,
                ),
    );
  }
}

class LoadingScreen extends StatelessWidget {
  const LoadingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(child: CircularProgressIndicator()),
    );
  }
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.onLogin});

  final Future<void> Function(String apiBaseUrl, String email, String password) onLogin;

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
      setState(() {
        _error = error.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
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
                Icon(Icons.fact_check_outlined, size: 56, color: Theme.of(context).colorScheme.primary),
                const SizedBox(height: 18),
                Text('Llegada de pacientes', textAlign: TextAlign.center, style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 8),
                Text('Ingreso de recepción', textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyLarge),
                const SizedBox(height: 24),
                Form(
                  key: _formKey,
                  child: Column(
                    children: [
                      TextFormField(
                        controller: _serverController,
                        keyboardType: TextInputType.url,
                        decoration: const InputDecoration(labelText: 'Servidor API'),
                        validator: (value) {
                          final text = value?.trim() ?? '';
                          final uri = Uri.tryParse(text);
                          if (uri == null || !uri.hasScheme || uri.host.isEmpty) {
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
                        validator: (value) => (value?.trim().isEmpty ?? true) ? 'Capture el correo.' : null,
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
                            icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                            onPressed: () => setState(() => _obscure = !_obscure),
                          ),
                        ),
                        validator: (value) => (value?.isEmpty ?? true) ? 'Capture la contraseña.' : null,
                        onFieldSubmitted: (_) => _submit(),
                      ),
                      const SizedBox(height: 18),
                      FilledButton.icon(
                        onPressed: _loading ? null : _submit,
                        icon: _loading
                            ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
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

class HomeScreen extends StatelessWidget {
  const HomeScreen({
    super.key,
    required this.session,
    required this.api,
    required this.logStore,
    required this.deviceId,
    required this.onLogout,
  });

  final SavedSession session;
  final ApiClient api;
  final LocalLogStore logStore;
  final String deviceId;
  final Future<void> Function() onLogout;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Llegada de pacientes'),
        actions: [
          IconButton(
            tooltip: 'Cerrar sesión',
            onPressed: onLogout,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            SessionCard(session: session),
            const SizedBox(height: 18),
            if (session.canCheckin) ...[
              ActionPanel(
                icon: Icons.qr_code_scanner,
                title: 'Registrar con QR',
                subtitle: 'Usa la cámara del celular.',
                onTap: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => QrCheckinScreen(api: api, logStore: logStore, session: session, deviceId: deviceId),
                    ),
                  );
                },
              ),
              const SizedBox(height: 12),
              ActionPanel(
                icon: Icons.person_search,
                title: 'Buscar por datos',
                subtitle: 'Nombre más celular o fecha de nacimiento.',
                onTap: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => ManualSearchScreen(api: api, logStore: logStore, session: session, deviceId: deviceId),
                    ),
                  );
                },
              ),
            ],
            if (session.canViewLogs) ...[
              if (session.canCheckin) const SizedBox(height: 12),
              ActionPanel(
                icon: Icons.list_alt,
                title: 'Log local',
                subtitle: 'Consulta de actividad del dispositivo.',
                onTap: () {
                  Navigator.of(context).push(MaterialPageRoute(builder: (_) => LocalLogScreen(logStore: logStore)));
                },
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class SessionCard extends StatelessWidget {
  const SessionCard({super.key, required this.session});

  final SavedSession session;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(session.name, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(session.email),
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: session.roles.map((role) => Chip(label: Text(role), visualDensity: VisualDensity.compact)).toList(),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(Icons.timer_outlined, size: 18),
                const SizedBox(width: 6),
                Text('Sesión hasta ${formatDateTime(session.expiresAt)}'),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class ActionPanel extends StatelessWidget {
  const ActionPanel({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Icon(icon, size: 34, color: Theme.of(context).colorScheme.primary),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 3),
                    Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right),
            ],
          ),
        ),
      ),
    );
  }
}

class QrCheckinScreen extends StatefulWidget {
  const QrCheckinScreen({
    super.key,
    required this.api,
    required this.logStore,
    required this.session,
    required this.deviceId,
  });

  final ApiClient api;
  final LocalLogStore logStore;
  final SavedSession session;
  final String deviceId;

  @override
  State<QrCheckinScreen> createState() => _QrCheckinScreenState();
}

class _QrCheckinScreenState extends State<QrCheckinScreen> {
  final MobileScannerController _controller = MobileScannerController(formats: const [BarcodeFormat.qrCode]);
  bool _processing = false;
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (_processing) return;
    String? qrToken;
    for (final barcode in capture.barcodes) {
      final value = barcode.rawValue;
      if (value != null && value.trim().isNotEmpty) {
        qrToken = value.trim();
        break;
      }
    }
    if (qrToken == null) return;

    setState(() {
      _processing = true;
      _error = null;
    });
    await _controller.stop();
    try {
      final response = await widget.api.checkinQr(qrToken, widget.deviceId);
      if (response.folioTurno != null) {
        await widget.logStore.add(qrToken: qrToken, folioTurno: response.folioTurno, recepcionistaLogin: widget.session.email);
      }
      TicketResponse? ticket;
      String? ticketError;
      if (response.citaId != null) {
        try {
          ticket = await widget.api.fetchTicket(response.citaId!);
        } catch (error) {
          ticketError = 'Llegada registrada, pero no fue posible obtener el ticket: $error';
        }
      }
      if (!mounted) return;
      await Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => CheckinResultScreen(response: response, ticket: ticket, initialError: ticketError)),
      );
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
        _processing = false;
      });
      await _controller.start();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Escanear QR')),
      body: Stack(
        children: [
          MobileScanner(controller: _controller, onDetect: _onDetect),
          Align(
            alignment: Alignment.center,
            child: Container(
              width: 260,
              height: 260,
              decoration: BoxDecoration(
                border: Border.all(color: Colors.white, width: 3),
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
          if (_processing)
            const ColoredBox(
              color: Color(0xAA000000),
              child: Center(child: CircularProgressIndicator()),
            ),
          if (_error != null)
            Align(
              alignment: Alignment.bottomCenter,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: ErrorBanner(message: _error!),
              ),
            ),
        ],
      ),
    );
  }
}

class ManualSearchScreen extends StatefulWidget {
  const ManualSearchScreen({
    super.key,
    required this.api,
    required this.logStore,
    required this.session,
    required this.deviceId,
  });

  final ApiClient api;
  final LocalLogStore logStore;
  final SavedSession session;
  final String deviceId;

  @override
  State<ManualSearchScreen> createState() => _ManualSearchScreenState();
}

class _ManualSearchScreenState extends State<ManualSearchScreen> {
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  DateTime? _birthDate;
  List<CitaSearchResult> _results = const [];
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  Future<void> _pickBirthDate() async {
    final now = DateTime.now();
    final selected = await showDatePicker(
      context: context,
      initialDate: _birthDate ?? DateTime(now.year - 30, now.month, now.day),
      firstDate: DateTime(1900),
      lastDate: now,
    );
    if (selected != null) {
      setState(() {
        _birthDate = selected;
      });
    }
  }

  Future<void> _search() async {
    final name = _nameController.text.trim();
    final phone = _phoneController.text.trim();
    if (name.isEmpty) {
      setState(() => _error = 'Capture el nombre del paciente.');
      return;
    }
    if (phone.isEmpty && _birthDate == null) {
      setState(() => _error = 'Capture celular o fecha de nacimiento.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
      _results = const [];
    });
    try {
      final rows = await widget.api.searchCitas(paciente: name, celular: phone, fechaNacimiento: _birthDate);
      if (!mounted) return;
      setState(() {
        _results = rows;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  Future<void> _checkin(CitaSearchResult cita) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final response = await widget.api.checkinManual(cita.id, widget.deviceId);
      if (response.folioTurno != null) {
        await widget.logStore.add(qrToken: null, folioTurno: response.folioTurno, recepcionistaLogin: widget.session.email);
      }
      TicketResponse? ticket;
      String? ticketError;
      if (response.citaId != null) {
        try {
          ticket = await widget.api.fetchTicket(response.citaId!);
        } catch (error) {
          ticketError = 'Llegada registrada, pero no fue posible obtener el ticket: $error';
        }
      }
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => CheckinResultScreen(response: response, ticket: ticket, initialError: ticketError)),
      );
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Buscar cita')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            TextField(
              controller: _nameController,
              textInputAction: TextInputAction.next,
              decoration: const InputDecoration(labelText: 'Nombre del paciente'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _phoneController,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(labelText: 'Celular'),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: _pickBirthDate,
              icon: const Icon(Icons.cake_outlined),
              label: Text(_birthDate == null ? 'Fecha de nacimiento' : formatDate(_birthDate!)),
            ),
            const SizedBox(height: 14),
            FilledButton.icon(
              onPressed: _loading ? null : _search,
              icon: _loading
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.search),
              label: const Text('Buscar'),
            ),
            if (_error != null) ...[
              const SizedBox(height: 14),
              ErrorBanner(message: _error!),
            ],
            const SizedBox(height: 18),
            if (_results.isEmpty && !_loading)
              const EmptyState(icon: Icons.event_busy, text: 'No hay citas para mostrar.')
            else
              ..._results.map(
                (cita) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: CitaTile(cita: cita, loading: _loading, onCheckin: () => _checkin(cita)),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class CitaTile extends StatelessWidget {
  const CitaTile({super.key, required this.cita, required this.loading, required this.onCheckin});

  final CitaSearchResult cita;
  final bool loading;
  final VoidCallback onCheckin;

  @override
  Widget build(BuildContext context) {
    final detail = [
      shortTime(cita.horaCita),
      if ((cita.consultorio ?? '').isNotEmpty) cita.consultorio!,
      if ((cita.piso ?? '').isNotEmpty) cita.piso!,
      cita.estado,
    ].join(' · ');
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(cita.folioTurno, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(detail),
            const SizedBox(height: 10),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton.icon(
                onPressed: loading ? null : onCheckin,
                icon: const Icon(Icons.how_to_reg),
                label: const Text('Registrar llegada'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class CheckinResultScreen extends StatefulWidget {
  const CheckinResultScreen({super.key, required this.response, required this.ticket, this.initialError});

  final CheckinResponse response;
  final TicketResponse? ticket;
  final String? initialError;

  @override
  State<CheckinResultScreen> createState() => _CheckinResultScreenState();
}

class _CheckinResultScreenState extends State<CheckinResultScreen> {
  bool _printing = false;
  late String? _error;

  @override
  void initState() {
    super.initState();
    _error = widget.initialError;
  }

  Future<void> _print() async {
    final ticket = widget.ticket;
    if (ticket == null) return;
    setState(() {
      _printing = true;
      _error = null;
    });
    try {
      await printTicketPdf(ticket);
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      if (mounted) {
        setState(() => _printing = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = statusColor(widget.response.resultado);
    return Scaffold(
      appBar: AppBar(title: const Text('Resultado')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.circle, color: color, size: 18),
                        const SizedBox(width: 8),
                        Text(widget.response.resultado, style: Theme.of(context).textTheme.headlineSmall),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text(widget.response.mensaje),
                    if (widget.response.folioTurno != null) ...[
                      const SizedBox(height: 16),
                      Text('Turno', style: Theme.of(context).textTheme.labelLarge),
                      Text(widget.response.folioTurno!, style: Theme.of(context).textTheme.displaySmall),
                    ],
                    if (widget.response.estadoCita != null) Text('Estado: ${widget.response.estadoCita}'),
                  ],
                ),
              ),
            ),
            if (widget.ticket != null) ...[
              const SizedBox(height: 14),
              TicketPreview(ticket: widget.ticket!),
              const SizedBox(height: 14),
              FilledButton.icon(
                onPressed: _printing ? null : _print,
                icon: _printing
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.print),
                label: const Text('Imprimir ticket PDF'),
              ),
            ],
            if (_error != null) ...[
              const SizedBox(height: 14),
              ErrorBanner(message: _error!),
            ],
          ],
        ),
      ),
    );
  }
}

class TicketPreview extends StatelessWidget {
  const TicketPreview({super.key, required this.ticket});

  final TicketResponse ticket;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Ticket', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text('${ticket.encabezadoFecha} · ${ticket.leyenda}'),
            Text('Turno ${ticket.turno}'),
            Text('${ticket.consultorio} · ${ticket.piso}'),
            Text('Hora ${ticket.hora}'),
          ],
        ),
      ),
    );
  }
}

class LocalLogScreen extends StatefulWidget {
  const LocalLogScreen({super.key, required this.logStore});

  final LocalLogStore logStore;

  @override
  State<LocalLogScreen> createState() => _LocalLogScreenState();
}

class _LocalLogScreenState extends State<LocalLogScreen> {
  late Future<List<ActivityLogEntry>> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.logStore.latest();
  }

  Future<void> _refresh() async {
    setState(() {
      _future = widget.logStore.latest();
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Log local')),
      body: SafeArea(
        child: FutureBuilder<List<ActivityLogEntry>>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            final rows = snapshot.data ?? const [];
            if (rows.isEmpty) {
              return RefreshIndicator(
                onRefresh: _refresh,
                child: ListView(
                  padding: const EdgeInsets.all(18),
                  children: const [EmptyState(icon: Icons.list_alt, text: 'No hay actividad registrada en este dispositivo.')],
                ),
              );
            }
            return RefreshIndicator(
              onRefresh: _refresh,
              child: ListView.separated(
                padding: const EdgeInsets.all(18),
                itemBuilder: (context, index) => LogEntryTile(entry: rows[index]),
                separatorBuilder: (_, _) => const SizedBox(height: 10),
                itemCount: rows.length,
              ),
            );
          },
        ),
      ),
    );
  }
}

class LogEntryTile extends StatelessWidget {
  const LogEntryTile({super.key, required this.entry});

  final ActivityLogEntry entry;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Cita ${entry.folioTurno ?? '-'}', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 6),
            Text('Fecha y hora: ${formatDateTime(entry.createdAt)}'),
            Text('Recepción: ${entry.recepcionistaLogin}'),
            const SizedBox(height: 6),
            Text('QR: ${entry.qrToken ?? '-'}', style: TextStyle(fontFamily: 'monospace')),
          ],
        ),
      ),
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
        padding: const EdgeInsets.symmetric(vertical: 28),
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
          Icon(Icons.error_outline, color: Theme.of(context).colorScheme.onErrorContainer),
          const SizedBox(width: 8),
          Expanded(child: Text(message, style: TextStyle(color: Theme.of(context).colorScheme.onErrorContainer))),
        ],
      ),
    );
  }
}

String formatDate(DateTime value) {
  final local = value.toLocal();
  return '${_pad(local.day)}/${_pad(local.month)}/${local.year}';
}

String formatDateTime(DateTime value) {
  final local = value.toLocal();
  return '${formatDate(local)} ${_pad(local.hour)}:${_pad(local.minute)}';
}

String shortTime(String value) => value.length >= 5 ? value.substring(0, 5) : value;

String _pad(int value) => value.toString().padLeft(2, '0');

Color statusColor(String status) {
  switch (status.toUpperCase()) {
    case 'VERDE':
      return const Color(0xFF11845B);
    case 'AMARILLO':
      return const Color(0xFFB7791F);
    case 'ROJO':
      return const Color(0xFFC53030);
    default:
      return const Color(0xFF4A5568);
  }
}
