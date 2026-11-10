# Labelling package: organiser notes (do not send to coders)

Built by `python3 scripts/labeling.py build -o validation/labeling` from the
blank sheets in `validation/`. Rebuilding is refused once any answer has been
imported. A rebuild also writes a copy of the guide into `coder-A/`, `coder-B/`,
`shared/` and `validation/labeling_src/`; the package keeps a single copy at
the top of this folder.

## What to send

| File | To |
|---|---|
| `coder-A/GHAgentCI-labeling-coder-A.xlsx` | coder A only |
| `coder-B/GHAgentCI-labeling-coder-B.xlsx` | coder B only |
| `GHAgentCI-coding-guide.pdf` | both coders |

Keep `shared/GHAgentCI-calibration.xlsx` yourself: it holds the 30 calibration
units, coded together on one copy in the joint session. Keep this file too.

Neither coder's workbook shows the detector's output, and A and B hold the same
units in the same order. Never send a coder the other's workbook, and do not
send `precision_sample.csv`, `recall_sample.csv` or anything else from
`validation/`.

## Before coding starts

1. Send each coder their workbook and the guide, so they can read the guide
   before calibration.
2. Run the calibration session with both coders on the shared workbook.
3. Settle Section 6 of the guide (the `actions/ai-inference` rule) and send the
   decision to both coders before they start: by email, or by filling it into
   `validation/labeling_src/guide.tex` and rebuilding the PDF.
4. Coders return their workbooks by 3 November 2026.

## When workbooks come back

Save them under `validation/returned/`, then:

```bash
python3 scripts/labeling.py import validation/returned/GHAgentCI-calibration.xlsx --calibration
python3 scripts/labeling.py import validation/returned/GHAgentCI-labeling-coder-A.xlsx --coder A
python3 scripts/labeling.py import validation/returned/GHAgentCI-labeling-coder-B.xlsx --coder B
python3 scripts/score_validation.py -d validation/      # writes precision_adjudication.csv
```

The import writes nothing if a unit is missing or unknown, or a value is
outside the codebook; it prints what to fix. Then adjudicate the Q1
disagreements in `precision_adjudication.csv` and `recall_adjudication.csv`
(fill `q1_final`), score again, and rebuild the paper (validation/PLAN.md).
