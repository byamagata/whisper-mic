import unittest
from unittest.mock import MagicMock, patch, ANY
import numpy as np
import queue
import time
import main  # Importing the module to test classes

class TestAudioRecorder(unittest.TestCase):
    @patch('main.sd.InputStream')
    def test_start_stop_recording(self, mock_input_stream):
        recorder = main.AudioRecorder()

        # Test start
        recorder.start_recording()
        self.assertTrue(recorder.recording)
        self.assertIsNotNone(recorder.stream)
        mock_input_stream.assert_called_once()
        recorder.stream.start.assert_called_once()

        # Simulate some data
        with recorder._lock:
            recorder.frames.append(np.zeros((1024, 1), dtype='float32'))

        # Test stop
        audio_data = recorder.stop_recording()
        self.assertFalse(recorder.recording)
        self.assertIsNone(recorder.stream)
        self.assertIsNotNone(audio_data)
        # Check shape (flattened)
        self.assertEqual(audio_data.shape, (1024,))

    def test_stop_without_start(self):
        recorder = main.AudioRecorder()
        result = recorder.stop_recording()
        self.assertIsNone(result)

class TestTranscriber(unittest.TestCase):
    @patch('main.WhisperModel')
    @patch('main.keyboard.Controller')
    def test_transcribe_flow(self, mock_kb_controller, mock_whisper):
        # Setup mocks
        mock_model_instance = MagicMock()
        mock_whisper.return_value = mock_model_instance

        # Mock segment result
        mock_segment = MagicMock()
        mock_segment.text = "Hello world"
        mock_model_instance.transcribe.return_value = ([mock_segment], None)

        transcriber = main.Transcriber(device="cpu", compute_type="int8")

        # Verify model init
        mock_whisper.assert_called_with("distil-medium.en", device="cpu", compute_type="int8")

        # Test transcribe_and_type directly to avoid threading issues in unit test
        fake_audio = np.zeros(1024, dtype='float32')
        transcriber.transcribe_and_type(fake_audio)

        mock_model_instance.transcribe.assert_called_with(fake_audio, beam_size=5)
        transcriber.keyboard_controller.type.assert_called_with("Hello world ")

class TestInputController(unittest.TestCase):
    def test_hotkey_logic(self):
        recorder = MagicMock()
        transcriber = MagicMock()
        transcriber.audio_queue = MagicMock()

        controller = main.InputController(recorder, transcriber, hotkey='opt')

        # Test Press
        controller.on_press('opt')
        self.assertTrue(controller.is_holding)
        recorder.start_recording.assert_called_once()

        # Test Release
        recorder.stop_recording.return_value = "fake_audio"
        controller.on_release('opt')
        self.assertFalse(controller.is_holding)
        recorder.stop_recording.assert_called_once()
        transcriber.audio_queue.put.assert_called_with("fake_audio")

    def test_ignore_other_keys(self):
        recorder = MagicMock()
        transcriber = MagicMock()

        controller = main.InputController(recorder, transcriber, hotkey='opt')

        controller.on_press('a')
        self.assertFalse(controller.is_holding)
        recorder.start_recording.assert_not_called()

if __name__ == '__main__':
    unittest.main()
