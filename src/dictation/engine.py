"""Main event loop wiring audio capture, transcription, command routing, and text output."""

from __future__ import annotations

import logging
import signal
import threading

from dictation.audio import AudioListener
from dictation.commands import (
    AppState,
    CommandRouter,
    StartDictation,
    StopDictation,
    TypeText,
)
from dictation.output import TextOutput
from dictation.transcriber import Transcriber

logger = logging.getLogger(__name__)


class DictationEngine:
    """Orchestrates the full dictation pipeline.

    Captures audio, detects speech via VAD, transcribes with Whisper,
    routes commands through the state machine, and inserts text into
    the active text field.

    Intermediate audio segments are transcribed progressively so text
    appears while the user is still speaking.
    """

    def __init__(
        self,
        *,
        model: str = "mlx-community/whisper-small.en-mlx",
        vad_threshold: float = 0.5,
        device: int | None = None,
    ) -> None:
        logger.debug("DictationEngine.__init__ Start")
        logger.debug(
            "DictationEngine.__init__ model=%r, vad_threshold=%.2f, device=%s",
            model,
            vad_threshold,
            device,
        )

        print(f"Loading model {model} ...")
        self._transcriber = Transcriber(model_name=model)
        print("Model ready.")

        self._listener = AudioListener(
            vad_threshold=vad_threshold,
        )
        self._router = CommandRouter()
        self._output = TextOutput()
        self._shutdown = threading.Event()

        # Tracks what has already been typed during the current utterance
        # so we only type the new suffix on each intermediate transcription.
        self._committed_text = ""

        logger.info("DictationEngine initialized")
        logger.debug("DictationEngine.__init__ End")

    def run(self) -> None:
        """Run the main dictation loop until interrupted."""
        logger.debug("DictationEngine.run Start")

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        print("[LISTENING] Waiting for \"dictate\"...")

        try:
            for segment, is_final in self._listener.listen(shutdown_event=self._shutdown):
                if self._shutdown.is_set():
                    break

                text = self._transcriber.transcribe(segment)
                if not text:
                    logger.debug("Empty transcription, skipping")
                    if is_final:
                        self._committed_text = ""
                    continue

                if self._router.state is AppState.LISTENING:
                    self._handle_listening(text, is_final)
                else:
                    self._handle_dictating(text, is_final)

        except Exception:
            logger.exception("Unexpected error in main loop")
        finally:
            print("\n[SHUTDOWN] Goodbye!")
            logger.info("DictationEngine stopped")
            logger.debug("DictationEngine.run End")

    def _handle_listening(self, text: str, is_final: bool) -> None:
        """In LISTENING mode, only check final segments for the 'dictate' keyword."""
        if not is_final:
            logger.debug("Listening mode: ignoring intermediate segment")
            return

        action = self._router.process(text)
        match action:
            case StartDictation():
                print("[DICTATING] Activated!")
                logger.info("Dictation mode activated")
            case _:
                print(f"[LISTENING] heard: \"{text}\" (ignored)")
                logger.debug("Ambient speech ignored: %r", text)

    def _handle_dictating(self, text: str, is_final: bool) -> None:
        """In DICTATING mode, stream text progressively and check for commands on final."""
        if is_final:
            # Route through command router to detect "stop", "new line", etc.
            action = self._router.process(text)
            match action:
                case StopDictation():
                    # Type any remaining new text before the stop keyword.
                    self._committed_text = ""
                    print("[LISTENING] Stopped. Waiting for \"dictate\"...")
                    logger.info("Dictation mode deactivated")

                case TypeText(text=action_text):
                    if action_text in ("\n", "\n\n"):
                        self._output.type_text(action_text)
                        display = repr(action_text)
                        print(f"[DICTATING] > typed: {display}")
                    else:
                        new_text = self._extract_new_text(action_text)
                        if new_text:
                            self._output.type_text(new_text)
                            print(f"[DICTATING] > typed: {new_text}")

                    self._committed_text = ""

        else:
            # Intermediate segment: type the new portion of the transcription.
            new_text = self._extract_new_text(text)
            if new_text:
                self._output.type_text(new_text)
                self._committed_text = text
                print(f"[DICTATING] > streaming: {new_text}")
                logger.debug(
                    "Streamed text: new=%r, committed=%r",
                    new_text,
                    self._committed_text,
                )

    def _extract_new_text(self, full_text: str) -> str:
        """Return the portion of *full_text* not yet typed.

        Compares against ``_committed_text`` to find what's new.
        If the model revised earlier text (full_text doesn't start
        with committed), we fall back to typing everything after
        the committed length to avoid getting stuck.
        """
        if not self._committed_text:
            return full_text

        if full_text.startswith(self._committed_text):
            return full_text[len(self._committed_text):]

        # Model revised earlier output — use length-based fallback.
        if len(full_text) > len(self._committed_text):
            new = full_text[len(self._committed_text):]
            logger.debug(
                "Text revision detected, using length fallback: committed=%r, full=%r, new=%r",
                self._committed_text,
                full_text,
                new,
            )
            return new

        logger.debug(
            "Text revision shorter than committed, skipping: committed=%r, full=%r",
            self._committed_text,
            full_text,
        )
        return ""

    def _signal_handler(self, signum: int, frame: object) -> None:
        """Handle SIGINT / SIGTERM for graceful shutdown."""
        logger.info("Received signal %d — shutting down", signum)
        self._shutdown.set()
