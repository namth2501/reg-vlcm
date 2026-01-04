import whisper
import glob
import os
import time
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

def solve_audio_captcha():
    # Load model
    print("Loading Whisper model (base)...")
    try:
        model = whisper.load_model("base")
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    samples_dir = 'samples'
    audio_files = glob.glob(os.path.join(samples_dir, '*.mp3'))
    
    print(f"Found {len(audio_files)} audio files.")
    
    for audio_path in sorted(audio_files):
        print(f"Processing {os.path.basename(audio_path)}...")
        start_time = time.time()
        
        try:
            # Transcribe
            result = model.transcribe(audio_path)
            text = result["text"].strip()
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            print(f"File: {os.path.basename(audio_path)} -> Text: '{text}' (Time: {elapsed_time:.4f}s)")
        except Exception as e:
            print(f"Error processing {audio_path}: {e}")

if __name__ == "__main__":
    solve_audio_captcha()
