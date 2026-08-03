"""
Domain service: şehir adı normalizasyonu.

Saf fonksiyon — I/O yok, bağımlılık yok (stdlib).

Neden var: ChromaDB metadata filtresi birebir string eşitliği yapar.
KB'de şehirler Title Case ("Tokyo"), kullanıcı ise ne yazarsa yazar.
Normalize edilmeden 'tokyo' hiçbir chunk bulamaz ve RAG sessizce kapanır.
"""

from __future__ import annotations

import unicodedata

# Türkçe nokta tuzağı: 'İ'.lower() 'i' + U+0307 (birleşen nokta) üretir,
# bu da 'i' ile eşleşmez. Noktalı/noktasız i harflerini casefold'dan ÖNCE
# sade 'i'ye indiriyoruz.
_I_VARIANTS = str.maketrans({"İ": "i", "I": "i", "ı": "i"})


def normalize_city(raw: str) -> str:
    """
    Şehir adını karşılaştırılabilir bir anahtara indirger.

    Hem ingestion (metadata yazarken) hem sorgu (filtre kurarken)
    aynı fonksiyondan geçmelidir.

    >>> normalize_city("Tokyo")
    'tokyo'
    >>> normalize_city("İstanbul")
    'istanbul'
    >>> normalize_city("  NEW   YORK ")
    'new york'
    """
    s = raw.translate(_I_VARIANTS)
    s = s.casefold()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(s.split())
