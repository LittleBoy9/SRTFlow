"""
Translation engine clients.
Supports DatPMT (free), LibreTranslate (free/self-hosted),
DeepL (API key required), and Google Translate (API key required).
All share the same interface: translate(), translate_batch(), test_connection().
"""

from __future__ import annotations
import time
import logging
from typing import List, Optional, Dict
from urllib.parse import quote

import requests

logger = logging.getLogger("srtflow.translator")

# Available translation engines
ENGINES = {
    "datpmt":         "DatPMT (Free, no key)",
    "libretranslate": "LibreTranslate",
    "deepl":          "DeepL (API key required)",
    "google":         "Google Translate (API key required)",
}

# Languages (display name → code)
LANGUAGES: Dict[str, str] = {
    "Auto Detect":  "auto",
    "Arabic":       "ar",
    "Azerbaijani":  "az",
    "Catalan":      "ca",
    "Chinese":      "zh",
    "Czech":        "cs",
    "Danish":       "da",
    "Dutch":        "nl",
    "English":      "en",
    "Esperanto":    "eo",
    "Finnish":      "fi",
    "French":       "fr",
    "German":       "de",
    "Greek":        "el",
    "Hebrew":       "he",
    "Hindi":        "hi",
    "Hungarian":    "hu",
    "Indonesian":   "id",
    "Irish":        "ga",
    "Italian":      "it",
    "Japanese":     "ja",
    "Korean":       "ko",
    "Persian":      "fa",
    "Polish":       "pl",
    "Portuguese":   "pt",
    "Romanian":     "ro",
    "Russian":      "ru",
    "Slovak":       "sk",
    "Spanish":      "es",
    "Swedish":      "sv",
    "Thai":         "th",
    "Turkish":      "tr",
    "Ukrainian":    "uk",
    "Vietnamese":   "vi",
}

LANG_CODE_TO_NAME: Dict[str, str] = {v: k for k, v in LANGUAGES.items() if v != "auto"}


class TranslationError(Exception):
    """Raised when a translation request fails after all retries."""


# ─────────────────────────────────────────────────────────────────────────────
# DatPMT Client (free, no API key, GET-based)
# ─────────────────────────────────────────────────────────────────────────────

