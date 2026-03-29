---
name: csv-analyzer
description: >
  Analyze CSV files and generate summary reports with charts. Use when the user
  asks to analyze, summarize, or visualize CSV data. Triggers on phrases like
  "analyze this CSV", "summarize this data", "chart this spreadsheet".
allowed-tools: Read Bash Write Glob
license: Apache-2.0
metadata:
  author: testuser
  version: "1.0"
---

# CSV Analyzer

Analyze CSV files and produce a structured summary with optional visualizations.

## Step 1: Parse Input

Determine the CSV file path from the user's message.

- If the user provides a path, validate it exists
- If ambiguous, ask for clarification

## Step 2: Pre-process

Run the deterministic pre-processor to extract column types and basic stats:

```bash
python3 <skill-dir>/scripts/preprocess.py <csv-path> <work-dir>/stats.json
```

## Step 3: Deep Analysis

Read `<skill-dir>/references/analysis-guide.md` for the analysis methodology.

Analyze the data considering:
- Distribution of numeric columns
- Cardinality of categorical columns
- Missing value patterns
- Correlations between columns

## Step 4: Generate Report

Use the Write tool to create a markdown report at `<work-dir>/report.md` with:

- Executive summary
- Column-by-column analysis
- Key findings
- Recommendations

## Error Handling

If the CSV is malformed or empty, report the error clearly and stop.
If a column type cannot be determined, flag it as "unknown" and continue.
