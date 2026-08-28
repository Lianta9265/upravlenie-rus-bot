from pathlib import Path
import json
import re

BASE = Path(__file__).resolve().parents[1]
ENTRIES = json.loads((BASE / "data" / "entries.json").read_text(encoding="utf-8"))
ALIASES = json.loads((BASE / "data" / "aliases.json").read_text(encoding="utf-8"))
SOURCES = json.loads((BASE / "data" / "sources.json").read_text(encoding="utf-8"))

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
