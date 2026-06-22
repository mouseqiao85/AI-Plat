from __future__ import annotations

import re
import urllib.parse
import zipfile
from datetime import date, datetime
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any

import yaml

from app.knowledge.schemas import ObsidianParseResult, ParsedNote, ParsedWikilink

_SKIP_DIR_NAMES = {".obsidian", "_templates", ".git"}
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)
_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_WIKILINK_RE = re.compile(r"(!)?\[\[([^\]]+)\]\]")
_TAG_RE = re.compile(r"(?<![\w/])#([A-Za-z0-9_\-/一-鿿]+)")


_TAG_RE = re.compile(r"(?<![\w/])#([A-Za-z0-9_\-/\u4e00-\u9fff]+)")
_MOJIBAKE_HINT_RE = re.compile(r"[╔-╬░-▓│-┼]")


def _recover_zip_name(name: str, *, utf8_flag: bool = True) -> str:
    """Recover GBK/GB18030 zip entry names decoded as CP437 by zipfile."""
    if not _MOJIBAKE_HINT_RE.search(name):
        return name
    try:
        return name.encode("cp437").decode("gb18030")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return name


def _normalize_zip_path(name: str) -> str:
    normalized = name.replace("\\", "/").lstrip("/")
    path = PurePosixPath(normalized)
    if not normalized or normalized.endswith("/"):
        return ""
    if path.is_absolute() or any(part == ".." for part in path.parts):
        raise ValueError(f"zip entry escapes vault root: {name}")
    return str(path)


def _should_skip(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return any(part in _SKIP_DIR_NAMES or part.startswith(".") for part in parts)


def _is_markdown(path: str) -> bool:
    return path.lower().endswith((".md", ".markdown"))


def _split_frontmatter(content: str) -> tuple[dict[str, Any], str, str]:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    match = _FRONTMATTER_RE.match(normalized)
    if not match:
        return {}, normalized, ""
    raw = match.group(1)
    try:
        parsed = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        return {}, match.group(2), f"YAML frontmatter parse error: {exc}"
    if not isinstance(parsed, dict):
        return {}, match.group(2), f"frontmatter parsed as {type(parsed).__name__}, expected mapping"
    return parsed, match.group(2), ""


def _json_safe(value: Any) -> Any:
    """Convert YAML-loaded values into values accepted by JSON columns."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(_json_safe(key)): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.replace(",", " ").split() if part.strip()]
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, str):
                out.append(item.strip())
            elif item is not None:
                out.append(str(item).strip())
        return [item for item in out if item]
    return [str(value).strip()] if str(value).strip() else []


def _extract_tags(frontmatter: dict[str, Any], body: str) -> list[str]:
    tags = set()
    for raw in _coerce_list(frontmatter.get("tags") or frontmatter.get("tag")):
        tags.add(raw.lstrip("#").strip())
    for match in _TAG_RE.finditer(body):
        tags.add(match.group(1).strip().strip("/"))
    return sorted(tag for tag in tags if tag)


def _extract_wikilinks(body: str) -> tuple[list[ParsedWikilink], list[ParsedWikilink]]:
    links: list[ParsedWikilink] = []
    embeds: list[ParsedWikilink] = []
    for match in _WIKILINK_RE.finditer(body):
        raw_target = match.group(2).strip()
        if not raw_target:
            continue
        target_part, alias = raw_target, ""
        if "|" in raw_target:
            target_part, alias = raw_target.split("|", 1)
        heading = ""
        if "#" in target_part:
            target_part, heading = target_part.split("#", 1)
        link = ParsedWikilink(
            raw=match.group(0),
            target=target_part.strip(),
            alias=alias.strip(),
            heading=heading.strip(),
            embed=bool(match.group(1)),
        )
        if link.embed:
            embeds.append(link)
        else:
            links.append(link)
    return links, embeds


def _first_h1(body: str) -> str:
    match = _H1_RE.search(body)
    return match.group(1).strip() if match else ""


def _preview(body: str, limit: int = 240) -> str:
    text = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    text = re.sub(r"[#>*_`\[\]()]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _obsidian_uri(vault_name: str, path: str) -> str:
    file_path = str(PurePosixPath(path).with_suffix(""))
    return (
        "obsidian://open?"
        f"vault={urllib.parse.quote(vault_name)}"
        f"&file={urllib.parse.quote(file_path)}"
    )


def parse_obsidian_zip(content: bytes, *, vault_name: str, filename: str = "vault.zip") -> ObsidianParseResult:
    """Parse an Obsidian vault zip into note/tag/link structures without extracting to disk."""
    vault_name = vault_name.strip() or PurePosixPath(filename).stem or "Obsidian Vault"
    result = ObsidianParseResult(vault_name=vault_name)

    try:
        zf = zipfile.ZipFile(BytesIO(content), "r")
    except zipfile.BadZipFile as exc:
        raise ValueError("Invalid zip file") from exc

    with zf:
        for info in sorted(zf.infolist(), key=lambda item: item.filename):
            try:
                path = _normalize_zip_path(
                    _recover_zip_name(info.filename, utf8_flag=bool(info.flag_bits & 0x800))
                )
            except ValueError:
                raise
            if not path:
                continue
            if _should_skip(path):
                result.skipped.append({"path": path, "reason": "skipped_directory"})
                continue
            if not _is_markdown(path):
                result.skipped.append({"path": path, "reason": "not_markdown"})
                continue
            try:
                raw = zf.read(info)
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                result.errors.append({"path": path, "reason": "decode_error"})
                continue

            frontmatter, body, fm_error = _split_frontmatter(text)
            if fm_error:
                result.errors.append({"path": path, "reason": "frontmatter_error", "detail": fm_error})
            frontmatter = _json_safe(frontmatter)

            aliases = _coerce_list(frontmatter.get("aliases") or frontmatter.get("alias"))
            tags = _extract_tags(frontmatter, body)
            wikilinks, embeds = _extract_wikilinks(body)
            stem = PurePosixPath(path).stem
            title = str(frontmatter.get("title") or _first_h1(body) or stem).strip()

            result.notes.append(
                ParsedNote(
                    key=path,
                    path=path,
                    title=title,
                    body=body,
                    content_preview=_preview(body),
                    frontmatter=frontmatter,
                    aliases=aliases,
                    tags=tags,
                    wikilinks=wikilinks,
                    embeds=embeds,
                    uri=_obsidian_uri(vault_name, path),
                )
            )

    return result


def normalize_link_target(target: str) -> str:
    """Normalize a wikilink target for matching against imported note paths and titles."""
    value = target.strip().replace("\\", "/").strip("/")
    if value.lower().endswith((".md", ".markdown")):
        value = str(PurePosixPath(value).with_suffix(""))
    return value.lower()
