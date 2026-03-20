# SRTFlow — DaVinci Resolve Subtitle Translation Plugin

## Project Summary
A Python script plugin for DaVinci Resolve that translates subtitles. Supports two translation engines: **DatPMT** (free, no key) and **LibreTranslate** (free/self-hosted). Runs as an external PyQt6 window launched from DaVinci's Scripts menu.

Two modes:
- **Full UI** — file-based SRT translation with drag-and-drop, output file management, full settings
- **Quick Translate** — minimal dialog that reads subtitle items from the active DaVinci timeline, lets the user select which blocks to translate, and writes translations back in-place

## Core User Goals
- Translate `.srt` files without leaving DaVinci Resolve
- Translate subtitle blocks directly on the timeline (select blocks → pick language → translate)
- Support selecting multiple subtitle blocks at once for batch translation
- Modern, polished UI — user should feel the quality

## Tech Stack
- **Language**: Python 3.8+
- **UI Framework**: PyQt6 (modern dark QSS-styled UI)
- **SRT Parsing**: Manual parser (no heavy deps)
- **HTTP**: `requests` library
- **Translation APIs** (user-selectable):
  - **DatPMT** (default): `GET https://api.datpmt.com/api/v2/dictionary/translate?string=...&from_lang=...&to_lang=...` — free, no key
  - **LibreTranslate**: `POST /translate` — free tier or self-hosted
- **DaVinci Bridge**: DaVinci Resolve Python Scripting API (optional, degrades gracefully)
- **Cache**: Local JSON file (`~/.srtflow/cache.json`)

## Project Structure
```
SRTFlow/
├── CLAUDE.md
├── README.md
├── SRTFlow.py              # Entry point (--quick for Quick Translate mode)
├── requirements.txt
├── install.sh
├── install.bat
├── config.json             # Default user settings
├── glossary.json           # Custom term replacements
└── src/
    ├── __init__.py
    ├── translator.py       # DatPMT + LibreTranslate API clients, retry, rate limit
    ├── srt_parser.py       # SRT read/write, timing preserved, inline tags safe
    ├── resolve_bridge.py   # DaVinci Resolve scripting API (TimelineSubtitleItem + write-back)
    ├── cache.py            # Translation cache (JSON-based)
    ├── config_manager.py   # Load/save user config
    ├── undo.py             # Undo manager — stores originals before timeline overwrites
    └── ui/
        ├── __init__.py
        ├── app.py              # Main window (SRTFlowWindow) — file-based workflow
        ├── quick_translate.py  # Quick Translate dialog — timeline workflow (with preview + undo)
        ├── preview_dialog.py   # Side-by-side preview before committing to timeline
        ├── worker.py           # TranslationWorker + TimelineTranslationWorker (QThread)
        ├── theme.py            # Colors, fonts, spacing, master QSS stylesheet
        ├── widgets.py          # Reusable widgets (FileDropZone, LogPanel, ProgressPanel, etc.)
        └── components/
            ├── __init__.py
            ├── header.py           # Logo + title bar + DaVinci status badge
            ├── file_panel.py       # Output file path + browse button
            ├── lang_selector.py    # Source/target language dropdowns + swap button
            └── settings_panel.py   # Collapsible API settings (engine, endpoint, key, cache)
```

## Architecture Decisions
- **PyQt6** chosen for modern dark aesthetic matching DaVinci Resolve
- Plugin runs as a **standalone window** launched via DaVinci Scripts menu
- DaVinci integration is **optional** — degrades gracefully if no DaVinci instance found
- **Two UI modes**: Full window (file-based) and Quick Translate (timeline-based)
- `app.py` is a thin orchestrator that imports from `components/` — no monolithic UI file
- `worker.py` contains two QThread workers: `TranslationWorker` (file output) and `TimelineTranslationWorker` (in-place timeline write-back)
- `resolve_bridge.py` uses `TimelineSubtitleItem` wrapper that holds a reference to the Resolve item for write-back via `SetName()`
- **Skip-and-continue**: when a batch translation fails, workers retry one-by-one; still-failing lines are skipped and logged
- **Preview before commit**: `TimelineTranslationWorker` returns results without writing; `PreviewDialog` shows side-by-side review before applying
- **Undo**: `UndoManager` stores original text in `~/.srtflow/undo_history.json` before timeline overwrites (keeps last 10 operations)
- **Multi-track**: `resolve_bridge.get_subtitle_track_names()` lists all tracks; Quick Translate has a track picker dropdown
- Translation cache keyed by `(source_lang, target_lang, text_hash)` — avoids re-translating
- Inline tags (`<i>`, `<b>`, `<u>`) are preserved by stripping before translate + re-inserting
- Config stored in `~/.srtflow/config.json` (user home, not project dir)

