# SRTFlow

A DaVinci Resolve plugin for subtitle translation. Drop in an SRT file, pick a language, translate — all without leaving your editing workflow.

Powered by [LibreTranslate](https://libretranslate.com) (free, open-source).

---

## Features

- Drag & drop SRT file translation
- 30+ languages via LibreTranslate
- Preserves all timecodes and inline formatting (`<i>`, `<b>`, `<u>`)
- Translation cache — never re-translates the same line twice
- DaVinci Resolve timeline integration (when running inside Resolve)
- Works standalone (no DaVinci required for file-mode)
- Self-hosted LibreTranslate support for unlimited translation

---

## Requirements

- Python 3.8+
- PyQt6
- requests

---

## Install

**macOS / Linux**
```bash
cd SRTFlow
chmod +x install.sh
./install.sh
```

**Windows**
```
install.bat
```

Then in DaVinci Resolve: `Workspace → Scripts → Utility → SRTFlow`

**Manual install**
```bash
pip install PyQt6 requests
```
Place the `SRTFlow/` folder in your DaVinci Resolve Scripts/Utility directory.

---

## Usage

1. Launch SRTFlow from DaVinci Resolve's Scripts menu (or run `python SRTFlow.py` standalone)
2. Drop your `.srt` file into the drop zone
3. Select source and target languages
4. Click **Translate**
5. Translated file is saved alongside the original (e.g. `movie_es.srt`)

---

## Self-hosted LibreTranslate

For unlimited, private translation:

```bash
pip install libretranslate
libretranslate --host 0.0.0.0 --port 5000
```

Then set the API endpoint in SRTFlow's settings to `http://localhost:5000`.

---

## Glossary

Edit `glossary.json` to add terms that should never be translated:

```json
{
  "terms": {
    "DaVinci Resolve": "DaVinci Resolve",
    "Blackmagic": "Blackmagic"
  }
}
```

---

## Config

User settings are stored at `~/.srtflow/config.json`. You can edit them directly or via the Settings panel in the app.

| Key | Default | Description |
|---|---|---|
| `api_endpoint` | `https://libretranslate.com` | LibreTranslate server URL |
| `api_key` | `""` | API key (optional) |
| `source_lang` | `"auto"` | Source language code |
| `target_lang` | `"es"` | Target language code |
| `cache_enabled` | `true` | Cache translated lines |
| `batch_size` | `10` | Lines per API batch |
| `timeout` | `30` | Request timeout (seconds) |

---

## License

MIT
