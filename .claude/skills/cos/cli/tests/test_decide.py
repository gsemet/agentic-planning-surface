"""The Foreman's decision table, driven through `cos event` and `cos order`."""
import json
from pathlib import Path


def batch(repo, name="b1"):
    return json.loads((repo / ".agents/changes/batches" / name / "batch.json").read_text())


def status_of(repo, cr, name="b1"):
    return next(c for c in batch(repo, name)["crs"] if c["id"] == cr)["status"]


def test_open_creates_crs_branches_and_worktrees(ready, cos):
    d = batch(ready)
    assert [c["id"] for c in d["crs"]] == ["CR-101", "CR-102", "CR-103"]
    for c in d["crs"]:
        assert Path(c["worktree"]).is_dir()
        assert c["branch"].startswith(f"cos/b1/{c['id'].lower()}-")
    assert (ready / ".agents/changes/batches/b1/brief.md").exists()
    assert (ready / ".agents/changes/batches/b1/crs/CR-101/task.md").read_text() == "Fix login\n"


def test_start_fills_slots(ready, cos):
    code, out, _ = cos("event", "start")
    assert out == ["spawn CR-101", "spawn CR-102"]
    assert status_of(ready, "CR-103") == "queued"
    assert cos("event", "start")[1] == ["none"]  # slots full


def test_ready_hand_back_frees_a_slot(ready, cos):
    cos("event", "start")
    code, out, _ = cos("event", "hand-back-ready", "CR-101", "https://github.com/acme/demo/pull/7")
    assert out == ["spawn CR-103", "ask-cos ready CR-101 https://github.com/acme/demo/pull/7"]
    assert status_of(ready, "CR-101") == "ready"


def test_anomaly_after_hand_back_resumes_with_a_new_driver(ready, cos):
    cos("event", "start")
    cos("event", "hand-back-ready", "CR-101")
    assert cos("event", "anomaly", "CR-101", "CI red on lint")[1] == \
        ["spawn CR-101 resume round: CI red on lint"]
    assert cos("event", "anomaly", "CR-101", "still red")[1] == ["message CR-101 round still red"]


def test_round_limit_blocks(ready, cos):
    cos("event", "start")
    for _ in range(3):
        cos("report", "CR-101", "round-done")
    code, out, _ = cos("event", "anomaly", "CR-101", "flaky")
    assert out[0].startswith("ask-cos blocked CR-101 round limit (3)")
    assert out[1] == "spawn CR-103"


def test_lost_driver_resumes_twice_then_blocks(ready, cos):
    cos("event", "start")
    assert cos("event", "driver-done", "CR-101")[1] == ["spawn CR-101 resume"]
    assert cos("event", "driver-lost", "CR-101")[1] == ["spawn CR-101 resume"]
    out = cos("event", "driver-lost", "CR-101")[1]
    assert out[0].startswith("ask-cos blocked CR-101") and out[1] == "spawn CR-103"


def test_driver_done_after_hand_back_is_quiet(ready, cos):
    cos("event", "start")
    cos("event", "hand-back-ready", "CR-101")
    assert cos("event", "driver-done", "CR-101")[1] == ["none"]


def test_orders_have_ids_and_are_idempotent(ready, cos):
    cos("event", "start")
    code, out, _ = cos("order", "drop", "CR-103")
    assert out == ["[cos→foreman] order O-1 drop CR-103"]
    assert cos("event", "--order", "O-1")[1] == ["ok O-1 drop CR-103"]
    assert cos("event", "--order", "O-1")[1] == ["ok O-1 already done"]
    assert status_of(ready, "CR-103") == "cancelled"


def test_drop_of_a_live_cr_asks_for_a_cancel(ready, cos):
    cos("event", "start")
    cos("order", "drop", "CR-101")
    assert cos("event", "--order", "O-1")[1] == ["cancel CR-101", "ok O-1 drop CR-101"]


def test_order_add_creates_a_cr_with_a_worktree(ready, cos):
    cos("event", "start")
    cos("order", "add", "--note", "Rate limit the API")
    out = cos("event", "--order", "O-1")[1]
    assert out == ["ok O-1 add CR-104"]
    c = batch(ready)["crs"][-1]
    assert c["title"] == "Rate limit the API" and Path(c["worktree"]).is_dir()


def test_pause_and_resume(ready, cos):
    cos("order", "pause")
    cos("event", "--order", "O-1")
    assert cos("event", "start")[1] == ["none"]
    cos("order", "resume")
    assert cos("event", "--order", "O-2")[1] == ["ok O-2 resume", "spawn CR-101", "spawn CR-102"]


