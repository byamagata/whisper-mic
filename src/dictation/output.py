"""Text insertion into the active macOS text field via clipboard paste."""

import logging
import subprocess
import time

from pynput.keyboard import Controller, Key

logger = logging.getLogger(__name__)

# Delay between clipboard write and paste keystroke to ensure clipboard is ready.
_CLIPBOARD_SETTLE_DELAY = 0.01


class TextOutput:
    """Inserts text into the active text field using clipboard + Cmd+V."""

    def __init__(self) -> None:
        logger.debug("TextOutput.__init__ Start")
        self._keyboard = Controller()
        logger.info("TextOutput initialized")
        logger.debug("TextOutput.__init__ End")

    def type_text(self, text: str) -> None:
        """Copy *text* to the clipboard via pbcopy, then paste with Cmd+V.

        Does nothing when *text* is empty or whitespace-only.
        """
        logger.debug("type_text Start")
        logger.debug("type_text text=%r", text)

        if not text:
            logger.debug("type_text skipped: empty text")
            logger.debug("type_text End")
            return

        self._copy_to_clipboard(text)
        time.sleep(_CLIPBOARD_SETTLE_DELAY)
        self._paste()

        logger.info("Typed %d characters into active field", len(text))
        logger.debug("type_text End")

    def backspace(self, count: int) -> None:
        """Simulate *count* backspace key presses to delete previously typed text."""
        logger.debug("backspace Start")
        logger.debug("backspace count=%d", count)

        for _ in range(count):
            self._keyboard.press(Key.backspace)
            self._keyboard.release(Key.backspace)

        logger.info("Backspaced %d characters", count)
        logger.debug("backspace End")

    def type_key(self, key: Key) -> None:
        """Simulate a single special key press (e.g. Key.enter)."""
        logger.debug("type_key Start")
        logger.debug("type_key key=%s", key)

        self._keyboard.press(key)
        self._keyboard.release(key)

        logger.info("Typed special key %s", key)
        logger.debug("type_key End")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _copy_to_clipboard(self, text: str) -> None:
        """Write *text* to the macOS clipboard using pbcopy."""
        logger.debug("_copy_to_clipboard Start")
        process = subprocess.Popen(
            ["pbcopy"],
            stdin=subprocess.PIPE,
        )
        process.communicate(text.encode("utf-8"))
        logger.debug("_copy_to_clipboard End")

    def _paste(self) -> None:
        """Simulate Cmd+V to paste from clipboard."""
        logger.debug("_paste Start")
        self._keyboard.press(Key.cmd)
        self._keyboard.press("v")
        self._keyboard.release("v")
        self._keyboard.release(Key.cmd)
        logger.debug("_paste End")
