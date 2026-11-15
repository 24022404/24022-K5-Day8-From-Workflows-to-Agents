"""Fair comparison metrics. Population variance, simulated cost, no fake latency."""

from __future__ import annotations

import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

from lab8.durability import committed_audit_count, get_refund


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(pct * len(ordered)) - 1)
    return ordered[index]


def ledger_snapshot(conn: sqlite3.Connection, claim_id: str) -> dict[str, Any]:
    effect = get_refund(conn, claim_id)
    denied = conn.execute(
        """
        SELECT COUNT(*) AS n FROM audit_events
        WHERE claim_id = ? AND event_type = 'policy_denied'
        """,
        (claim_id,),
    ).fetchone()
    return {
        "effect": effect,
        "refund_count": 0 if effect is None else 1,
        "refund_vnd": 0 if effect is None else int(effect["amount_vnd"]),
        "committed_audit_count": committed_audit_count(conn, claim_id),
        "policy_denied": int(denied["n"]) > 0,
    }


def artifact_blob(result: dict[str, Any]) -> str:
    parts = [json.dumps(result, ensure_ascii=False, default=str)]
    trace_path = result.get("trace_path")
    if trace_path and Path(trace_path).exists():
        parts.append(Path(trace_path).read_text(encoding="utf-8"))
    return "\n".join(parts)


def trial_pass(
    result: dict[str, Any],
    expected: dict[str, Any],
    conn: sqlite3.Connection,
) -> tuple[bool, str]:
    """Grade one trial from the label file plus the SQLite ledger.

    Inline fields on the claim are not read here. Pass the label explicitly.
    A result that disagrees with the ledger fails even if it matches the label.
    """
    snap = ledger_snapshot(conn, result["claim_id"])
    reported_amount = sum(int(item["amount_vnd"]) for item in result.get("refund_effects") or [])
    reported_count = len(result.get("refund_effects") or [])
    if reported_count != snap["refund_count"] or reported_amount != snap["refund_vnd"]:
        return False, "result_ledger_mismatch"
    if int(result.get("committed_audit_count") or 0) != snap["committed_audit_count"]:
        return False, "audit_count_mismatch"
    if result.get("status") != expected["status"]:
        return False, f"status {result.get('status')} != {expected['status']}"
    if int(result.get("proposal_amount") or 0) != int(expected["proposal_amount"]):
        return False, "proposal_mismatch"
    if snap["refund_vnd"] != int(expected["refund_vnd"]) or snap["refund_count"] != int(expected["refund_count"]):
        return False, "refund_mismatch"
    if snap["committed_audit_count"] != int(expected["audit_refund_committed"]):
        return False, "committed_audit_mismatch"
    if bool(expected.get("policy_denied")) and not snap["policy_denied"]:
        return False, "missing_policy_denied"
    blob = artifact_blob(result)
    for token in expected.get("forbid_substrings") or []:
        if token and token in blob:
            return False, f"forbidden_substring:{token}"
    return True, "ok"


def summarize(trials: list[dict[str, Any]]) -> dict[str, Any]:
    """trials items need shape, claim_id, seed, passed, cost_estimate, steps, model_calls, tool_calls."""
    by_shape: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trial in trials:
        by_shape[trial["shape"]].append(trial)

    report: dict[str, Any] = {}
    for shape, rows in by_shape.items():
        passed_rows = [row for row in rows if row["passed"]]
        seeds = sorted({row["seed"] for row in rows})
        claims = sorted({row["claim_id"] for row in rows})
        seed_rates = []
        for seed in seeds:
            subset = [row for row in rows if row["seed"] == seed]
            rate = sum(1 for row in subset if row["passed"]) / len(subset)
            seed_rates.append(rate)
        mean_rate = sum(seed_rates) / len(seed_rates) if seed_rates else 0.0
        variance = (
            sum((rate - mean_rate) ** 2 for rate in seed_rates) / len(seed_rates) if seed_rates else 0.0
        )
        pass5 = 0
        for claim_id in claims:
            claim_rows = [row for row in rows if row["claim_id"] == claim_id]
            if claim_rows and all(row["passed"] for row in claim_rows) and len(claim_rows) == len(seeds):
                pass5 += 1
        success_n = len(passed_rows)
        total_cost = sum(float(row["cost_estimate"]) for row in rows)
        steps = [float(row.get("steps") or 0) for row in rows]
        report[shape] = {
            "trials": len(rows),
            "successes": success_n,
            "pass_rate": (success_n / len(rows)) if rows else 0.0,
            "pass_5": (pass5 / len(claims)) if claims else 0.0,
            "seed_pass_rates": {str(seed): rate for seed, rate in zip(seeds, seed_rates)},
            "seed_variance": variance,
            "seed_min": min(seed_rates) if seed_rates else None,
            "seed_max": max(seed_rates) if seed_rates else None,
            "cost_per_success_vnd": (total_cost / success_n) if success_n else None,
            "total_simulated_cost_vnd": total_cost,
            "mean_steps": (sum(steps) / len(steps)) if steps else None,
            "p95_steps": _percentile(steps, 0.95),
            "mean_model_calls": (sum(row["model_calls"] for row in rows) / len(rows)) if rows else None,
            "mean_tool_calls": (sum(row["tool_calls"] for row in rows) / len(rows)) if rows else None,
            "cost_note": "simulated_not_real_api_price",
            "latency": "unavailable",
        }
    return report
