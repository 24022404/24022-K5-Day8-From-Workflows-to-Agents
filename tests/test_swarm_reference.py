import pytest

from lab8.db import connect
from lab8.metrics import trial_pass
from lab8.shapes.swarm_reference import run_claim
from tests.conftest import BY_ID


@pytest.mark.parametrize(
    "claim_id",
    ["C-001", "C-002", "C-003", "C-004", "C-005", "C-006", "C-007", "C-008", "C-009", "C-010"],
)
def test_reference_swarm_passes_published_traps(public_db, claim_id):
    result = run_claim(claim_id, seed=11, store_path=str(public_db))
    conn = connect(public_db)
    try:
        passed, reason = trial_pass(result.as_dict(), BY_ID[claim_id]["expected"], conn)
    finally:
        conn.close()
    assert passed, reason
