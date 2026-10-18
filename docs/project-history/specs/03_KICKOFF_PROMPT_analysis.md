# Kickoff prompt for Claude Code: task 02 (analysis)

> **Archived build specification** given to an AI coding assistant (Claude Code) during the project; see [`../README.md`](../README.md) for context. Section references to `docs/data_notes.md` point to an earlier version of that file.

Open Claude Code in the project folder (plan mode recommended, Shift+Tab) and paste:

```text
The pipeline (task 01) is done and committed. Next is the analysis: milestones M3–M5.

Read these first, in this order:
1. CLAUDE.md (scope has been updated; note the new research rule about specifications)
2. docs/data_notes.md, especially §10 (pipeline facts) and §11 (analysis pre-checks with sanity values)
3. docs/project-history/specs/02_TASK_analysis.md: the full spec with fixed definitions, model specs, outputs and acceptance values
4. config.yaml (add an `analysis:` section for every new parameter)

Then:
- Give me a short plan and flag anything in the spec you think is wrong or ambiguous before writing code.
- Build and RUN the steps in order (descriptives → segments → event study → hype regressions → Q4 → robustness → key numbers). After each step, compare against the §11 sanity values, commit, and move on.
- Report results honestly. If H2 (hyped games fade more) is not supported, say so; don't search for a specification that supports it.
- Q3 (crowdfunding) is optional: run it only if data/external/kaggle_bgg/ exists; otherwise skip cleanly.
- Don't build the dashboard or write narrative text yet.

When finished, give me: the headline-numbers table from reports/results/key_numbers.json, any acceptance value that differed and why, what was skipped, and the rerun commands.
```

**Optional, before starting (for Q3):** download the Kaggle dataset "Board Game Database from BoardGameGeek" (by threnjen) and unzip it into `data/external/kaggle_bgg/`. Without it, Q3 is skipped and everything else still runs.
