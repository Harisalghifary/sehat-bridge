"""Unit-level guarantees for the adapter boundary and secret handling."""

from __future__ import annotations

import inspect
import uuid

import pytest
from app.integrations.satusehat.crypto import InvalidToken, SecretBox
from app.integrations.satusehat.live import LiveAdapter
from app.integrations.satusehat.mock import MockAdapter, deterministic_id, deterministic_token
from app.integrations.satusehat.port import (
    SatusehatPort,
    join_url,
    retryable_status,
)
from app.integrations.satusehat.service import build_drafts, redact_body


def test_both_adapters_satisfy_the_protocol() -> None:
    mock = MockAdapter("http://localhost:8090/fhir-r4/v1")
    live = LiveAdapter("https://example.test/fhir-r4/v1")
    assert isinstance(mock, SatusehatPort)
    assert isinstance(live, SatusehatPort)

    for name in (
        "issue_token",
        "put_organization",
        "put_patient",
        "get_resource",
    ):
        assert inspect.signature(getattr(MockAdapter, name)) == inspect.signature(
            getattr(LiveAdapter, name)
        )


def test_mock_ids_are_deterministic() -> None:
    assert deterministic_id("Organization", "1000000001") == deterministic_id(
        "Organization", "1000000001"
    )
    assert deterministic_id("Organization", "1000000001") != deterministic_id(
        "Organization", "1000000002"
    )
    assert deterministic_token("client-a") == deterministic_token("client-a")


def test_join_url_preserves_failure_injection_query() -> None:
    injected = "http://localhost:8090/fhir-r4/v1?fail=500"
    assert (
        join_url(injected, "Organization")
        == "http://localhost:8090/fhir-r4/v1/Organization?fail=500"
    )


def test_retryable_status_classification() -> None:
    assert retryable_status(500) is True
    assert retryable_status(503) is True
    assert retryable_status(429) is True
    assert retryable_status(408) is True
    assert retryable_status(400) is False
    assert retryable_status(404) is False


def test_secret_box_roundtrip_and_wrong_key() -> None:
    box = SecretBox("key-one")
    ciphertext = box.encrypt("client-secret-value")
    assert b"client-secret-value" not in ciphertext
    assert SecretBox("key-one").decrypt(ciphertext) == "client-secret-value"
    with pytest.raises(InvalidToken):
        SecretBox("key-two").decrypt(ciphertext)


def test_redaction_strips_identifiers() -> None:
    body = {
        "resourceType": "OperationOutcome",
        "identifier": [{"value": "1000000001"}],
        "name": "Rumah Sakit",
        "nested": {"nik": "123", "safe": "ok"},
    }
    redacted = redact_body(body)
    assert redacted["identifier"] == "[redacted]"
    assert redacted["name"] == "[redacted]"
    assert redacted["nested"]["nik"] == "[redacted]"
    assert redacted["nested"]["safe"] == "ok"


def test_build_drafts_from_snapshot() -> None:
    local_id = uuid.uuid4()
    org = build_drafts(
        {
            "resourceType": "Organization",
            "identifier": "1000000001",
            "name": "Klinik Sehat",
        },
        local_id,
    )
    assert org.identifier == "1000000001"
    assert org.name == "Klinik Sehat"

    patient = build_drafts(
        {
            "resourceType": "Patient",
            "identifier": "sb-demo-abc",
            "display_name": "Pasien Demo",
        },
        local_id,
    )
    assert patient.identifier == "sb-demo-abc"
