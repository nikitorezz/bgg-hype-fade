# Documentation

| Document | What it covers |
|---|---|
| [Write-up](../reports/writeup.md) | The article: question, data, findings, what a platform could do, limitations. Start here. |
| [Technical findings](findings.md) | Every finding with estimates and intervals, the model specifications, validation and caveats. |
| [Data notes](data_notes.md) | The source data, its quality problems and fixes, sample construction, metric definitions and analysis traps. |
| [Deployment](deploy.md) | Where the results are published, what is (and isn't) published, and how to update it. |
| [Project history](project-history/) | The original proposal, the plan and the build specifications, kept for transparency. |

Generated reports:

- [`reports/results/results_summary.md`](../reports/results/results_summary.md): every headline number with its interval and source
- [`reports/results/`](../reports/results/): model tables (event study, hype regressions, crowdfunding, robustness)
- [`reports/qc/qc_report.md`](../reports/qc/qc_report.md): the 36 automated data-quality checks

All numbers in the documentation come from [`reports/results/key_numbers.json`](../reports/results/key_numbers.json).