class DatPMTClient:
    """
    Uses: GET https://api.datpmt.com/api/v2/dictionary/translate
    Params: string, from_lang, to_lang
    Returns: plain translated text.
    """

    ENDPOINT = "https://api.datpmt.com/api/v2/dictionary/translate"

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **_kwargs,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.detected_language: Optional[str] = None
        self._session = requests.Session()

    def translate(self, text: str, source: str, target: str) -> str:
        if not text.strip():
            return text
        return self._request(text, source, target)

    def translate_batch(self, texts: List[str], source: str, target: str) -> List[str]:
        results: List[str] = []
        for text in texts:
            if text.strip():
                results.append(self._request(text, source, target))
            else:
                results.append(text)
        return results

    def _request(self, text: str, source: str, target: str) -> str:
        params = {
            "string": text,
            "from_lang": source,
            "to_lang": target,
        }
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = self._session.get(
                    self.ENDPOINT,
                    params=params,
                    timeout=self.timeout,
                )
                if resp.status_code == 429:
                    wait = self.retry_delay * (2 ** attempt)
                    logger.warning("Rate limited. Waiting %.1fs", wait)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                # Response is plain text (the translated string)
                result = resp.text.strip()
                if result:
                    return result
                return text
            except requests.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))

        raise TranslationError(f"DatPMT translation failed after {self.max_retries} attempts: {last_error}")

    def test_connection(self) -> bool:
        try:
            resp = self._session.get(
                self.ENDPOINT,
                params={"string": "hello", "from_lang": "en", "to_lang": "es"},
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False


# ─────────────────────────────────────────────────────────────────────────────
# LibreTranslate Client (self-hosted or public, POST-based)
# ─────────────────────────────────────────────────────────────────────────────

class LibreTranslateClient:
    def __init__(
        self,
        endpoint: str = "https://libretranslate.com",
        api_key: str = "",
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.5,
        **_kwargs,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.detected_language: Optional[str] = None
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def translate(self, text: str, source: str, target: str) -> str:
        if not text.strip():
            return text
        results = self.translate_batch([text], source, target)
        return results[0]

    def translate_batch(self, texts: List[str], source: str, target: str) -> List[str]:
        if not texts:
            return []

        non_empty_indices = [(i, t) for i, t in enumerate(texts) if t.strip()]
        if not non_empty_indices:
            return texts[:]

        separator = "\n⚡\n"
        combined = separator.join(t for _, t in non_empty_indices)

        try:
            translated_combined = self._request_translate(combined, source, target)
            translated_parts = translated_combined.split("⚡")
            translated_parts = [p.strip() for p in translated_parts]

            if len(translated_parts) != len(non_empty_indices):
                return self._translate_one_by_one(texts, source, target)

            results = list(texts)
            for (idx, _), translated in zip(non_empty_indices, translated_parts):
                results[idx] = translated
            return results

        except TranslationError:
            raise
        except Exception:
            return self._translate_one_by_one(texts, source, target)

    def _translate_one_by_one(self, texts: List[str], source: str, target: str) -> List[str]:
        results = []
        for text in texts:
            if text.strip():
                results.append(self._request_translate(text, source, target))
            else:
                results.append(text)
        return results

    def _request_translate(self, text: str, source: str, target: str) -> str:
        payload = {
            "q": text,
            "source": source,
            "target": target,
            "format": "html",
        }
        if self.api_key:
            payload["api_key"] = self.api_key

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = self._session.post(
                    f"{self.endpoint}/translate",
                    json=payload,
                    timeout=self.timeout,
                )
                if resp.status_code == 429:
                    wait = self.retry_delay * (2 ** attempt)
                    logger.warning("Rate limited. Waiting %.1fs before retry.", wait)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                return data.get("translatedText", text)
            except requests.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))

        raise TranslationError(f"Translation failed after {self.max_retries} attempts: {last_error}")

    def test_connection(self) -> bool:
        try:
            resp = self._session.get(f"{self.endpoint}/languages", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False


# ─────────────────────────────────────────────────────────────────────────────
# DeepL Client (API key required, POST-based)
# ─────────────────────────────────────────────────────────────────────────────

# DeepL language code mapping (some differ from our standard codes)
_DEEPL_LANG_MAP = {
    "auto": None,   # DeepL omits source for auto-detect
    "zh": "ZH",
    "en": "EN",
    "pt": "PT-BR",  # Default to Brazilian Portuguese
}


class DeepLClient:
    """
    Uses DeepL API v2.
    Free tier: https://api-free.deepl.com/v2/translate
    Pro tier:  https://api.deepl.com/v2/translate
    """

    FREE_ENDPOINT = "https://api-free.deepl.com/v2/translate"
    PRO_ENDPOINT = "https://api.deepl.com/v2/translate"

    def __init__(
        self,
        api_key: str = "",
        endpoint: str = "",
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **_kwargs,
    ):
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.detected_language: Optional[str] = None
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"DeepL-Auth-Key {self.api_key}",
            "Content-Type": "application/json",
        })
        # Free keys end with ":fx"
        if endpoint:
            self._endpoint = endpoint.rstrip("/")
        elif api_key.rstrip().endswith(":fx"):
            self._endpoint = self.FREE_ENDPOINT
        else:
            self._endpoint = self.PRO_ENDPOINT

    @staticmethod
    def _map_lang(code: str, is_target: bool = False) -> Optional[str]:
        """Map our language code to DeepL's format."""
        if code == "auto":
            return None
        mapped = _DEEPL_LANG_MAP.get(code, code.upper())
        return mapped

    def translate(self, text: str, source: str, target: str) -> str:
        if not text.strip():
            return text
        results = self.translate_batch([text], source, target)
        return results[0]

    def translate_batch(self, texts: List[str], source: str, target: str) -> List[str]:
        if not texts:
            return []

        non_empty = [(i, t) for i, t in enumerate(texts) if t.strip()]
        if not non_empty:
            return texts[:]

        payload: dict = {
            "text": [t for _, t in non_empty],
            "target_lang": self._map_lang(target, is_target=True),
        }
        src = self._map_lang(source)
        if src:
            payload["source_lang"] = src

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = self._session.post(
                    self._endpoint, json=payload, timeout=self.timeout,
                )
                if resp.status_code == 429:
                    wait = self.retry_delay * (2 ** attempt)
                    logger.warning("DeepL rate limited. Waiting %.1fs", wait)
                    time.sleep(wait)
                    continue
                if resp.status_code == 403:
                    raise TranslationError("DeepL: Invalid API key or unauthorized.")
                if resp.status_code == 456:
                    raise TranslationError("DeepL: Quota exceeded.")
                resp.raise_for_status()

                data = resp.json()
                translations = data.get("translations", [])

                # Capture detected source language from first result
                if translations and not self.detected_language:
                    det = translations[0].get("detected_source_language", "")
                    if det:
                        self.detected_language = det.lower()

                results = list(texts)
                for (idx, _), tr in zip(non_empty, translations):
                    results[idx] = tr.get("text", texts[idx])
                return results

            except TranslationError:
                raise
            except requests.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))

        raise TranslationError(f"DeepL translation failed after {self.max_retries} attempts: {last_error}")

    def test_connection(self) -> bool:
        try:
            resp = self._session.get(
                self._endpoint.replace("/translate", "/usage"),
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False


# ─────────────────────────────────────────────────────────────────────────────
# Google Translate Client (Cloud Translation API v2, API key required)
# ─────────────────────────────────────────────────────────────────────────────

class GoogleTranslateClient:
    """
    Uses Google Cloud Translation API v2.
    Endpoint: POST https://translation.googleapis.com/language/translate/v2
    Requires an API key.
    """

    ENDPOINT = "https://translation.googleapis.com/language/translate/v2"

    def __init__(
        self,
        api_key: str = "",
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **_kwargs,
    ):
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.detected_language: Optional[str] = None
        self._session = requests.Session()

    def translate(self, text: str, source: str, target: str) -> str:
        if not text.strip():
            return text
        results = self.translate_batch([text], source, target)
        return results[0]

    def translate_batch(self, texts: List[str], source: str, target: str) -> List[str]:
        if not texts:
            return []

        non_empty = [(i, t) for i, t in enumerate(texts) if t.strip()]
        if not non_empty:
            return texts[:]

        payload: dict = {
            "q": [t for _, t in non_empty],
            "target": target,
            "format": "html",
            "key": self.api_key,
        }
        if source and source != "auto":
            payload["source"] = source

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = self._session.post(
                    self.ENDPOINT, json=payload, timeout=self.timeout,
                )
                if resp.status_code == 429:
                    wait = self.retry_delay * (2 ** attempt)
                    logger.warning("Google Translate rate limited. Waiting %.1fs", wait)
                    time.sleep(wait)
                    continue
                if resp.status_code == 403:
                    raise TranslationError("Google Translate: Invalid API key or API not enabled.")
                resp.raise_for_status()

                data = resp.json()
                translations = data.get("data", {}).get("translations", [])

                # Capture detected source language from first result
                if translations and not self.detected_language:
                    det = translations[0].get("detectedSourceLanguage", "")
                    if det:
                        self.detected_language = det.lower()

                results = list(texts)
                for (idx, _), tr in zip(non_empty, translations):
                    results[idx] = tr.get("translatedText", texts[idx])
                return results

            except TranslationError:
                raise
            except requests.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))

        raise TranslationError(f"Google Translate failed after {self.max_retries} attempts: {last_error}")

    def test_connection(self) -> bool:
        try:
            resp = self._session.get(
                f"{self.ENDPOINT}?key={self.api_key}&q=hello&target=es",
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False


# ─────────────────────────────────────────────────────────────────────────────
# Factory — create the right client from config
# ─────────────────────────────────────────────────────────────────────────────

def create_client(engine: str = "datpmt", **kwargs):
    """
    Factory to create the appropriate translation client.
    engine: "datpmt" | "libretranslate" | "deepl" | "google"
    """
    if engine == "libretranslate":
        return LibreTranslateClient(**kwargs)
    elif engine == "deepl":
        return DeepLClient(**kwargs)
    elif engine == "google":
        return GoogleTranslateClient(**kwargs)
    else:
        return DatPMTClient(**kwargs)
