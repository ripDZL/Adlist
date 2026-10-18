"""Failure-path checks for a router-facing data pipeline; no network/router access."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch
import io
from email.message import Message
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("builder", ROOT / "build_adlist.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        self.output = self.root / "output"
        self.cfg = json.loads((ROOT / "sources.json").read_text())
        self.cfg.update(min_domains=1, max_domains=10)
        self.cfg.pop("original_sources_sha256", None)
        self.cfg["sources"] = self.cfg["sources"][:1]
        self.cfg["sources"][0].update(id="hagezi-light", format="hosts")
        self.cfg["sources"][0].pop("fallback_urls", None)
        self.cfg["sources"][0].update(min_domains=1, max_domains=10)
        self.cfg["sources"][0].pop("max_age_hours", None)
        self.cfg["sources"][0]["require_entry_count"] = False
        self.config = self.root / "sources.json"
        self.allow = self.root / "allowlist.txt"
        self.block = self.root / "blocklist.txt"
        self.allow.write_text("")
        self.block.write_text("")
        self.config.write_text(json.dumps(self.cfg))
        self.args = argparse.Namespace(config=self.config, output=self.output,
            allowlist=self.allow, blocklist=self.block, input_dir=self.inputs,
            dry_run=False, accept_large_change=False)
        self.input = self.inputs / "hagezi-light.txt"
        self.input.write_text("0.0.0.0 ads.vendor.net\n0.0.0.0 sub.ads.vendor.net\n")

    def snapshot(self):
        return {p.relative_to(self.output).as_posix(): p.read_bytes()
                for p in self.output.rglob("*") if p.is_file() and p.name != ".build.lock"}

    def test_exact_names_preserve_parent_and_child(self):
        r = b.run(self.args)
        self.assertEqual(r["domains"], 2)
        text = (self.output / "merged_hosts.txt").read_text()
        self.assertIn("0.0.0.0 ads.vendor.net\n", text)
        self.assertIn("0.0.0.0 sub.ads.vendor.net\n", text)

    def test_reject_browser_syntax_and_non_sink_hosts(self):
        names, stats = b.parse_hosts("||ads.vendor.net^\n@@||safe.net^\nexample.net##.ad\n1.2.3.4 bad.net\n0.0.0.0 one.net two.net\n", 10)
        self.assertFalse(names)
        self.assertEqual(stats["invalid_lines"], 5)

    def test_normalization_duplicates_reserved_and_ips(self):
        names, stats = b.parse_hosts("ADS.VENDOR.NET\n0.0.0.0 ads.vendor.net # comment\n127.0.0.1 localhost\n0.0.0.0 foo.local\n0.0.0.0 192.168.0.1\n", 10)
        self.assertEqual(names, {"ads.vendor.net"})
        self.assertEqual(stats["duplicate_names"], 1)
        self.assertEqual(stats["invalid_lines"], 3)

    def test_allowlist_exact_and_suffix_priority(self):
        self.allow.write_text("*.ads.vendor.net\n")
        self.block.write_text("ads.vendor.net\nother.vendor.net\n")
        r = b.run(self.args)
        self.assertEqual(r["domains"], 1)
        self.assertEqual(r["allowlist_removed"], 2)
        self.assertFalse(b.allowed("notads.vendor.net", set(), {"ads.vendor.net"}))

    def test_failed_required_source_preserves_every_output(self):
        b.run(self.args)
        before = self.snapshot()
        self.input.write_text("<html>404 Not Found</html>")
        with self.assertRaises(b.BuildError):
            b.run(self.args)
        self.assertEqual(before, self.snapshot())

    def test_domain_cap_preserves_every_output(self):
        b.run(self.args)
        before = self.snapshot()
        self.input.write_text("".join(f"ad{i}.vendor.net\n" for i in range(11)))
        with self.assertRaises(b.BuildError):
            b.run(self.args)
        self.assertEqual(before, self.snapshot())

    def test_byte_cap_cannot_be_overridden(self):
        b.run(self.args)
        before = self.snapshot()
        self.cfg["max_output_bytes"] = 100
        self.config.write_text(json.dumps(self.cfg))
        self.args.accept_large_change = True
        with self.assertRaises(b.BuildError):
            b.run(self.args)
        self.assertEqual(before, self.snapshot())

    def test_same_count_replacement_detects_churn(self):
        b.run(self.args)
        before = self.snapshot()
        self.input.write_text("other.bad.net\nnew.bad.net\n")
        with self.assertRaises(b.BuildError):
            b.run(self.args)
        self.assertEqual(before, self.snapshot())

    def test_reviewed_change_keeps_one_previous_copy(self):
        b.run(self.args)
        old = (self.output / "merged_hosts.txt").read_bytes()
        self.input.write_text("other.bad.net\nnew.bad.net\n")
        self.args.accept_large_change = True
        b.run(self.args)
        self.assertEqual((self.output / "merged_hosts.previous.txt").read_bytes(), old)

    def test_unchanged_build_does_not_rewrite_files(self):
        b.run(self.args)
        before = {p.name: p.stat().st_mtime_ns for p in self.output.iterdir() if p.name != ".build.lock"}
        self.assertFalse(b.run(self.args)["changed"])
        after = {p.name: p.stat().st_mtime_ns for p in self.output.iterdir() if p.name != ".build.lock"}
        self.assertEqual(before, after)

    def test_missing_count_sidecar_is_repaired(self):
        b.run(self.args)
        (self.output / "expected_names.txt").unlink()
        b.run(self.args)
        self.assertEqual((self.output / "expected_names.txt").read_text(), "2")

    def test_concurrent_build_is_rejected(self):
        self.output.mkdir()
        with b.build_lock(self.output):
            with self.assertRaises(b.BuildError):
                b.run(self.args)

    def test_download_cap_and_tls_context(self):
        class Response:
            status = 200
            url = "https://example.net/hosts"
            headers = {"Content-Type": "text/plain"}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read1(self, count): return b"x" * 20
        source = copy.deepcopy(self.cfg["sources"][0])
        source["max_download_bytes"] = 10
        with patch.object(b.urllib.request.OpenerDirector, "open", return_value=Response()) as opener, patch.object(b.time, "sleep"), patch.object(b.urllib.request, "build_opener", wraps=b.urllib.request.build_opener) as factory:
            with self.assertRaises(b.BuildError):
                b.download(source)
            self.assertEqual(opener.call_count, 3)
            self.assertTrue(factory.call_args.args[0]._context.check_hostname)
            self.assertEqual(factory.call_args.args[0]._context.verify_mode, b.ssl.CERT_REQUIRED)

    def test_download_refuses_incomplete_transfer(self):
        class Response:
            status = 200
            url = "https://example.net/hosts"
            headers = {"Content-Type": "text/plain", "Content-Length": "100"}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read1(self, count): return b""
        with patch.object(b.urllib.request.OpenerDirector, "open", return_value=Response()), patch.object(b.time, "sleep"):
            with self.assertRaises(b.BuildError):
                b.download(self.cfg["sources"][0])

    def test_dry_run_leaves_output_absent(self):
        self.args.dry_run = True
        b.run(self.args)
        self.assertFalse((self.output / "merged_hosts.txt").exists())

    def test_verifier_detects_statistics_corruption(self):
        b.run(self.args)
        stats_path = self.output / "stats.json"
        stats = json.loads(stats_path.read_text())
        stats["domains"] += 1
        stats_path.write_text(json.dumps(stats))
        with self.assertRaises(b.BuildError):
            b.verify_output(self.output, self.cfg)

    def test_verifier_detects_router_bundle_corruption(self):
        b.run(self.args)
        hosts = next((self.output / "router-ready").glob("adlist-v3-*.txt"))
        hosts.write_text("corrupted")
        with self.assertRaises(b.BuildError):
            b.verify_output(self.output, self.cfg)




    def test_filesystem_failure_restores_all_published_files(self):
        b.run(self.args)
        before = self.snapshot()
        self.input.write_text("different.vendor.net\nnew.vendor.net\n")
        self.args.accept_large_change = True
        replace = b.os.replace
        failed = False
        def fail_once(source, destination):
            nonlocal failed
            if Path(destination) == self.output / "stats.json" and not failed:
                failed = True
                raise OSError("simulated replace failure")
            return replace(source, destination)
        with patch.object(b.os, "replace", side_effect=fail_once):
            with self.assertRaises(OSError):
                b.run(self.args)
        self.assertTrue(failed)
        self.assertEqual(before, self.snapshot())

    def test_process_crash_recovers_original_files(self):
        b.run(self.args)
        before = self.snapshot()
        self.input.write_text("different.vendor.net\nnew.vendor.net\n")
        code = '''import argparse,importlib.util,os,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("builder",sys.argv[1]);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
root=Path(sys.argv[2]);out=root/"output";replace=b.os.replace
def crash(source,destination):
 replace(source,destination)
 if Path(destination)==out/"stats.json": os._exit(77)
b.os.replace=crash
args=argparse.Namespace(config=root/"sources.json",output=out,allowlist=root/"allowlist.txt",blocklist=root/"blocklist.txt",input_dir=root/"inputs",dry_run=False,accept_large_change=True)
b.run(args)
'''
        child = subprocess.run([sys.executable, "-c", code, str(ROOT / "build_adlist.py"), str(self.root)], capture_output=True, timeout=20)
        self.assertEqual(child.returncode, 77, child.stderr.decode(errors="replace"))
        with self.assertRaises(b.BuildError):
            b.verify_output(self.output, self.cfg)
        b.recover_transaction(self.output)
        self.assertEqual(before, self.snapshot())
        self.assertTrue(b.verify_output(self.output, self.cfg)["verified"])

    def test_router_snapshot_names_change_with_content(self):
        b.run(self.args)
        first = set(p.name for p in (self.output / "router-ready").glob("adlist-v3-*.txt"))
        self.input.write_text("different.vendor.net\nnew.vendor.net\n")
        self.args.accept_large_change = True
        b.run(self.args)
        second = set(p.name for p in (self.output / "router-ready").glob("adlist-v3-*.txt"))
        self.assertTrue(first.isdisjoint(second))
        self.assertTrue(b.verify_output(self.output, self.cfg)["verified"])

    def test_dry_run_does_not_recover_or_change_pending_publication(self):
        b.run(self.args)
        folder = self.output / ".adlist-transaction"
        folder.mkdir()
        before = self.snapshot()
        self.args.dry_run = True
        with self.assertRaises(b.BuildError):
            b.run(self.args)
        self.assertEqual(before, self.snapshot())
        self.assertTrue(folder.exists())

    def test_invalid_configuration_has_compact_failure(self):
        invalid_url = copy.deepcopy(self.cfg)
        invalid_url["sources"][0]["url"] = 7
        for value in ([], {**self.cfg, "protected_exact": [None]}, {**self.cfg, "sources": ["not an object"]}, invalid_url):
            self.config.write_text(json.dumps(value))
            with self.assertRaises(b.BuildError):
                b.config_at(self.config)

    def test_broken_http_chunk_transfer_gets_finite_retries(self):
        class Response:
            status = 200
            url = "https://example.net/hosts"
            headers = {"Content-Type": "text/plain"}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read1(self, count): raise b.http.client.IncompleteRead(b"partial")
        with patch.object(b.urllib.request.OpenerDirector, "open", return_value=Response()) as opener, patch.object(b.time, "sleep"):
            with self.assertRaises(b.BuildError):
                b.download(self.cfg["sources"][0])
            self.assertEqual(opener.call_count, 3)

    def test_redirect_downgrade_is_rejected_before_dispatch(self):
        import urllib.response
        dispatched = []
        class RedirectingServer(b.urllib.request.HTTPSHandler):
            def https_open(self, req):
                dispatched.append(req.full_url)
                headers = Message()
                headers["Location"] = "http://unsafe.vendor.net/list"
                response = urllib.response.addinfourl(io.BytesIO(b""), headers, req.full_url, 302)
                response.msg = "Found"
                return response
            def http_open(self, req):
                dispatched.append(req.full_url)
                raise AssertionError("An HTTP request must never be dispatched")
        opener = b.urllib.request.build_opener(RedirectingServer(), b.HTTPSRedirectHandler())
        with self.assertRaises(b.BuildError):
            opener.open("https://safe.vendor.net/list")
        self.assertEqual(dispatched, ["https://safe.vendor.net/list"])

    def test_https_redirect_allowed_and_credential_redirect_rejected(self):
        handler = b.HTTPSRedirectHandler()
        req = b.urllib.request.Request("https://safe.vendor.net/list")
        redirect = handler.redirect_request(req, None, 302, "Found", {}, "https://cdn.vendor.net/list")
        self.assertEqual(redirect.full_url, "https://cdn.vendor.net/list")
        for target in ("https://user:secret@cdn.vendor.net/list", "ftp://cdn.vendor.net/list", "http://cdn.vendor.net/list"):
            with self.assertRaises(b.BuildError):
                handler.redirect_request(req, None, 302, "Found", {}, target)

    def test_committed_cleanup_failure_keeps_a_verifiable_result(self):
        remove = b.shutil.rmtree
        def fail_committed(path):
            state = Path(path) / "state.json"
            if state.exists() and json.loads(state.read_text())["phase"] == "committed":
                raise OSError("simulated cleanup permission failure")
            return remove(path)
        with patch.object(b.shutil, "rmtree", side_effect=fail_committed):
            result = b.run(self.args)
        self.assertIn("cleanup_warning", result)
        self.assertTrue(b.verify_output(self.output, self.cfg)["verified"])
        b.run(self.args)
        self.assertFalse((self.output / ".adlist-transaction").exists())


if __name__ == "__main__":
    unittest.main()
