"""Integrity checks for C0 accounting, without launching models or external code."""

import json

import pytest

from c0.campaign import append_event, read_events, sha, verify_manifest


def test_journal_keeps_prior_bytes_and_rejects_tampering(tmp_path):
    path = tmp_path / "journal.jsonl"
    append_event(path, {"event": "planned", "attempt": "one"})
    first = path.read_bytes()
    append_event(path, {"event": "failed", "attempt": "one"})
    assert path.read_bytes().startswith(first)
    assert [r["event"] for r in read_events(path)] == ["planned", "failed"]
    path.write_text(path.read_text().replace('"failed"', '"passed"'))
    corrupted = path.read_bytes()
    with pytest.raises(ValueError, match="hash"):
        append_event(path, {"event": "another"})
    assert path.read_bytes() == corrupted


def test_manifest_stops_when_a_frozen_input_changes(tmp_path):
    source = tmp_path / "rules.txt"
    source.write_text("frozen")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"frozen_files": [{"path": str(source), "sha256": sha(source)}]}))
    manifest.with_suffix(".json.sha256").write_text(sha(manifest))
    verify_manifest(manifest)
    source.write_text("changed")
    with pytest.raises(ValueError, match="Frozen file changed"):
        verify_manifest(manifest)


def test_manifest_cannot_redefine_its_own_frozen_inputs(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"frozen_files": []}')
    manifest.with_suffix(".json.sha256").write_text(sha(manifest))
    manifest.write_text('{"frozen_files": [], "changed": true}')
    with pytest.raises(ValueError, match="Manifest seal"):
        verify_manifest(manifest)
