from __future__ import annotations

import json
import ssl
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from upset_model.config import PROBE_REPORT_DIR, expand_probe_urls

DEFAULT_TIMEOUT_SECONDS = 15
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"


@dataclass
class HttpProbeResult:
    url: str
    method: str
    ok: bool
    status_code: int | None
    final_url: str | None
    content_type: str | None
    error: str | None
    snippet: str | None


@dataclass
class ProbeReport:
    created_at_utc: str
    urls: list[str]
    results: list[HttpProbeResult]


def _read_snippet(body: bytes, limit: int = 240) -> str:
    return body.decode("utf-8", errors="replace").replace("\n", " ")[:limit]


def probe_with_urllib(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> HttpProbeResult:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    ssl_context = ssl.create_default_context()

    try:
        with urlopen(request, timeout=timeout, context=ssl_context) as response:
            body = response.read(512)
            status_code = getattr(response, "status", None)
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type")
            return HttpProbeResult(
                url=url,
                method="urllib",
                ok=True,
                status_code=status_code,
                final_url=final_url,
                content_type=content_type,
                error=None,
                snippet=_read_snippet(body),
            )
    except HTTPError as exc:
        return HttpProbeResult(
            url=url,
            method="urllib",
            ok=False,
            status_code=exc.code,
            final_url=url,
            content_type=exc.headers.get("Content-Type"),
            error=f"HTTPError: {exc}",
            snippet=None,
        )
    except URLError as exc:
        return HttpProbeResult(
            url=url,
            method="urllib",
            ok=False,
            status_code=None,
            final_url=None,
            content_type=None,
            error=f"URLError: {exc}",
            snippet=None,
        )
    except Exception as exc:  # pragma: no cover - keep raw diagnostic details
        return HttpProbeResult(
            url=url,
            method="urllib",
            ok=False,
            status_code=None,
            final_url=None,
            content_type=None,
            error=f"{type(exc).__name__}: {exc}",
            snippet=None,
        )


def probe_with_curl(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> HttpProbeResult:
    command = [
        "curl",
        "-I",
        "-L",
        "--max-time",
        str(timeout),
        "-A",
        USER_AGENT,
        url,
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    status_code = None
    content_type = None
    for line in lines:
        if line.upper().startswith("HTTP/"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                status_code = int(parts[1])
        if line.lower().startswith("content-type:"):
            content_type = line.split(":", 1)[1].strip()

    return HttpProbeResult(
        url=url,
        method="curl_head",
        ok=completed.returncode == 0 and status_code is not None and status_code < 400,
        status_code=status_code,
        final_url=None,
        content_type=content_type,
        error=None if completed.returncode == 0 else output.strip() or f"curl exited with {completed.returncode}",
        snippet="\n".join(lines[:8]) if lines else None,
    )


def run_probe(include_http: bool = False) -> ProbeReport:
    urls = expand_probe_urls(include_http=include_http)
    results: list[HttpProbeResult] = []
    for url in urls:
        results.append(probe_with_urllib(url))
        results.append(probe_with_curl(url))
    return ProbeReport(
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        urls=urls,
        results=results,
    )


def save_report(report: ProbeReport, output_path: Path | None = None) -> Path:
    PROBE_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    target = output_path or PROBE_REPORT_DIR / f"win007_probe_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return target
