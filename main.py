import time
import queue
import threading
import sys
import numpy as np
import sounddevice as sd
from pynput import keyboard
from faster_whisper import WhisperModel

# Configuration
SAMPLE_RATE = 16000
CHANNELS = 1
# Using Right Option (Alt) as the PTT key
# You can change this to keyboard.Key.f13 if preferred
HOTKEY = keyboard.Key.alt_r

class AudioRecorder:
    """
    Handles audio capture from the microphone using sounddevice.
    Captures raw audio frames while recording is active.
    """
    def __init__(self, sample_rate=SAMPLE_RATE, channels=CHANNELS):
        self.sample_rate = sample_rate
        self.channels = channels
        self.frames = []
        self.recording = False
        self.stream = None
        self._lock = threading.Lock()

    def _callback(self, indata, frames, time_info, status):
        """Callback for sounddevice InputStream."""
        if status:
            print(f"Audio status: {status}", file=sys.stderr)
        if self.recording:
            with self._lock:
                self.frames.append(indata.copy())

    def start_recording(self):
        """Starts capturing audio."""
        with self._lock:
            self.frames = []
            self.recording = True

        # We create a new stream each time or restart an existing one.
        # Creating a new one is safer to ensure clean buffer state, though slightly higher latency.
        # For sub-500ms latency, we should try to keep it simple.
        # However, InputStream startup is usually fast enough.
        # Let's try starting it here.
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self._callback
        )
        self.stream.start()
        print(" [Recording started]", end="\r", flush=True)

    def stop_recording(self):
        """Stops capturing and returns the recorded audio buffer."""
        if not self.recording:
            return None

        with self._lock:
            self.recording = False

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        print(" [Recording stopped]", end="\r", flush=True)

        with self._lock:
            if not self.frames:
                return None
            # Concatenate all frames into a single numpy array
            audio_data = np.concatenate(self.frames, axis=0)

        # Flatten to 1D array for Whisper (it expects mono audio as a 1D array)
        return audio_data.flatten()


class Transcriber(threading.Thread):
    """
    Worker thread that picks up audio segments and runs inference.
    """
    def __init__(self, model_name="distil-medium.en", device="cpu", compute_type="int8"):
        super().__init__()
        self.audio_queue = queue.Queue()
        self.running = True
        self.keyboard_controller = keyboard.Controller()

        print(f"Loading model '{model_name}' on {device} with {compute_type}...")
        self.model = WhisperModel(model_name, device=device, compute_type=compute_type)
        print("Model Loaded.")

    def run(self):
        while self.running:
            try:
                # Wait for audio data
                audio_data = self.audio_queue.get(timeout=1.0)
                if audio_data is None:
                    continue

                self.transcribe_and_type(audio_data)
                self.audio_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in transcriber: {e}")

    def transcribe_and_type(self, audio_data):
        """Runs inference and types the result."""
        start_time = time.time()

        try:
            # Inference
            segments, info = self.model.transcribe(audio_data, beam_size=5)

            # fast-whisper returns a generator, so we must iterate to get the text
            text_segments = [segment.text for segment in segments]
            text = " ".join(text_segments).strip()

            if text:
                duration = time.time() - start_time
                print(f"\nTranscribed ({duration:.2f}s): {text}")

                # Safety: Ensure modifier keys are released
                time.sleep(0.1)

                # Type the text
                self.keyboard_controller.type(text + " ")
        except Exception as e:
            print(f"Transcription failed: {e}")

    def stop(self):
        self.running = False


class InputController:
    """
    Listens for hotkeys and controls the recording state.
    """
    def __init__(self, recorder, transcriber, hotkey=HOTKEY):
        self.recorder = recorder
        self.transcriber = transcriber
        self.hotkey = hotkey
        self.is_holding = False

    def on_press(self, key):
        if key == self.hotkey and not self.is_holding:
            self.is_holding = True
            self.recorder.start_recording()

    def on_release(self, key):
        if key == self.hotkey and self.is_holding:
            self.is_holding = False
            audio_data = self.recorder.stop_recording()
            if audio_data is not None:
                self.transcriber.audio_queue.put(audio_data)

    def start(self):
        # Blocking listener
        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            try:
                listener.join()
            except KeyboardInterrupt:
                print("\nExiting NeuralMic...")


def main():
    print("Initializing NeuralMic...")
    print("Press and hold 'Right Option' to talk.")
    print("Press Ctrl+C in terminal to exit.")

    # 1. Initialize Components
    try:
        recorder = AudioRecorder()
        transcriber = Transcriber()
    except Exception as e:
        print(f"Failed to initialize: {e}")
        return

    # 2. Start Transcriber Thread
    transcriber.start()

    # 3. Start Input Controller (Main Loop)
    controller = InputController(recorder, transcriber)

    try:
        controller.start()
    except KeyboardInterrupt:
        pass
    finally:
        transcriber.stop()
        transcriber.join()
        print("Shutdown complete.")

if __name__ == "__main__":
    main()
