import pytest
from app.db.tenant_context import InvalidSlug, schema_name


def test_schema_name_maps_hyphens() -> None:
    assert schema_name("klinik-sehat") == "tenant_klinik_sehat"


def test_schema_name_is_prefixed() -> None:
    assert schema_name("acme") == "tenant_acme"


@pytest.mark.parametrize("slug", ["A", "Klinik", "ab", "a b", "-abc", "a;drop"])
def test_schema_name_rejects_bad_slugs(slug: str) -> None:
    if slug == "ab":
        assert schema_name(slug) == "tenant_ab"
    else:
        with pytest.raises(InvalidSlug):
            schema_name(slug)
