# Implementation Plan: MVP Dictation System

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Main Event Loop                     │
│                                                      │
│  ┌──────────┐    ┌──────────┐    ┌───────────────┐  │
│  │sounddevice│───>│silero-vad│───>│ Audio Buffer   │  │
│  │InputStream│    │ (32ms    │    │ (accumulates   │  │
│  │ (16kHz)   │    │  chunks) │    │  speech audio) │  │
│  └──────────┘    └──────────┘    └───────┬───────┘  │
│                                          │           │
│                                 on speech end        │
│                                          │           │
│                                          ▼           │
│                                  ┌──────────────┐   │
│                                  │  mlx-whisper  │   │
│                                  │ (transcribe)  │   │
│                                  └──────┬───────┘   │
│                                         │            │
│                                         ▼            │
│                                 ┌───────────────┐   │
│                                 │ Command Router │   │
│                                 │               │   │
│                                 │ "dictate" ──> │   │
│                                 │   start mode  │   │
│                                 │ "stop" ────> │   │
│                                 │   end mode    │   │
│                                 │ otherwise ──> │   │
│                                 │   type text   │   │
│                                 └───────────────┘   │
│                                         │            │
│                                         ▼            │
│                                 ┌───────────────┐   │
│                                 │  Text Output   │   │
│                                 │ (clipboard +   │   │
│                                 │  Cmd+V paste)  │   │
│                                 └───────────────┘   │
└─────────────────────────────────────────────────────┘
```

## State Machine

```
                 ┌──────────┐
        ┌───────>│ LISTENING │<────────┐
        │        │ (idle)    │         │
        │        └─────┬─────┘         │
        │              │               │
        │     speech detected          │
        │     transcription            │
        │     contains "dictate"       │
        │              │               │
        │              ▼               │
        │        ┌──────────┐          │
        │        │ DICTATING │         │
        │        │ (active)  │─────────┘
        │        └─────┬─────┘   speech contains
        │              │         "stop"
        │              │
        │     speech detected,
        │     transcribed text
        │     typed into active
        │     text field
        │              │
        └──────────────┘
              (continues dictating)
```

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Language | Python 3.11+ | Best ML ecosystem, fast prototyping |
| Audio capture | sounddevice | Outputs numpy arrays, clean macOS install |
| VAD | silero-vad | 1.8MB model, sub-1ms per chunk, excellent accuracy |
| Transcription | mlx-whisper | Native Apple Silicon GPU, 30-40% faster than whisper.cpp |
| Whisper model | `mlx-community/whisper-small.en` | Good accuracy/speed tradeoff for M2 Pro |
| Text insertion | clipboard + Cmd+V | Fastest, works in all apps, full Unicode |
| Keyboard sim | pynput | For Cmd+V simulation, simple API |

## Project Structure

```
dictation/
├── pyproject.toml          # Project config, dependencies
├── README.md               # Usage instructions
├── ROADMAP.md              # Future features
├── PLAN.md                 # This file
├── src/
│   └── dictation/
│       ├── __init__.py
│       ├── __main__.py     # Entry point: python -m dictation
│       ├── engine.py       # Main event loop, state machine
│       ├── audio.py        # Audio capture (sounddevice + silero-vad)
│       ├── transcriber.py  # Whisper transcription wrapper
│       ├── commands.py     # Command detection and routing
│       └── output.py       # Text insertion (clipboard paste)
└── tests/
    ├── __init__.py
    ├── test_commands.py    # Test command detection
    └── test_output.py      # Test text output
