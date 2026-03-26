import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import '../services/llm_service.dart';
import '../services/notification_service.dart';
import '../storage/local_db.dart';
import '../theme.dart';
import '../widgets/glass_card.dart';
import 'setup_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  // ── Services ─────────────────────────────────────────────────────────────
  final _llmService = LlmService();
  final _notificationService = NotificationService();

  // ── API Key ───────────────────────────────────────────────────────────────
  final _apiKeyController = TextEditingController();
  bool _apiKeySet = false;
  bool _savingApiKey = false;

  // ── Notification times ────────────────────────────────────────────────────
  TimeOfDay _morningTime = const TimeOfDay(hour: 8, minute: 0);
  TimeOfDay _eveningTime = const TimeOfDay(hour: 21, minute: 0);

  // ── Schedule (from WeekConfig) ────────────────────────────────────────────
  String _wakeTime = '07:00';
  String _sleepTime = '23:00';

  bool _loading = true;

  // ── Lifecycle ─────────────────────────────────────────────────────────────

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final apiKey = await _llmService.getApiKey();
    final morningTime = await _notificationService.getMorningTime();
    final eveningTime = await _notificationService.getEveningTime();

    final db = LocalDb();
    await db.init();
    final config = await db.getLatestWeekConfig();
    await db.close();

    if (!mounted) return;
    setState(() {
      _apiKeySet = apiKey != null && apiKey.isNotEmpty;
      if (_apiKeySet) {
        _apiKeyController.text = _maskApiKey(apiKey!);
      }
      _morningTime = morningTime;
      _eveningTime = eveningTime;
      if (config != null) {
        _wakeTime = config.wakeTime;
        _sleepTime = config.sleepTime;
      }
      _loading = false;
    });
  }

  @override
  void dispose() {
    _apiKeyController.dispose();
    super.dispose();
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  String _maskApiKey(String key) {
    if (key.length <= 8) return '••••••••';
    return '${key.substring(0, 4)}${'•' * (key.length - 8)}${key.substring(key.length - 4)}';
  }

  String _formatTime(TimeOfDay time) {
    final hour = time.hourOfPeriod == 0 ? 12 : time.hourOfPeriod;
    final minute = time.minute.toString().padLeft(2, '0');
    final period = time.period == DayPeriod.am ? 'AM' : 'PM';
    return '$hour:$minute $period';
  }

  // ── Actions ───────────────────────────────────────────────────────────────

  Future<void> _saveApiKey() async {
    final raw = _apiKeyController.text.trim();
    if (raw.isEmpty || raw.contains('•')) return;

    setState(() => _savingApiKey = true);
    try {
      await _llmService.setApiKey(raw);
      if (!mounted) return;
      setState(() {
        _apiKeySet = true;
        _apiKeyController.text = _maskApiKey(raw);
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('API key saved'),
          backgroundColor: AppColors.healthPrimary,
        ),
      );
    } finally {
      if (mounted) setState(() => _savingApiKey = false);
    }
  }

  Future<void> _pickMorningTime() async {
    final picked = await _showTimePicker(_morningTime);
    if (picked == null) return;
    setState(() => _morningTime = picked);
    await _notificationService.scheduleMorning(picked);
  }

  Future<void> _pickEveningTime() async {
    final picked = await _showTimePicker(_eveningTime);
    if (picked == null) return;
    setState(() => _eveningTime = picked);
    await _notificationService.scheduleEvening(picked);
  }

  Future<TimeOfDay?> _showTimePicker(TimeOfDay initial) async {
    TimeOfDay? result;

    await showCupertinoModalPopup<void>(
      context: context,
      builder: (ctx) {
        Duration selected = Duration(
          hours: initial.hour,
          minutes: initial.minute,
        );

        return Container(
          height: 300,
          color: AppColors.surface,
          child: Column(
            children: [
              // Toolbar
              Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    CupertinoButton(
                      padding: EdgeInsets.zero,
                      onPressed: () => Navigator.of(ctx).pop(),
                      child: const Text(
                        'Cancel',
                        style: TextStyle(color: AppColors.textSecondary),
                      ),
                    ),
                    CupertinoButton(
                      padding: EdgeInsets.zero,
                      onPressed: () {
                        result = TimeOfDay(
                          hour: selected.inHours % 24,
                          minute: selected.inMinutes % 60,
                        );
                        Navigator.of(ctx).pop();
                      },
                      child: const Text(
                        'Done',
                        style: TextStyle(
                          color: AppColors.workPrimary,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: CupertinoTimerPicker(
                  mode: CupertinoTimerPickerMode.hm,
                  initialTimerDuration: selected,
                  onTimerDurationChanged: (d) => selected = d,
                ),
              ),
            ],
          ),
        );
      },
    );

    return result;
  }

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Settings'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(color: AppColors.workPrimary),
            )
          : ListView(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 40),
              children: [
                _buildApiKeySection(),
                const SizedBox(height: 20),
                _buildNotificationSection(),
                const SizedBox(height: 20),
                _buildScheduleSection(),
              ],
            ),
    );
  }

  // ── API Key section ───────────────────────────────────────────────────────

  Widget _buildApiKeySection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionLabel('AI Integration'),
        const SizedBox(height: 10),
        GlassCard(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Text(
                    'Claude API Key',
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const Spacer(),
                  _buildKeyStatusChip(),
                ],
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _apiKeyController,
                obscureText: false,
                style: const TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 14,
                  letterSpacing: 0.5,
                ),
                decoration: const InputDecoration(
                  hintText: 'sk-ant-...',
                  hintStyle: TextStyle(color: AppColors.textMuted),
                ),
                onTap: () {
                  // Clear mask when user taps to edit
                  if (_apiKeyController.text.contains('•')) {
                    _apiKeyController.clear();
                  }
                },
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _savingApiKey ? null : _saveApiKey,
                  child: _savingApiKey
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            color: Colors.white,
                            strokeWidth: 2,
                          ),
                        )
                      : const Text('Save'),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildKeyStatusChip() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: _apiKeySet ? AppColors.healthBg : AppColors.glassBg,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color:
              _apiKeySet ? AppColors.healthPrimary : AppColors.glassBorder,
        ),
      ),
      child: Text(
        _apiKeySet ? 'Key set' : 'Not set',
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w500,
          color:
              _apiKeySet ? AppColors.healthPrimary : AppColors.textMuted,
        ),
      ),
    );
  }

  // ── Notification section ──────────────────────────────────────────────────

  Widget _buildNotificationSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionLabel('Notifications'),
        const SizedBox(height: 10),
        GlassCard(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Column(
            children: [
              _timeTile(
                icon: Icons.wb_sunny_outlined,
                iconColor: AppColors.errandPrimary,
                label: 'Morning reminder',
                time: _morningTime,
                onTap: _pickMorningTime,
              ),
              Divider(
                height: 1,
                color: AppColors.glassBorder,
                indent: 56,
              ),
              _timeTile(
                icon: Icons.nights_stay_outlined,
                iconColor: AppColors.workPrimary,
                label: 'Evening check-in',
                time: _eveningTime,
                onTap: _pickEveningTime,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _timeTile({
    required IconData icon,
    required Color iconColor,
    required String label,
    required TimeOfDay time,
    required VoidCallback onTap,
  }) {
    return ListTile(
      leading: Container(
        width: 32,
        height: 32,
        decoration: BoxDecoration(
          color: iconColor.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(icon, color: iconColor, size: 16),
      ),
      title: Text(
        label,
        style: const TextStyle(
          fontSize: 14,
          color: AppColors.textPrimary,
        ),
      ),
      trailing: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: AppColors.glassBg,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppColors.glassBorder),
          ),
          child: Text(
            _formatTime(time),
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w500,
              color: AppColors.workPrimary,
            ),
          ),
        ),
      ),
    );
  }

  // ── Schedule section ──────────────────────────────────────────────────────

  Widget _buildScheduleSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionLabel('Schedule'),
        const SizedBox(height: 10),
        GlassCard(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              _infoRow('Wake time', _wakeTime),
              const SizedBox(height: 10),
              _infoRow('Sleep time', _sleepTime),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => const SetupScreen(isUpdate: true),
                      ),
                    );
                  },
                  icon: const Icon(
                    Icons.edit_calendar_outlined,
                    size: 16,
                    color: AppColors.workPrimary,
                  ),
                  label: const Text(
                    'Update teaching days',
                    style: TextStyle(color: AppColors.workPrimary),
                  ),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppColors.workPrimary),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _infoRow(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 14,
            color: AppColors.textSecondary,
          ),
        ),
        Text(
          value,
          style: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w500,
            color: AppColors.textPrimary,
          ),
        ),
      ],
    );
  }

  // ── Shared ────────────────────────────────────────────────────────────────

  Widget _sectionLabel(String label) {
    return Text(
      label.toUpperCase(),
      style: const TextStyle(
        fontSize: 11,
        fontWeight: FontWeight.w600,
        color: AppColors.sectionTitle,
        letterSpacing: 0.8,
      ),
    );
  }
}
