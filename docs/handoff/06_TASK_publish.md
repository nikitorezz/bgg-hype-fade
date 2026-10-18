# Task 04: Final polish and publish (milestone M7)

**Goal:** turn the finished project into a public portfolio piece. A recruiter landing on the GitHub repo should get the finding in 2 minutes, click through to a live dashboard, and see a clean, tested, reproducible codebase.

Read first: `CLAUDE.md`, `docs/findings.md`, `reports/writeup.md` (**now draft v2**, edited by the user's reviewer), `docs/deploy.md`.

Same rules: numbers come only from key_numbers/tables; config-driven; commit per step; `reports/writeup.md` and `docs/findings.md` are the user's documents. You may fill in the link placeholders in the write-up, but report any other contradiction instead of editing.

---

## Part A: Dashboard fixes (found in review)

1. **Trust sliders in aggregates mode.** The public app runs in aggregates mode, where only the 0.25/0.5 tolerances exist, so the tolerance slider is mostly dead. Precompute `q4_accuracy_by_k` for tolerances **0.10 to 0.50 in 0.05 steps** (an aggregate table, no game-level data) and ship it in `app/data/tables/`. Then both sliders work in both modes. Snap the tolerance slider to those steps.
2. **One rounding helper.** The hype takeaway shows "0.41 vs 0.36", while the write-up says −0.37 (key value −0.3654: float rounding of 0.365). Use one formatting function across the app, the figure titles and the static export, with `decimal.Decimal` half-up rounding. Grep for other hand-rolled `round(`/f-string formats in `app/` and `src/bgg/plots.py`.
3. **Sample waterfall table:** thousands separators; show "–" instead of "None"; hide the index column.
4. **Overview:** drop the duplicated heading ("Does the hype fade?" appears twice). Add markers + labels at k = 12/24/36 on the main curve, as in Fig 1.
5. **Replace the lost "Look up a game" section** with an aggregates-safe **"Explore segments"** section: pick a segment type (launch year, hype quartile, starting-rating decile, popularity, Kickstarted) and see its curve against the overall curve, plus a small table of change_12/change_36 with CIs (from `segments.csv` / `curve_by_segment.csv`). No game names, no per-game data.
6. Re-take the screenshots (desktop + mobile) and re-run the app tests.

## Part B: README as the portfolio front page

Rewrite `README.md` (keep the technical "Run" section, moved lower). Structure:
1. Title + one-line subtitle + **badges** (CI status, Python version, licence).
2. `social_card.png` (or Fig 1) as the hero image.
3. **TL;DR**: the 4 bullets from the write-up (numbers rendered from key_numbers by a small script, see Part C).
4. **Links:** live dashboard · offline dashboard (GitHub Pages) · full write-up (`reports/writeup.md`).
5. **Key findings**: 4 short sections, each with one figure (Fig 1, Fig 2, Fig 9, Fig 8) and 2–3 sentences.
6. **What this project demonstrates**, for hiring managers: e.g. SQL/DuckDB pipeline over 2.6M rows · data-quality engineering (truncated files, dedup, junk metadata, rounding-error bounds) · cohort/panel analysis · fixed-effects event study, robust regression, bootstrap · out-of-sample predictive check · honest reporting of a null hypothesis · interactive dashboard · tests + CI.
7. **Method in brief** + **limitations** (from findings §4, condensed).
8. **Repository structure** (short tree with a one-line description per folder).
9. **Reproduce** (the existing run commands; note the ~540 MB download and the mainland-China tip).
10. **Data & licence**: data credit, no redistribution of data, Kaggle attribution (CC BY-SA 3.0), code licence.

Keep it scannable: under ~250 lines, with images at a sensible width (`<img width="720">`).

## Part C: Repo hygiene

- **README numbers from key_numbers:** a small script `scripts/render_readme.py` fills `{{key}}` placeholders in `README.template.md` → `README.md`, so README numbers can't drift. Add a test that fails if README.md is stale.
- **Code licence:** add `LICENSE` (MIT, author = the user; ask for the name to put on it if it's not in git config). Make clear in the README that the licence covers code only, not data.
- **CI:** `.github/workflows/ci.yml`: on push/PR, set up uv, then `uv sync`, `ruff check .`, `pytest`. Tests that need local data must **skip cleanly** in CI (no data in the repo). Verify locally by running pytest with `data/` temporarily hidden (or an env flag).
- `pyproject.toml`: add authors, description, readme, a license field and project URLs (placeholders until the remote exists).
- `.gitignore` re-check: no game-level files, no `user_ratings.csv`, nothing over 5 MB tracked. Print the 10 largest tracked blobs in the final report.
- Delete or archive stale bits: `reports/results/_fragments/` (if intermediate), unused code paths, TODOs.
- Docs index: `docs/README.md`, listing what each doc is (data_notes, findings, deploy, handoff/ = how the project was built).

## Part D: Publish (some steps need the user; prepare everything, then ask)

1. **GitHub:** if `gh` is installed and authenticated, offer to create a **public** repo (name suggestion `bgg-hype-fade`) and push `main`. Otherwise print the exact commands. Before pushing, run a final secret/PII scan: no usernames, no emails except the author's, no tokens (`git log -p | grep -iE "token|password|user_ratings"`).
2. **GitHub Pages (offline dashboard):** script `scripts/publish_pages.py` that builds `bgg export-static` and pushes `index.html` + `social_card.png` to a `gh-pages` branch. Set the page title/description/OG image meta tags in the export so links preview nicely on LinkedIn.
3. **Streamlit Community Cloud:** the user does this in the browser (needs their GitHub login). Give a 5-step checklist with the exact field values from `docs/deploy.md`. Afterwards, set `BGG_REPO_URL` / `BGG_WRITEUP_URL`.
4. After the user reports the URLs, fill in the link placeholders in README, write-up and app config, and commit.

## Part E (optional, ask before doing): extras
- `notebooks/02_results_walkthrough.ipynb` (skipped in task 02): loads tables/figures and walks through them, saved with outputs.
- Daily-vs-monthly robustness for one cohort (2019 entries, first 12 months ≈ 365 daily files ≈ 1.5 GB). Only if the user wants it.

## Acceptance
- App: sliders change the trust month in aggregates mode (e.g. ±0.25/80% → 13; ±0.50/80% → an earlier month); the explore-segments view works; numbers are consistently rounded; tests pass.
- README renders on GitHub with images, numbers match key_numbers, and the stale-README test passes.
- CI green on a clean clone (no data).
- Largest tracked blob < 5 MB; no game-level data or PII in history.
- Final report to the user: what changed, the screenshots, the publish checklist (what's done, what needs them), and the list of URLs to send back.
