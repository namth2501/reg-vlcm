import whisper
import os
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

class AudioSolver:
    def __init__(self, model_size="base"):
        print(f"Loading Whisper Model ({model_size})...")
        try:
            self.model = whisper.load_model(model_size)
            print("Whisper Model loaded successfully.")
        except Exception as e:
            print(f"Failed to load Whisper model: {e}")
            raise e

    def solve(self, audio_path):
        """
        Transcribes audio file.
        """
        try:
            result = self.model.transcribe(audio_path)
            return result["text"].strip()
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None
