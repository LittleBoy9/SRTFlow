#!/usr/bin/env python3
"""
SRTFlow — DaVinci Resolve Subtitle Translation Plugin
======================================================
Place this file (and the src/ folder) in your DaVinci Resolve Scripts directory.

  macOS:  ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/
  Windows: %APPDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion\\Scripts\\Utility\\
  Linux:  ~/.local/share/DaVinciResolve/Fusion/Scripts/Utility/

Then launch via:  Workspace → Scripts → Utility → SRTFlow

Modes:
  - Full UI:        Opens the main window with file-based translation + Quick Translate button
  - Quick Translate: Pass --quick to jump straight to the timeline Quick Translate dialog
"""

import sys
import os

# Ensure the plugin's own directory is on the path so `src` is importable.
_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

# Friendly error if PyQt6 is missing.
try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
except ImportError:
    print(
        "\n[SRTFlow] PyQt6 is required.\n"
        "Run:  pip install PyQt6 requests\n"
        "Then restart DaVinci Resolve.\n"
    )
    sys.exit(1)

from src.ui.app import run_app


def run_quick():
    """Launch only the Quick Translate dialog (timeline mode)."""
    from src.resolve_bridge import ResolveBridge
    from src.config_manager import ConfigManager
    from src.ui.quick_translate import QuickTranslateDialog

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("SRTFlow")

    resolve = ResolveBridge()
    config = ConfigManager()

    if not resolve.is_available():
        QMessageBox.warning(
            None,
            "SRTFlow — Quick Translate",
            "DaVinci Resolve timeline not found.\n\n"
            "Make sure DaVinci Resolve is running and a timeline is open,\n"
            "or use the full SRTFlow window for file-based translation.",
        )
        return

    dlg = QuickTranslateDialog(resolve, config)
    dlg.exec()


if __name__ == "__main__":
    if "--quick" in sys.argv:
        run_quick()
    else:
        run_app()
