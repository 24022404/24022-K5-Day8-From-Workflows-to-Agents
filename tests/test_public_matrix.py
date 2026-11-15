"""Student self-check for T01–T12. Excluded from the default pytest run.

    pytest -q -m student -o addopts=

Swarm is the reference and should pass. workflow, single, and orchestrator
stay red until the group implements them.
"""

from __future__ import annotations

import pytest

from lab8.db import connect, init_store
from lab8.durability import InjectedCrash
from lab8.metrics import trial_pass
from lab8.shapes import SHAPES
from tests.conftest import BY_ID, CLAIMS, WORLD

SHAPES_UNDER_TEST = ["workflow", "single", "orchestrator", "swarm"]


def _store(tmp_path, name: str):
    path = tmp_path / name
    init_store(path, WORLD, CLAIMS)
    return path


@pytest.mark.student
@pytest.mark.parametrize("shape", SHAPES_UNDER_TEST)
@pytest.mark.parametrize("claim_id", [f"C-{i:03d}" for i in range(1, 11)])
@pytest.mark.parametrize("seed", [11, 22, 33, 44, 55])
def test_public_cases_t01_through_t10(tmp_path, shape, claim_id, seed):
    store = _store(tmp_path, f"{shape}-{claim_id}-{seed}.sqlite")
    result = SHAPES[shape](claim_id, seed=seed, store_path=str(store))
    conn = connect(store)
    try:
        passed, reason = trial_pass(result.as_dict(), BY_ID[claim_id]["expected"], conn)
    finally:
        conn.close()
    assert passed, reason


@pytest.mark.student
@pytest.mark.parametrize("shape", SHAPES_UNDER_TEST)
def test_t11_retry_keeps_one_refund(tmp_path, shape):
    store = _store(tmp_path, f"{shape}-t11.sqlite")
    first = SHAPES[shape]("C-011", seed=11, store_path=str(store))
    second = SHAPES[shape]("C-011", seed=11, store_path=str(store))
    conn = connect(store)
    try:
        passed, reason = trial_pass(second.as_dict(), BY_ID["C-011"]["expected"], conn)
        count = conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = 'C-011'").fetchone()["n"]
    finally:
        conn.close()
    assert first.status == "resolved"
    assert passed, reason
    assert count == 1


@pytest.mark.student
@pytest.mark.parametrize("shape", SHAPES_UNDER_TEST)
def test_t12_crash_before_checkpoint_does_not_double_pay(tmp_path, shape):
    store = _store(tmp_path, f"{shape}-t12.sqlite")
    try:
        SHAPES[shape](
            "C-012",
            seed=11,
            store_path=str(store),
            crash_at="after_effect_before_checkpoint",
        )
    except InjectedCrash:
        pass
    result = SHAPES[shape]("C-012", seed=11, store_path=str(store))
    conn = connect(store)
    try:
        passed, reason = trial_pass(result.as_dict(), BY_ID["C-012"]["expected"], conn)
        count = conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = 'C-012'").fetchone()["n"]
    finally:
        conn.close()
    assert passed, reason
    assert count == 1
