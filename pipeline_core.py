#!/usr/bin/env python3
"""Bounded, exact-name RouterOS hosts builder. Python 3.11+, standard library only.

SPDX-License-Identifier: GPL-3.0-or-later
Upstream lists retain their authorship and licensing; see SOURCES.md and LICENSE.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import ssl
import shutil
import sys
import tempfile
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
VERSION = "3.0.2"
LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
SOURCE_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
RESERVED = {"localhost", "local", "lan", "test", "invalid", "example", "onion"}
SINK_IPS = {"0.0.0.0", "127.0.0.1", "::", "::1"}


class BuildError(Exception):
    pass


def domain(value: str) -> str | None:
    """Validate an ASCII DNS hostname, without substring/URL extraction."""
    value = value.lower()
    if not value or len(value) > 253 or not value.isascii():
        return None
    labels = value.split(".")
    if len(labels) < 2 or labels[-1] in RESERVED or labels[-1].isdigit():
        return None
    if value == "home.arpa" or value.endswith(".home.arpa"):
        return None
    if not all(LABEL.fullmatch(label) for label in labels):
        return None
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return value
    return None


def parse_hosts(text: str, limit: int) -> tuple[set[str], dict]:
    names: set[str] = set()
    counts = {"data_lines": 0, "invalid_lines": 0, "duplicate_names": 0}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = re.split(r"\s+#", line, maxsplit=1)[0].strip()
        counts["data_lines"] += 1
        parts = line.split()
        if len(parts) == 1:
            candidate = parts[0]
        elif len(parts) == 2 and parts[0] in SINK_IPS:
            candidate = parts[1]
        else:
            counts["invalid_lines"] += 1
            continue
        name = domain(candidate)
        if name is None:
            counts["invalid_lines"] += 1
            continue
        if name in names:
            counts["duplicate_names"] += 1
        names.add(name)
        if len(names) > limit:
            raise BuildError(f"Source exceeds its {limit:,}-domain limit; no output changed")
    return names, counts


def read_bounded(path: Path, limit: int) -> bytes:
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise BuildError(f"{path.name} exceeds its byte limit")
    return data


def decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise BuildError("Source is not valid UTF-8 text") from exc


class HTTPSRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject a downgrade before urllib sends any request to its target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urlparse(newurl)
        if target.scheme != "https" or not target.hostname or target.username or target.password:
            raise BuildError("Refusing a redirect outside credential-free HTTPS")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def positive_int(value: object, name: str, maximum: int) -> int:
    if type(value) is not int or not 1 <= value <= maximum:
        raise BuildError(f"{name} must be an integer from 1 to {maximum:,}")
    return value


def user_rules(path: Path, wildcards: bool) -> tuple[set[str], set[str]]:
    exact: set[str] = set()
    suffix: set[str] = set()
    for index, raw in enumerate(decode(read_bounded(path, 1048576)).splitlines(), 1):
        line = raw.strip().lower()
        if not line or line.startswith("#"):
            continue
        line = re.split(r"\s+#", line, maxsplit=1)[0].strip()
        parts = line.split()
        if len(parts) == 2 and parts[0] in SINK_IPS:
            line = parts[1]
        is_suffix = line.startswith("*.")
        candidate = line[2:] if is_suffix else line
        if domain(candidate) is None or (is_suffix and not wildcards):
            raise BuildError(f"{path.name}:{index}: invalid rule {line!r}")
        (suffix if is_suffix else exact).add(candidate)
    return exact, suffix


def allowed(name: str, exact: set[str], suffix: set[str]) -> bool:
    if name in exact or name in suffix:
        return True
    labels = name.split(".")
    return any(".".join(labels[i:]) in suffix for i in range(1, len(labels) - 1))


@contextlib.contextmanager
def build_lock(directory: Path):
    """OS file lock, released even on process termination; no stale PID lock."""
    path = directory / ".build.lock"
    with path.open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise BuildError("Another build is already running") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_write(path: Path, data: bytes):
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".adlist-", delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def checked_path(output: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise BuildError("Unsafe publication path")
    path = output / rel
    if not path.resolve().is_relative_to(output.resolve()):
        raise BuildError("Publication path leaves output directory")
    return path


def discard_transaction(output: Path):
    target = output / ".adlist-transaction"
    if target.is_symlink() or target.resolve().parent != output.resolve():
        raise BuildError("Unsafe transaction directory")
    if target.exists():
        shutil.rmtree(target)


def recover_transaction(output: Path):
    """A prepared transaction is rolled back, including after a process crash."""
    folder = checked_path(output, ".adlist-transaction")
    if not folder.exists():
        return
    manifest = folder / "state.json"
    if not manifest.exists():
        # All original files are still untouched until state.json is durable.
        discard_transaction(output)
        return
    state = json.loads(decode(read_bounded(manifest, 1048576)))
    if not isinstance(state, dict) or state.get("phase") not in ("prepared", "committed"):
        raise BuildError("Publication recovery state is invalid; preserve it for inspection")
    entries = state.get("entries")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 20:
        raise BuildError("Publication recovery entries are invalid")
    # Validate every entry and backup before restoring any file.
    for entry in entries:
        if not isinstance(entry, dict) or type(entry.get("existed")) is not bool:
            raise BuildError("Publication recovery entry is invalid")
        rel = entry["path"]
        if rel not in {"merged_hosts.txt", "merged_hosts.txt.gz", "merged_hosts.previous.txt", "stats.json", "merged_hosts.sha256", "expected_names.txt", "router-ready/install-rb5009-local.rsc", "router-ready/INSTALL.txt", "source-audit.csv", "suffix_domains.txt", "allowlist.txt", "blocklist.txt", "coverage-audit.json", "source-overlap.csv", "domain-review.csv.gz"} and not re.fullmatch(r"router-ready/adlist-v3-[0-9a-f]{16}(?:\.count)?\.txt", rel):
            raise BuildError("Publication recovery path is invalid")
        checked_path(output, rel)
        if state["phase"] == "prepared" and entry["existed"]:
            raw = read_bounded(checked_path(folder / "before", rel), 268435456)
            if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
                raise BuildError("Publication recovery backup checksum mismatch")
    if state["phase"] == "prepared":
        for entry in reversed(entries):
            target = checked_path(output, entry["path"])
            if entry["existed"]:
                target.parent.mkdir(parents=True, exist_ok=True)
                atomic_write(target, read_bounded(folder / "before" / entry["path"], 268435456))
            else:
                target.unlink(missing_ok=True)
    discard_transaction(output)


def publish_files(output: Path, files: dict[str, bytes]):
    """Stage all bytes, keep recovery copies, then replace files. Hosts goes last."""
    folder = checked_path(output, ".adlist-transaction")
    if folder.exists():
        raise BuildError("Recover the pending publication before starting another")
    if shutil.disk_usage(output).free < max(67108864, sum(map(len, files.values())) * 3):
        raise BuildError("Not enough free PC disk space to stage a recoverable publication")
    entries = []
    try:
        for rel, raw in files.items():
            target = checked_path(output, rel)
            entry = {"path": rel, "existed": target.exists()}
            if entry["existed"]:
                before = read_bounded(target, 268435456)
                entry["sha256"] = hashlib.sha256(before).hexdigest()
                backup = folder / "before" / rel
                backup.parent.mkdir(parents=True, exist_ok=True)
                atomic_write(backup, before)
            staged = folder / "after" / rel
            staged.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(staged, raw)
            entries.append(entry)
        state = {"phase": "prepared", "entries": entries}
        atomic_write(folder / "state.json", (json.dumps(state) + "\n").encode())
        for rel in files:
            target = checked_path(output, rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(folder / "after" / rel, target)
        state["phase"] = "committed"
        atomic_write(folder / "state.json", (json.dumps(state) + "\n").encode())
    except BaseException:
        recover_transaction(output)
        raise
    try:
        discard_transaction(output)
    except OSError:
        return "Publication committed; transaction cleanup will be retried by the next build"
    return None


