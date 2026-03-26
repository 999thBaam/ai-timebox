import 'package:speech_to_text/speech_to_text.dart';

class SpeechService {
  final SpeechToText _speech = SpeechToText();
  bool _isAvailable = false;

  bool get isAvailable => _isAvailable;

  Future<void> init() async {
    _isAvailable = await _speech.initialize(
      onError: (_) {},
      onStatus: (_) {},
    );
  }

  Future<void> startListening({required Function(String) onResult}) async {
    if (!_isAvailable) return;

    await _speech.listen(
      onResult: (result) {
        if (result.finalResult) {
          onResult(result.recognizedWords);
        }
      },
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 3),
      listenOptions: SpeechListenOptions(
        partialResults: false,
      ),
    );
  }

  Future<void> stopListening() async {
    await _speech.stop();
  }
}
