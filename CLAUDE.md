# SRTFlow — DaVinci Resolve Subtitle Translation Plugin

## Project Summary
A Python script plugin for DaVinci Resolve that translates subtitles. Supports five translation engines: **DatPMT** (free, no key), **LibreTranslate** (free/self-hosted), **DeepL** (API key required), **Google Translate** (API key required), and **Claude AI** (Anthropic API key required, context-aware). Runs as an external PyQt6 window launched from DaVinci's Scripts menu.

Two modes:
- **Full UI** — file-based SRT translation with drag-and-drop, batch file support, output file management, multi-format export, quality scoring, full settings
- **Quick Translate** — minimal dialog that reads subtitle items from the active DaVinci timeline, lets the user select which blocks to translate, and writes translations back in-place

## Core User Goals
- Translate `.srt` files without leaving DaVinci Resolve
- Translate subtitle blocks directly on the timeline (select blocks → pick language → translate)
- Support selecting multiple subtitle blocks at once for batch translation
- Export translations to VTT, ASS/SSA, TTML, or CSV for collaboration
- Modern, polished UI — user should feel the quality

## Tech Stack
- **Language**: Python 3.8+
- **UI Framework**: PyQt6 (modern dark QSS-styled UI)
- **SRT Parsing**: Manual parser (no heavy deps)
- **HTTP**: `requests` library
- **Translation APIs** (user-selectable):
  - **DatPMT** (default): `GET https://api.datpmt.com/api/v2/dictionary/translate?string=...&from_lang=...&to_lang=...` — free, no key
  - **LibreTranslate**: `POST /translate` — free tier or self-hosted
  - **DeepL**: `POST https://api-free.deepl.com/v2/translate` (free) or `https://api.deepl.com/v2/translate` (pro) — API key required
  - **Google Translate**: `POST https://translation.googleapis.com/language/translate/v2` — API key required
  - **Claude AI**: `POST https://api.anthropic.com/v1/messages` — Anthropic API key required, context-aware subtitle translation
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
    ├── translator.py       # 5 translation clients (DatPMT, LibreTranslate, DeepL, Google, Claude)
    ├── srt_parser.py       # SRT read/write, timing preserved, inline tags safe
    ├── resolve_bridge.py   # DaVinci Resolve scripting API (TimelineSubtitleItem + write-back)
    ├── cache.py            # Translation cache (JSON-based)
    ├── config_manager.py   # Load/save user config
    ├── undo.py             # Undo manager — stores originals before timeline overwrites
    ├── export.py           # Multi-format export (VTT, ASS/SSA, TTML, CSV)
    ├── quality.py          # Translation quality scorer (per-line scoring + flags)
    ├── subtitle_validator.py  # Character/line length limits + reading speed checks
    ├── progress_store.py   # Progress persistence for resume-on-failure
    └── ui/
        ├── __init__.py
        ├── app.py              # Main window (SRTFlowWindow) — file-based workflow + batch + export
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
            ├── settings_panel.py   # Collapsible API settings (engine, endpoint, key, cache)
            └── glossary_editor.py  # Collapsible glossary editor (add/remove/search terms)
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
- **Batch file processing**: drop or select multiple .srt files; they're translated sequentially, auto-advancing after each completes
- **Glossary**: custom find→replace terms applied post-translation; stored in `glossary.json`, edited via collapsible UI panel
- **Language auto-detection**: DeepL and Google return detected source language; displayed in log after first batch
- **Keyboard shortcuts**: Ctrl+T translate, Ctrl+Shift+T quick translate, Ctrl+O open file, Ctrl+E export, Escape cancel, Ctrl+Z undo
- **Claude AI translation**: Sends numbered subtitle lines with context in a single prompt, parses numbered responses back; uses Haiku model for speed/cost
- **Quality scoring**: Post-translation analysis checks length ratios, untranslated words, punctuation mismatches; emits `quality_report` signal from worker
- **Subtitle validation**: Checks character/line limits (42 chars/line, 2 lines max, 25 chars/sec reading speed); runs on file load and on-demand
- **Multi-format export**: VTT (web), ASS/SSA (styled subs), TTML (broadcast), CSV (review sheet); all from `export.py` via `export_by_extension()`
- **Progress persistence**: `ProgressStore` saves translated text hashes to `~/.srtflow/progress.json`; worker saves per-batch; cancelled/crashed translations resume automatically

## UI Design Philosophy
- **Dark theme** matching DaVinci Resolve's aesthetic (#0c0c0e bg, #151518 surface)
- **Accent color**: #4f9cf9 (blue) for primary actions
- **Modern flat design** — no borders, subtle shadows, rounded corners
- **Responsive feedback** — progress bars, live log, status indicators, toast notifications
- **Post-translation actions**: Export and Validate buttons appear after translation completes
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

### DeepL (API key required)
- Free tier: `POST https://api-free.deepl.com/v2/translate` (keys ending in `:fx`)
- Pro tier: `POST https://api.deepl.com/v2/translate`
- Payload: `{"text": ["..."], "target_lang": "ES", "source_lang": "EN"}`
- Returns detected source language in response
- Auto-selects free/pro endpoint based on API key suffix
- Handles 403 (invalid key) and 456 (quota exceeded) specifically

