"""requirements.txt gerçekten import edilen paketleri beyan ediyor mu?"""

import pathlib
import re

REQS = pathlib.Path(__file__).parents[3] / "requirements.txt"


def declared_packages() -> set[str]:
    names = set()
    for line in REQS.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        name = re.split(r"[><=\[]", line)[0].strip().lower()
        if name:
            names.add(name)
    return names


def test_sentence_transformers_is_declared():
    """LocalEmbeddingAdapter onu import ediyor; beyan edilmezse kurulum eksik kalır."""
    assert "sentence-transformers" in declared_packages()


def test_foundry_local_sdk_is_not_declared():
    """Hiçbir yerde import edilmiyor — ölü bağımlılık."""
    assert "foundry-local-sdk" not in declared_packages()
