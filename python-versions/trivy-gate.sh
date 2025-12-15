#!/usr/bin/env bash
set -euo pipefail

# --- Help / Documentation ---
show_help() {
    cat << EOF
Trivy Security Gate
-------------------
Analyzes Trivy JSON reports (Vulnerabilities & Secrets) and enforces a security gate
based on severity thresholds.

Usage: 
  $(basename "$0") [VULN_JSON] [OUTPUT_JSON] [SECRET_JSON]

Arguments:
  VULN_JSON    Path to the Trivy Vulnerability JSON report (Default: /tmp/artifact/trivy-report.json)
  OUTPUT_JSON  Path where the gate result JSON will be written (Default: /tmp/artifact/trivy-gate-result.json)
  SECRET_JSON  (Optional) Path to the Trivy Secrets JSON report.

Environment Variables (Thresholds):
  FAIL_ON_CRITICAL  Set to '1' to block on Critical vulnerabilities (Default: 1)
  FAIL_ON_HIGH      Set to '1' to block on High vulnerabilities (Default: 1)
  FAIL_ON_MEDIUM    Set to '1' to block on Medium vulnerabilities (Default: 0)
  FAIL_ON_SECRET    Set to '1' to block on any found Secrets (Default: 1)

Exit Codes:
  0 - Gate Passed
  1 - Gate Failed (Blocking issues found)
  2 - Script Error (Missing dependencies or files)

Example:
  export FAIL_ON_HIGH=1
  ./trivy-gate.sh report.json result.json secrets.json
EOF
}

# Check for help flag
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    show_help
    exit 0
fi

# --- Inputs ---
VULN_JSON="${1:-/tmp/artifact/trivy-report.json}"
GATE_RESULT="${2:-/tmp/artifact/trivy-gate-result.json}"
SECRET_JSON="${3:-}" # Optional 3rd argument

log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"; }

# --- 1. Validation & Setup ---

# Validate dependencies
if ! command -v jq >/dev/null 2>&1; then log "ERROR: 'jq' missing."; exit 2; fi

# Validate Vuln File
if [ ! -f "$VULN_JSON" ]; then log "ERROR: Vulnerability report not found at $VULN_JSON"; exit 2; fi

# Validate Secret File (if provided)
SECRET_JQ_ARG="--argjson secrets []"
if [ -n "$SECRET_JSON" ]; then
    if [ -f "$SECRET_JSON" ]; then
        log "Secret report detected: $SECRET_JSON"
        SECRET_JQ_ARG="--slurpfile secrets $SECRET_JSON"
    else
        log "WARN: Secret report path provided ($SECRET_JSON) but file not found. Skipping secrets."
    fi
fi

# Ensure output directory
mkdir -p "$(dirname "$GATE_RESULT")"

# Validate Thresholds (Coerce to 0 if invalid/unset, strict 1 enables)
for var in FAIL_ON_CRITICAL FAIL_ON_HIGH FAIL_ON_MEDIUM FAIL_ON_SECRET; do
    val="${!var:-0}"
    # Default FAIL_ON_CRITICAL and FAIL_ON_SECRET to 1 if not set in env, else 0? 
    # Actually, let's respect the user's environment or default inside the script logic.
    # Below defaults: CRITICAL=1, SECRET=1, others=0
    if [[ -z "${!var:-}" ]]; then
        case "$var" in 
            FAIL_ON_CRITICAL|FAIL_ON_HIGH|FAIL_ON_SECRET) val=1 ;;
            *) val=0 ;;
        esac
    fi
    [[ "$val" != "1" ]] && export "$var"=0 || export "$var"=1
done

log "--- Parsing Trivy Results ---"
log "Thresholds: CRITICAL=${FAIL_ON_CRITICAL} HIGH=${FAIL_ON_HIGH} MEDIUM=${FAIL_ON_MEDIUM} SECRETS=${FAIL_ON_SECRET}"

# --- 2. Analysis ---
# We pass the secrets file (or empty array) into jq using the variable argument we constructed above.

stats=$(jq -n \
    $SECRET_JQ_ARG \
    --argjson fail_crit "$FAIL_ON_CRITICAL" \
    --argjson fail_high "$FAIL_ON_HIGH" \
    --argjson fail_med  "$FAIL_ON_MEDIUM" \
    --argjson fail_sec  "$FAIL_ON_SECRET" \
    --slurpfile input "$VULN_JSON" \
    '
    # 1. Process Vulnerabilities
    [ $input[].Results[]? | .Target as $t | .Vulnerabilities[]? | . + {Target: $t, Type: "Vulnerability"} ] as $vulns |
    
    # 2. Process Secrets (Flatten similarly)
    [ $secrets[].Results[]? | .Target as $t | .Secrets[]? | . + {Target: $t, Type: "Secret", Severity: "SECRET"} ] as $sec_items |

    # 3. Count Stats
    ($vulns | map(select(.Severity == "CRITICAL")) | length) as $c |
    ($vulns | map(select(.Severity == "HIGH"))     | length) as $h |
    ($vulns | map(select(.Severity == "MEDIUM"))   | length) as $m |
    ($sec_items | length) as $s |

    # 4. Determine Block Status
    ($c > 0 and $fail_crit == 1) as $block_c |
    ($h > 0 and $fail_high == 1) as $block_h |
    ($m > 0 and $fail_med  == 1) as $block_m |
    ($s > 0 and $fail_sec  == 1) as $block_s |
    
    # 5. Compile List of Blocking Items (for logs)
    (
        ($vulns | map(select(
            (.Severity == "CRITICAL" and $block_c) or
            (.Severity == "HIGH"     and $block_h) or
            (.Severity == "MEDIUM"   and $block_m)
        ))) 
        + 
        ($sec_items | map(select($block_s)))
    ) as $blocking_list |

    # 6. Output Object
    {
        critical: $c,
        high: $h,
        medium: $m,
        secrets: $s,
        block: ($block_c or $block_h or $block_m or $block_s),
        reasons: [
            (if $block_c then "critical" else empty end),
            (if $block_h then "high" else empty end),
            (if $block_m then "medium" else empty end),
            (if $block_s then "secrets" else empty end)
        ],
        blocking_items: $blocking_list
    }
    ')

# Extract Decision
should_block=$(echo "$stats" | jq '.block')

# --- 3. Output ---
# Write JSON (exclude verbose list)
echo "$stats" | jq 'del(.blocking_items)' > "$GATE_RESULT" || { log "ERROR: Write failed"; exit 2; }

# Log Results
summary=$(echo "$stats" | jq -r '"CRITICAL=\(.critical) HIGH=\(.high) MEDIUM=\(.medium) SECRETS=\(.secrets)"')
log "Analysis Complete: $summary"

if [ "$should_block" = "true" ]; then
    log "!!! GATE FAILED: Blocking issues found !!!"
    
    # Print formatted list. Handle optional fields safely.
    echo "$stats" | jq -r '
        .blocking_items[]? | 
        if .Type == "Secret" then
            "  - [SECRET] \(.Title // .RuleID) in \(.Target)"
        else
            "  - [\(.Severity)] \(.PkgName) (\(.VulnerabilityID)) in \(.Target) -> Fixed: \(.FixedVersion // "Not Fixed")"
        end
    '
    exit 1
else
    log "GATE PASSED."
    exit 0
fi