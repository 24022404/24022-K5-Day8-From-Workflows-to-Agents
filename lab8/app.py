"""Runner shared by the CLI, benchmark, and smoke test."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lab8.config_loader import repo_path
from lab8.db import init_store, load_json, load_jsonl
from lab8.schemas import RunResult
from lab8.shapes import SHAPES

PUBLIC_WORLD = repo_path("data", "public_world_state.json")
PUBLIC_CLAIMS = repo_path("data", "public_claims.jsonl")


def prepare_store(
    store_path: str | Path,
    world_path: str | Path = PUBLIC_WORLD,
    claims_path: str | Path = PUBLIC_CLAIMS,
    extra_claims: list[dict[str, Any]] | None = None,
) -> None:
    world = load_json(world_path)
    claims = load_jsonl(claims_path)
    if extra_claims:
        claims = claims + extra_claims
    init_store(store_path, world, claims)


def run_shape(
    shape: str,
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    if shape not in SHAPES:
        raise SystemExit(f"unknown shape {shape!r}; choose from {', '.join(SHAPES)}")
    return SHAPES[shape](claim_id, seed=seed, store_path=str(store_path), crash_at=crash_at)
