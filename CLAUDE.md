# Dictation - Project Instructions

## What This Is
100% local voice dictation system for macOS on Apple Silicon. Always-on listener with keyword activation ("dictate" / "stop") that types into the active text field. Zero API calls, zero cost.

## Tech Stack
- **Python 3.11+** with hatchling build system
- **mlx-whisper** — speech-to-text on Apple Silicon GPU (model: `mlx-community/whisper-small.en-mlx`)
- **silero-vad** — voice activity detection (1.8MB model, sub-1ms per chunk)
- **sounddevice** — audio capture (16kHz, mono, float32, 512-sample blocks)
- **pynput** — keyboard simulation for clipboard paste (Cmd+V)

## Project Structure
```
src/dictation/
├── __main__.py     # CLI entry point (argparse)
├── engine.py       # Main loop — wires audio → transcribe → commands → output
├── audio.py        # AudioListener: sounddevice + silero-vad, yields (audio, is_final) tuples
├── transcriber.py  # Whisper wrapper — passes numpy arrays directly (no ffmpeg)
├── commands.py     # State machine: LISTENING ↔ DICTATING, keyword routing
└── output.py       # Text insertion via pbcopy + Cmd+V paste
tests/
├── test_commands.py
└── test_output.py
```

## Key Architecture Decisions
- **Numpy arrays passed directly to mlx-whisper** — avoids temp files and ffmpeg dependency
- **Model loaded eagerly at startup** — so first "dictate" command is instant
- **Streaming transcription** — intermediate segments yielded every ~2s during speech; engine diffs against committed text to type only new suffixes
- **Command detection only on final segments** — prevents false "stop" triggers mid-sentence
- **Clipboard paste (Cmd+V)** for text insertion — fastest, works in all apps, handles full Unicode

## Running
```bash
source .venv/bin/activate
python -m dictation           # default
python -m dictation -v        # verbose/debug logging
python -m dictation --list-devices
```

## Testing
```bash
source .venv/bin/activate
python -m pytest tests/ -v
```
- Do NOT try to run the app itself in tests — it requires microphone + accessibility permissions
- Mock pynput and subprocess in output tests
- commands.py is pure logic — test the state machine thoroughly

## Conventions
- Use `logging.getLogger(__name__)` in every module
- Debug logs at method entry/exit with method name
- Info logs for state changes and transcription results
- Keep modules focused — each file has one class with one responsibility
- Modern Python: dataclasses, match statements, type hints, `from __future__ import annotations`

## Roadmap
See ROADMAP.md for upcoming phases. Current: Phase 1 (MVP) complete + streaming.
