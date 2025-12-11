# NeuralMic

A local, high-performance dictation CLI for macOS.

## Setup

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Permissions (Critical):**
    macOS requires specific permissions for this tool to work (key logging and microphone access).

    *   **Accessibility (Input Monitoring):**
        *   Open **System Settings** -> **Privacy & Security** -> **Accessibility**.
        *   Click the `+` button and add your terminal application (e.g., Terminal.app, iTerm.app, VSCode).
        *   If it's already there, you may need to toggle it off and on again if the script fails to detect keys.
        *   *Why?* This is required for `pynput` to listen for the global hotkey and simulate keystrokes.

    *   **Microphone:**
        *   When you first run the script, macOS might prompt you to allow Microphone access. Click **Allow**.
        *   If not prompted (or if recording fails), check **System Settings** -> **Privacy & Security** -> **Microphone** and ensure your terminal app is allowed.

## Usage

1.  Run the script:
    ```bash
    python main.py
    ```

2.  Wait for the model to load ("Model Loaded").

3.  **Hold the Right Option key**, speak, and release.
    *   The transcribed text will be typed into your active window.

## Configuration

*   **Model:** Defaults to `distil-medium.en` (English). You can change this in `main.py`.
*   **Hotkey:** Defaults to `Right Option` (`Key.alt_r`). Editable in `main.py`.
