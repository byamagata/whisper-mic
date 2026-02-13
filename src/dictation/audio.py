"""Audio capture with voice activity detection using sounddevice and silero-vad."""

from __future__ import annotations

import logging
import queue
import threading
from collections import deque
from typing import Generator

import numpy as np
import sounddevice as sd
import torch
from silero_vad import VADIterator, load_silero_vad

logger = logging.getLogger(__name__)

# silero-vad requires exactly 512 samples per chunk at 16kHz (32ms)
_BLOCK_SIZE = 512
_CHANNELS = 1
_DTYPE = "float32"


class AudioListener:
    """Captures audio from the default input device and yields speech segments.

    Uses sounddevice for audio capture and silero-vad for voice activity
    detection. Speech segments are yielded as contiguous numpy arrays with
    pre-speech padding to avoid clipping the beginning of utterances.

    When *stream_interval_s* is set (default 2.0), intermediate segments are
    yielded during speech so the caller can transcribe progressively.
    """

    def __init__(
        self,
        *,
        sample_rate: int = 16_000,
        vad_threshold: float = 0.5,
        speech_pad_ms: int = 300,
        stream_interval_s: float = 2.0,
    ) -> None:
        logger.debug(
            "AudioListener.__init__ Start — sample_rate=%d, vad_threshold=%.2f, "
            "speech_pad_ms=%d, stream_interval_s=%.1f",
            sample_rate,
            vad_threshold,
            speech_pad_ms,
            stream_interval_s,
        )

        self.sample_rate = sample_rate
        self.speech_pad_ms = speech_pad_ms

        self._model = load_silero_vad()
        self._vad_iterator = VADIterator(
            self._model,
            threshold=vad_threshold,
            sampling_rate=sample_rate,
        )
        self._queue: queue.Queue[np.ndarray | None] = queue.Queue()

        # Number of chunks to keep in the ring buffer for pre-speech padding.
        chunk_duration_ms = (_BLOCK_SIZE / sample_rate) * 1000
        self._pad_chunks = max(1, int(speech_pad_ms / chunk_duration_ms))

        # Number of chunks that make up one streaming interval.
        chunk_duration_s = _BLOCK_SIZE / sample_rate
        self._stream_interval_chunks = max(1, int(stream_interval_s / chunk_duration_s))

        logger.debug(
            "AudioListener.__init__ End — pad_chunks=%d, stream_interval_chunks=%d",
            self._pad_chunks,
            self._stream_interval_chunks,
        )

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,  # noqa: ARG002
        time_info: object,  # noqa: ARG002
        status: sd.CallbackFlags,
    ) -> None:
        """sounddevice callback — runs in a separate thread."""
        if status:
            logger.warning("Audio callback status: %s", status)
        # indata shape is (512, 1); copy and flatten to (512,)
        self._queue.put(indata[:, 0].copy())

    def listen(
        self,
        shutdown_event: threading.Event | None = None,
    ) -> Generator[tuple[np.ndarray, bool], None, None]:
        """Yield speech segments as ``(audio, is_final)`` tuples.

        During speech, intermediate segments are yielded every
        *stream_interval_s* seconds with ``is_final=False``.  These
        contain only the **new** audio since the last yield.

        When VAD detects the end of speech, a final segment is yielded
        with ``is_final=True`` containing the remaining audio.

        Parameters
        ----------
        shutdown_event:
            When set, the generator will finish the current utterance (if any)
            and return.
        """
        logger.debug("listen Start")

        ring_buffer: deque[np.ndarray] = deque(maxlen=self._pad_chunks)
        speech_buffer: list[np.ndarray] = []
        in_speech = False
        chunks_since_yield = 0

        stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=_CHANNELS,
            dtype=_DTYPE,
            blocksize=_BLOCK_SIZE,
            callback=self._audio_callback,
        )

        try:
            stream.start()
            logger.info("Audio stream started — listening for speech")

            while True:
                # Check for shutdown between queue reads.
                if shutdown_event is not None and shutdown_event.is_set():
                    logger.info("Shutdown event received — stopping listener")
                    break

                try:
                    chunk = self._queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                if chunk is None:
                    logger.debug("Received sentinel — stopping listener")
                    break

                # Feed chunk to VAD.
                tensor = torch.from_numpy(chunk).float()
                vad_result = self._vad_iterator(tensor, return_seconds=False)

                if vad_result is not None:
                    if "start" in vad_result:
                        logger.debug(
                            "VAD speech start detected at sample %s",
                            vad_result["start"],
                        )
                        in_speech = True
                        chunks_since_yield = 0
                        # Prepend ring buffer contents for pre-speech padding.
                        speech_buffer.extend(ring_buffer)
                        ring_buffer.clear()
                        speech_buffer.append(chunk)
                        chunks_since_yield += 1

                    elif "end" in vad_result:
                        logger.debug(
                            "VAD speech end detected at sample %s",
                            vad_result["end"],
                        )
                        speech_buffer.append(chunk)

                        # Yield remaining audio as final segment.
                        segment = np.concatenate(speech_buffer)
                        duration_s = len(segment) / self.sample_rate
                        logger.info(
                            "Speech segment final — %.2fs (%d samples)",
                            duration_s,
                            len(segment),
                        )

                        yield segment, True

                        # Reset state for next utterance.
                        speech_buffer.clear()
                        in_speech = False
                        chunks_since_yield = 0
                        self._vad_iterator.reset_states()

                elif in_speech:
                    speech_buffer.append(chunk)
                    chunks_since_yield += 1

                    # Yield an intermediate segment if enough audio accumulated.
                    if chunks_since_yield >= self._stream_interval_chunks:
                        segment = np.concatenate(speech_buffer)
                        duration_s = len(segment) / self.sample_rate
                        logger.info(
                            "Speech segment intermediate — %.2fs (%d samples)",
                            duration_s,
                            len(segment),
                        )

                        yield segment, False

                        # Keep the full buffer for context but reset the
                        # counter so we only yield new audio next time.
                        chunks_since_yield = 0

                else:
                    ring_buffer.append(chunk)

        finally:
            stream.stop()
            stream.close()
            logger.info("Audio stream closed")
            logger.debug("listen End")