```

## File-by-File Implementation

### 1. `pyproject.toml` — Project configuration

Dependencies:
- `sounddevice` — audio capture
- `numpy` — audio array handling
- `silero-vad` — voice activity detection
- `torch` — required by silero-vad
- `mlx-whisper` — transcription engine
- `pynput` — keyboard simulation for Cmd+V

CLI entry point: `dictation = "dictation.__main__:main"`

### 2. `src/dictation/audio.py` — Audio Capture + VAD

**Class: `AudioListener`**
- Opens a `sounddevice.InputStream` at 16kHz, mono, float32
- Chunk size: 512 samples (32ms) to match silero-vad requirements
- Loads silero-vad model on init
- Uses `VADIterator` to detect speech start/end events
- On speech start: begins accumulating audio chunks into a buffer
- On speech end: returns the accumulated audio buffer as a numpy array
- Adds a small padding (300ms) before/after speech for better transcription
- Configurable VAD threshold (default 0.5)
- Uses a callback-based architecture with a queue for thread safety

### 3. `src/dictation/transcriber.py` — Whisper Transcription

**Class: `Transcriber`**
- Loads mlx-whisper model on init (lazy load on first transcription)
- Model: `mlx-community/whisper-small.en` (configurable)
- Method: `transcribe(audio: np.ndarray) -> str`
  - Accepts raw float32 numpy array at 16kHz
  - Writes to a temp WAV file (mlx-whisper needs file input)
  - Returns transcribed text, stripped and lowercased for command matching
  - Returns original-case text for dictation output

### 4. `src/dictation/commands.py` — Command Detection & Routing

**Enum: `AppState`** — `LISTENING`, `DICTATING`

**Class: `CommandRouter`**
- Holds current `AppState`
- Method: `process(text: str) -> Action`
- In LISTENING state:
  - If text contains "dictate" → transition to DICTATING, return `StartDictation` action
  - Otherwise → ignore (just ambient speech)
- In DICTATING state:
  - If text contains "stop" → transition to LISTENING, return `StopDictation` action
  - If text contains "new line" → return `TypeText("\n")` action
  - If text contains "new paragraph" → return `TypeText("\n\n")` action
  - Otherwise → return `TypeText(text)` action

**Action dataclasses:**
- `StartDictation` — signals dictation mode started (for logging/feedback)
- `StopDictation` — signals dictation mode ended
- `TypeText(text: str)` — text to insert into active field

### 5. `src/dictation/output.py` — Text Insertion

**Class: `TextOutput`**
- Method: `type_text(text: str)`
  - Copies text to clipboard via `subprocess.Popen(['pbcopy'])`
  - Simulates Cmd+V via pynput `Controller`
  - Small delay (10ms) between clipboard set and paste
- Method: `type_key(key)` — for special keys like Enter

### 6. `src/dictation/engine.py` — Main Event Loop

**Class: `DictationEngine`**
- Composes `AudioListener`, `Transcriber`, `CommandRouter`, `TextOutput`
- Main loop:
  1. `AudioListener` captures audio, VAD detects speech segments
  2. On speech end, sends audio to `Transcriber`
  3. Passes transcription to `CommandRouter`
  4. Executes resulting `Action` via `TextOutput`
- Handles graceful shutdown on SIGINT/SIGTERM
- Prints state transitions to stdout for CLI feedback

### 7. `src/dictation/__main__.py` — CLI Entry Point

- Parses minimal CLI args (--model, --threshold, --device)
- Prints startup banner with current settings
- Prints required permissions reminder (Accessibility)
- Creates and starts `DictationEngine`
- Handles Ctrl+C for clean shutdown

## Implementation Order

1. **`pyproject.toml`** — set up project and deps
2. **`output.py`** — text insertion (testable independently)
3. **`commands.py`** — command routing (pure logic, easy to unit test)
4. **`transcriber.py`** — Whisper wrapper
5. **`audio.py`** — audio capture + VAD
6. **`engine.py`** — wire everything together
7. **`__main__.py`** — CLI entry point
8. **Tests** — unit tests for commands and output
9. **Manual testing** — end-to-end dictation workflow

## Permissions Required

The user must grant **Accessibility** permission to their terminal app:
- System Settings → Privacy & Security → Accessibility
- Add Terminal.app (or iTerm2, VS Code, etc.)

This is required for pynput to simulate Cmd+V keystrokes.

## Open Questions (Resolved)

- ~~Whisper model size?~~ → `small.en` (good accuracy, fast on M2 Pro)
- ~~Text insertion method?~~ → Clipboard paste (fastest, most compatible)
- ~~Wake word system?~~ → VAD + Whisper on every utterance, check for "dictate" keyword
- ~~Streaming vs batch?~~ → Batch per utterance (simpler, reliable)
