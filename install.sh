#!/usr/bin/env bash
# SRTFlow installer — macOS / Linux
set -e

PLUGIN_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "╔═══════════════════════════════════════╗"
echo "║         SRTFlow Installer             ║"
echo "╚═══════════════════════════════════════╝"
echo ""

# ── 1. Install Python dependencies ──────────────────────────────────────────
echo "▶ Installing Python dependencies…"
pip3 install --quiet --break-system-packages PyQt6 requests 2>/dev/null \
  || pip3 install --quiet PyQt6 requests 2>/dev/null \
  || echo "  ⚠  Could not install automatically. Run: pip3 install PyQt6 requests"
echo "  ✓ PyQt6 and requests installed"

# ── 2. Detect DaVinci Resolve scripts folder ────────────────────────────────
if [[ "$OSTYPE" == "darwin"* ]]; then
    DR_SCRIPTS="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility"
else
    DR_SCRIPTS="$HOME/.local/share/DaVinciResolve/Fusion/Scripts/Utility"
fi

# ── 3. Create symlink or copy ────────────────────────────────────────────────
if [ -d "$DR_SCRIPTS" ]; then
    echo "▶ DaVinci Resolve scripts folder found:"
    echo "  $DR_SCRIPTS"
    echo ""

    TARGET="$DR_SCRIPTS/SRTFlow.py"

    if [ -L "$TARGET" ] || [ -f "$TARGET" ]; then
        echo "  ⚠  SRTFlow already exists at target. Removing old version…"
        rm -f "$TARGET"
    fi
    # Also clean up old directory symlink if present
    [ -L "$DR_SCRIPTS/SRTFlow" ] && rm -f "$DR_SCRIPTS/SRTFlow"

    ln -s "$PLUGIN_DIR/SRTFlow.py" "$TARGET"
    echo "  ✓ Symlink created: $TARGET → $PLUGIN_DIR/SRTFlow.py"
    echo ""
    echo "═══════════════════════════════════════════"
    echo "  ✓ Installation complete!"
    echo ""
    echo "  In DaVinci Resolve:"
    echo "  Workspace → Scripts → Utility → SRTFlow"
    echo "═══════════════════════════════════════════"
else
    echo "  ⚠  DaVinci Resolve scripts folder not found."
    echo "  Manually place the SRTFlow folder in your Scripts/Utility directory."
    echo ""
    echo "  Expected path:"
    echo "  $DR_SCRIPTS"
fi
echo ""
