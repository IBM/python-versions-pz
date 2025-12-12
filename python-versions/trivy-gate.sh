#!/bin/sh
set +e

# Logging Helper
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Inputs
VULN_JSON=${1:-/tmp/artifact/trivy-${PYTHON_VERSION}-${TARGETARCH}-vuln.json}
SECRET_JSON=${2:-/tmp/artifact/trivy-${PYTHON_VERSION}-${TARGETARCH}-secret.json}
GATE_RESULT=/tmp/artifact/trivy-gate-result.json
FLAT_REPORT=/tmp/artifact/trivy-flat-report.json

# Thresholds
FAIL_ON_CRITICAL=${FAIL_ON_CRITICAL:-1}
FAIL_ON_HIGH=${FAIL_ON_HIGH:-0}
FAIL_ON_MEDIUM=${FAIL_ON_MEDIUM:-0}
FAIL_ON_SECRET=${FAIL_ON_SECRET:-1}

log "--- Parsing Trivy Results ---"

# 1. FLATTEN THE DATA
if [ -f "$VULN_JSON" ]; then
    log "Flattening vulnerability report..."
    jq '[.Results[] | .Target as $t | .Vulnerabilities[]? | . + {"Target": $t}]' "$VULN_JSON" > "$FLAT_REPORT"
else
    log "No vulnerability report found. Assuming 0 vulnerabilities."
    echo "[]" > "$FLAT_REPORT"
fi

# 2. ANALYZE SEVERITY
critical=$(jq '[.[] | select(.Severity=="CRITICAL")] | length' "$FLAT_REPORT")
high=$(jq '[.[] | select(.Severity=="HIGH")] | length' "$FLAT_REPORT")
medium=$(jq '[.[] | select(.Severity=="MEDIUM")] | length' "$FLAT_REPORT")

if [ -f "$SECRET_JSON" ]; then
    secrets=$(jq '[.Results[].Secrets[]?] | length' "$SECRET_JSON" 2>/dev/null || echo 0)
else
    secrets=0
fi

log "Analysis Complete: CRITICAL=$critical HIGH=$high MEDIUM=$medium SECRETS=$secrets"

# 3. DETAILED LOGGING
if [ "$critical" -gt 0 ]; then
    log "!!! CRITICAL VULNERABILITIES FOUND !!!"
    jq -r '.[] | select(.Severity=="CRITICAL") | "  - [$t] \(.PkgName) (\(.VulnerabilityID)) in \(.Target)"' "$FLAT_REPORT"
fi

# 4. DECISION LOGIC
BLOCK=false
REASON="none"

# Check in priority order: CRITICAL > HIGH > MEDIUM > SECRETS
if [ "$FAIL_ON_CRITICAL" -eq 1 ] && [ "$critical" -gt 0 ]; then BLOCK=true; REASON="critical"; fi
if [ "$FAIL_ON_HIGH" -eq 1 ] && [ "$high" -gt 0 ] && [ "$REASON" = "none" ]; then BLOCK=true; REASON="high"; fi
if [ "$FAIL_ON_MEDIUM" -eq 1 ] && [ "$medium" -gt 0 ] && [ "$REASON" = "none" ]; then BLOCK=true; REASON="medium"; fi
if [ "$FAIL_ON_SECRET" -eq 1 ] && [ "$secrets" -gt 0 ] && [ "$REASON" = "none" ]; then BLOCK=true; REASON="secrets"; fi

printf '{"critical":%d,"high":%d,"medium":%d,"secrets":%d,"block":%s,"reason":"%s"}\n' "$critical" "$high" "$medium" "$secrets" "$BLOCK" "$REASON" > "$GATE_RESULT"

if [ "$BLOCK" = "true" ]; then
    log "GATE FAILED: Blocking due to $REASON severity."
    exit 1
else
    log "GATE PASSED."
    exit 0
fi
