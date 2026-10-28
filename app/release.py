"""Single internal version and synthetic-tested model capability matrix.

This matrix encodes supported application request modes, not live vendor SLA
or proof a specific Groq catalog entry remains available.
"""
import os
from fastapi import HTTPException
VERSION="8.1.0"
RELEASE_STAGE="research-pilot-not-regulated-production"
DEFAULT_GROQ_MODEL="openai/gpt-oss-120b"
MODEL_CAPABILITIES={
    "openai/gpt-oss-120b":{"json_schema":True,"browser_search":True},
    "openai/gpt-oss-20b":{"json_schema":True,"browser_search":True},
}
def configured_groq_model():
    model=os.getenv("GROQ_MODEL",DEFAULT_GROQ_MODEL).strip()
    if model not in MODEL_CAPABILITIES:
        raise HTTPException(409,"Unsupported GROQ_MODEL for this release. Select an explicitly QA-listed GPT-OSS model; offline local mode remains available.")
    return model

def model_manifest():
    model=os.getenv("GROQ_MODEL",DEFAULT_GROQ_MODEL).strip()
    return {"configuredModel":model,"supported":model in MODEL_CAPABILITIES,
        "qaAllowedModels":list(MODEL_CAPABILITIES),
        "modes":MODEL_CAPABILITIES.get(model,{}),
        "source":"local synthetic contract fixtures",
        "liveProviderCatalogChecked":False,"vendorModelAvailabilityVerified":False,
        "fallback":"Local saved-source analysis; no silent remote model substitution."}
