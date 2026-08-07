import pytest
from backend.infrastructure.knowledge_base.resolver import DestinationResolver

def test_destination_resolver_canonical_name():
    resolver = DestinationResolver()
    
    res1 = resolver.resolve("Istanbul, Turkey")
    assert res1.canonical_name == "Istanbul"
    
    res2 = resolver.resolve("   TOKYO   ")
    assert res2.canonical_name == "Tokyo"
    
    res3 = resolver.resolve("Eskişehir")
    assert res3.canonical_name == "Eskişehir"
