# Kickoff prompt for Claude Code: task 04 (polish + publish)

Open Claude Code in the project folder and paste:

```text
Task 03 (dashboard) has been reviewed. It's good, with a few fixes. Last task: task 04, final polish and publishing.

Read first:
1. CLAUDE.md
2. docs/handoff/06_TASK_publish.md: the spec (Parts A–E)
3. reports/writeup.md: now draft v2 (edited by my reviewer)
4. docs/deploy.md

Then:
- Short plan first; flag anything ambiguous.
- Part A (dashboard fixes) → Part B (README front page) → Part C (hygiene: README rendering, LICENSE, CI, pyproject, cleanup). Commit after each part.
- Part D: run the PII/secret scan, then ASK me before creating the GitHub repo or pushing anything. Ask me for the name to put on the MIT licence if git config doesn't have it.
- Part E is optional: ask me first.

When finished: what changed, new screenshots, CI status, the 10 largest tracked files, and a checklist of what I still need to do (e.g. Streamlit Cloud) plus which URLs to send back to you.
```
