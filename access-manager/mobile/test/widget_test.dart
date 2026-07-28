import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/main.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  testWidgets('muestra el login de recepción', (tester) async {
    SharedPreferences.setMockInitialValues({});

    await tester.pumpWidget(const AccessMobileApp());
    await tester.pumpAndSettle();

    expect(find.text('Llegada de pacientes'), findsWidgets);
    expect(find.text('Ingreso de recepción'), findsOneWidget);
    expect(find.text('Iniciar sesión'), findsOneWidget);
  });
}
