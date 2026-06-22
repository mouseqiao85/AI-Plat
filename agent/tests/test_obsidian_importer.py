from __future__ import annotations

import zipfile
from io import BytesIO

import pytest

from app.knowledge.obsidian_importer import _recover_zip_name, normalize_link_target, parse_obsidian_zip


def _zip(entries: dict[str, str | bytes]) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in entries.items():
            data = content if isinstance(content, bytes) else content.encode("utf-8")
            zf.writestr(name, data)
    return buf.getvalue()


def test_parse_obsidian_frontmatter_tags_aliases_and_links():
    content = _zip({
        "Index.md": """---
title: Agent Platform
tags:
  - csm
  - knowledge/graph
aliases:
  - AP
---

# Ignored H1

Linked to [[Projects/CSM-27|CSM 27]] and [[Unresolved Concept]].
Embedded ![[diagram.png]].

#agent-platform
""",
        "Projects/CSM-27.md": "# CSM-27\n\nGraph storage model.",
        ".obsidian/app.json": "{}",
        "_templates/template.md": "# Template",
        "assets/diagram.png": b"png",
    })

    result = parse_obsidian_zip(content, vault_name="Vault", filename="vault.zip")

    assert [note.path for note in result.notes] == ["Index.md", "Projects/CSM-27.md"]
    index = result.notes[0]
    assert index.title == "Agent Platform"
    assert index.aliases == ["AP"]
    assert index.tags == ["agent-platform", "csm", "knowledge/graph"]
    assert [link.target for link in index.wikilinks] == ["Projects/CSM-27", "Unresolved Concept"]
    assert index.wikilinks[0].alias == "CSM 27"
    assert [embed.target for embed in index.embeds] == ["diagram.png"]
    assert index.uri == "obsidian://open?vault=Vault&file=Index"
    assert any(item["path"].startswith(".obsidian") for item in result.skipped)
    assert any(item["path"].startswith("_templates") for item in result.skipped)


def test_parse_obsidian_title_fallback_order():
    content = _zip({
        "Frontmatter.md": "---\ntitle: From Frontmatter\n---\n# From H1",
        "Heading.md": "# From H1\nBody",
        "No Heading.md": "Body only",
    })

    result = parse_obsidian_zip(content, vault_name="Vault", filename="vault.zip")

    titles = {note.path: note.title for note in result.notes}
    assert titles["Frontmatter.md"] == "From Frontmatter"
    assert titles["Heading.md"] == "From H1"
    assert titles["No Heading.md"] == "No Heading"


def test_parse_obsidian_frontmatter_dates_are_json_safe_strings():
    content = _zip({
        "Dated.md": """---
title: Dated Note
created: 2026-06-05
nested:
  due: 2026-06-06
list:
  - 2026-06-07
---
Body
""",
    })

    result = parse_obsidian_zip(content, vault_name="Vault", filename="vault.zip")

    frontmatter = result.notes[0].frontmatter
    assert frontmatter["created"] == "2026-06-05"
    assert frontmatter["nested"]["due"] == "2026-06-06"
    assert frontmatter["list"] == ["2026-06-07"]


def test_recover_zip_name_handles_gb18030_names_decoded_as_cp437():
    mojibake = "90_模板".encode("gb18030").decode("cp437")

    assert mojibake == "90_─ú░σ"
    assert _recover_zip_name(mojibake, utf8_flag=False) == "90_模板"
    assert _recover_zip_name("90_模板", utf8_flag=True) == "90_模板"


def test_parse_obsidian_recovers_gb18030_zip_entry_names():
    content = _zip({
        "90_模板/示例.md".encode("gb18030").decode("cp437"): "# 示例\n#中文标签",
    })

    result = parse_obsidian_zip(content, vault_name="Vault", filename="vault.zip")

    assert result.notes[0].path == "90_模板/示例.md"
    assert result.notes[0].title == "示例"
    assert result.notes[0].tags == ["中文标签"]


def test_parse_obsidian_rejects_zip_slip():
    content = _zip({"../escape.md": "# Escape"})

    with pytest.raises(ValueError, match="escapes vault root"):
        parse_obsidian_zip(content, vault_name="Vault", filename="vault.zip")


def test_normalize_link_target_handles_extensions_and_headings():
    assert normalize_link_target("Folder/Note.md") == "folder/note"
    assert normalize_link_target(" Folder\\Note ") == "folder/note"
