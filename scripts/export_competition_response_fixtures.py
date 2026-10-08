"""从真实本地 API 导出三类响应，保留完整内容用于前端联调。"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tests/fixtures/competition/retrieve_responses.json"


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(f"拒绝覆盖已有响应样例：{OUTPUT}")

    os.environ["DACHUANG_RETRIEVE_MODE"] = "mock"
    os.environ["DACHUANG_LOCAL_MOCK_ACK"] = "1"
    os.environ["DACHUANG_GENERATOR_MODE"] = "template"
    os.environ.pop("DACHUANG_VECTOR_BACKEND", None)
    sys.path.insert(0, str(ROOT))

    from fastapi.testclient import TestClient
    from src.api.main import app

    cases = [
        ("approved", "遵义会议后的思想政治教育有哪些作用？"),
        ("needs_review", "抗日战争时期党的干部教育为什么重要？"),
        ("blocked", "量子芯片如何纠错？"),
    ]
    samples = []
    with TestClient(app) as client:
        for expected_status, query in cases:
            request = {"query": query, "target_grade": "university"}
            response = client.post("/retrieve", json=request)
            response.raise_for_status()
            body = response.json()
            assert body["final_decision"]["status"] == expected_status
            assert body["final_decision"]["can_output"] == (
                expected_status == "approved"
            )
            samples.append({"request": request, "response": body})

    source_commit = subprocess.check_output(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()
    payload = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_commit": source_commit,
            "endpoint": "/retrieve",
            "transport": "FastAPI TestClient / ASGI（进程内真实后端）",
            "retrieve_mode": "mock",
            "local_mock_ack": "1",
            "vector_backend": "unset（本地轻量召回）",
            "generator_mode": "template",
            "limitations": "本地检索与模板证据摘要；非在线模型，非浏览器端到端验收。",
        },
        "samples": samples,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(f"已导出 {len(samples)} 类完整响应：{OUTPUT}")


if __name__ == "__main__":
    main()
