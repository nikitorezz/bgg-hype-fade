# Kickoff prompt for Claude Code: task 03 (analysis polish + dashboard)

Open Claude Code in the project folder (plan mode recommended) and paste:

```text
The analysis (task 02) is done and has been reviewed. Next: task 03, analysis polish plus the interactive dashboard.

Read these first, in this order:
1. CLAUDE.md (scope updated)
2. docs/findings.md: the review of your analysis (verdict, interpreted findings F1–F9, the story, caveats, items for this task)
3. reports/writeup.md: the draft article; dashboard text must agree with it
4. docs/handoff/04_TASK_dashboard.md: the full spec (Parts A–D) with acceptance criteria

Then:
- Give me a short plan and flag anything in the spec you think is wrong or ambiguous before writing code.
- Do Part A first (new key numbers, figs 9–10, figure polish), rerun `bgg analysis`, check the review values, and look at every figure PNG yourself before committing.
- Then Part B (data extract) and Part C (Streamlit app). Run the app locally and check that every number matches key_numbers.json.
- Part D: prepare deployment and the static export, but DON'T deploy. Ask me the D0 data-publication question and include the drafted GitHub issue text.
- If a new number contradicts docs/findings.md or reports/writeup.md, tell me; don't silently edit the write-up.

When finished: what was built, screenshots of each dashboard section, any numbers that changed, and the D0 question.
```
