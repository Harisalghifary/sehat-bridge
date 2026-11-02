"""SATUSEHAT mock stub.

M0 only needs a health endpoint. M5 fills in OAuth2 and the FHIR resources.
"""

from fastapi import FastAPI

app = FastAPI(title="SATUSEHAT mock", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "mock"}


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "mock-satusehat", "docs": "/docs"}