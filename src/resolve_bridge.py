"""
DaVinci Resolve scripting bridge.
All calls wrapped in try/except — degrades gracefully when DaVinci is not running.
"""

from __future__ import annotations
import logging
import sys
from typing import Dict, List, Optional, Tuple

from .srt_parser import SubtitleEntry

logger = logging.getLogger("srtflow.resolve")


def _get_resolve():
    """Attempt to import and return the DaVinci Resolve object."""
    try:
        import DaVinciResolveScript as dvr  # type: ignore
        resolve = dvr.scriptapp("Resolve")
        return resolve
    except Exception:
        pass

    # Try alternate import path (Windows/Linux)
    try:
        sys.path.insert(0, "/opt/resolve/libs/Fusion/")
        import fusionscript as dvr  # type: ignore
        resolve = dvr.scriptapp("Resolve")
        return resolve
    except Exception:
        pass

    return None


class TimelineSubtitleItem:
    """
    Wraps a single DaVinci subtitle track item.
    Holds a reference to the original Resolve item so we can write back.
    """

    def __init__(self, resolve_item, index: int, start_tc: str, end_tc: str, text: str):
        self._item = resolve_item
        self.index = index
        self.start = start_tc
        self.end = end_tc
        self.text = text

    def set_text(self, new_text: str) -> bool:
        """Write translated text back to the timeline subtitle item."""
        try:
            self._item.SetName(new_text)
            self.text = new_text
            return True
        except Exception as e:
            logger.error("Failed to write subtitle text back: %s", e)
            return False

    def to_entry(self) -> SubtitleEntry:
        """Convert to a SubtitleEntry for use with the translation pipeline."""
        return SubtitleEntry(
            index=self.index,
            start=self.start,
            end=self.end,
            text=self.text,
        )


class ResolveBridge:
    """
    Thin wrapper around DaVinci Resolve's Python scripting API.
    Use is_available() before calling any other method.
    """

    def __init__(self):
        self._resolve = _get_resolve()
        self._project = None
        self._timeline = None

        if self._resolve:
            try:
                pm = self._resolve.GetProjectManager()
                self._project = pm.GetCurrentProject() if pm else None
                if self._project:
                    self._timeline = self._project.GetCurrentTimeline()
            except Exception as e:
                logger.warning("Could not get DaVinci project/timeline: %s", e)

    def is_available(self) -> bool:
        return self._resolve is not None and self._timeline is not None

    def get_timeline_name(self) -> Optional[str]:
        if not self._timeline:
            return None
        try:
            return self._timeline.GetName()
        except Exception:
            return None

    def get_subtitle_track_count(self) -> int:
        if not self._timeline:
            return 0
        try:
            return self._timeline.GetTrackCount("subtitle")
        except Exception:
            return 0

    def get_subtitle_track_names(self) -> Dict[int, str]:
        """
        Return {track_index: track_name} for all subtitle tracks.
        Falls back to 'Subtitle N' if the track name is empty.
        """
        result: Dict[int, str] = {}
        count = self.get_subtitle_track_count()
        for i in range(1, count + 1):
            try:
                name = self._timeline.GetTrackName("subtitle", i)
                result[i] = name if name else f"Subtitle {i}"
            except Exception:
                result[i] = f"Subtitle {i}"
        return result

    def get_subtitle_items(self, track_index: int = 1) -> List[TimelineSubtitleItem]:
        """
        Read all subtitle items from the specified subtitle track.
        Returns wrapped items that support write-back via set_text().
        """
        if not self._timeline:
            return []
        try:
            items = self._timeline.GetItemListInTrack("subtitle", track_index)
            if not items:
                return []

            fps = self._get_fps()
            result: List[TimelineSubtitleItem] = []

            for i, item in enumerate(items, start=1):
                start_frame = item.GetStart()
                end_frame = item.GetEnd()
                text = item.GetName()

                start_tc = _frames_to_timecode(start_frame, fps)
                end_tc = _frames_to_timecode(end_frame, fps)

                result.append(TimelineSubtitleItem(
                    resolve_item=item,
                    index=i,
                    start_tc=start_tc,
                    end_tc=end_tc,
                    text=text,
                ))
            return result
        except Exception as e:
            logger.error("Failed to read subtitle track: %s", e)
            return []

    def get_subtitle_entries(self, track_index: int = 1) -> List[SubtitleEntry]:
        """Read subtitle items and return as SubtitleEntry list (no write-back)."""
        return [item.to_entry() for item in self.get_subtitle_items(track_index)]

    def write_subtitle_items(
        self, items: List[TimelineSubtitleItem], translations: List[str]
    ) -> Tuple[int, int]:
        """
        Write translated texts back to timeline subtitle items.
        Returns (success_count, fail_count).
        """
        success = 0
        fail = 0
        for item, text in zip(items, translations):
            if item.set_text(text):
                success += 1
            else:
                fail += 1
        return success, fail

    def refresh_timeline(self) -> None:
        """Re-fetch the current timeline (e.g. after user switches timelines)."""
        if not self._resolve:
            return
        try:
            pm = self._resolve.GetProjectManager()
            self._project = pm.GetCurrentProject() if pm else None
            if self._project:
                self._timeline = self._project.GetCurrentTimeline()
        except Exception as e:
            logger.warning("Failed to refresh timeline: %s", e)

    def _get_fps(self) -> float:
        try:
            if self._timeline:
                fps_str = self._timeline.GetSetting("timelineFrameRate")
                return float(fps_str)
        except Exception:
            pass
        return 24.0

    def export_srt(self, output_path: str, track_index: int = 1) -> bool:
        """Export subtitle track to SRT file via DaVinci's built-in export."""
        if not self._timeline:
            return False
        try:
            self._timeline.Export(output_path, 0, track_index)
            return True
        except Exception as e:
            logger.error("SRT export failed: %s", e)
            return False


def _frames_to_timecode(frames: int, fps: float) -> str:
    """Convert frame count to SRT timecode HH:MM:SS,mmm."""
    total_ms = int((frames / fps) * 1000)
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    m = (total_s // 60) % 60
    h = total_s // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
