"""Approval gate. Reads autonomy_policy.yaml. Does not mint approvals."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from lab8.config_loader import as_of, load_yaml


@dataclass
class AuthDecision:
    ok: bool
    reason: str
    amount_vnd: int
    approved_vnd: int
    approval_id: str | None


def authorize(
    conn: sqlite3.Connection,
    claim_id: str,
    proposed_vnd: int,
    *,
    paid_vnd: int,
) -> AuthDecision:
    policy = load_yaml("config/autonomy_policy.yaml")
    refund = policy["refund"]
    today = as_of()
    if not refund["require_approval_event"]:
        raise RuntimeError("lab policy requires an approval event")

    row = conn.execute(
        "SELECT * FROM approvals WHERE claim_id = ?",
        (claim_id,),
    ).fetchone()
    if row is None:
        return AuthDecision(False, "missing_approval", 0, 0, None)
    if refund["reject_non_valid_status"] and row["status"] != "valid":
        return AuthDecision(False, f"approval_{row['status']}", 0, int(row["approved_vnd"]), row["approval_id"])
    if refund["reject_expired"] and str(row["expires_at"]) < today:
        return AuthDecision(False, "approval_expired", 0, int(row["approved_vnd"]), row["approval_id"])
    if int(row["approved_vnd"]) <= 0 or int(proposed_vnd) <= 0:
        return AuthDecision(False, "non_positive_amount", 0, int(row["approved_vnd"]), row["approval_id"])

    amount = int(proposed_vnd)
    if refund["cap_at_approved_amount"]:
        amount = min(amount, int(row["approved_vnd"]))
    if refund["cap_at_paid_amount"]:
        amount = min(amount, int(paid_vnd))
    if amount <= 0:
        return AuthDecision(False, "capped_to_zero", 0, int(row["approved_vnd"]), row["approval_id"])
    return AuthDecision(True, "ok", amount, int(row["approved_vnd"]), row["approval_id"])
