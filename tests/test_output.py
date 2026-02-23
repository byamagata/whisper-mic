"""Tests for TextOutput clipboard-based text insertion."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest
from pynput.keyboard import Key

from dictation.output import TextOutput


@pytest.fixture()
def mock_controller() -> MagicMock:
    """Return a mock pynput keyboard Controller."""
    return MagicMock()


@pytest.fixture()
def output(mock_controller: MagicMock) -> TextOutput:
    """Return a TextOutput instance with a mocked keyboard controller."""
    with patch("dictation.output.Controller", return_value=mock_controller):
        out = TextOutput()
    return out


class TestTypeText:
    """Test TextOutput.type_text clipboard + paste behaviour."""

    @patch("dictation.output.time.sleep")
    @patch("dictation.output.subprocess.Popen")
    def test_type_text_calls_pbcopy_with_correct_bytes(
        self,
        mock_popen: MagicMock,
        mock_sleep: MagicMock,
        output: TextOutput,
    ) -> None:
        process = MagicMock()
        mock_popen.return_value = process

        output.type_text("hello")

        mock_popen.assert_called_once_with(["pbcopy"], stdin=-1)
        process.communicate.assert_called_once_with(b"hello")

    @patch("dictation.output.time.sleep")
    @patch("dictation.output.subprocess.Popen")
    def test_type_text_simulates_cmd_v(
        self,
        mock_popen: MagicMock,
        mock_sleep: MagicMock,
        output: TextOutput,
        mock_controller: MagicMock,
    ) -> None:
        mock_popen.return_value = MagicMock()

        output.type_text("hello")

        mock_controller.press.assert_any_call(Key.cmd)
        mock_controller.press.assert_any_call("v")
        mock_controller.release.assert_any_call("v")
        mock_controller.release.assert_any_call(Key.cmd)

    @patch("dictation.output.time.sleep")
    @patch("dictation.output.subprocess.Popen")
    def test_type_text_cmd_v_key_order(
        self,
        mock_popen: MagicMock,
        mock_sleep: MagicMock,
        output: TextOutput,
        mock_controller: MagicMock,
    ) -> None:
        """Verify the paste sequence is Cmd down, v down, v up, Cmd up."""
        mock_popen.return_value = MagicMock()

        output.type_text("x")

        press_calls = mock_controller.press.call_args_list
        release_calls = mock_controller.release.call_args_list

        assert press_calls == [call(Key.cmd), call("v")]
        assert release_calls == [call("v"), call(Key.cmd)]

    @patch("dictation.output.subprocess.Popen")
    def test_type_text_empty_string_is_noop(
        self,
        mock_popen: MagicMock,
        output: TextOutput,
    ) -> None:
        output.type_text("")

        mock_popen.assert_not_called()

    @patch("dictation.output.time.sleep")
    @patch("dictation.output.subprocess.Popen")
    def test_type_text_unicode(
        self,
        mock_popen: MagicMock,
        mock_sleep: MagicMock,
        output: TextOutput,
    ) -> None:
        process = MagicMock()
        mock_popen.return_value = process

        output.type_text("cafe\u0301")

        process.communicate.assert_called_once_with("cafe\u0301".encode("utf-8"))


class TestBackspace:
    """Test TextOutput.backspace key simulation."""

    def test_backspace_presses_key_n_times(
        self,
        output: TextOutput,
        mock_controller: MagicMock,
    ) -> None:
        output.backspace(3)

        assert mock_controller.press.call_count == 3
        assert mock_controller.release.call_count == 3
        for c in mock_controller.press.call_args_list:
            assert c == call(Key.backspace)

    def test_backspace_zero_is_noop(
        self,
        output: TextOutput,
        mock_controller: MagicMock,
    ) -> None:
        output.backspace(0)

        mock_controller.press.assert_not_called()
        mock_controller.release.assert_not_called()

    def test_backspace_press_release_order(
        self,
        output: TextOutput,
        mock_controller: MagicMock,
    ) -> None:
        """Each backspace should be a press+release pair."""
        call_order: list[str] = []
        mock_controller.press.side_effect = lambda k: call_order.append("press")
        mock_controller.release.side_effect = lambda k: call_order.append("release")

        output.backspace(2)

        assert call_order == ["press", "release", "press", "release"]


class TestTypeKey:
    """Test TextOutput.type_key special key simulation."""

    def test_type_key_sends_press_and_release(
        self,
        output: TextOutput,
        mock_controller: MagicMock,
    ) -> None:
        output.type_key(Key.enter)

        mock_controller.press.assert_called_once_with(Key.enter)
        mock_controller.release.assert_called_once_with(Key.enter)

    def test_type_key_press_before_release(
        self,
        output: TextOutput,
        mock_controller: MagicMock,
    ) -> None:
        """Verify press is called before release."""
        call_order: list[str] = []
        mock_controller.press.side_effect = lambda k: call_order.append("press")
        mock_controller.release.side_effect = lambda k: call_order.append("release")

        output.type_key(Key.enter)

        assert call_order == ["press", "release"]
