from pathlib import Path
import json
import os
import re
import tempfile

BUNDLED_DATA_DIR = Path(__file__).resolve().parent / "data"


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _load_json(name: str):
    """Load persistent data when valid, otherwise restore it from the bundle."""
    bundled_path = BUNDLED_DATA_DIR / name
    bundled_data = _read_json(bundled_path)
    configured_dir = os.getenv("DATA_DIR")
    if not configured_dir:
        return bundled_data

    persistent_path = Path(configured_dir) / name
    try:
        persistent_data = _read_json(persistent_path)
        if type(persistent_data) is not type(bundled_data):
            raise ValueError("Unexpected JSON root type")
        return persistent_data
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        temporary_path = None
        try:
            persistent_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=persistent_path.parent,
                prefix=f".{name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(bundled_path.read_bytes())
                temporary_path = Path(temporary.name)
            temporary_path.replace(persistent_path)
        except OSError:
            if temporary_path:
                temporary_path.unlink(missing_ok=True)
        return bundled_data


ENTRIES = _load_json("entries.json")
ALIASES = _load_json("aliases.json")
SOURCES = _load_json("sources.json")

BY_LEMMA = {e["lemma"]: e for e in ENTRIES}


def normalize(text: str) -> str:
    text = (text or "").strip().lower().replace("ё", "е")
    text = text.replace("—", " ").replace("–", " ")
    text = re.sub(r"[^\w\- ]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def find_entry(query: str):
    q = normalize(query)
    if not q:
        return None

    if q in ALIASES:
        return BY_LEMMA.get(ALIASES[q])

    tokens = q.split()
    # Сначала точные леммы, затем словоформы-алиасы.
    for token in tokens:
        if token in BY_LEMMA:
            return BY_LEMMA[token]
    for token in tokens:
        lemma = ALIASES.get(token)
        if lemma:
            return BY_LEMMA.get(lemma)
    return None


def source_title(source_id: str) -> str:
    src = SOURCES.get(source_id, {})
    return src.get("title", source_id)


def render_entry(entry: dict) -> str:
    if not entry:
        return "В проверенной локальной базе точной статьи пока нет."

    out = [f"СЛОВО: {entry['lemma']}"]
    senses = entry.get("senses", [])

    for i, s in enumerate(senses, 1):
        if len(senses) > 1:
            out.append(f"\n{i}. {s.get('meaning', '').strip()}")
        elif s.get("meaning"):
            out.append(f"\nЗНАЧЕНИЕ: {s['meaning']}")

        out.append("УПРАВЛЕНИЕ:")
        for g in s.get("government", []):
            line = f"• {g.get('question','')} — {g.get('pattern','')}"
            if g.get("note"):
                line += f" ({g['note']})"
            out.append(line)

        if s.get("examples"):
            out.append("ПРИМЕРЫ:")
            out.extend(f"• {x}" for x in s["examples"])

        if s.get("collocations"):
            out.append("СОЧЕТАЕМОСТЬ:")
            out.extend(f"• {x}" for x in s["collocations"])

        if s.get("wrong"):
            out.append("НЕПРАВИЛЬНО:")
            out.extend(f"• {x}" for x in s["wrong"])

        if s.get("comment"):
            out.append(f"КОММЕНТАРИЙ: {s['comment']}")

    source_ids = []
    for s in senses:
        for sid in s.get("sources", []):
            if sid not in source_ids:
                source_ids.append(sid)

    if source_ids:
        out.append("\nИСТОЧНИК:")
        out.extend(f"• {source_title(sid)}" for sid in source_ids)

    out.append("✓ Проверено по локальной словарной базе.")
    return "\n".join(out)


def render_sources() -> str:
    out = ["ПОДКЛЮЧЁННЫЕ ИСТОЧНИКИ:"]
    for src in SOURCES.values():
        out.append(f"• {src['title']} — {src['publisher']}")
        out.append(src["url"])
    return "\n".join(out)


def stats() -> dict:
    return {
        "entries": len(ENTRIES),
        "aliases": len(ALIASES),
    }
