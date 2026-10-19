"""Check this distribution and optionally replay its six golden CLI examples.

SHA-256 detects changed bytes. This local manifest is not a signed trust root.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical_response(raw):
    return json.dumps(json.loads(raw), sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode()


def verify(smoke=False):
    if sys.version_info < (3, 12):
        raise ValueError("Python 3.12 or newer required; reference tests used 3.12.14")
    manifest = json.loads((ROOT / "RUNTIME_MANIFEST.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("files"), dict):
        raise ValueError("invalid distribution manifest")
    expected = manifest["files"]
    for name, digest in expected.items():
        path = PurePosixPath(name)
        if (not name or path.is_absolute() or ".." in path.parts or "\\" in name
                or path.as_posix() != name or name == "RUNTIME_MANIFEST.json"
                or not isinstance(digest, str) or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)):
            raise ValueError("invalid manifest entry")
    actual = set()
    for path in ROOT.rglob("*"):
        if path.is_symlink():
            raise ValueError("symbolic links are not allowed")
        if path.is_file() and "__pycache__" not in path.relative_to(ROOT).parts:
            actual.add(path.relative_to(ROOT).as_posix())
    if actual != set(expected) | {"RUNTIME_MANIFEST.json"}:
        raise ValueError("package inventory mismatch (missing or unexpected file)")
    if len({name.casefold() for name in actual}) != len(actual):
        raise ValueError("case-insensitive path collision")
    for name, digest in expected.items():
        if sha((ROOT / name).read_bytes()) != digest:
            raise ValueError("package checksum mismatch: " + name)

    # The existing registry also verifies release identity, artifacts and features.
    sys.path.insert(0, str(ROOT))
    from blackbox.registry import selected
    config, _ = selected(ROOT)
    if config["mode"] != "conservative" or config["release_id"] != manifest["release_id"]:
        raise ValueError("unexpected deployment selection")
    result = {"passed": True, "files_verified": len(actual),
              "release_id": config["release_id"], "default_mode": config["mode"],
              "reference_python_family": sys.version_info[:2] == (3, 12),
              "smoke_cases": 0, "rejected_invalid_inputs": 0,
              "actual_container_verification": False}
    if smoke:
        env = dict(os.environ)
        for key in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "BLACKBOX_POLICY_MODE"):
            env.pop(key, None)
        env.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
        for case in manifest["golden_smoke_cases"]:
            proc = subprocess.run(
                [sys.executable, "-S", "-B", str(ROOT / "policy.py"), "--mode", case["mode"]],
                cwd=ROOT, input=(ROOT / case["example"]).read_bytes(),
                capture_output=True, timeout=15, env=env)
            if proc.returncode != 0 or sha(canonical_response(proc.stdout)) != case["response_sha256"]:
                raise ValueError("golden response mismatch: " + case["mode"] + "/" + case["example"])
            result["smoke_cases"] += 1
        for raw in (b"{}", b'{"x":NaN}', b" " * (1024 ** 2 + 1)):
            proc = subprocess.run([sys.executable, "-S", "-B", str(ROOT / "policy.py")],
                                  cwd=ROOT, input=raw, capture_output=True, timeout=15, env=env)
            if proc.returncode != 2 or proc.stdout:
                raise ValueError("invalid request was not rejected safely")
            result["rejected_invalid_inputs"] += 1
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="also run six golden examples and three invalid requests")
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.smoke), sort_keys=True))
        return 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired, RecursionError) as error:
        print(json.dumps({"passed": False, "error": str(error)[:240]}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
