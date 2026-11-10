"""Check all frozen release files and the V450 index against their hashes."""

import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(root):
    inventory = json.loads((root / "RELEASE_INVENTORY.json").read_text(encoding="utf-8"))
    issues = []
    for relative, record in inventory["copies"].items():
        path = root / relative
        if not path.is_file():
            issues.append(f"Missing: {relative}")
        elif path.stat().st_size != record["bytes"] or digest(path) != record["sha256"]:
            issues.append(f"Changed bytes: {relative}")

    study = root / "work" / "fleet_study_v450_full_baselines_memory_online_20261107"
    index = json.loads((study / "FINAL_EVIDENCE_INDEX_01.json").read_text(encoding="utf-8-sig"))
    for relative, expected in index["evidence"].items():
        path = study / relative
        if not path.is_file() or digest(path) != expected:
            issues.append(f"V450 index mismatch: {relative}")

    if issues:
        raise SystemExit("\n".join(issues))
    print(json.dumps({
        "status": "PASS",
        "frozen_files": len(inventory["copies"]),
        "frozen_bytes": inventory["bytes"],
        "v450_index_entries": len(index["evidence"]),
        "recorded_exclusions": len(inventory["exclusions"]),
    }, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    verify(parser.parse_args().root.resolve())
