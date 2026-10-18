# Project history

How this project was planned and built. These documents are kept for transparency; they describe the process, not the final results (see the [write-up](../../reports/writeup.md) and [technical findings](../findings.md) for those).

## Documents

| File | What it is |
|---|---|
| [`proposal.md`](proposal.md) | The original research proposal: questions, hypotheses, data availability and the planned method. |
| [`plan.md`](plan.md) | The implementation plan for turning the proposal into a portfolio project, with design decisions and a progress log. |
| [`specs/`](specs/) | The build specifications, in order: one specification and one kick-off prompt per stage. |

## How the work was done

The project was built in four stages with an AI coding assistant (Claude Code) writing and running the code, and each stage checked before the next one started:

1. **Pipeline** ([spec](specs/01_TASK_pipeline_steps_1-5.md)): download, load, cohorts, panel and quality checks. A pilot run on the raw data first surfaced the truncated snapshots, duplicate rows and rounding problem, so the specification could require fixes for them.
2. **Analysis** ([spec](specs/02_TASK_analysis.md)): figures, the event study, the hype regressions, the trust rule and the robustness grid. Sanity values were computed independently beforehand, and the analysis had to reproduce them.
3. **Dashboard** ([spec](specs/04_TASK_dashboard.md)): new key numbers and figures from the review, the Streamlit app and the static page. Only aggregate data is published.
4. **Publishing** ([spec](specs/06_TASK_publish.md)): README, licence, continuous integration, a privacy scan of the git history and deployment.

Every specification fixed the research definitions up front (sample, outcome, model specifications) and required that a null or reversed result be reported as found. That is why the main hypothesis, that hyped games fade more, is reported as not supported.
