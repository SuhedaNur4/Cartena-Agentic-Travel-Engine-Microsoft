"""normalize_city — şehir eşleştirmesi kullanıcının yazımına takılmamalı."""

import pytest

from backend.domain.services.city import normalize_city


class TestBasicNormalization:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Tokyo", "tokyo"),
            ("tokyo", "tokyo"),
            ("TOKYO", "tokyo"),
            ("  Tokyo  ", "tokyo"),
            ("New York", "new york"),
            ("new york", "new york"),
            ("NEW YORK", "new york"),
            ("New   York", "new york"),
        ],
    )
    def test_case_and_whitespace(self, raw, expected):
        assert normalize_city(raw) == expected


class TestTurkishDottedI:
    """
    Python'da 'İ'.lower() -> 'i' + U+0307 (birleşen nokta).
    Naif casefold, Türkçe klavyeyle yazılan İstanbul'u ıskalar.
    """

    @pytest.mark.parametrize(
        "raw", ["İstanbul", "Istanbul", "ISTANBUL", "istanbul", "ıstanbul"]
    )
    def test_all_istanbul_variants_collapse(self, raw):
        assert normalize_city(raw) == "istanbul"

    def test_no_combining_marks_survive(self):
        assert "̇" not in normalize_city("İstanbul")


class TestIdempotence:
    def test_normalizing_twice_is_stable(self):
        once = normalize_city("İSTANBUL")
        assert normalize_city(once) == once
