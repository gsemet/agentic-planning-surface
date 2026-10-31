"""Locking, output size, batch resolution, reports and transcript pricing."""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from cos import costs

SRC = Path(__file__).resolve().parents[1] / "src"


def test_concurrent_writers_lose_nothing(ready):
    env = {**os.environ, "PYTHONPATH": str(SRC)}

    def report(i):
        return subprocess.run([sys.executable, "-m", "cos", "report", "CR-101", "note", f"n{i}"],
                              cwd=ready, env=env, capture_output=True, text=True).returncode

    with ThreadPoolExecutor(12) as pool:
        assert set(pool.map(report, range(24))) == {0}
    d = json.loads((ready / ".agents/changes/batches/b1/batch.json").read_text())
    assert len(d["crs"][0]["notes"]) == 24
    events = (ready / ".agents/changes/batches/b1/events.jsonl").read_text().splitlines()
    assert sum(1 for e in events if json.loads(e)["kind"] == "report") == 24


def test_output_is_at_most_ten_lines(repo, cos):
    cos("setup")
    code, out, _ = cos("open", "big", *[f"Item {i}" for i in range(15)], "--no-worktrees")
    assert code == 0 and len(out) == 10 and out[-1].startswith("…")
    assert len(cos("status")[1]) == 10
    assert json.loads("\n".join(cos("status", "--json")[1]))["id"] == "big"


def test_batch_resolution(repo, cos, monkeypatch):
    cos("setup")
    cos("open", "one", "A", "--no-worktrees")
    cos("open", "two", "B", "--no-worktrees")
    assert cos("status")[1][0].startswith("two ")
    monkeypatch.setenv("COS_BATCH", "one")
    assert cos("status")[1][0].startswith("one ")
    assert cos("status", "--batch", "two")[1][0].startswith("two ")
    assert cos("report", "CR-102", "note", "x")[0] == 0  # found in `two` by CR id


def test_cr_numbers_are_unique_across_batches(repo, cos):
    cos("setup")
    cos("open", "one", "A", "B", "--no-worktrees")
    cos("open", "two", "C", "--no-worktrees")
    assert cos("status", "--batch", "two")[1][1].startswith("CR-103 ")


def test_open_from_a_backlog_file(repo, cos):
    cos("setup")
    item = repo / "backlog.md"
    item.write_text("# Fix the flaky upload\n\nDetails.\n")
    cos("open", "f1", f"@{item}", "--no-worktrees")
    d = json.loads((repo / ".agents/changes/batches/f1/batch.json").read_text())
    assert d["crs"][0]["title"] == "Fix the flaky upload"


def test_open_requires_setup_and_a_valid_id(repo, cos):
    assert cos("open", "x", "A")[0] == 2
    cos("setup")
    assert cos("open", "Bad Id", "A")[0] == 1


def test_reports_update_the_cr(ready, cos):
    cos("report", "CR-101", "pr-opened", "https://github.com/acme/demo/pull/3")
    cos("report", "CR-101", "ci-red", "lint")
    cos("report", "CR-101", "round-done", "--note", "r1 APPROVE")
    row = cos("status", "--notes")[1][1]
    assert row == "CR-101 queued r1 https://github.com/acme/demo/pull/3 ci red | round-done: r1 APPROVE"


def test_heartbeat(ready, cos):
    cos("foreman", "set", "local_x")
    cos("order", "pause")
    code, out, _ = cos("heartbeat", "--epoch", 1)
    assert out[0] == "heartbeat b1: 0 live, 1 orders pending"
    assert "heartbeat 0 min" in cos("status")[1][0]


def _assistant(mid, model, inp=0, w5=0, w1=0, read=0, out=0):
    return json.dumps({"type": "assistant", "message": {
        "id": mid, "model": model, "usage": {
            "input_tokens": inp, "cache_read_input_tokens": read, "output_tokens": out,
            "cache_creation": {"ephemeral_5m_input_tokens": w5,
                               "ephemeral_1h_input_tokens": w1}}}})


@pytest.mark.parametrize("model,tokens,usd", [
    ("claude-opus-5-5", dict(out=1_000_000), 20.0),
    ("claude-sonnet-5-5", dict(w1=1_000_000), 4.0),
    ("claude-haiku-5-5", dict(read=50_000, out=1_000), 0.0005 + 0.0005),
    ("claude-haiku-5-5", dict(read=200_000), 0.01),  # above 100k: 0.05 $/MTok
])
def test_pricing(tmp_path, model, tokens, usd):
    f = tmp_path / "t.jsonl"
    f.write_text(_assistant("m1", model, **tokens) + "\n" + _assistant("m1", model, **tokens))
    assert costs.usage(f)["usd"] == pytest.approx(usd)
    assert costs.usage(f)["calls"] == 1  # a message id is counted once


def test_cost_by_role_and_cr(ready, cos, tmp_path):
    cos("foreman", "set", "local_x")
    cos("foreman", "transcript", "uuid-1", "--epoch", 1)
    cos("event", "start")
    cos("agents", "set", "CR-101", "a1")
    main = costs.transcript_path(ready.resolve(), "uuid-1")
    sub = main.with_suffix("") / "subagents"
    sub.mkdir(parents=True)
    main.write_text(_assistant("f1", "claude-sonnet-5-5", out=100_000) + "\n")
    (sub / "agent-a1.jsonl").write_text(_assistant("d1", "claude-sonnet-5-5", out=50_000) + "\n")
    (sub / "agent-a1.meta.json").write_text(json.dumps({"agentType": "cr-driver"}))
    (sub / "agent-c9.jsonl").write_text(_assistant("c1", "claude-sonnet-5-5", out=10_000) + "\n")
    (sub / "agent-c9.meta.json").write_text(json.dumps({"agentType": "coder"}))
    code, out, _ = cos("cost", "--update")
    assert out[0] == "b1: $1.600 over 3 model calls"
    assert out[1:] == ["foreman: $1.000 (1 calls)", "cr-driver: $0.500 (1 calls)",
                       "coder: $0.100 (1 calls)"]
    assert cos("cost", "--by", "cr")[1][1:] == ["foreman: $1.000 (1 calls)",
                                                "CR-101: $0.500 (1 calls)",
                                                "other: $0.100 (1 calls)"]
    assert "spent $1.60" in cos("status")[1][0]


def test_cost_without_transcript_is_explained(ready, cos):
    code, _, err = cos("cost")
    assert code == 2 and "cos foreman transcript" in err
