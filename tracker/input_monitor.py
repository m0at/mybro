"""Keyboard/mouse input monitoring using pynput. Counts only, never content."""

import threading
import time

from pynput import keyboard, mouse


class InputMonitor:
    def __init__(self):
        self.keystrokes = 0
        self.mouse_moves = 0
        self.mouse_clicks = 0
        self.scroll_events = 0
        self.last_input_time = time.time()
        self._lock = threading.Lock()
        self._kb_listener = None
        self._mouse_listener = None

    def start(self):
        self._kb_listener = keyboard.Listener(on_press=self._on_key)
        self._mouse_listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._kb_listener.start()
        self._mouse_listener.start()

    def stop(self):
        if self._kb_listener:
            self._kb_listener.stop()
        if self._mouse_listener:
            self._mouse_listener.stop()

    def _on_key(self, key):
        with self._lock:
            self.keystrokes += 1
            self.last_input_time = time.time()

    def _on_move(self, x, y):
        with self._lock:
            self.mouse_moves += 1
            self.last_input_time = time.time()

    def _on_click(self, x, y, button, pressed):
        if pressed:
            with self._lock:
                self.mouse_clicks += 1
                self.last_input_time = time.time()

    def _on_scroll(self, x, y, dx, dy):
        with self._lock:
            self.scroll_events += 1
            self.last_input_time = time.time()

    def flush(self) -> dict:
        """Return current counts and reset to zero."""
        with self._lock:
            data = {
                "keystrokes": self.keystrokes,
                "mouse_moves": self.mouse_moves,
                "mouse_clicks": self.mouse_clicks,
                "scroll_events": self.scroll_events,
            }
            self.keystrokes = 0
            self.mouse_moves = 0
            self.mouse_clicks = 0
            self.scroll_events = 0
            return data

    def seconds_since_input(self) -> float:
        with self._lock:
            return time.time() - self.last_input_time
