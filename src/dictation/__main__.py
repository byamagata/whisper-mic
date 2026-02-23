"""CLI entry point for the dictation system.

Usage::

    python -m dictation
    python -m dictation --model mlx-community/whisper-base.en
    python -m dictation --list-devices
    python -m dictation -v  # verbose / debug logging
"""

from __future__ import annotations

import argparse
import logging
import sys

import sounddevice as sd

from dictation import __version__
from dictation.engine import DictationEngine

logger = logging.getLogger("dictation")

_BANNER = """\
Dictation v{version}
Model: {model}
VAD threshold: {threshold}
Microphone: {device}

Say "dictate" to start typing, "stop" to end.
Press Ctrl+C to quit.

NOTE: Accessibility permission required for your terminal app.
      System Settings → Privacy & Security → Accessibility
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dictation",
        description="100%% local dictation system with keyword activation.",
    )
    parser.add_argument(
        "--model",
        default="mlx-community/whisper-small.en-mlx",
        help="mlx-whisper model name or HuggingFace repo (default: %(default)s)",
    )
    parser.add_argument(
        "--vad-threshold",
        type=float,
        default=0.5,
        help="VAD sensitivity 0.0–1.0 (default: %(default)s)",
    )
    parser.add_argument(
        "--device",
        type=int,
        default=None,
        help="Audio input device index (see --list-devices)",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio devices and exit",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.list_devices:
        print(sd.query_devices())
        sys.exit(0)

    engine = DictationEngine(
        model=args.model,
        vad_threshold=args.vad_threshold,
        device=args.device,
    )

    print(
        _BANNER.format(
            version=__version__,
            model=args.model,
            threshold=args.vad_threshold,
            device=engine.device_name,
        )
    )

    try:
        engine.run()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Goodbye!")


if __name__ == "__main__":
    main()
