# Dependency Risk Register

Known vulnerabilities in third-party dependencies: what was fixed, what is
accepted, and when to look again. Update this file whenever a Dependabot alert
is fixed, dismissed or accepted.

**Last audit:** 2026-10-26 (B58); previous 2026-10-11 (pip-audit on requirements.txt / requirements.lock /
requirements-dev.in, `npm audit --package-lock-only` on all three lockfiles).

---

## Summary

| Area | Status |
|------|--------|
| Python (web app) | No known vulnerabilities after B53 (urllib3 2.8.0 in both files) |
| npm, repo root | No known vulnerabilities |
| npm, `mobile/msmobile` | 3 accepted advisories (no upstream fix) |
| npm, `mobile/nmmobile` | 3 accepted advisories (no upstream fix) |

All remaining advisories are in **developer tooling** (Expo CLI, Metro bundler,
Jest, react-devtools-core). None of these packages is bundled into the shipped
iOS/Android apps, and none runs on the web servers. Exposure is limited to a
developer's machine or a CI build runner.

---

## Fixed

| Package | Advisory | Where | Fix |
|---------|----------|-------|-----|
| certifi 2026.4.22 | PYSEC-2026-4320 / GHSA-6q48-6c7w-9gw2 — bundled emSign ECC Root CA - G3 has intermediates with compromised keys (on-path TLS interception of outbound requests) | requirements.txt / .lock | 2026.10.23 (B58) |
| opentelemetry-api 1.44.0 | CVE-2026-114603 / GHSA-xcq7-p3pf-p88h — O(N²) `tracestate` parsing; unauthenticated DoS through FastAPI instrumentation (Apache's ~8 KB header limit reduced the impact) | requirements.txt / .lock | OpenTelemetry 1.45.1 / 0.66b1 (B58) |
| urllib3 2.7.0 | CVE-2026-97687, CVE-2026-97688, CVE-2026-97689 (streaming decompression memory use, proxy TLS config) | requirements.lock (staging only) | Lock regenerated to 2.8.0 (B53) |
| shell-quote 1.10.0 | [GHSA-pqg4-j6r4-53mv](https://github.com/advisories/GHSA-pqg4-j6r4-53mv) — critical, `quote()` command injection | msmobile, nmmobile (via @expo/cli, react-devtools-core) | npm override `"shell-quote": "^1.12.0"` |
| uuid 7.0.3 | [GHSA-w5hq-g745-h8pq](https://github.com/advisories/GHSA-w5hq-g745-h8pq) — moderate, missing buffer bounds check | nmmobile (via xcode → @expo/config-plugins) | npm override `"uuid": ">=11.1.1"` (same as msmobile; verified `xcode` still generates UUIDs against the real nmmobile project with uuid 14) |

---

## Accepted (no fixed version exists)

Review each one when its advisory publishes a patched version, or at the latest
on **2027-01-11**. When a fix ships, add an npm override for it and move the
row to "Fixed".

| Package | Advisory | Severity | Pulled in by | Why accepted |
|---------|----------|----------|--------------|--------------|
| node-forge ≤ 1.4.0 (latest is 1.4.0) | [GHSA-86w9-cpqp-85rv](https://github.com/advisories/GHSA-86w9-cpqp-85rv) — RSA PKCS#1 v1.5 signature verification accepts extra nested DigestAlgorithm elements | High | @expo/code-signing-certificates, @expo/cli | Only used by the Expo CLI on the developer machine (code-signing certificate generation). Neither app depends on expo-updates, so nothing verifies signatures with it at runtime. No patched release. |
| braces ≤ 3.0.3 (latest is 3.0.3) | [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) — stack exhaustion DoS from deeply nested patterns | High | micromatch → Metro, Jest | Only processes glob patterns written by us in build/test config. Worst case is a crashed local build. No patched release. |
| sprintf-js ≤ 1.1.3 (installed 1.0.3) | [GHSA-hp3w-g68c-fv3c](https://github.com/advisories/GHSA-hp3w-g68c-fv3c) — DoS via unbounded precision specifiers | Moderate | argparse → js-yaml 3 → babel-plugin-istanbul (Jest coverage) | Only formats strings inside test tooling. No patched release. |

`npm audit` counts every package that depends on these three (43 "high" in
msmobile, 21 in nmmobile). Those counts are the same three advisories, not
separate problems.

---

## Rules

- **Do not run `npm audit fix --force`** or apply its suggestions. For these
  advisories it proposes downgrading `expo` to 44.0.6 or jumping `react-native`
  to 0.87, both of which break the apps without fixing anything. Use targeted
  `overrides` in `package.json` instead, then refresh the lock with
  `npm install --package-lock-only --ignore-scripts`.
- **nmmobile stays on its Expo canary build** (`55.0.20-canary-20260327-0789fbc`)
  for now, by decision on 2026-10-11. Dependabot is told to ignore Expo packages
  there (see `.github/dependabot.yml`).
- Python: `requirements.txt` and `requirements.lock` must pin identical versions
  (`tests/test_requirements_sync.py`); see B53.
