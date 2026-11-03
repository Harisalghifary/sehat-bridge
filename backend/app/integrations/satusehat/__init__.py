"""SATUSEHAT integration: the only package allowed to speak FHIR."""

from app.integrations.satusehat.factory import build_adapter
from app.integrations.satusehat.port import SatusehatPort

__all__ = ["SatusehatPort", "build_adapter"]
