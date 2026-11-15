"""Shape B — one ReAct agent. Student work.

Use `lab8.runtime.run_react` with max_steps=8. `decide` may pick a read tool.
It must not call `issue_refund`. After the loop, the host validates the quote
and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.
"""

from __future__ import annotations

from lab8.schemas import RunResult
from lab8.shapes.common import not_implemented


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    del store_path, crash_at
    return not_implemented("single", claim_id, seed)
