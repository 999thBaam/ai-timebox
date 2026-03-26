import 'package:flutter/material.dart';

class AppColors {
  // Base colors
  static const Color background = Color(0xFF0F172A);
  static const Color surface = Color(0xFF1E293B);

  // Glass effect colors
  static const Color glassBg = Color(0x0AFFFFFF); // rgba(255,255,255,0.04)
  static const Color glassBorder = Color(0x0FFFFFFF); // rgba(255,255,255,0.06)

  // Text colors
  static const Color textPrimary = Color(0xFFF1F5F9);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF64748B);
  static const Color sectionTitle = Color(0xFF475569);

  // Work category
  static const Color workPrimary = Color(0xFF818CF8);
  static const Color workBg = Color(0x1F6366F1); // rgba(99,102,241,0.12)

  // Health category
  static const Color healthPrimary = Color(0xFF34D399);
  static const Color healthBg = Color(0x1434D399); // rgba(52,211,153,0.08)

  // Errand category
  static const Color errandPrimary = Color(0xFFF59E0B);
  static const Color errandBg = Color(0x14F59E0B); // rgba(245,158,11,0.08)

  // Social category
  static const Color socialPrimary = Color(0xFFFB7185);
  static const Color socialBg = Color(0x14F43F5E); // rgba(244,63,94,0.08)
}

final ThemeData appTheme = ThemeData(
  brightness: Brightness.dark,
  scaffoldBackgroundColor: AppColors.background,
  colorScheme: const ColorScheme.dark(
    surface: AppColors.surface,
    primary: AppColors.workPrimary,
    onPrimary: AppColors.textPrimary,
    onSurface: AppColors.textPrimary,
    secondary: AppColors.healthPrimary,
    onSecondary: AppColors.textPrimary,
    error: AppColors.socialPrimary,
    onError: AppColors.textPrimary,
  ),
  textTheme: const TextTheme(
    displayLarge: TextStyle(
      color: AppColors.textPrimary,
      fontWeight: FontWeight.bold,
    ),
    displayMedium: TextStyle(
      color: AppColors.textPrimary,
      fontWeight: FontWeight.bold,
    ),
    displaySmall: TextStyle(
      color: AppColors.textPrimary,
      fontWeight: FontWeight.bold,
    ),
    headlineLarge: TextStyle(
      color: AppColors.textPrimary,
      fontWeight: FontWeight.w600,
    ),
    headlineMedium: TextStyle(
      color: AppColors.textPrimary,
      fontWeight: FontWeight.w600,
    ),
    headlineSmall: TextStyle(
      color: AppColors.textPrimary,
      fontWeight: FontWeight.w600,
    ),
    titleLarge: TextStyle(
      color: AppColors.textPrimary,
      fontWeight: FontWeight.w600,
    ),
    titleMedium: TextStyle(
      color: AppColors.textPrimary,
      fontWeight: FontWeight.w500,
    ),
    titleSmall: TextStyle(
      color: AppColors.textSecondary,
      fontWeight: FontWeight.w500,
    ),
    bodyLarge: TextStyle(color: AppColors.textPrimary),
    bodyMedium: TextStyle(color: AppColors.textSecondary),
    bodySmall: TextStyle(color: AppColors.textMuted),
    labelLarge: TextStyle(
      color: AppColors.textPrimary,
      fontWeight: FontWeight.w500,
    ),
    labelMedium: TextStyle(color: AppColors.textSecondary),
    labelSmall: TextStyle(color: AppColors.textMuted),
  ),
  appBarTheme: const AppBarTheme(
    backgroundColor: AppColors.background,
    elevation: 0,
    scrolledUnderElevation: 0,
    titleTextStyle: TextStyle(
      color: AppColors.textPrimary,
      fontSize: 20,
      fontWeight: FontWeight.w600,
    ),
    iconTheme: IconThemeData(color: AppColors.textPrimary),
  ),
  cardTheme: CardThemeData(
    color: AppColors.surface,
    elevation: 0,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.all(Radius.circular(16)),
      side: BorderSide(color: AppColors.glassBorder),
    ),
  ),
  dividerTheme: const DividerThemeData(
    color: AppColors.glassBorder,
    thickness: 1,
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: AppColors.glassBg,
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: AppColors.glassBorder),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: AppColors.glassBorder),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: AppColors.workPrimary, width: 1.5),
    ),
    hintStyle: const TextStyle(color: AppColors.textMuted),
    labelStyle: const TextStyle(color: AppColors.textSecondary),
  ),
  elevatedButtonTheme: ElevatedButtonThemeData(
    style: ElevatedButton.styleFrom(
      backgroundColor: AppColors.workPrimary,
      foregroundColor: AppColors.textPrimary,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
    ),
  ),
  iconTheme: const IconThemeData(color: AppColors.textSecondary),
  useMaterial3: true,
);
