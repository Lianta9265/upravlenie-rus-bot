import sys
from pathlib import Path
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src"))
from core import find_entry, render_entry, stats

assert find_entry("заведующий")["lemma"] == "заведующий"
assert find_entry("заведующая кафедрой")["lemma"] == "заведующий"
assert find_entry("как правильно: оплатить проезд или оплатить за проезд?")["lemma"] == "оплатить"
assert find_entry("командовать над подчинёнными")["lemma"] == "командовать"
assert find_entry("несуществующее_слово") is None
assert stats()["entries"] >= 40
print("OK", stats())
