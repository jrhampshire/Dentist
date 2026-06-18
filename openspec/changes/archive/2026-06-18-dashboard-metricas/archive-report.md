# Archive Report — dashboard-metricas

**Archived**: 2026-06-18
**Status**: PASS WITH WARNINGS
**Artifact Store**: openspec (file-backed)

---

## Precondition Evaluation

| Precondition | Result |
|---|---|
| Verify report present | ✅ `verify-report.md` |
| Verify report passing | ✅ PASS WITH WARNINGS — no CRITICAL/Fail/Blocked |
| Required artifacts (proposal, design) | ✅ `proposal.md`, `design.md` |
| Specs artifact | N/A — no `specs/` directory; no domain specs to sync |
| Sync report | N/A — no canonical specs to merge; sync not required |
| Config rules (`openspec/config.yaml`) | N/A — file does not exist |
| Tasks artifact (`tasks.md`) | N/A — tasks were tracked in design.md; no separate tasks.md |
| Final task completion gate | ✅ No `tasks.md` with unchecked `- [ ]` markers; all 10 tasks confirmed complete in verify-report |
| Destructive merge guard | N/A — no specs to sync, no REMOVED/MODIFIED operations |
| Same-domain active changes | ✅ None |

---

## Artifacts Read

1. **proposal.md** — Change proposal: backend metrics endpoint + Recharts dashboard visualization. Defines 7 success criteria, 4 key decisions, risk assessment, and out-of-scope items.
2. **design.md** — Technical design: DashboardMetricsViewSet with rich response schema (11 metric builders), architecture decisions (ViewSet pattern, clinic access, trend gap-filling, upcoming appointments). Defines file changes, interfaces, and testing strategy.
3. **verify-report.md** — Verification results: 10/10 tasks complete, 11/12 backend specs compliant, 1 test assertion bug (not implementation), 3 TS type errors (Recharts 3.x types only).

---

## Verification Summary

### Backend Tests: 11/12 passed

- **11 compliant scenarios**: structure, revenue accuracy (2 tests), tenant isolation (revenue trend), empty state, auth, appointments today, appointment trend, patients this month, upcoming appointments (2 tests)
- **1 failed (test-bug)**: `test_clinic_a_does_not_see_clinic_b_data` — asserts `patients_total == 1` but fixture creates 2 patients (appointment fixture implicitly creates a patient). The **implementation is correct** — same filtering logic passes in `test_revenue_trend_excludes_other_clinics`. Correct assertion would be `== 2`.

### Frontend TypeScript: 3 type errors (non-runtime)

- `DashboardPage.tsx` lines 211, 212, 245: Recharts 3.x Tooltip formatter type mismatches
- Root cause: Recharts 3.x introduced stricter `Tooltip` formatter callbacks; design specified `^2.12.0` but implementation installed `^3.8.1`
- Impact: type-checking only; runtime behavior unaffected

### Warnings Recorded

| # | Warning | Severity | Resolution |
|---|---------|----------|------------|
| 1 | Tenant isolation test asserts wrong patient count | Low — test-bug, implementation correct | Fix assertion to `== 2` in follow-up |
| 2 | 3 TS Tooltip type errors from Recharts 3.x | Low — type-checking only | Add explicit formatter types or downgrade to `^2.12.0` in follow-up |

---

## Sync Summary

**No sync performed** — this change has no `specs/` directory and no domain spec artifacts. The change scope (dashboard metrics) does not modify any existing canonical domain specs. No `ADDED`, `MODIFIED`, or `REMOVED` requirements are recorded.

---

## Task Completion Gate

| Check | Result |
|---|---|
| `tasks.md` exists | ❌ No — tasks tracked in design.md |
| Unchecked `- [ ]` markers | N/A — no tasks.md file |
| Tasks complete per verify report | ✅ 10/10 |
| Stale-checkbox reconciliation | N/A — no tasks.md with unchecked boxes |

---

## Structured Status Findings

- **changeName**: `dashboard-metricas` (resolved by parent delegation)
- **artifactStore**: `openspec`
- **actionContext.mode**: `repo-local`
- **allowedEditRoots**: `D:\Programacion\Dentist`
- **dependencies**: All phases (`apply`, `verify`, `sync`, `archive`) marked `blocked` by status engine due to ambiguous change selection — overridden by explicit parent delegation to archive this specific change
- **No collisions, no conflicts, no superseded/amended changes**

---

## Destructive Merge

N/A — no canonical specs modified. No REMOVED requirements. No destructive operations.

---

## Archive Path

```
openspec/changes/archive/2026-06-18-dashboard-metricas/
```

---

## Post-Archive Recommendations

1. Fix tenant isolation test assertion (`patients_total == 2` instead of `== 1`)
2. Resolve Recharts 3.x Tooltip type errors in `DashboardPage.tsx` (add explicit formatter types)
3. Consider creating a `specs/` directory for future changes to track formal spec compliance
4. Consider creating a `tasks.md` for future changes to enable proper SDD task-checkbox gating

---

**Verdict**: Archive approved. No critical blockers. Two low-severity warnings carried forward for follow-up work.
