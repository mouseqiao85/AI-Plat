"""Create and run the remote "04 产品匹配度分析" multi-agent flow."""
from __future__ import annotations

import json
import sys
import time

from ssh_config import DeployConfigError, DeployConnectionError, RemoteCommandError, connect, load_deploy_config, run_remote


PROMPT_TEMPLATE = """你正在执行垂类智能体产品交付流程中的独立阶段：04. 产品匹配度分析。

阶段职责：评估现有产品/平台能力与需求的匹配度、差距和改造范围。

用户输入：
{input}

上游材料 / 相关流程输出：
{prior}

输出要求：
- 基于当前 skill / 角色职责完成产品匹配度分析，不要泛泛而谈。
- 输出匹配结论、能力差距、改造范围、风险和下一阶段输入。
- 使用结构化 Markdown。
"""

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass


def shq(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def run(
    client,
    command: str,
    *,
    label: str,
    timeout: int = 120,
    check: bool = False,
    print_output: bool = True,
    max_output_chars: int = 4000,
):
    return run_remote(
        client,
        command,
        timeout=timeout,
        label=label,
        check=check,
        print_output=print_output,
        max_output_chars=max_output_chars,
    )


def curl_json(method: str, path: str, payload: dict | None = None, *, timeout: int = 30) -> str:
    body = ""
    if payload is not None:
        raw = json.dumps(payload, ensure_ascii=False)
        body = f" -H 'Content-Type: application/json' -d {shq(raw)}"
    return f"curl -fsS --max-time {timeout} -X {method} http://127.0.0.1:8002/api/v2{path}{body}"


def run_summary_command(run_id: int) -> str:
    script = f"""
import json, sqlite3
db='/home/admin/.agent-platform/orchestrator.db.root'
conn=sqlite3.connect(db)
conn.row_factory=sqlite3.Row
run=conn.execute('select * from flow_runs where id=?', ({run_id},)).fetchone()
if run is None:
    raise SystemExit('run not found')
outputs=json.loads(run['outputs'] or '[]')
messages=conn.execute('select type, status, role_id, payload from collaboration_messages where run_id=? order by seq', ({run_id},)).fetchall()
summary={{
  'id': run['id'],
  'flow_id': run['flow_id'],
  'status': run['status'],
  'error': run['error'] or '',
  'finished_at': run['finished_at'],
  'output_count': len(outputs),
  'outputs': [
    {{'role_id': o.get('role_id'), 'error': o.get('error'), 'latency_ms': o.get('latency_ms'), 'content_preview': (o.get('content') or '')[:240]}}
    for o in outputs
  ],
  'message_count': len(messages),
  'message_types': sorted(set(row['type'] for row in messages)),
  'messages': [
    {{'type': row['type'], 'status': row['status'], 'role_id': row['role_id'], 'payload': json.loads(row['payload'] or '{{}}')}}
    for row in messages[-12:]
  ],
}}
print(json.dumps(summary, ensure_ascii=False))
"""
    return "/home/admin/agent-platform/agent/.venv/bin/python - <<'PY'\n" + script + "PY"


def main() -> int:
    try:
        config = load_deploy_config(default_host="8.215.63.182", default_user="root")
        print(f"=== Connecting to {config.endpoint} via {config.auth_method} auth ===")
        client = connect(config)
    except (DeployConfigError, DeployConnectionError) as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        return 1

    flow_id = None
    try:
        print("=== Select product matching roles ===")
        selected = ["brave-search", "plan-design-review", "design-review", "devex-review"]
        print(f"[ok] selected roles: {', '.join(selected)}")

        payload = {
            "name": f"04. 产品匹配度分析 smoke {int(time.time())}",
            "description": "评估现有产品/平台能力与需求的匹配度、差距和改造范围。",
            "flow_type": "competitive",
            "role_ids": selected,
            "scenario_id": "",
            "prompt_template": PROMPT_TEMPLATE,
            "model": "deepseek-v4-pro",
            "owner_id": 0,
            "flow_spec": {
                "preset": "product-delivery",
                "stage_index": 4,
                "stage_name": "产品匹配度分析",
                "original_flow_type": "competitive",
                "smoke_test": True,
            },
        }
        print("=== Create flow ===")
        _, out, _ = run(client, curl_json("POST", "/flows", payload), label="create-flow", timeout=30, check=True, print_output=False)
        flow = json.loads(out, strict=False)
        flow_id = flow["id"]
        print(f"[ok] created flow_id={flow_id} type={flow.get('flow_type')} roles={flow.get('role_ids')}")

        message = (
            "客户是一家区域制造业集团，想把当前 agent-platform 用于售前线索分级、"
            "产品方案推荐、报价材料生成和交付风险评估。请评估平台现有多智能体、"
            "知识图谱/GraphRAG、技能市场和流程编排能力与该需求的匹配度。"
        )
        print("=== Start run ===")
        _, run_raw, _ = run(client, curl_json("POST", f"/flows/{flow_id}/runs", {"message": message}, timeout=30), label="start-run", timeout=45, check=True, print_output=False)
        run_data = json.loads(run_raw, strict=False)
        run_id = run_data["run_id"]
        print(f"[ok] started run_id={run_id}")

        terminal = None
        for _ in range(36):
            time.sleep(10)
            _, current_raw, _ = run(client, run_summary_command(run_id), label="poll-run", timeout=20, check=True, print_output=False, max_output_chars=20000)
            current = json.loads(current_raw, strict=False)
            status = current.get("status")
            print(f"[poll] status={status} outputs={current.get('output_count')} messages={current.get('message_count')}")
            if status in {"succeeded", "failed", "cancelled"}:
                terminal = current
                break
        if terminal is None:
            raise RuntimeError(f"run {run_id} did not finish within polling window")

        summary = {
            "flow_id": flow_id,
            "run_id": run_id,
            "status": terminal.get("status"),
            "error": terminal.get("error"),
            "output_count": terminal.get("output_count"),
            "message_count": terminal.get("message_count"),
            "message_types": terminal.get("message_types"),
            "outputs": terminal.get("outputs"),
            "recent_messages": terminal.get("messages"),
        }
        print("=== PRODUCT MATCHING FLOW RESULT ===")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if terminal.get("status") != "succeeded":
            raise RuntimeError(f"flow run did not succeed: {terminal.get('status')} {terminal.get('error')}")
        if not terminal.get("message_count"):
            raise RuntimeError("no collaboration messages recorded")
        return 0
    except (RemoteCommandError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        try:
            run(client, "tail -160 /tmp/hermes-bridge.log 2>&1 || true", label="hermes-log", timeout=30)
        except Exception:
            pass
        return 2
    finally:
        if flow_id is not None:
            try:
                run(client, f"curl -fsS --max-time 10 -X DELETE http://127.0.0.1:8002/api/v2/flows/{flow_id}", label="delete-flow", timeout=20, print_output=False)
                print(f"[ok] deleted flow_id={flow_id}")
            except Exception as exc:
                print(f"[warn] failed to delete flow {flow_id}: {exc}", file=sys.stderr)
        try:
            client.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
