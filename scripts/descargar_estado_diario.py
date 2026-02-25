#!/usr/bin/env python3
"""Descarga el PDF más reciente del Estado Diario de Marcas de INAPI."""

from __future__ import annotations

import re
import sys
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urljoin
from urllib.request import Request, urlopen

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]

BASE_URL = "https://tramites.inapi.cl/EstadosDiariosMarcas"
USER_AGENT = "Mozilla/5.0 (compatible; INAPI-EstadoDiario-Bot/1.0)"

ROOT_DIR = Path(__file__).resolve().parents[1]
DOWNLOADS_DIR = ROOT_DIR / "downloads"
LOGS_DIR = ROOT_DIR / "logs"
LOG_FILE = LOGS_DIR / "descarga.log"


class DownloadError(Exception):
    """Error controlado para fallas de descarga."""


def now_in_chile() -> datetime:
    if ZoneInfo is not None:
        return datetime.now(ZoneInfo("America/Santiago"))
    return datetime.now()


def log_result(success: bool, message: str) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = now_in_chile().isoformat(timespec="seconds")
    status = "OK" if success else "ERROR"
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] {status} - {message}\n")


def fetch_page(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def extract_pdf_links(html: str, base_url: str) -> list[str]:
    pattern = re.compile(r'href\s*=\s*["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']', re.IGNORECASE)
    links = [urljoin(base_url, unescape(match.group(1).strip())) for match in pattern.finditer(html)]

    deduped: list[str] = []
    seen: set[str] = set()
    for link in links:
        if link not in seen:
            seen.add(link)
            deduped.append(link)
    return deduped


def parse_date_from_text(text: str) -> Optional[datetime]:
    decoded = unquote(text)
    patterns = [
        (r"(20\d{2})[-_/](\d{1,2})[-_/](\d{1,2})", "ymd_sep"),
        (r"(\d{1,2})[-_/](\d{1,2})[-_/](20\d{2})", "dmy_sep"),
        (r"(20\d{2})(\d{2})(\d{2})", "ymd_compact"),
    ]

    for pattern, kind in patterns:
        match = re.search(pattern, decoded)
        if not match:
            continue

        try:
            if kind == "ymd_sep":
                year, month, day = map(int, match.groups())
            elif kind == "dmy_sep":
                day, month, year = map(int, match.groups())
            else:
                year, month, day = map(int, match.groups())
            return datetime(year, month, day)
        except ValueError:
            continue

    return None


def get_last_modified(url: str) -> Optional[datetime]:
    request = Request(url, headers={"User-Agent": USER_AGENT}, method="HEAD")
    try:
        with urlopen(request, timeout=20) as response:
            last_modified = response.headers.get("Last-Modified")
    except Exception:
        return None

    if not last_modified:
        return None

    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S GMT"):
        try:
            return datetime.strptime(last_modified, fmt)
        except ValueError:
            continue
    return None


def select_latest_pdf(urls: list[str]) -> tuple[str, datetime]:
    if not urls:
        raise DownloadError("No se encontraron enlaces PDF en la página.")

    dated_candidates: list[tuple[str, datetime]] = []
    for url in urls:
        detected_date = parse_date_from_text(url)
        if detected_date:
            dated_candidates.append((url, detected_date))

    if dated_candidates:
        return max(dated_candidates, key=lambda item: item[1])

    modified_candidates: list[tuple[str, datetime]] = []
    for url in urls:
        modified = get_last_modified(url)
        if modified:
            modified_candidates.append((url, modified))

    if modified_candidates:
        return max(modified_candidates, key=lambda item: item[1])

    return urls[0], now_in_chile()


def download_pdf(url: str, target_path: Path) -> None:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=60) as response:
        content = response.read()

    if not content.startswith(b"%PDF"):
        raise DownloadError("El archivo descargado no parece ser un PDF válido.")

    target_path.write_bytes(content)


def main() -> int:
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        html = fetch_page(BASE_URL)
        pdf_links = extract_pdf_links(html, BASE_URL)
        selected_url, selected_date = select_latest_pdf(pdf_links)

        output_name = f"INAPI_EstadoDiario_Marcas_{selected_date.strftime('%Y-%m-%d')}.pdf"
        output_path = DOWNLOADS_DIR / output_name

        download_pdf(selected_url, output_path)

        log_result(True, f"Descarga exitosa: {selected_url} -> {output_path.name}")
        print(f"Descarga completada: {output_path}")
        return 0
    except Exception as exc:
        log_result(False, str(exc))
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
