"""Same claims, same seeds, same prices, separate database per trial.

python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm \
    --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from lab8.app import prepare_store, run_shape
from lab8.config_loader import as_of, pricing, repo_path
from lab8.db import connect, load_json, load_jsonl
from lab8.metrics import summarize, trial_pass


def _steps(trace_path: str) -> int:
    path = Path(trace_path)
    if not path.exists():
        return 0
    return int(json.loads(path.read_text(encoding="utf-8")).get("steps") or 0)


def run_benchmark(
    *,
    world: dict[str, Any],
    claims: list[dict[str, Any]],
    shapes: list[str],
    seeds: list[int],
    labels: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Score shapes. When `labels` is set, claim['expected'] is ignored."""
    trials: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="lab8-bench-") as tmp:
        for shape in shapes:
            for claim in claims:
                claim_id = claim["claim_id"]
                expected = (labels or {}).get(claim_id)
                if expected is None:
                    if labels is not None:
                        raise KeyError(f"missing label for {claim_id}")
                    expected = claim["expected"]
                for seed in seeds:
                    store = Path(tmp) / f"{shape}-{claim_id}-{seed}.sqlite"
                    prepare_from_memory(store, world, claims)
                    result = run_shape(shape, claim_id, seed=seed, store_path=str(store))
                    payload = result.as_dict()
                    conn = connect(store)
                    try:
                        passed, reason = trial_pass(payload, expected, conn)
                    finally:
                        conn.close()
                    row = {
                        "shape": shape,
                        "claim_id": claim_id,
                        "seed": seed,
                        "passed": passed,
                        "reason": reason,
                        "cost_estimate": payload["cost_estimate"],
                        "steps": _steps(payload["trace_path"]),
                        "model_calls": payload["model_calls"],
                        "tool_calls": payload["tool_calls"],
                        "run_id": payload["run_id"],
                        "status": payload["status"],
                    }
                    trials.append(row)
                    details.append(row)
    prices = pricing()
    return {
        "controlled_variables": {
            "as_of": as_of(),
            "seeds": seeds,
            "claim_ids": [claim["claim_id"] for claim in claims],
            "pricing": {
                "simulated": True,
                "currency": prices["currency"],
                "input_per_1k_tokens_vnd": prices["input_per_1k_tokens_vnd"],
                "output_per_1k_tokens_vnd": prices["output_per_1k_tokens_vnd"],
                "tool_call_vnd": prices["tool_call_vnd"],
            },
            "model_backend": "MockLLM",
            "latency": "unavailable",
            "isolation": "fresh_sqlite_per_trial",
        },
        "by_shape": summarize(trials),
        "trials": details,
    }


def prepare_from_memory(store: Path, world: dict[str, Any], claims: list[dict[str, Any]]) -> None:
    from lab8.db import init_store

    init_store(store, world, claims)


def render_table(report: dict[str, Any]) -> str:
    lines = [
        f"{'shape':<14} {'pass':>8} {'pass^5':>8} {'var':>10} {'min':>6} {'max':>6} {'cost/success':>14} {'steps':>8}",
        "-" * 82,
    ]
    for shape, stats in report["by_shape"].items():
        cost = stats["cost_per_success_vnd"]
        cost_s = "-" if cost is None else f"{cost:.2f}"
        lines.append(
            f"{shape:<14} {stats['pass_rate']:>8.3f} {stats['pass_5']:>8.3f} "
            f"{stats['seed_variance']:>10.6f} {stats['seed_min']:>6.3f} {stats['seed_max']:>6.3f} "
            f"{cost_s:>14} {stats['mean_steps']:>8.2f}"
        )
    lines.append("cost is simulated VND, not an API bill. latency: unavailable")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark shapes on the same claims and seeds")
    parser.add_argument("--shapes", required=True, help="comma-separated: workflow,single,orchestrator,swarm")
    parser.add_argument("--cases", default=str(repo_path("data", "public_claims.jsonl")))
    parser.add_argument("--world", default=str(repo_path("data", "public_world_state.json")))
    parser.add_argument("--seeds", default="11,22,33,44,55")
    parser.add_argument("--out", required=True)
    parser.add_argument("--labels", default=None, help="JSON map claim_id -> expected. Ignores inline expected.")
    args = parser.parse_args(argv)
    shapes = [part.strip() for part in args.shapes.split(",") if part.strip()]
    seeds = [int(part) for part in args.seeds.split(",") if part.strip()]
    world = load_json(args.world)
    claims = load_jsonl(args.cases)
    labels = load_json(args.labels) if args.labels else None
    report = run_benchmark(world=world, claims=claims, shapes=shapes, seeds=seeds, labels=labels)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(render_table(report))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