def test_first_moves_a_cr_to_the_top(ready, cos):
    cos("order", "first", "CR-103")
    assert cos("event", "--order", "O-1")[1] == \
        ["ok O-1 first CR-103", "spawn CR-103", "spawn CR-101"]


def test_all_merged_lands_and_land_is_refused_while_live(ready, cos):
    cos("event", "start")
    code, out, err = cos("land")
    assert code == 2 and "live ['CR-101', 'CR-102']" in err
    for cr in ("CR-101", "CR-102"):
        cos("event", "hand-back-ready", cr)
    cos("event", "hand-back-ready", "CR-103")
    code, _, err = cos("land")
    assert code == 2 and "not merged ['CR-101', 'CR-102', 'CR-103']" in err
    for i, cr in enumerate(("CR-101", "CR-102", "CR-103"), 1):
        cos("order", "merged", cr)
        out = cos("event", "--order", f"O-{i}")[1]
    assert out == ["ok O-3 merged CR-103", "land"]
    code, out, _ = cos("land")
    assert code == 0 and out[0] == "landed b1: cleaned 3 worktrees"
    assert not Path(batch(ready)["crs"][0]["worktree"]).exists()
    assert cos("event", "tick", "--batch", "b1")[1] == ["none landed"]


def test_stale_foreman_epoch_is_refused(ready, cos):
    cos("foreman", "set", "local_aaa")
    cos("foreman", "set", "local_bbb")
    code, _, err = cos("event", "start", "--epoch", 1)
    assert code == 3 and "stale Foreman" in err
    assert cos("event", "start", "--epoch", 2)[0] == 0
    assert cos("foreman", "get")[1] == ["local_bbb epoch 2"]


def test_qa_cr_goes_through_its_qa_driver(repo, cos):
    cos("setup")
    cos("open", "q1", "Checkout flow", "--qa", "all", "--slots", 1)
    cos("event", "start")
    assert cos("event", "hand-back-ready", "CR-101")[1] == ["spawn qa:CR-101"]
    assert cos("event", "qa-done", "CR-101", "2 findings")[1] == ["none"]
    cos("event", "anomaly", "CR-101", "fix the 2 QA findings")
    assert cos("event", "hand-back-ready", "CR-101")[1] == ["spawn qa:CR-101"]
    assert cos("event", "qa-done", "CR-101", "0")[1] == ["ask-cos ready CR-101 no-pr"]


def test_stack_mode_starts_then_messages_the_stack_driver(repo, cos):
    cos("setup")
    cos("open", "s1", "Schema", "API", "--stack", "--slots", 2)
    cos("event", "start")
    assert cos("event", "hand-back-ready", "CR-101")[1] == ["none"]
    out = cos("event", "hand-back-ready", "CR-102")[1]
    assert out == ["spawn stack", "ask-cos stack-ready CR-101=no-pr CR-102=no-pr"]
    cos("order", "change", "CR-101", "--note", "rename the column")
    cos("event", "--order", "O-1")
    cos("event", "start")
    out = cos("event", "hand-back-ready", "CR-101")[1]
    assert out[0] == "message stack restack"
    cos("event", "driver-done", "stack")
    assert batch(repo, "s1")["stack_live"] is False


def test_budget_stops_spawning_and_asks_once(repo, cos):
    cos("setup")
    cos("open", "m1", "A", "B", "C", "--slots", 1, "--budget", 1)
    cos("event", "start")
    d_path = repo / ".agents/changes/batches/m1/batch.json"
    d = json.loads(d_path.read_text())
    d["spent_usd"] = 1.5
    d_path.write_text(json.dumps(d))
    out = cos("event", "hand-back-ready", "CR-101")[1]
    assert out[0] == "ask-cos budget 1.50/1.0"
    assert cos("event", "tick")[1] == ["none"]


def test_tick_pings_silent_drivers(ready, cos):
    cos("event", "start")
    p = ready / ".agents/changes/batches/b1/batch.json"
    d = json.loads(p.read_text())
    d["crs"][0]["updated"] = "2020-01-01T00:00:00Z"
    p.write_text(json.dumps(d))
    out = cos("event", "tick")[1]
    assert out[0].startswith("message CR-101 ping")


def test_unknown_event_is_a_usage_error(ready, cos):
    code, _, err = cos("event", "explode", "CR-101")
    assert code == 1 and "unknown event kind" in err
