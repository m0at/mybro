"""AFK detection — 180s no mouse + no keyboard = AFK."""

import asyncio
import subprocess
import time

from backend.config import config


class AFKDetector:
    def __init__(self, input_monitor):
        self.input_monitor = input_monitor
        self.threshold_s = config.tracker.afk_threshold_s
        self.is_afk = False
        self.afk_start: float | None = None

    def check(self) -> dict | None:
        """Check AFK status. Returns an event dict if state changed."""
        idle = self.input_monitor.seconds_since_input()

        if not self.is_afk and idle >= self.threshold_s:
            self.is_afk = True
            self.afk_start = time.time() - idle
            claude_active = self._check_claude_running()
            return {
                "event": "afk_start",
                "started_at": self.afk_start,
                "claude_active": claude_active,
            }

        if self.is_afk and idle < self.threshold_s:
            duration = time.time() - (self.afk_start or time.time())
            claude_active = self._check_claude_running()
            self.is_afk = False
            result = {
                "event": "afk_end",
                "started_at": self.afk_start,
                "ended_at": time.time(),
                "duration_s": duration,
                "claude_active": claude_active,
            }
            self.afk_start = None
            return result

        return None

    def _check_claude_running(self) -> bool:
        try:
            result = subprocess.run(
                ["pgrep", "-f", "claude"],
                capture_output=True, timeout=2,
            )
            return result.returncode == 0
        except Exception:
            return False
