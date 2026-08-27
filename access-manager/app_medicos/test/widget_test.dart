import 'package:app_medicos/main.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  testWidgets('muestra login cuando no hay sesión guardada', (tester) async {
    SharedPreferences.setMockInitialValues({});

    await tester.pumpWidget(const DoctorsMobileApp());
    await tester.pumpAndSettle();

    expect(find.text('App de Médicos'), findsOneWidget);
    expect(find.text('Iniciar sesión'), findsOneWidget);
  });
}
