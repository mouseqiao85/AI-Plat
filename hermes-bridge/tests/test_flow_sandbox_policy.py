from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

_test_dir = os.path.dirname(os.path.abspath(__file__))
_bridge_dir = os.path.join(_test_dir, "..")
sys.path.insert(0, _bridge_dir)

from bridge import db
from bridge.flows import create as create_flow, get as get_flow, update as update_flow
from bridge.sandbox_policy import HIGH_SECURITY_SANDBOX_POLICY


@pytest.fixture(autouse=True)
def _temp_db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    os.environ["ORCHESTRATOR_DB"] = tmp.name
    db.DB_PATH = Path(tmp.name)
    db._conn = None
    db.init()
    yield
    db._conn.close()
    db._conn = None
    os.unlink(tmp.name)


def test_create_flow_without_policy_returns_default_policy():
    flow = create_flow(name="default policy", flow_type="sequential", role_ids=["role-A"])

    assert flow.sandbox_policy["security_level"] == "local_dev"
    assert flow.sandbox_policy["filesystem"]["mode"] == "workspace"
    assert get_flow(flow.id).sandbox_policy == flow.sandbox_policy


def test_create_flow_with_high_policy_persists_normalized_policy():
    flow = create_flow(
        name="high policy",
        flow_type="parallel",
        role_ids=["role-A", "role-B"],
        sandbox_policy=HIGH_SECURITY_SANDBOX_POLICY,
    )

    loaded = get_flow(flow.id)
    assert loaded.sandbox_policy["security_level"] == "high"
    assert loaded.sandbox_policy["filesystem"]["mode"] == "read_only"
    assert loaded.sandbox_policy["network"]["allow_all"] is False


def test_update_flow_replaces_policy():
    flow = create_flow(name="policy update", flow_type="sequential", role_ids=["role-A"])

    updated = update_flow(flow.id, sandbox_policy={"filesystem": {"mode": "read_only"}})

    assert updated.sandbox_policy["security_level"] == "local_dev"
    assert updated.sandbox_policy["filesystem"]["mode"] == "read_only"
    assert updated.sandbox_policy["filesystem"]["write_paths"] == []


def test_invalid_policy_raises_value_error():
    with pytest.raises(ValueError, match="security_level"):
        create_flow(
            name="invalid policy",
            flow_type="sequential",
            role_ids=["role-A"],
            sandbox_policy={"security_level": "unsafe"},
        )


def test_empty_policy_json_in_existing_row_is_readable():
    flow = create_flow(name="empty policy", flow_type="sequential", role_ids=["role-A"])
    with db.cursor() as cur:
        cur.execute("UPDATE dialog_flows SET sandbox_policy = '' WHERE id = ?", (flow.id,))

    loaded = get_flow(flow.id)

    assert loaded.sandbox_policy["security_level"] == "local_dev"