### Google Translate (API key required)
- Endpoint: `POST https://translation.googleapis.com/language/translate/v2`
- Payload: `{"q": ["..."], "target": "es", "format": "html", "key": "..."}`
- Returns `detectedSourceLanguage` when source is `auto`
- Widest language coverage of all engines

### Claude AI (Anthropic API key required)
- Endpoint: `POST https://api.anthropic.com/v1/messages`
- Model: `claude-haiku-4-5-20251001` (fast + cost-effective for translation)
- Sends numbered subtitle lines with translation instructions
- Parses `[1] translated text\n[2] translated text` response format
- Context-aware: handles idioms, tone, register naturally for subtitles
- Fallback: if numbered parsing fails, splits by newlines
- Handles 429 (rate limit), 401 (invalid key), 403 (access denied)

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

## Keyboard Shortcuts
- **Ctrl+T** — Start translation (file mode)
- **Ctrl+Shift+T** — Open Quick Translate (timeline mode, requires DaVinci)
- **Ctrl+O** — Open/browse for SRT file(s)
- **Ctrl+E** — Export translation to other formats (VTT, ASS, TTML, CSV)
- **Escape** — Cancel running translation
- **Ctrl+Z** — Undo last timeline translation
- **Ctrl+/** — Show keyboard shortcuts help

## Key Conventions
- All modules import-safe — no side effects at module level
- `resolve_bridge.py` wraps all DaVinci calls in try/except (DaVinci may not be running)
- SRT timing is NEVER modified — only the text content changes
- Cache is always consulted before making API calls
- Log all translation events (source line → translated line) to the UI log panel
- User config is loaded at startup, saved on every change
- UI components are self-contained with their own signals
- All translation clients share the same interface: `translate()`, `translate_batch()`, `test_connection()`
- All clients expose `detected_language` attribute (set after first API call when source is `auto`)
- Quality scoring runs automatically after translation completes
- Subtitle validation runs on file load + on-demand via "Check Limits" button
- Progress is saved per-batch; cancelled translations can be resumed

## Export Formats
- **SRT** — SubRip (default output format)
- **VTT** — WebVTT for web players (timecodes use `.` instead of `,`)
- **ASS/SSA** — Advanced SubStation Alpha for styled subtitles (supports `<i>`, `<b>`, `<u>` → ASS overrides)
- **TTML** — Timed Text Markup Language for broadcast (XML-based, includes styling/layout)
- **CSV** — Side-by-side review sheet (original + translated + timecode + notes column)

## Quality Scoring
- Runs automatically after translation via `quality_report` signal
- Per-line score (0–100) based on:
  - **Length ratio**: flags if translation is <30% or >300% of original length
  - **Identical text**: flags if translation matches original (likely untranslated)
  - **Untranslated words**: detects original words appearing in translation
  - **Punctuation mismatch**: flags missing `?` or `!` in translation
  - **Empty translation**: score = 0 if translation is blank
- Average score displayed in log + toast notification
- Low-scoring lines (<70) shown individually in log

## Subtitle Validation
- Checks against industry-standard subtitle limits:
  - Max 42 characters per line
  - Max 2 lines per subtitle
  - Max 25 characters/second reading speed
  - Min 5 characters/second (unusually slow)
- `auto_reflow()` function splits long lines at word boundaries
- Runs automatically on file load (summary warning) + on-demand ("Check Limits" button)

## Progress Persistence
- Stored in `~/.srtflow/progress.json`
- Keyed by `{input_path}|{target_lang}`
- Saves after each batch: translated text hashes + completed index
- On cancellation: progress saved, "click Translate to resume" message shown
- On resume: previously translated texts loaded from progress store (skips re-translating)
- Stale detection: compares input file MD5 hash — clears progress if file changed
- Cleared automatically on successful completion

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

### Stage 2 — Pro Translation Engines + UX ✅ COMPLETE
- **DeepL engine** — industry-standard translation quality (API key required, auto free/pro endpoint)
- **Google Translate engine** — widest language coverage (API key required)
- **Keyboard shortcuts** — Ctrl+T translate, Ctrl+Shift+T quick translate, Ctrl+O open, Esc cancel, Ctrl+Z undo
- **Multiple file batch processing** — drop multiple .srt files, translate all in sequence
- **Glossary editor UI** — add/remove/search terms without editing JSON (collapsible panel)
- **Language auto-detection display** — show detected language in log after first batch

### Stage 3 — Wow Factor / Differentiators ✅ COMPLETE
- **AI-powered translation** — Claude API (Anthropic) as a 5th translation engine, context-aware subtitle translation
- **Character/line length limits** — validate against industry standards (42 chars/line, 2 lines, 25 CPS), auto-reflow support
- **Export to multiple formats** — VTT (web), ASS/SSA (styled), TTML (broadcast) via export dialog
- **Quality score per line** — automatic post-translation scoring (length ratio, untranslated words, punctuation, empty lines)
- **Collaboration export** — CSV review sheet with original + translated + timecode + notes column
- **Progress persistence** — save/resume interrupted translations via ~/.srtflow/progress.json
