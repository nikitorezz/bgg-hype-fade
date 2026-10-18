# Kickoff prompt for Claude Code

> **Archived build specification** given to an AI coding assistant (Claude Code) during the project; see [`../README.md`](../README.md) for context. Section references to `docs/data_notes.md` point to an earlier version of that file.

Open Claude Code in the project folder:

```
cd "G:\PROJECTS\Data Analytics\Personal\BGG Hype Fade"
claude
```

Optionally press **Shift+Tab** until you're in *plan mode* first, so Claude Code shows its plan before writing code. Then paste the prompt below.

---

```text
You're building the data pipeline for my portfolio project "Does the Hype Fade?" (BoardGameGeek post-release rating trajectories).

Read these files before doing anything else, in this order:
1. CLAUDE.md: project context, environment (Windows, path with spaces, no make), conventions, research rules you must not change
2. docs/data_notes.md: verified facts about the data, including the traps (truncated snapshot files, duplicate rows, 2-decimal rounding)
3. docs/project-history/specs/01_TASK_pipeline_steps_1-5.md: the full spec with acceptance criteria
4. config.yaml: all parameters (already filled in; don't hard-code values from it)

Scope: pipeline steps 1–5 only (download → load → cohorts → panel → quality checks). Build everything from scratch; the folder has only docs and config so far.

How to work:
- First check the environment (python version, uv, git), then give me a short plan with the stages and anything in the spec you think is wrong or ambiguous.
- Then build and RUN each stage in order. After each stage, check its acceptance criteria against the real data, commit, and move on.
- The download is ~700 MB from GitHub and I'm in mainland China. If the http backend is slow or blocked, tell me and switch to --backend git, or ask me to set HTTPS_PROXY.
- If an acceptance number doesn't match, investigate before changing anything. If the fix would change a research rule (entry/cohort definitions, new-release rule, outcome variable, new_avg usability rule), stop and ask me.
- Record any new data quirk in docs/data_notes.md.

When finished, give me: what was built, the QC summary (PASS/WARN/FAIL with explanations), deviations from the spec, and the exact commands to rerun everything.
```
