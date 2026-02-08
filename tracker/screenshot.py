"""Screenshot capture — 20s interval, region around cursor."""

import subprocess
import time
from datetime import datetime
from pathlib import Path

from backend.config import config

try:
    import Quartz
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False


def get_mouse_position() -> tuple[int, int]:
    """Get current mouse position using Quartz."""
    if HAS_QUARTZ:
        loc = Quartz.NSEvent.mouseLocation()
        # Convert from bottom-left to top-left coordinate system
        screen_h = Quartz.CGDisplayPixelsHigh(Quartz.CGMainDisplayID())
        return int(loc.x), int(screen_h - loc.y)
    return 0, 0


def capture_region(x: int, y: int, size: int = 400) -> tuple[str, dict] | None:
    """Capture a screenshot of a region around (x, y). Returns (filepath, metadata)."""
    half = size // 2
    rx = max(0, x - half)
    ry = max(0, y - half)

    now = datetime.now()
    day_dir = Path(config.db.data_dir) / "screenshots" / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    filepath = day_dir / f"{now.strftime('%H%M%S')}.jpg"

    try:
        if HAS_QUARTZ:
            region = Quartz.CGRectMake(rx, ry, size, size)
            image = Quartz.CGWindowListCreateImage(
                region,
                Quartz.kCGWindowListOptionOnScreenOnly,
                Quartz.kCGNullWindowID,
                Quartz.kCGWindowImageDefault,
            )
            if image:
                from Quartz import CGImageDestinationCreateWithURL, CGImageDestinationAddImage, CGImageDestinationFinalize
                from CoreFoundation import CFURLCreateWithFileSystemPath, kCFAllocatorDefault, kCFURLPOSIXPathStyle
                url = CFURLCreateWithFileSystemPath(
                    kCFAllocatorDefault, str(filepath), kCFURLPOSIXPathStyle, False
                )
                dest = CGImageDestinationCreateWithURL(url, "public.jpeg", 1, None)
                if dest:
                    options = {
                        "kCGImageDestinationLossyCompressionQuality": config.tracker.screenshot_quality / 100.0
                    }
                    CGImageDestinationAddImage(dest, image, options)
                    CGImageDestinationFinalize(dest)
        else:
            # Fallback to screencapture CLI
            subprocess.run(
                [
                    "screencapture", "-x", "-R",
                    f"{rx},{ry},{size},{size}",
                    "-t", "jpg",
                    str(filepath),
                ],
                capture_output=True, timeout=5,
            )
    except Exception as e:
        print(f"Screenshot failed: {e}")
        return None

    if not filepath.exists():
        return None

    return str(filepath), {
        "region_x": rx,
        "region_y": ry,
        "region_w": size,
        "region_h": size,
        "timestamp": time.time(),
    }


def cleanup_old_screenshots(max_age_days: int = 7):
    """Delete screenshots older than N days."""
    screenshots_dir = Path(config.db.data_dir) / "screenshots"
    if not screenshots_dir.exists():
        return
    cutoff = time.time() - (max_age_days * 86400)
    for day_dir in screenshots_dir.iterdir():
        if not day_dir.is_dir():
            continue
        try:
            # Parse directory name as date
            dir_time = datetime.strptime(day_dir.name, "%Y-%m-%d").timestamp()
            if dir_time < cutoff:
                for f in day_dir.iterdir():
                    f.unlink()
                day_dir.rmdir()
        except (ValueError, OSError):
            pass
