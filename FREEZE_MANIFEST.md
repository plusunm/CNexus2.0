# CNexus 2.0 Personal Edition — Freeze Manifest

> **Status:** `RC_FROZEN` — Release Candidate, **not** General Availability  
> **Target GA:** `v2.4.0` (pending desktop `tauri:build` verification)  
> **RC Tag:** `v2.4.0-rc.1`  
> **Manifest date:** 2026-06-22  
> **Strategy:** 所筑即所测 — build artifacts must match tested code exactly.

---

## Git baseline

| Field | Value |
|-------|-------|
| Branch | `main` |
| Parent commit (pre-RC) | `6aaca1c1efb74ea64441edaf5677b2f2fb81d5b2` |
| Parent message | Add runtime bootstrap, memory domain, and L3 project binding. |
| Previous GA tag | `v2.3.0` |
| RC tag (this freeze) | `v2.4.0-rc.1` → **this commit** |
| GA tag (deferred) | `v2.4.0` — **do not create until desktop gate passes** |

Resolve RC commit hash:

```bash
git rev-parse v2.4.0-rc.1
```

---

## Version pins (declared)

| Artifact | Version |
|----------|---------|
| Product (package.json) | `2.4.0` |
| Tauri (tauri.conf.json) | `2.4.0` |
| Python runtime | 3.10+ (gateway stdlib); bundle embed 3.11.9 |
| Node (build) | ≥ 20 |
| Next.js (lockfile) | 15.5.19 |
| PyNaCl | ≥ 1.5.0 |

---

## Dependency lock files (must match manifest commit)

| Lock file | Tracked |
|-----------|---------|
| `requirements.txt` | yes |
| `frontend/package-lock.json` | yes |
| `frontend/src-tauri/Cargo.lock` | yes |

---

## Verification gate (RC baseline)

| Gate | Command | Result at freeze |
|------|---------|------------------|
| Python tests | `python -m pytest tests/ -q` | **245 passed** |
| Frontend typecheck | `cd frontend && npm run typecheck` | **pass** |
| Static UI export | `cd frontend && npm run build:personal` | **pass** → `ui/` synced |
| Desktop toolchain | `npm run prebuild:toolchain` | **not run at RC** |
| Runtime bundle | `npm run bundle:runtime` | **not run at RC** |
| Tauri installer | `npm run tauri:build` | **BLOCKED — deferred to RC validation** |
| Smoke (live :7864) | `npm run prebuild:smoke` | **not run at RC** |

---

## Module freeze matrix

Legend: **FROZEN** = code + tests locked for RC · **PARTIAL** = functional but GA gate incomplete · **OPEN** = not in Personal GA scope

| Module | Path / entry | Freeze | Tests | Notes |
|--------|----------------|--------|-------|-------|
| **L0 Cognitive Kernel** | `src/kernel/` | **FROZEN** | `tests/kernel_compliance/*`, `test_kernel_*` | Six-step reducers; compliance suite green |
| **L5 Runtime (Constitution)** | `src/runtime/`, `runtime/constitution/`, `runtime/policy/` | **FROZEN** | `tests/test_runtime_bootstrap.py` | BOOT compile, Ed25519 sign/verify |
| **L1 Conversation Scratch** | `src/gateway/services/conversation_scratch.py` | **FROZEN** | `tests/test_project_binding.py` | Session-scoped; not in `memory_level` table |
| **L3 Project binding** | `src/gateway/services/memory/project.py`, `project_control.py` | **FROZEN** | `tests/test_project_binding.py` | `project_id` on Block; lock in `engine_state.active_project` |
| **L4 Foundation** | `src/gateway/services/memory/protection.py` | **FROZEN** | `tests/test_memory_protection.py` | append-only policy; UI promote button in frontend |
| **Memory Domain** | `src/gateway/services/memory/` | **FROZEN** | `tests/test_gateway_memory_*` | graph, query, rem, wormhole |
| **Identity / Ed25519** | `src/core/identity_manager.py`, `src/runtime/signing.py` | **FROZEN** | `tests/test_identity_manager.py`, bootstrap | `data/identity.key` never committed |
| **Gateway HTTP** | `app_v2.py`, `src/gateway/` | **FROZEN** | 245 pytest total | Modular services; static `ui/` on :7864 |
| **Shadow APIs** | `src/gateway/services/shadow_projection.py` | **FROZEN** | `tests/test_gateway_shadow_projection.py` | Personal → enterprise contract projection |
| **Ingest / multimodal** | `src/gateway/services/ingest.py` | **FROZEN** | `tests/test_gateway_ingest*.py` | Code AST + image routes |
| **Frontend UI** | `frontend/` → `ui/` | **FROZEN** | typecheck + build:personal | Static export committed in RC |
| **Build pipeline** | `scripts/prepare-build.ps1`, `scripts/prebuild-*` | **FROZEN** | manual | Personal Edition paths fixed (`../scripts/`) |
| **Desktop Tauri** | `frontend/src-tauri/` | **PARTIAL** | none automated | Sidecar targets `app_v2.py:7864`; **installer not verified** |
| **Runtime bundle** | `frontend/src-tauri/runtime-bundle/` | **OPEN** | `verify-runtime-bundle.ps1` | Generated at build time; gitignored |
| **Network / P2P** | `src/network/` | **OPEN** | various | Present but not Personal GA blocker |

---

## RC scope — what changed since v2.3.0

Included in this RC (already on `main` before build-prep commit):

- Runtime BOOT + Constitution compiler (`src/runtime/`)
- Memory domain extraction (`src/gateway/services/memory/`)
- L3 `project_id` binding + `active_project_lock`
- L1 Conversation Scratch
- Ed25519 bundle signing
- Frontend: Promote-to-L4, ActiveProjectBadge, RuntimeBootBadge, cognitive lab UI fixes

Included in build-prep commit (this manifest):

- Personal Edition build scripts under `scripts/`
- Version bump 2.4.0 in `package.json` / `tauri.conf.json`
- Rebuilt `ui/` static export
- `.gitignore` for build cache / runtime-bundle
- README build section
- Test fix: `test_gateway_memory_recall.py` (network scope for peer asset pull)

---

## Explicit RC blockers (must pass before `v2.4.0` GA tag)

1. `cd frontend && npm run prebuild:release` — toolchain + gate + smoke on clean machine  
2. `npm run bundle:runtime` — Personal runtime-bundle completes  
3. `npm run tauri:build` — NSIS installer or exe artifact produced  
4. Manual: install → float window → quit → no orphan on :7864  
5. Update this manifest: set status to `GA_FROZEN`, add GA tag + installer artifact SHA256  

---

## Reproducible web build (RC-verified)

```powershell
cd CNexus2.0
powershell -ExecutionPolicy Bypass -File scripts/prepare-build.ps1
python app_v2.py
# http://127.0.0.1:7864
```

---

## Integrity rule

After `v2.4.0-rc.1`:

- **No feature commits on `main`** until RC validation completes or RC.2 is declared.
- Hotfixes: cherry-pick to RC branch or tag `v2.4.0-rc.2` with manifest amendment.
- GA `v2.4.0` tag must point to **identical tree** as final RC pass (or document delta in RELEASE_NOTES).

---

*Generated as part of CNexus 2.0 Personal Edition release process.*
