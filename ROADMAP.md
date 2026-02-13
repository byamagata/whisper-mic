# Dictation Tool Roadmap

## Phase 1: MVP - Voice Dictation (Current)
- [x] Always-on listening daemon
- [x] Voice Activity Detection (silero-vad)
- [x] Local speech-to-text (mlx-whisper on Apple Silicon)
- [x] "Dictate" keyword starts typing into active text field
- [x] "Stop" keyword ends dictation
- [x] Text insertion via clipboard paste (Cmd+V)
- [x] Basic punctuation commands ("new line", "new paragraph")
- [x] CLI daemon (no GUI)

## Phase 2: Menu Bar UI
- [ ] macOS menu bar icon showing state (green=listening, yellow=dictating, red=sleeping)
- [ ] Click to toggle listening on/off
- [ ] Visual feedback during dictation (waveform or pulsing indicator)
- [ ] Settings panel for model selection and audio device

## Phase 3: App Launching & System Control
- [ ] "Ask Claude" / "Hey Claude" - opens Claude desktop app or claude.ai
- [ ] "Open terminal" - launches Terminal/iTerm
- [ ] "Open browser" - launches default browser
- [ ] "Open [app name]" - generic app launcher via `open -a`
- [ ] "Take a screenshot" - triggers macOS screenshot
- [ ] "Lock screen" - locks the machine
- [ ] "Do not disturb" - toggles Focus mode
- [ ] "Volume up/down/mute" - audio control

## Phase 4: Productivity & Workflow
- [ ] "Note to self: ..." - appends text to a local markdown notes file
- [ ] "Remind me to ..." - creates a local reminder/todo entry
- [ ] "Search for ..." - opens a web search in the browser
- [ ] "Summarize clipboard" - reads clipboard, runs local LLM to summarize (ollama/llama.cpp)

## Phase 5: Developer-Specific Commands
- [ ] "Run tests" - executes test command in current project
- [ ] "Git status" - opens terminal and runs git status
- [ ] "Build project" - triggers a build command
- [ ] "Commit changes" - starts a git commit workflow

## Phase 6: Advanced Text Editing
- [ ] "Delete that" - removes the last dictated phrase
- [ ] "Select all" / "Copy that" / "Paste" - clipboard operations via voice
- [ ] "Undo" - reverts the last action
- [ ] Smarter punctuation inference (auto-capitalize after periods, etc.)

## Phase 7: Extensibility
- [ ] YAML/TOML config file for custom keyword-to-action mappings
- [ ] Plugin system for user-defined actions (keyword -> shell command)
- [ ] "What can I say?" - reads back available commands
- [ ] User-trainable wake words (via openWakeWord custom training)

## Phase 8: Power Features
- [ ] "Go to sleep" / "Wake up" - pause/resume listener to save resources
- [ ] Multiple language support (switch Whisper model on the fly)
- [ ] Noise cancellation / environment adaptation
- [x] Continuous dictation with streaming transcription (partial results)
- [ ] Cross-platform support (Linux, Windows)

## Technical Debt & Polish
- [ ] Save/restore clipboard contents after paste insertion
- [x] Automatic model download on first run
- [ ] Configurable audio input device
- [ ] Configurable Whisper model size
- [ ] Logging and diagnostics mode
- [ ] System startup integration (launchd plist)
- [ ] Homebrew formula for easy installation