## UI Design Philosophy
- **Dark theme** matching DaVinci Resolve's aesthetic (#0c0c0e bg, #151518 surface)
- **Accent color**: #4f9cf9 (blue) for primary actions
- **Modern flat design** — no borders, subtle shadows, rounded corners
- **Responsive feedback** — progress bars, live log, status indicators
- Fonts: System default (SF Pro on Mac, Segoe UI on Win)
- PyQt6 appearance: dark mode always via QSS stylesheet

## Translation APIs

### DatPMT (default)
- Endpoint: `GET https://api.datpmt.com/api/v2/dictionary/translate`
- Params: `string`, `from_lang`, `to_lang`
- Returns: plain translated text
- No API key needed, supports `auto` detection
- Free, no rate limit published

### LibreTranslate (optional)
- Default endpoint: `https://libretranslate.com`
- User can override with self-hosted instance URL
- Endpoint: `POST /translate`
- Payload: `{"q": "text", "source": "en", "target": "es", "format": "html", "api_key": ""}`
- Rate limit: ~80 req/min on free tier — handle with exponential backoff

## Quick Translate Workflow
1. User opens SRTFlow from `Workspace → Scripts → Utility → SRTFlow`
2. If DaVinci is running, a "Quick Translate Timeline" button appears in the main window
3. Clicking it opens the Quick Translate dialog
4. User picks which **subtitle track** to work on (multi-track support)
5. Dialog reads all subtitle items from the selected track
6. User selects which items to translate (checkbox list, select-all toggle)
7. User picks source/target language
8. Hits "Translate Selected" — translations run in a QThread (with skip-and-continue on error)
9. **Preview dialog** opens: side-by-side table showing original vs translated for every item
10. User reviews and clicks "Apply to Timeline" or "Cancel"
11. On confirm: translations written to timeline + **undo entry** stored (original texts saved)
12. "Undo Last" button restores the previous originals from undo history
13. Alternative: launch directly via `python SRTFlow.py --quick`

## Key Conventions
- All modules import-safe — no side effects at module level
- `resolve_bridge.py` wraps all DaVinci calls in try/except (DaVinci may not be running)
- SRT timing is NEVER modified — only the text content changes
- Cache is always consulted before making API calls
- Log all translation events (source line → translated line) to the UI log panel
- User config is loaded at startup, saved on every change
- UI components are self-contained with their own signals

## DaVinci Resolve Scripting Notes
- DaVinci exposes a `resolve` object via `DaVinciResolveScript` module
- Timeline subtitles accessed via `timeline.GetItemListInTrack("subtitle", 1)`
- Write back to subtitle items via `item.SetName(translated_text)`
- Script placed in: `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/` (macOS)
- DaVinci must be running for bridge to work; file-mode works standalone

## Install Locations (macOS)
- Scripts: `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/`
- Plugin appears under: `Workspace > Scripts > Utility > SRTFlow`

## User Preferences
- UI must feel premium and modern — no dated widgets
- Keep code modular and clean — one responsibility per file
- Graceful degradation — always work even without DaVinci running
- User-friendly — minimal steps to translate timeline subtitles

## Feature Roadmap

### Stage 1 — Production-Ready Core (reliability + trust) ✅ COMPLETE
- **Preview before commit** — side-by-side original vs translated dialog before writing to timeline
- **Skip-and-continue on error** — failed lines are logged + skipped, translation continues
- **Undo support** — store original text before overwriting timeline items, allow revert
- **Multi-track support** — user picks which subtitle track to translate (not hardcoded to track 1)

### Stage 2 — Pro Translation Engines + UX
- **DeepL engine** — industry-standard translation quality (API key required)
- **Google Translate engine** — widest language coverage (API key required)
- **Keyboard shortcuts** — Cmd+T translate, Cmd+Shift+T quick translate, etc.
- **Multiple file batch processing** — drop multiple .srt files, translate all in sequence
- **Glossary editor UI** — add/remove/search terms without editing JSON
- **Language auto-detection display** — show detected language after first batch

### Stage 3 — Wow Factor / Differentiators
- **AI-powered translation** — Claude API as a translation engine (context-aware, idiom-handling)
- **Character/line length limits** — warn or auto-reflow when subtitles exceed display constraints
- **Export to multiple formats** — VTT (web), ASS/SSA (styled), TTML (broadcast)
- **Quality score per line** — flag suspicious translations (too short, untranslated words, etc.)
- **Collaboration export** — CSV/XLSX review sheet with original + translated side-by-side
- **Progress persistence** — resume from where translation stopped after failure
