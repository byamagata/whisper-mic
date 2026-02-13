"""Tests for the CommandRouter state machine."""

from __future__ import annotations

import pytest

from dictation.commands import AppState, CommandRouter, StartDictation, StopDictation, TypeText


class TestCommandRouterInitialState:
    """Verify the router starts in the correct state."""

    def test_initial_state_is_listening(self) -> None:
        router = CommandRouter()
        assert router.state is AppState.LISTENING


class TestListeningState:
    """Test behaviour while the router is in LISTENING state."""

    def test_dictate_keyword_transitions_to_dictating(self) -> None:
        router = CommandRouter()
        result = router.process("dictate")
        assert isinstance(result, StartDictation)
        assert router.state is AppState.DICTATING

    def test_dictate_keyword_case_insensitive(self) -> None:
        router = CommandRouter()
        result = router.process("DICTATE")
        assert isinstance(result, StartDictation)
        assert router.state is AppState.DICTATING

    def test_dictate_keyword_mixed_case(self) -> None:
        router = CommandRouter()
        result = router.process("Dictate")
        assert isinstance(result, StartDictation)
        assert router.state is AppState.DICTATING

    def test_dictate_keyword_within_sentence(self) -> None:
        router = CommandRouter()
        result = router.process("please dictate this")
        assert isinstance(result, StartDictation)
        assert router.state is AppState.DICTATING

    def test_random_speech_returns_none(self) -> None:
        router = CommandRouter()
        result = router.process("hello world")
        assert result is None
        assert router.state is AppState.LISTENING

    def test_stop_keyword_in_listening_state_is_ignored(self) -> None:
        router = CommandRouter()
        result = router.process("stop")
        assert result is None
        assert router.state is AppState.LISTENING

    def test_empty_string_returns_none(self) -> None:
        router = CommandRouter()
        result = router.process("")
        assert result is None
        assert router.state is AppState.LISTENING

    def test_whitespace_only_returns_none(self) -> None:
        router = CommandRouter()
        result = router.process("   ")
        assert result is None
        assert router.state is AppState.LISTENING


class TestDictatingState:
    """Test behaviour while the router is in DICTATING state."""

    @pytest.fixture()
    def router(self) -> CommandRouter:
        """Return a CommandRouter already in DICTATING state."""
        r = CommandRouter()
        r.process("dictate")
        return r

    def test_stop_transitions_to_listening(self, router: CommandRouter) -> None:
        result = router.process("stop")
        assert isinstance(result, StopDictation)
        assert router.state is AppState.LISTENING

    def test_stop_case_insensitive(self, router: CommandRouter) -> None:
        result = router.process("STOP")
        assert isinstance(result, StopDictation)
        assert router.state is AppState.LISTENING

    def test_normal_text_returns_type_text(self, router: CommandRouter) -> None:
        result = router.process("hello world")
        assert isinstance(result, TypeText)
        assert result.text == "hello world"
        assert router.state is AppState.DICTATING

    def test_new_line_returns_newline(self, router: CommandRouter) -> None:
        result = router.process("new line")
        assert isinstance(result, TypeText)
        assert result.text == "\n"

    def test_new_paragraph_returns_double_newline(self, router: CommandRouter) -> None:
        result = router.process("new paragraph")
        assert isinstance(result, TypeText)
        assert result.text == "\n\n"

    def test_dictate_keyword_in_dictating_state_types_the_word(
        self, router: CommandRouter
    ) -> None:
        """When already dictating, 'dictate' should be typed, not re-trigger."""
        result = router.process("dictate")
        assert isinstance(result, TypeText)
        assert result.text == "dictate"
        assert router.state is AppState.DICTATING

    def test_empty_string_in_dictating_returns_none(
        self, router: CommandRouter
    ) -> None:
        result = router.process("")
        assert result is None
        assert router.state is AppState.DICTATING

    def test_whitespace_only_in_dictating_returns_none(
        self, router: CommandRouter
    ) -> None:
        result = router.process("   ")
        assert result is None
        assert router.state is AppState.DICTATING


class TestFullStateCycle:
    """Test complete state machine transitions."""

    def test_listening_to_dictating_and_back(self) -> None:
        router = CommandRouter()
        assert router.state is AppState.LISTENING

        # Transition to DICTATING
        result = router.process("dictate")
        assert isinstance(result, StartDictation)
        assert router.state is AppState.DICTATING

        # Type some text while dictating
        result = router.process("hello world")
        assert isinstance(result, TypeText)
        assert result.text == "hello world"
        assert router.state is AppState.DICTATING

        # Transition back to LISTENING
        result = router.process("stop")
        assert isinstance(result, StopDictation)
        assert router.state is AppState.LISTENING

        # Verify random speech is now ignored again
        result = router.process("hello")
        assert result is None
        assert router.state is AppState.LISTENING

    def test_multiple_cycles(self) -> None:
        router = CommandRouter()

        for _ in range(3):
            assert router.state is AppState.LISTENING
            router.process("dictate")
            assert router.state is AppState.DICTATING
            router.process("stop")
            assert router.state is AppState.LISTENING
