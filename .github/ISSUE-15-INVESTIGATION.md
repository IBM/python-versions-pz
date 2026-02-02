# Issue #15 Investigation Summary

## Overview

This document summarizes the comprehensive investigation conducted for Issue #15, which examined multiple failures and risks in the Python release pipeline. The investigation clarified the distinction between **actual failures**, **initial assumptions**, and **design risks** that justified pipeline improvements.

---

## Timeline of Investigation

### Initial Observation
- CI jobs failed with `exec format error`
- Python setup step downloaded binaries for wrong architecture
- Initial hypothesis: manifest corruption affecting downstream users

### Root Cause Analysis
- Test workflow matrix passed `architecture` independently of `runs-on`
- Jobs declaring `ppc64le` or `s390x` actually ran on x64 GitHub-hosted runners
- Setup action selected non-x64 binaries, which failed on x64 hardware

### Scope Clarification
- **Actual impact**: CI testing only
- **User impact**: None - no releases, manifests, or downstream consumers affected
- **Design risks**: Multiple pipeline correctness risks identified during investigation

---

## Summary of Bugs and Root Causes

### 1. CI Testing Workflow: Wrong Binary Downloaded → `exec format error`

**Observed behavior**
* CI jobs failed with `exec format error`
* Python setup step downloaded a binary for the wrong architecture

**Root cause**
* The test workflow matrix passed `architecture` independently of `runs-on`
* Jobs declaring `ppc64le` or `s390x` were actually running on x64 GitHub-hosted runners
* The setup action selected a non-x64 binary, which failed to execute on x64

**Scope**
* CI testing only
* No releases, manifests, or users were affected

**Status**
* ✅ Fixed by explicitly binding runner labels to architecture (PR #20)

---

### 2. Incorrect Initial Assumption About User-Facing Impact

**Observed behavior**
* Early investigation assumed that users were receiving wrong binaries due to manifest corruption

**Root cause**
* CI failures and architecture mismatches produced symptoms that resembled a release/manifest issue
* Limited early visibility led to a broader initial hypothesis

**Scope**
* Investigation and documentation only

**Status**
* ✅ Clarified: no downstream or user-facing bug occurred

---

### 3. Release Pipeline Design Risk: Parallel Manifest Writes

**Observed risk**
* Multiple architecture jobs wrote directly to shared version manifests
* Retry + rebase logic was used to resolve conflicts

**Root cause**
* Parallel jobs were allowed to mutate shared, user-facing state
* Serialization was not enforced
* Retry logic masked race conditions instead of preventing them

**Scope**
* Real release pipeline correctness risk
* Could result in non-deterministic manifest contents under concurrency

**Status**
* ✅ Addressed by fan-in, single-writer manifest update model (PR #25)

---

### 4. Manifest Pollution Risk After Adding Trivy Artifacts

**Observed risk**
* Trivy SBOMs and scan reports were uploaded alongside release artifacts
* Manifest generation logic did not strictly filter artifact types

**Root cause**
* Manifest parsing assumed homogeneous release artifacts
* No explicit filtering or validation of artifact purpose or architecture

**Scope**
* Release pipeline correctness risk
* Could lead to incorrect URLs appearing in manifests

**Status**
* ✅ Addressed in manifest aggregation and validation design (PR #23)

---

### 5. Workflow Cancellation Due to Infrastructure Failures

**Observed behavior**
* Transient failures (e.g. `dotnet-install.py` on `s390x`) cancelled entire workflows
* Successful builds on other architectures were discarded

**Root cause**
* Architecture jobs were coupled via fail-fast behavior
* Infrastructure instability was allowed to affect release correctness

**Scope**
* Release reliability issue

**Status**
* ✅ Mitigated by:
  - Decoupling architecture jobs with `fail-fast: false` (PR #20)
  - Adding retry logic to dotnet-install.py (PR #22)

---

## Related Pull Requests

| PR # | Title | Addresses |
|------|-------|-----------|
| #20 | Fix CI testing workflow: bind architecture to runner labels | Bug #1, Risk #5 (CI-level) |
| #21 | Remove references to older manifests path | Manifest cleanup (unrelated to Issue #15) |
| #22 | Enhance build reliability and security scanning | Risk #5 (infrastructure failures) |
| #23 | Add partial manifest generation and application scripts | Foundation for Risk #3 & #4 |
| #24 | Add backfill workflow for manifest regeneration | Recovery tooling (uses PR #23) |
| #25 | Refactor release workflows for atomic manifest updates | Risk #3 (parallel manifest writes) |

---

## Final Clarification

* The **only confirmed failure** was a **CI testing workflow misconfiguration**
* **No downstream consumers or users were affected**
* The release pipeline analysis remains valuable as it identified **real design risks** that justified the proposed refactor

This summary reflects:
- ✅ What actually broke
- ✅ What was initially assumed
- ✅ What structural risks were correctly identified and addressed

---

## Lessons Learned

1. **CI testing should mirror production constraints**: Test workflows should enforce architectural constraints to catch misconfigurations early
2. **Fail-fast is not always desirable**: Decoupling architecture builds improves reliability when dealing with heterogeneous infrastructure
3. **Concurrent writes need explicit coordination**: Retry-based conflict resolution masks race conditions rather than preventing them
4. **Artifact types need explicit filtering**: Adding new artifact types (security reports) can pollute manifests without proper validation
5. **Investigation scope can expand productively**: While the initial bug was CI-only, the investigation revealed valuable design improvements

---

*Last updated: January 2026*
