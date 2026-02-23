"""Tests for spoken punctuation processing."""

from __future__ import annotations

import pytest

from dictation.punctuation import process_punctuation


class TestAutoPunctuationStripping:
    """Verify that Whisper's auto-inserted punctuation is removed."""

    def test_trailing_period_stripped(self) -> None:
        assert process_punctuation("Hello world.") == "Hello world"

    def test_trailing_question_mark_stripped(self) -> None:
        assert process_punctuation("How are you?") == "How are you"

    def test_trailing_exclamation_stripped(self) -> None:
        assert process_punctuation("Wow!") == "Wow"

    def test_mid_sentence_comma_stripped(self) -> None:
        assert process_punctuation("Hello, world.") == "Hello world"

    def test_multiple_auto_punctuation_stripped(self) -> None:
        assert process_punctuation("Wait, what?!") == "Wait what"

    def test_colon_and_semicolon_stripped(self) -> None:
        assert process_punctuation("Note: yes; no.") == "Note yes no"

    def test_apostrophes_preserved(self) -> None:
        assert process_punctuation("don't it's we're") == "don't it's we're"

    def test_plain_text_unchanged(self) -> None:
        assert process_punctuation("hello world") == "hello world"


class TestSpokenPunctuationReplacement:
    """Verify that spoken punctuation words become symbols."""

    def test_period(self) -> None:
        assert process_punctuation("hello period") == "hello."

    def test_comma(self) -> None:
        assert process_punctuation("hello comma world") == "hello, world"

    def test_question_mark(self) -> None:
        assert process_punctuation("how are you question mark") == "how are you?"

    def test_exclamation_point(self) -> None:
        assert process_punctuation("wow exclamation point") == "wow!"

    def test_exclamation_mark(self) -> None:
        assert process_punctuation("wow exclamation mark") == "wow!"

    def test_colon(self) -> None:
        assert process_punctuation("note colon") == "note:"

    def test_semicolon(self) -> None:
        assert process_punctuation("first semicolon second") == "first; second"

    def test_semicolon_two_words(self) -> None:
        assert process_punctuation("first semi colon second") == "first; second"

    def test_ellipsis(self) -> None:
        assert process_punctuation("well ellipsis") == "well..."

    def test_full_stop(self) -> None:
        assert process_punctuation("the end full stop") == "the end."

    def test_dash_becomes_em_dash(self) -> None:
        result = process_punctuation("hello dash world")
        assert result == "hello \u2014 world"

    def test_hyphen_joins_words(self) -> None:
        assert process_punctuation("well hyphen known") == "well-known"


class TestOpenClosePunctuation:
    """Verify brackets, parens, quotes, and braces."""

    def test_open_close_paren(self) -> None:
        assert process_punctuation("hello open paren maybe close paren world") == "hello (maybe) world"

    def test_open_close_parenthesis(self) -> None:
        assert process_punctuation("hello open parenthesis yes close parenthesis") == "hello (yes)"

    def test_open_close_bracket(self) -> None:
        assert process_punctuation("open bracket 1 close bracket") == "[1]"

    def test_open_close_brace(self) -> None:
        assert process_punctuation("open brace x close brace") == "{x}"

    def test_open_close_quote(self) -> None:
        result = process_punctuation("he said open quote hello close quote")
        assert result == "he said \u201chello\u201d"


class TestCaseInsensitivity:
    """Spoken punctuation should match regardless of case."""

    def test_period_uppercase(self) -> None:
        assert process_punctuation("hello PERIOD") == "hello."

    def test_comma_mixed_case(self) -> None:
        assert process_punctuation("hello Comma world") == "hello, world"

    def test_open_paren_caps(self) -> None:
        assert process_punctuation("Open Paren hi Close Paren") == "(hi)"


class TestWhisperAutoAndSpokenCombined:
    """Test realistic Whisper output where auto-punctuation and spoken words coexist."""

    def test_period_with_auto_period(self) -> None:
        # Whisper: "Hello period." (auto period after spoken "period")
        assert process_punctuation("Hello period.") == "Hello."

    def test_comma_with_auto_comma(self) -> None:
        # Whisper: "Hello, comma world."
        assert process_punctuation("Hello, comma world.") == "Hello, world"

    def test_question_mark_with_auto_question(self) -> None:
        assert process_punctuation("Are you sure question mark?") == "Are you sure?"

    def test_multiple_spoken_punctuation(self) -> None:
        result = process_punctuation("hello comma how are you question mark")
        assert result == "hello, how are you?"

    def test_paren_with_auto_punctuation(self) -> None:
        result = process_punctuation("I think, open paren maybe, close paren that's right.")
        assert result == "I think (maybe) that's right"


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_string(self) -> None:
        assert process_punctuation("") == ""

    def test_whitespace_only(self) -> None:
        assert process_punctuation("   ") == ""

    def test_only_auto_punctuation(self) -> None:
        assert process_punctuation("...") == ""

    def test_word_boundary_prevents_partial_match(self) -> None:
        # "dashboard" should not match "dash"
        assert process_punctuation("dashboard") == "dashboard"

    def test_commas_in_longer_word(self) -> None:
        # "commander" should not match "comma"
        assert process_punctuation("commander") == "commander"

    def test_periods_in_longer_word(self) -> None:
        # "periodic" should not match "period"
        assert process_punctuation("periodic") == "periodic"

    def test_spoken_punctuation_at_start(self) -> None:
        assert process_punctuation("period hello") == ". hello"

    def test_consecutive_spoken_punctuation(self) -> None:
        result = process_punctuation("hello period period")
        assert result == "hello.."
