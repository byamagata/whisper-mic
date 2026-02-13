"""Whisper transcription wrapper using mlx-whisper for local speech-to-text."""

import logging
import time

import mlx.core as mx
import mlx_whisper
import numpy as np
from mlx_whisper.transcribe import ModelHolder

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "mlx-community/whisper-small.en-mlx"


class Transcriber:
    """Wraps mlx-whisper to transcribe raw audio arrays into text.

    The model is downloaded (if needed) and loaded eagerly at construction
    time so that the first transcription call is fast.
    """

    def __init__(self, model_name: str = _DEFAULT_MODEL) -> None:
        logger.debug("Transcriber.__init__ Start")
        logger.debug("Transcriber.__init__ model_name=%r", model_name)
        self._model_name = model_name

        logger.info("Loading model %s (this may download on first run)...", model_name)
        start = time.perf_counter()
        ModelHolder.get_model(model_name, mx.float16)
        elapsed = time.perf_counter() - start
        logger.info("Model loaded in %.2fs", elapsed)

        logger.debug("Transcriber.__init__ End")

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe a float32 numpy audio array into text.

        Passes the numpy array directly to mlx-whisper (no ffmpeg needed).

        Returns the transcribed text stripped of surrounding whitespace,
        or an empty string when transcription fails or produces no output.
        """
        logger.debug("transcribe Start")
        logger.debug(
            "transcribe audio.shape=%s sample_rate=%d duration=%.2fs",
            audio.shape,
            sample_rate,
            len(audio) / sample_rate,
        )

        try:
            start = time.perf_counter()
            result = mlx_whisper.transcribe(
                audio,
                path_or_hf_repo=self._model_name,
            )
            elapsed = time.perf_counter() - start

            text = result.get("text", "").strip()
            logger.info(
                "Transcription completed in %.2fs: %r",
                elapsed,
                text[:120] if text else "",
            )
            logger.debug("transcribe End")
            return text

        except Exception:
            logger.exception("Transcription failed")
            logger.debug("transcribe End")
            return ""
