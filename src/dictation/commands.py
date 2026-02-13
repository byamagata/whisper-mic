"""Command detection and state machine routing for dictation."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum, auto

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AppState(Enum):
    """Application states for the dictation state machine."""

    LISTENING = auto()
    DICTATING = auto()


# ---------------------------------------------------------------------------
# Action dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class StartDictation:
    """Signals that dictation mode has been activated."""


@dataclass(frozen=True, slots=True)
class StopDictation:
    """Signals that dictation mode has been deactivated."""


@dataclass(frozen=True, slots=True)
class TypeText:
    """Text to insert into the active field."""

    text: str


type Action = StartDictation | StopDictation | TypeText

# Pre-compiled patterns for keyword detection
_DICTATE_RE = re.compile(r"\bdictate\b", re.IGNORECASE)
_STOP_RE = re.compile(r"\bstop\b", re.IGNORECASE)
_NEW_LINE_RE = re.compile(r"\bnew\s+line\b", re.IGNORECASE)
_NEW_PARAGRAPH_RE = re.compile(r"\bnew\s+paragraph\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Command router
# ---------------------------------------------------------------------------

class CommandRouter:
    """Routes transcribed text to actions based on the current application state.

    Starts in ``LISTENING`` state and transitions between states based on
    keyword detection in transcribed text.
    """

    def __init__(self) -> None:
        self._state = AppState.LISTENING
        logger.info("CommandRouter initialized in %s state", self._state.name)

    @property
    def state(self) -> AppState:
        """Return the current application state."""
        return self._state

    def process(self, text: str) -> Action | None:
        """Process transcribed text and return an action (or ``None``).

        Args:
            text: Raw transcription text from the speech recogniser.

        Returns:
            An action to execute, or ``None`` if the text should be ignored.
        """
        logger.debug("process Start")
        logger.debug("process args: text=%r, state=%s", text, self._state.name)

        cleaned = text.strip()
        if not cleaned:
            logger.debug("process End (empty text, returning None)")
            return None

        match self._state:
            case AppState.LISTENING:
                result = self._handle_listening(cleaned)
            case AppState.DICTATING:
                result = self._handle_dictating(cleaned)

        logger.debug("process End -> %r", result)
        return result

    # -- Private handlers ---------------------------------------------------

    def _handle_listening(self, text: str) -> Action | None:
        """Handle text while in LISTENING state.

        Only responds to the "dictate" keyword. Everything else is ignored.
        """
        logger.debug("_handle_listening Start")

        if _DICTATE_RE.search(text):
            self._state = AppState.DICTATING
            logger.info(
                "State transition: %s -> %s (keyword: 'dictate')",
                AppState.LISTENING.name,
                AppState.DICTATING.name,
            )
            logger.debug("_handle_listening End -> StartDictation")
            return StartDictation()

        logger.debug("_handle_listening End -> None (no keyword match)")
        return None

    def _handle_dictating(self, text: str) -> Action | None:
        """Handle text while in DICTATING state.

        Responds to "stop" keyword, special phrases like "new line" / "new
        paragraph", and passes everything else through as ``TypeText``.
        """
        logger.debug("_handle_dictating Start")

        if _STOP_RE.search(text):
            self._state = AppState.LISTENING
            logger.info(
                "State transition: %s -> %s (keyword: 'stop')",
                AppState.DICTATING.name,
                AppState.LISTENING.name,
            )
            logger.debug("_handle_dictating End -> StopDictation")
            return StopDictation()

        if _NEW_PARAGRAPH_RE.search(text):
            logger.debug("_handle_dictating End -> TypeText(new paragraph)")
            return TypeText("\n\n")

        if _NEW_LINE_RE.search(text):
            logger.debug("_handle_dictating End -> TypeText(new line)")
            return TypeText("\n")

        logger.debug("_handle_dictating End -> TypeText(%r)", text)
        return TypeText(text)
