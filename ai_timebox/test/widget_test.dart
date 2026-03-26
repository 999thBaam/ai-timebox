import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ai_timebox/main.dart';

void main() {
  testWidgets('App renders placeholder home screen', (WidgetTester tester) async {
    await tester.pumpWidget(const AiTimeboxApp());
    expect(find.text('AI Timebox'), findsWidgets);
  });
}
