"""NeuroSage FastAPI backend — thin wrapper around the validated engine.

Loads model artifacts ONCE at startup (lifespan), exposes /health, /assess, /recommend.
All ML/business logic lives in engine.py. Persist data in Neon (added in Phase 2).
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .engine import Engine, DOM, WEAK_THRESHOLD

MODELS_DIR = os.getenv("MODELS_DIR", str(Path(__file__).resolve().parent.parent / "models"))
_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    _state["engine"] = Engine(MODELS_DIR)          # load artifacts once (free-tier rule)
    yield
    _state.clear()


app = FastAPI(title="NeuroSage API", version="0.1", lifespan=lifespan)

# CORS: allow the Vercel frontend + local dev. Set FRONTEND_ORIGINS (comma-separated) in prod.
_origins = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware, allow_origins=[o.strip() for o in _origins] or ["*"],
    allow_methods=["*"], allow_headers=["*"],
)


class AssessRequest(BaseModel):
    raw_tests: dict[str, Optional[float]] = Field(..., description="UDS v3 raw test scores, e.g. {'CRAFTVRS': 20, ...}")


class RecommendRequest(BaseModel):
    diagnosis_probabilities: dict[str, float] = Field(..., description="{'Alzheimer':.., 'Parkinson':.., 'Vascular':.., 'LBD':..}")
    domain_z: Optional[dict[str, Optional[float]]] = Field(None, description="5 domain z-scores (higher=healthier)")
    raw_tests: Optional[dict[str, Optional[float]]] = Field(None, description="UDS v3 raw scores (if domain_z not supplied)")
    age: Optional[float] = None
    education: Optional[float] = None
    sex: Optional[str] = Field(None, description="'M' or 'F'")
    top_k: int = 3


@app.get("/health")
def health():
    return {"status": "ok", "engine_loaded": "engine" in _state}


@app.post("/assess")
def assess(req: AssessRequest):
    eng: Engine = _state["engine"]
    dz = eng.tests_to_domain_z(req.raw_tests)
    weak = {d: (dz[d] is not None and dz[d] <= WEAK_THRESHOLD) for d in DOM}
    return {"domain_z": dz, "is_weak": weak, "threshold": WEAK_THRESHOLD}


@app.post("/recommend")
def recommend(req: RecommendRequest):
    eng: Engine = _state["engine"]
    dz = req.domain_z
    if dz is None:
        if not req.raw_tests:
            raise HTTPException(422, "Provide either domain_z or raw_tests.")
        dz = eng.tests_to_domain_z(req.raw_tests)
    dz = {d: dz.get(d) for d in DOM}
    try:
        return eng.recommend(req.diagnosis_probabilities, dz,
                             age=req.age, education=req.education, sex=req.sex, top_k=req.top_k)
    except ValueError as e:
        raise HTTPException(422, f"Invalid diagnosis probabilities: {e}")
