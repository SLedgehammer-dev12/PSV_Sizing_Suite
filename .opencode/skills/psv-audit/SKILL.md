---
name: psv-audit
description: Performs a comprehensive audit of the PSV Sizing Suite codebase. Finds security vulnerabilities, code quality issues, engineering formula errors, test coverage gaps, and build problems. Produces a severity-ranked report. USE FOR: audit the code, security review, code quality check, find bugs, full codebase review, analyze project health, comprehensive check.
---

# PSV Sizing Suite — Full Project Audit

## Overview
Launch all three audit agents in parallel (`psv-core`, `psv-desktop`, `psv-auditor`) to perform a comprehensive project audit. Each agent specializes in a different domain:

| Agent | Domain | Files |
|-------|--------|-------|
| `psv-core` | Engineering correctness | `core/*.py` (13 files) |
| `psv-desktop` | Desktop app + Web app | `desktop/*.py`, `*.py`, `web_app.py` |
| `psv-auditor` | Security + Code quality + Build | All files |

## Workflow

### Step 1: Launch parallel audits
Use the Task tool to launch all three agents simultaneously:

```
Task: psv-core → "Very thorough analysis of all core/ modules..."
Task: psv-desktop → "Very thorough analysis of all desktop/ modules..."
Task: psv-auditor → "Comprehensive security and code quality audit..."
```

### Step 2: Consolidate findings
Merge the three reports into a single unified report:
1. Deduplicate findings that appear in multiple reports
2. Re-rank by unified severity
3. Group by category: Engineering | Security | Code Quality | Build/Deploy | Testing

### Step 3: Present action plan
Present the top 10 most critical findings with concrete fix instructions.

## Agent prompts
Use these exact prompts with the Task tool for consistent results:

**psv-core prompt:**
"Read all files in D:\İş\Çalışan programlar\@Güncelleme\PSV_Sizing_Suite\core\ completely. Analyze every module for: 1) API 520/521 formula correctness, 2) Unit conversion errors, 3) Division by zero risks, 4) NaN/inf propagation, 5) Missing correction factors, 6) Dead code and unreachable branches, 7) Magic numbers, 8) Missing validation. Return a structured report with file:line references organized by severity."

**psv-desktop prompt:**
"Read all files in D:\İş\Çalışan programlar\@Güncelleme\PSV_Sizing_Suite\desktop\ plus main.py, web_app.py, run_streamlit.py. Analyze for: 1) UI thread safety and QThread issues, 2) Auth vulnerabilities, 3) Save/load correctness, 4) Duplicate code across tabs, 5) Signal/slot correctness, 6) Build/deploy issues. Return structured report with file:line references."

**psv-auditor prompt:**
"Read all files in the project root, core/, desktop/, tests/, and scripts/. Perform a comprehensive security and code quality audit: 1) Hardcoded secrets/credentials, 2) Input validation gaps, 3) Dead code and unused imports, 4) Test quality and coverage gaps, 5) Build script issues, 6) Documentation gaps, 7) Dependency management. Return structured report with file:line references."

## Output format
Present the final consolidated report as a markdown table with columns:
| Severity | Category | File:Line | Issue | Fix |
|----------|----------|-----------|-------|-----|
