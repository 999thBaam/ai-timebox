import 'package:flutter_test/flutter_test.dart';

import 'package:ai_timebox/main.dart';

void main() {
  testWidgets('App builds without error', (WidgetTester tester) async {
    await tester.pumpWidget(const AiTimeboxApp());
    await tester.pump();
    // App should render without throwing
    expect(find.byType(AiTimeboxApp), findsOneWidget);
  });
}
