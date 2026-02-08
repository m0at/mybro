"""Haiku vision classifier — identifies which project the user is working on."""

import base64
import json
import subprocess
from pathlib import Path

import anthropic

from backend.config import config

_client: anthropic.Anthropic | None = None
_project_names: list[str] = []
_last_window_title: str = ""
_last_classification: str | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    return _client


def _get_active_window() -> tuple[str, str]:
    """Get active window title and app name via AppleScript."""
    try:
        result = subprocess.run(
            ["osascript", "-e", """
                tell application "System Events"
                    set frontApp to name of first application process whose frontmost is true
                    set windowTitle to ""
                    try
                        set windowTitle to name of front window of (first application process whose frontmost is true)
                    end try
                    return frontApp & "|" & windowTitle
                end tell
            """],
            capture_output=True, text=True, timeout=3,
        )
        parts = result.stdout.strip().split("|", 1)
        return parts[0] if parts else "", parts[1] if len(parts) > 1 else ""
    except Exception:
        return "", ""


def set_project_names(names: list[str]):
    global _project_names
    _project_names = names


def classify(screenshot_path: str | None = None) -> dict:
    """Classify which project the user is working on.

    Returns: {"project": str|None, "confidence": float, "window_title": str, "app_name": str}
    """
    global _last_window_title, _last_classification

    app_name, window_title = _get_active_window()

    # Optimization: skip API call if window hasn't changed
    if window_title == _last_window_title and _last_classification:
        return {
            "project": _last_classification,
            "confidence": 0.9,
            "window_title": window_title,
            "app_name": app_name,
            "cached": True,
        }

    _last_window_title = window_title

    # Try to infer from window title / path without API call
    for name in _project_names:
        if name.lower() in window_title.lower():
            _last_classification = name
            return {
                "project": name,
                "confidence": 0.85,
                "window_title": window_title,
                "app_name": app_name,
                "method": "title_match",
            }

    # Use Haiku vision if we have a screenshot and API key
    if screenshot_path and config.anthropic_api_key and Path(screenshot_path).exists():
        try:
            with open(screenshot_path, "rb") as f:
                img_data = base64.standard_b64encode(f.read()).decode("utf-8")

            client = _get_client()
            resp = client.messages.create(
                model=config.tracker.classifier_model,
                max_tokens=100,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": "image/jpeg", "data": img_data},
                        },
                        {
                            "type": "text",
                            "text": (
                                f"Which project is this developer working on? "
                                f"Options: {', '.join(_project_names)}. "
                                f"Window title: {window_title}. App: {app_name}. "
                                f"Reply with ONLY a JSON object: {{\"project\": \"name\", \"confidence\": 0.0-1.0}}"
                            ),
                        },
                    ],
                }],
            )
            text = resp.content[0].text.strip()
            # Parse JSON from response
            if "{" in text:
                data = json.loads(text[text.index("{"):text.rindex("}") + 1])
                _last_classification = data.get("project")
                return {
                    "project": data.get("project"),
                    "confidence": data.get("confidence", 0.5),
                    "window_title": window_title,
                    "app_name": app_name,
                    "method": "haiku_vision",
                }
        except Exception as e:
            print(f"Haiku classification failed: {e}")

    _last_classification = None
    return {
        "project": None,
        "confidence": 0.0,
        "window_title": window_title,
        "app_name": app_name,
        "method": "unknown",
    }
