# EUCAST MIC Breakpoint Interpreter

### [Open the Live Application →](https://abusuraihsakhri.github.io/eucast-mic-breakpoint-interpreter/)

A local MIC categorisation utility for microbiology education, laboratory review, and development testing. It compares a reported MIC (mg/L) with **user-supplied, verified** EUCAST susceptible (S ≤) and resistant (R >) cutoffs. No official breakpoint table is embedded or downloaded.

**Clinical limitation:** This is not a validated diagnostic device or a substitute for laboratory interpretation. Check the organism identification, antimicrobial, infection site, exposure/dosing regimen, special instructions, notes, testing method, ATU, and current breakpoint edition before relying on a result. Never use example thresholds as clinical breakpoints.

## Features

- Interpret exact or qualified MICs (for example `1`, `<=0.25`, `>8`) without converting censored results into false exact values.
- Return **S**, **I** (susceptible, increased exposure), **R**, **ATU** (review), or **UNDETERMINED**.
- Refuse missing breakpoint information and non-finite/invalid measurements.
- Run entirely in the browser using the static `web/index.html`, with downloadable JSON.
- Run one sample or a CSV batch using the dependency-free Python core.
- Optional FastAPI endpoint at `POST /api/interpret`. Existing auxiliary audit and simulation commands remain separate from MIC interpretation.

## Browser use

Open `web/index.html` locally, or use the GitHub Pages deployment after its status has been verified. Enter the organism, antimicrobial, reported MIC, S ≤ and R > numerical thresholds, and the table version/source. Optional ATU limits must be entered together. The page contains **no backend calls**, external JavaScript dependencies, or automatic clinical breakpoint updates. Inputs are not transmitted to this project by the browser application.

Official EUCAST documents:
- [Clinical breakpoint tables](https://www.eucast.org/bacteria/clinical-breakpoints-and-interpretation/clinical-breakpoint-tables/)
- [Definitions of S, I and R](https://www.eucast.org/bacteria/clinical-breakpoints-and-interpretation/definition-of-s-i-and-r/)
- [Area of Technical Uncertainty guidance](https://www.eucast.org/bacteria/guidance-documents/)

As of October 2026, the bacterial clinical breakpoint tables are **version 16.1** (24 June 2026). Confirm the current version directly with EUCAST before use.

## Python CLI

Requires Python 3.10 or newer. The core interpreter uses only the standard library.

```bash
python eucast_interpreter.py single \
  --organism "Example species" --antimicrobial "Example agent" \
  --mic 2 --s-le 1 --r-gt 8 --breakpoint-version "ILLUSTRATIVE ONLY"
```

The thresholds above are **not clinical data**. A censored result may be supplied with `--mic '<=0.25'` or `--mic '>8'`.

```bash
python eucast_interpreter.py batch -i sample.csv -o results.csv
```

Required CSV headers: `organism,antimicrobial,mic,s_le,r_gt,breakpoint_version`. Optional: `atu_low,atu_high`. Each row is interpreted using its own breakpoints. Invalid rows are flagged `INVALID` with an explanation; they are not assigned an S/I/R category. The output is limited to interpretation fields, and spreadsheet-formula prefixes are escaped in exported text fields. CSV size is limited to 10 MiB and 50,000 rows.

## Server and auxiliary audit tools

```bash
python -m pip install -e ".[test]"
python cli.py serve --host 127.0.0.1 --port 8000
```

Example `POST /api/interpret` request:

```json
{
  "organism": "Example species",
  "antimicrobial": "Example agent",
  "mic": "2",
  "s_le": "1",
  "r_gt": "8",
  "breakpoint_version": "ILLUSTRATIVE ONLY"
}
```

The existing `cli.py audit`, `chat`, `batch`, and `verify-audit` commands and `/api/audit` endpoint support a separate generic auxiliary audit prototype. Their arbitrary numeric thresholds, mock language responses and in-memory audit records are **not EUCAST susceptibility interpretations** and must not be used for clinical decision-making. Audit signatures require a stable secret across restarts; set `AUDIT_SECRET_KEY` through your deployment environment, never in source control.

For Docker Compose, set `AUDIT_SECRET_KEY` to a long random value in your shell or an untracked environment file before running `docker compose up --build`.

## Development and tests

```bash
python -m pip install -e ".[test]"
python -m pytest -q
python -m compileall -q eucast_interpreter.py cli.py agents
```

GitHub Actions tests Python 3.10–3.13 and checks the browser JavaScript syntax. A separate workflow publishes `web/` to GitHub Pages on pushes to `master` where repository Pages settings allow GitHub Actions deployment. The static browser interface does not need Pyodide or a Python server. Build/test coverage does not constitute clinical validation.

## Technology, privacy, and license

Python standard library, FastAPI/Pydantic/Uvicorn for the optional server, and plain HTML/CSS/JavaScript for the browser. Current Chromium, Firefox, and Safari are the intended browser targets; no automated cross-browser test suite is provided. The browser stores no persistent user data. Server-side requests and audit functions are outside the static browser application's privacy guarantees and should not receive identifiable patient information. MIT licensed: see [LICENSE](LICENSE).
