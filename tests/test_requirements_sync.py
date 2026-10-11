"""
tests/test_requirements_sync.py — requirements.txt and requirements.lock must pin
exactly the same packages and versions.

Staging installs requirements.lock (hash-checked) and production must run what
staging tested. Dependabot only bumps requirements.txt, so a Dependabot PR
fails this test until the lock is regenerated (see requirements.in header):

    pip-compile --generate-hashes --constraint requirements.txt \
        requirements.in --output-file requirements.lock
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_PIN = re.compile(r"^([A-Za-z0-9_.\-]+)(?:\[[^\]]*\])?==([^\s;\\]+)")


def _pins(name: str) -> dict[str, str]:
    pins = {}
    for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
        m = _PIN.match(line.strip())
        if m:
            pins[re.sub(r"[-_.]+", "-", m.group(1)).lower()] = m.group(2)
    return pins


def test_txt_and_lock_pin_identical_versions():
    txt, lock = _pins("requirements.txt"), _pins("requirements.lock")
    assert txt, "no pins parsed from requirements.txt"
    diffs = {
        pkg: (txt.get(pkg), lock.get(pkg))
        for pkg in sorted(set(txt) | set(lock))
        if txt.get(pkg) != lock.get(pkg)
    }
    assert not diffs, f"requirements.txt vs requirements.lock differ (txt, lock): {diffs}"


def test_every_lock_pin_has_hashes():
    text = (ROOT / "requirements.lock").read_text(encoding="utf-8")
    blocks = re.split(r"\n(?=[A-Za-z0-9])", text)
    unhashed = [b.split()[0] for b in blocks if _PIN.match(b) and "--hash=sha256:" not in b]
    assert not unhashed, f"lock entries without hashes: {unhashed}"
