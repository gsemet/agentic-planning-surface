import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ai-autosync-git.py"
SPEC = importlib.util.spec_from_file_location("ai_autosync_git", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
autosync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(autosync)


@unittest.skipUnless(shutil.which("git"), "git is required")
class AutosyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.remote = self.base / "remote.git"
        self.root = self.base / "checkout"
        self.run_git(self.base, "init", "--bare", str(self.remote))
        self.run_git(self.base, "init", "-b", "main", str(self.root))
        self.run_git(self.root, "config", "user.email", "test@example.invalid")
        self.run_git(self.root, "config", "user.name", "Test User")
        self.run_git(self.root, "config", "core.autocrlf", "false")
        (self.root / "notes.txt").write_text("initial\n", encoding="utf-8")
        self.run_git(self.root, "add", "notes.txt")
        self.run_git(self.root, "commit", "-m", "initial")
        self.run_git(self.root, "remote", "add", "origin", str(self.remote))
        self.run_git(self.root, "push", "-u", "origin", "main")
        _, self.state = autosync.repository(self.root)
        self.state.mkdir(parents=True)

    def run_git(self, cwd, *args, check=True):
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )

    def sync_without_scanner_or_lfs(self):
        original_command = autosync.command

        def fake_command(args, cwd, **kwargs):
            if args[:3] == ["git", "lfs", "push"]:
                return subprocess.CompletedProcess(args, 0, "", "")
            return original_command(args, cwd, **kwargs)

        with mock.patch.object(autosync, "scan_pending", return_value=None), mock.patch.object(
            autosync, "command", side_effect=fake_command
        ):
            autosync.synchronize(self.root, self.state)

    def test_commits_and_pushes_tracked_and_new_files(self):
        (self.root / "notes.txt").write_text("changed\n", encoding="utf-8")
        (self.root / "new.txt").write_text("new\n", encoding="utf-8")
        self.sync_without_scanner_or_lfs()
        local = self.run_git(self.root, "rev-parse", "HEAD").stdout.strip()
        remote = self.run_git(self.root, "--git-dir", str(self.remote), "rev-parse", "refs/heads/main").stdout.strip()
        self.assertEqual(local, remote)
        self.assertEqual(self.run_git(self.root, "status", "--porcelain").stdout, "")
        self.assertEqual(autosync.read_json(self.state / "status.json")["state"], "synced")
        message = self.run_git(self.root, "log", "-1", "--format=%B").stdout
        self.assertEqual(
            message,
            f"chore: autosync repository changes\n\nAuthored-By: Ai-Autosync-git {autosync.__version__}\n\n",
        )

    def test_existing_staged_changes_need_explicit_approval(self):
        (self.root / "notes.txt").write_text("staged\n", encoding="utf-8")
        self.run_git(self.root, "add", "notes.txt")
        (self.root / "notes.txt").write_text("unstaged\n", encoding="utf-8")
        before = self.run_git(self.root, "diff", "--cached").stdout
        self.assertEqual(autosync.run_once(self.root, self.state), 1)
        self.assertEqual(self.run_git(self.root, "diff", "--cached").stdout, before)
        current = autosync.read_json(self.state / "status.json")
        autosync.approve(self.state, current["incident"])
        self.sync_without_scanner_or_lfs()
        self.assertEqual(self.run_git(self.root, "show", "HEAD:notes.txt").stdout, "staged\n")
        self.assertEqual((self.root / "notes.txt").read_text(), "unstaged\n")

    def test_index_lock_is_not_removed_if_owned_by_another_process(self):
        lock = self.root / ".git" / "index.lock"
        lock.write_text("external", encoding="utf-8")
        with self.assertRaises(autosync.SyncError):
            autosync.create_commit(self.root, self.state)
        self.assertEqual(lock.read_text(), "external")

    def test_remote_changes_are_not_integrated_over_local_edits(self):
        other = self.base / "other"
        self.run_git(self.base, "clone", "-b", "main", str(self.remote), str(other))
        self.run_git(other, "config", "user.email", "test@example.invalid")
        self.run_git(other, "config", "user.name", "Other User")
        (other / "notes.txt").write_text("remote\n", encoding="utf-8")
        self.run_git(other, "commit", "-am", "remote change")
        self.run_git(other, "push")
        (self.root / "notes.txt").write_text("local\n", encoding="utf-8")
        with self.assertRaisesRegex(autosync.SyncError, "agent integration"):
            self.sync_without_scanner_or_lfs()
        self.assertEqual((self.root / "notes.txt").read_text(), "local\n")
        self.assertEqual(self.run_git(self.root, "show", "HEAD:notes.txt").stdout, "local\n")

    def test_attributes_renormalize_crlf_to_lf_in_git(self):
        (self.root / ".gitattributes").write_text("*.txt text eol=lf\n", encoding="utf-8")
        (self.root / "notes.txt").write_bytes(b"first\r\nsecond\r\n")
        self.sync_without_scanner_or_lfs()
        blob = subprocess.check_output(["git", "show", "HEAD:notes.txt"], cwd=self.root)
        self.assertEqual(blob, b"first\nsecond\n")
        self.assertEqual((self.root / "notes.txt").read_bytes(), b"first\r\nsecond\r\n")

    def test_missing_scanner_blocks_push_after_local_commit(self):
        (self.root / "notes.txt").write_text("pending\n", encoding="utf-8")
        previous = self.run_git(self.root, "--git-dir", str(self.remote), "rev-parse", "refs/heads/main").stdout.strip()
        original_command = autosync.command

        def no_scanner(args, cwd, **kwargs):
            if args[0] == "gitleaks":
                raise autosync.SyncError("Required executable is unavailable: gitleaks")
            return original_command(args, cwd, **kwargs)

        with mock.patch.object(autosync, "command", side_effect=no_scanner):
            self.assertEqual(autosync.run_once(self.root, self.state), 1)
        self.assertEqual(
            self.run_git(self.root, "--git-dir", str(self.remote), "rev-parse", "refs/heads/main").stdout.strip(),
            previous,
        )
        self.assertEqual(self.run_git(self.root, "show", "HEAD:notes.txt").stdout, "pending\n")

    def test_lfs_failure_prevents_git_push(self):
        (self.root / "notes.txt").write_text("pending\n", encoding="utf-8")
        previous = self.run_git(self.root, "--git-dir", str(self.remote), "rev-parse", "refs/heads/main").stdout.strip()
        original_command = autosync.command

        def fail_lfs(args, cwd, **kwargs):
            if args[:3] == ["git", "lfs", "push"]:
                return subprocess.CompletedProcess(args, 1, "", "upload failed")
            return original_command(args, cwd, **kwargs)

        with mock.patch.object(autosync, "scan_pending", return_value=None), mock.patch.object(
            autosync, "command", side_effect=fail_lfs
        ):
            self.assertEqual(autosync.run_once(self.root, self.state), 2)
        current = self.run_git(self.root, "--git-dir", str(self.remote), "rev-parse", "refs/heads/main").stdout.strip()
        self.assertEqual(current, previous)
        self.assertEqual(autosync.read_json(self.state / "status.json")["state"], "offline")

    def test_lfs_attributes_without_filters_do_not_commit_raw_content(self):
        self.run_git(self.root, "config", "filter.lfs.clean", "")
        self.run_git(self.root, "config", "filter.lfs.smudge", "")
        (self.root / ".gitattributes").write_text("*.bin filter=lfs -text\n", encoding="utf-8")
        (self.root / "asset.bin").write_bytes(b"payload")
        previous = self.run_git(self.root, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(autosync.run_once(self.root, self.state), 1)
        self.assertEqual(self.run_git(self.root, "rev-parse", "HEAD").stdout.strip(), previous)
        self.assertEqual((self.root / "asset.bin").read_bytes(), b"payload")

    def test_edit_during_sync_is_reported_as_pending(self):
        (self.root / "notes.txt").write_text("first\n", encoding="utf-8")
        original_command = autosync.command

        def fake_command(args, cwd, **kwargs):
            if args[:3] == ["git", "lfs", "push"]:
                (self.root / "notes.txt").write_text("later\n", encoding="utf-8")
                return subprocess.CompletedProcess(args, 0, "", "")
            return original_command(args, cwd, **kwargs)

        with mock.patch.object(autosync, "scan_pending", return_value=None), mock.patch.object(
            autosync, "command", side_effect=fake_command
        ):
            autosync.synchronize(self.root, self.state)
        self.assertEqual(autosync.read_json(self.state / "status.json")["state"], "pending")
        self.assertEqual((self.root / "notes.txt").read_text(), "later\n")

    def test_local_only_never_fetches_or_pushes(self):
        (self.root / "notes.txt").write_text("local\n", encoding="utf-8")
        previous = self.run_git(self.root, "--git-dir", str(self.remote), "rev-parse", "refs/heads/main").stdout.strip()
        with mock.patch.object(autosync, "scan_pending", side_effect=AssertionError("unexpected scan")):
            autosync.synchronize(self.root, self.state, local_only=True)
        self.assertEqual(autosync.read_json(self.state / "status.json")["state"], "local_only")
        current = self.run_git(self.root, "--git-dir", str(self.remote), "rev-parse", "refs/heads/main").stdout.strip()
        self.assertEqual(current, previous)

    def test_running_watcher_can_receive_an_adhoc_sync_request(self):
        autosync.write_json(self.state / "watcher.json", {"pid": os.getpid(), "local_only": True})
        autosync.request_sync(self.state)
        self.assertIn("requested_at", autosync.read_json(self.state / "sync-request.json"))

    def test_local_only_request_does_not_trigger_a_remote_watcher(self):
        autosync.write_json(self.state / "watcher.json", {"pid": os.getpid(), "local_only": False})
        with self.assertRaisesRegex(autosync.SyncError, "can publish"):
            autosync.request_sync(self.state, local_only_requested=True)
        self.assertFalse((self.state / "sync-request.json").exists())

    def test_staged_attributes_are_renormalized_in_the_next_cycle(self):
        (self.root / "notes.txt").write_bytes(b"first\r\nsecond\r\n")
        (self.root / ".gitattributes").write_text("*.txt text eol=lf\n", encoding="utf-8")
        self.run_git(self.root, "add", ".gitattributes")
        self.assertEqual(autosync.run_once(self.root, self.state), 1)
        current = autosync.read_json(self.state / "status.json")
        autosync.approve(self.state, current["incident"])
        self.sync_without_scanner_or_lfs()
        self.sync_without_scanner_or_lfs()
        blob = subprocess.check_output(["git", "show", "HEAD:notes.txt"], cwd=self.root)
        self.assertEqual(blob, b"first\nsecond\n")

    @unittest.skipUnless(shutil.which("gitleaks"), "gitleaks is required")
    def test_real_scanner_blocks_secret_in_pending_history(self):
        key = "AK" + "IA" + "234567ABCDEFGHJK"
        (self.root / "secret.txt").write_text("aws_access_key_id = " + key + "\n", encoding="utf-8")
        previous = self.run_git(self.root, "--git-dir", str(self.remote), "rev-parse", "refs/heads/main").stdout.strip()
        result = autosync.run_once(self.root, self.state)
        self.assertEqual(result, 1)
        state = autosync.read_json(self.state / "status.json")
        self.assertEqual(state["state"], "approval_required")
        self.assertTrue(state["incident"].startswith("secrets-"))
        self.assertNotIn(key, json.dumps(state))
        self.assertEqual(
            self.run_git(self.root, "--git-dir", str(self.remote), "rev-parse", "refs/heads/main").stdout.strip(),
            previous,
        )

    @unittest.skipUnless(shutil.which("gitleaks") and shutil.which("git-lfs"), "gitleaks and git-lfs are required")
    def test_real_scanner_blocks_secret_in_lfs_object(self):
        self.run_git(self.root, "lfs", "install", "--local")
        (self.root / ".gitattributes").write_text(
            "*.secret filter=lfs diff=lfs merge=lfs -text\n", encoding="utf-8"
        )
        key = "AK" + "IA" + "234567ABCDEFGHJK"
        (self.root / "payload.secret").write_text("aws_access_key_id = " + key + "\n", encoding="utf-8")
        previous = self.run_git(self.root, "--git-dir", str(self.remote), "rev-parse", "refs/heads/main").stdout.strip()
        self.assertEqual(autosync.run_once(self.root, self.state), 1)
        state = autosync.read_json(self.state / "status.json")
        self.assertEqual(state["state"], "approval_required")
        self.assertNotIn(key, json.dumps(state))
        current = self.run_git(self.root, "--git-dir", str(self.remote), "rev-parse", "refs/heads/main").stdout.strip()
        self.assertEqual(current, previous)

    @unittest.skipUnless(shutil.which("git-lfs"), "git-lfs is required")
    def test_existing_file_is_renormalized_into_lfs_and_uploaded(self):
        self.run_git(self.root, "lfs", "install", "--local")
        (self.root / "asset.bin").write_bytes(b"existing binary contents")
        self.run_git(self.root, "add", "asset.bin")
        self.run_git(self.root, "commit", "-m", "add asset")
        self.run_git(self.root, "push")
        (self.root / ".gitattributes").write_text(
            "*.bin filter=lfs diff=lfs merge=lfs -text\n", encoding="utf-8"
        )
        with mock.patch.object(autosync, "scan_pending", return_value=None):
            autosync.synchronize(self.root, self.state)
        pointer = self.run_git(self.root, "show", "HEAD:asset.bin").stdout
        self.assertTrue(pointer.startswith("version https://git-lfs.github.com/spec/v1\n"))
        oid = next(line.split(":", 1)[1] for line in pointer.splitlines() if line.startswith("oid sha256:"))
        self.assertTrue((self.remote / "lfs" / "objects" / oid[:2] / oid[2:4] / oid).exists())
        self.assertEqual((self.root / "asset.bin").read_bytes(), b"existing binary contents")

    @unittest.skipUnless(shutil.which("git-lfs"), "git-lfs is required")
    def test_existing_binary_round_trips_into_and_out_of_lfs(self):
        self.run_git(self.root, "lfs", "install", "--local")
        payload = b"binary\x00contents\r\n\xff"
        asset = self.root / "asset.bin"
        attributes = self.root / ".gitattributes"
        asset.write_bytes(payload)
        self.run_git(self.root, "add", "asset.bin")
        self.run_git(self.root, "commit", "-m", "add binary")

        attributes.write_text("*.bin filter=lfs diff=lfs merge=lfs -text\n", encoding="utf-8")
        autosync.synchronize(self.root, self.state, local_only=True)
        pointer = subprocess.check_output(["git", "show", "HEAD:asset.bin"], cwd=self.root)
        self.assertTrue(pointer.startswith(b"version https://git-lfs.github.com/spec/v1\n"))
        self.assertEqual(asset.read_bytes(), payload)

        attributes.unlink()
        autosync.synchronize(self.root, self.state, local_only=True)
        restored = subprocess.check_output(["git", "show", "HEAD:asset.bin"], cwd=self.root)
        self.assertEqual(restored, payload)
        self.assertEqual(asset.read_bytes(), payload)
        self.assertEqual(self.run_git(self.root, "status", "--porcelain").stdout, "")

    def test_initialize_is_idempotent_and_preserves_existing_guidance(self):
        autosync.initialize(self.root)
        guidance = self.root / ".agents" / "guidelines" / "autosync.guidelines.md"
        guidance.write_text("Custom guidance\n", encoding="utf-8")
        autosync.initialize(self.root)
        self.assertEqual(guidance.read_text(), "Custom guidance\n")
        self.assertEqual((self.root / "AGENTS.md").read_text().count("## Git autosync"), 1)


@unittest.skipUnless(shutil.which("git"), "git is required")
class ParticipantGroupTests(unittest.TestCase):
    """Real processes: one leader per checkout, failover, and broadcast orders."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "checkout"
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.root)], check=True)
        for key, value in (("user.email", "test@example.invalid"), ("user.name", "Test"),
                           ("core.autocrlf", "false")):
            subprocess.run(["git", "-C", str(self.root), "config", key, value], check=True)
        (self.root / "notes.txt").write_text("initial\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "initial"], check=True)
        _, self.state = autosync.repository(self.root)
        self.env = {key: value for key, value in os.environ.items()
                    if key not in ("COPILOT_AGENT_SESSION_ID", "CLAUDECODE")}
        self.env["AI_AUTOSYNC_FOLLOWER_POLL"] = "0.2"
        self.processes = []

    def tearDown(self):
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    def spawn(self, *args):
        process = subprocess.Popen(
            [sys.executable, str(SCRIPT), *args], env=self.env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self.processes.append(process)
        return process

    def owner(self):
        return self.spawn_raw([sys.executable, "-c", "import time; time.sleep(120)"])

    def spawn_raw(self, argv):
        process = subprocess.Popen(argv)
        self.processes.append(process)
        return process

    def wait_for(self, predicate, timeout=20.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.1)
        self.fail(f"condition not met; state: {autosync.describe(self.state)}")

    def roles(self):
        return {item["pid"]: item["role"] for item in autosync.participants(self.state)}

    def test_single_leader_and_failover_when_a_session_ends(self):
        owner_a, owner_b = self.owner(), self.owner()
        first = self.spawn("start", str(self.root), "--local-only", "--owner-pid", str(owner_a.pid))
        self.wait_for(lambda: self.roles().get(first.pid) == "leader")
        second = self.spawn("join", str(self.root), "--owner-pid", str(owner_b.pid))
        self.wait_for(lambda: self.roles().get(second.pid) == "follower")
        self.assertEqual(sorted(self.roles().values()), ["follower", "leader"])

        owner_a.kill()
        owner_a.wait()
        first.wait(timeout=20)
        self.wait_for(lambda: self.roles() == {second.pid: "leader"})
        (self.root / "notes.txt").write_text("after failover\n", encoding="utf-8")
        self.wait_for(lambda: subprocess.run(
            ["git", "-C", str(self.root), "show", "HEAD:notes.txt"],
            capture_output=True, text=True,
        ).stdout == "after failover\n")

    def test_stop_and_start_orders_reach_every_participant(self):
        owner = self.owner()
        first = self.spawn("start", str(self.root), "--local-only", "--owner-pid", str(owner.pid))
        second = self.spawn("join", str(self.root), "--owner-pid", str(owner.pid))
        self.wait_for(lambda: sorted(self.roles().values()) == ["follower", "leader"])

        subprocess.run([sys.executable, str(SCRIPT), "stop", str(self.root)], env=self.env, check=True,
                       stdout=subprocess.DEVNULL)
        self.wait_for(lambda: self.roles() == {first.pid: "idle", second.pid: "idle"})
        self.assertIsNone(autosync.describe(self.state)["leader_pid"])
        (self.root / "notes.txt").write_text("while stopped\n", encoding="utf-8")
        time.sleep(1.5)
        self.assertEqual(subprocess.run(
            ["git", "-C", str(self.root), "show", "HEAD:notes.txt"], capture_output=True, text=True,
        ).stdout, "initial\n")

        subprocess.run([sys.executable, str(SCRIPT), "start", str(self.root), "--local-only",
                        "--enable-only"], env=self.env, check=True, stdout=subprocess.DEVNULL)
        self.wait_for(lambda: sorted(self.roles().values()) == ["follower", "leader"])
        self.assertTrue(all(process.poll() is None for process in (first, second)))

    def test_blocking_incident_pauses_the_whole_group(self):
        owner = self.owner()
        (self.root / "notes.txt").write_text("staged\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "notes.txt"], check=True)
        first = self.spawn("start", str(self.root), "--local-only", "--owner-pid", str(owner.pid))
        second = self.spawn("join", str(self.root), "--owner-pid", str(owner.pid))
        self.wait_for(lambda: not autosync.read_control(self.state)["enabled"])
        self.assertTrue(autosync.read_control(self.state)["reason"].startswith("blocked:"))
        self.wait_for(lambda: self.roles() == {first.pid: "idle", second.pid: "idle"})
        self.assertEqual(autosync.read_json(self.state / "status.json")["state"], "approval_required")


    def test_participant_leaves_when_its_copilot_session_closes(self):
        home = Path(self.tmp.name) / "copilot-home"
        session = home / "session-state" / "session-1"
        session.mkdir(parents=True)
        runtime = self.owner()
        in_use = session / f"inuse.{runtime.pid}.lock"
        in_use.write_text(str(runtime.pid), encoding="utf-8")
        self.env.update(COPILOT_HOME=str(home), COPILOT_AGENT_SESSION_ID="session-1")
        member = self.spawn("start", str(self.root), "--local-only")
        self.wait_for(lambda: self.roles().get(member.pid) == "leader")
        record = autosync.participants(self.state)[0]
        self.assertEqual((record["harness"], record["session_id"]), ("copilot", "session-1"))
        in_use.unlink()
        self.assertEqual(member.wait(timeout=20), 0)
        self.assertEqual(runtime.poll(), None)


class HarnessTests(unittest.TestCase):
    def test_auto_detection_picks_the_running_harness(self):
        cases = {
            "copilot": {"COPILOT_AGENT_SESSION_ID": "abc"},
            "claude-code": {"CLAUDECODE": "1"},
            "generic": {},
        }
        for name, env in cases.items():
            harness = autosync.resolve_harness("auto", None, None, env)
            self.assertEqual(harness.name, name)
        self.assertEqual(autosync.resolve_harness("auto", None, None, cases["copilot"]).session_id, "abc")
        self.assertEqual(autosync.resolve_harness("omp", 1, "s", {}).describe(),
                         {"harness": "omp", "owner_pid": 1, "session_id": "s"})

    def test_copilot_session_requires_a_live_in_use_lock(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"COPILOT_HOME": tmp}):
            session = Path(tmp) / "session-state" / "s1"
            session.mkdir(parents=True)
            harness = autosync.CopilotHarness(None, "s1")
            self.assertFalse(harness.alive())
            (session / "inuse.999999999.lock").write_text("", encoding="utf-8")
            self.assertFalse(harness.alive())
            (session / f"inuse.{os.getpid()}.lock").write_text("", encoding="utf-8")
            self.assertTrue(harness.alive())

if __name__ == "__main__":
    unittest.main()
