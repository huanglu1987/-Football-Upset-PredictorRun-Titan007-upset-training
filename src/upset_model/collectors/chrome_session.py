from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from upset_model.config import CHROME_APP_NAME, CHROME_SESSION_RAW_DIR, DEFAULT_CHROME_SOURCE_WAIT_SECONDS


@dataclass
class ChromeTabInfo:
    window_index: int
    tab_index: int
    active_tab_index: int
    url: str
    title: str


def run_osascript(script: str) -> str:
    completed = subprocess.run(
        ["osascript", "-"],
        input=script,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout).strip() or "osascript failed")
    return completed.stdout.strip()


def _escape_applescript(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def parse_tab_listing(raw_output: str) -> list[ChromeTabInfo]:
    tabs: list[ChromeTabInfo] = []
    for line in [line.strip() for line in raw_output.split(", ") if line.strip()]:
        left, url, title = line.split(" | ", 2)
        parts = {}
        for item in left.split(","):
            key, value = item.split("=", 1)
            parts[key] = int(value)
        tabs.append(
            ChromeTabInfo(
                window_index=parts["window"],
                tab_index=parts["tab"],
                active_tab_index=parts["active"],
                url=url,
                title=title,
            )
        )
    return tabs


def list_chrome_tabs() -> list[ChromeTabInfo]:
    script = f"""
tell application "{CHROME_APP_NAME}"
    set out to {{}}
    repeat with w from 1 to count of windows
        repeat with t from 1 to count of tabs of window w
            set end of out to ("window=" & w & ",tab=" & t & ",active=" & ((active tab index of window w) as text) & " | " & (URL of tab t of window w) & " | " & (title of tab t of window w))
        end repeat
    end repeat
    return out
end tell
"""
    output = run_osascript(script)
    return parse_tab_listing(output) if output else []


def get_active_tab() -> ChromeTabInfo:
    tabs = list_chrome_tabs()
    for tab in tabs:
        if tab.tab_index == tab.active_tab_index:
            return tab
    raise RuntimeError("No active Chrome tab found")


def open_view_source_for_url(url: str, window_index: int = 1) -> None:
    escaped = _escape_applescript(f"view-source:{url}")
    script = f"""
tell application "{CHROME_APP_NAME}"
    activate
    tell window {window_index}
        make new tab with properties {{URL:"{escaped}"}}
        set active tab index to (count of tabs)
    end tell
end tell
"""
    run_osascript(script)


def copy_active_tab_content_with_menu() -> None:
    script = f"""
tell application "{CHROME_APP_NAME}" to activate
delay 1
tell application "System Events"
    tell process "{CHROME_APP_NAME}"
        set frontmost to true
        click menu item "全选" of menu 1 of menu bar item "编辑" of menu bar 1
        delay 0.5
        click menu item "拷贝" of menu 1 of menu bar item "编辑" of menu bar 1
    end tell
end tell
"""
    run_osascript(script)


def read_clipboard_text() -> str:
    completed = subprocess.run(
        ["pbpaste"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout).strip() or "pbpaste failed")
    return completed.stdout


def clear_clipboard() -> None:
    subprocess.run(["pbcopy"], input="", text=True, capture_output=True, check=False)


def slugify_url(url: str) -> str:
    safe = quote(url, safe="")
    return safe.replace("%", "_")


def default_capture_path(url: str) -> Path:
    CHROME_SESSION_RAW_DIR.mkdir(parents=True, exist_ok=True)
    return CHROME_SESSION_RAW_DIR / f"{slugify_url(url)}.html"


def capture_current_tab_source(output_path: Path | None = None, wait_seconds: int = DEFAULT_CHROME_SOURCE_WAIT_SECONDS) -> Path:
    active_tab = get_active_tab()
    open_view_source_for_url(active_tab.url, window_index=active_tab.window_index)
    subprocess.run(["sleep", str(wait_seconds)], check=False)
    clear_clipboard()
    copy_active_tab_content_with_menu()
    subprocess.run(["sleep", "1"], check=False)
    content = read_clipboard_text()
    if not content.strip():
        raise RuntimeError("Clipboard is empty after copying Chrome source content")
    target = output_path or default_capture_path(active_tab.url)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target
