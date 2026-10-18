# Original research proposal (unused)

*Kept for reference. The portfolio plan is in implementation_plan.md.*

B. Does the hype fade? Post-release rating trajectories on BoardGameGeek
Topic proposal

Title: Does the Hype Fade? Post-Release Rating Trajectories of Board Games on BoardGameGeek, 2016–2026

Online ratings strongly shape consumer choice, yet early ratings are often systematically higher than later ones, because a product's first buyers tend to be those most predisposed to like it (Godes & Silva, 2012; Li & Hitt, 2008). This self-selection effect has been documented for books and general consumer products. It has not been examined for hobby board games, a market in which pre-release hype and crowdfunding are central and in which players themselves speak of a "cult of the new" (Booth, 2022). Existing studies that use BoardGameGeek (BGG), the largest online board game database, treat a game's rating as a fixed measure of its quality (Butticè & Noonan, 2020; Wachs & Vedres, 2021). This study will use a public archive of daily BGG ranking snapshots from October 2016 to September 2026 to track the average rating of more than 7,000 newly ranked games over their first 36 months. It will estimate the typical size and timing of rating decline and test whether games that attract raters most rapidly experience the steepest declines. The findings will indicate how reliable early ratings of new releases are as quality signals and may inform how rating platforms present recently released titles.

Research questions and hypotheses
RQ1 (change over time): How does a board game's average BGG rating change during the 36 months after it enters the BGG ranking?
H1: Average ratings decline after entry, and most of the decline happens in the first 12 months.
RQ2 (relationship between variables): Is the size of this decline related to how rapidly a game accumulates raters in its first six months, a proxy for hype?
H2: Games that gain raters fastest decline most.
Optional sub-question: Do crowdfunded games decline more than retail games? This needs the Kaggle metadata described under Data.
Gap and novelty
What is known	Closest studies	What is missing
Early reviews are more positive; ratings decline over time	Li & Hitt (2008, cited 1,784); Godes & Silva (2012); Moe & Schweidel (2012); Hu, Pavlou & Zhang (2017)	Books and general products on Amazon; one-off purchases, no hobby-community context
Publicity and awards lower later ratings	Kovács & Sharkey (2014, Goodreads)	Awards, not release hype
BGG as a research dataset	Butticè & Noonan (2020); Wachs & Vedres (2021); Samarasinghe et al. (2021); Nguyen et al. (2024); Herrero et al. (2025)	All treat BGG ratings as fixed quality scores, measured once
The "cult of the new"	Booth (2022, Material Game Studies)	Discussed qualitatively; never measured

Novelty in one sentence: This would be the first longitudinal measurement of post-release rating dynamics for hobby board games, using ten years of daily data, and it would test the self-selection explanation in a crowdfunding-heavy market.

Data: availability confirmed
Source: GitHub repository beefsack/bgg-ranking-historicals. One CSV file per day of BGG's full ranked list.
Checked 23–24 Sep: 3,633 daily files, 12 Oct 2016 → 23 Sep 2026, updated daily. Columns: ID, Name, Year, Rank, Average, Bayes average, Users rated, URL, Thumbnail. Each file grew from 12.7k games (2016) to 31.4k games (2026).
Sample size (checked with monthly snapshots):
Year a game entered the ranking	New releases entering	With ≥24 months of follow-up	With ≥36 months
2017	1,033	1,028	1,028
2018	1,045	1,041	1,040
2019	1,068	1,064	1,062
2020	921	913	911
2021	978	975	973
2022	1,055	1,048	1,047
2023	1,213	1,203	779
All (Oct 2016–Sep 2026)	10,920	8,298	7,078

A "new release" here means a game first ranked after October 2016 whose publication year is no more than one year before it entered. Games almost never drop out of the ranking, so follow-up is nearly complete.

Access: Plain download from GitHub (confirmed working); no login or API key needed. I couldn't check the repository's licence. Cite the repository and BGG as the source, and use the data for non-commercial academic work.
Optional metadata (crowdfunding flag, complexity, mechanics): the Kaggle dataset "Board Game Database from BoardGameGeek" (threnjen) has 22k games with 47 features each plus mechanics and theme tables, under a CC BY-SA 3.0 licence. It is an older snapshot, so it covers mostly games released before it was made. BGG's own XML API now requires an approved registration and token, and its website runs a bot check, so don't plan on scraping BGG directly.
Method
Prepare the data: Load all 3,633 files into DuckDB in one query, taking the date from each file name. Keep one snapshot per month (about 2.5M rows).
Define each game's "month 0" as its first month in the ranking, and keep new releases entering between 2017 and mid-2023.
Outcome: Use the raw Average, not the Bayes average. BGG's Bayes average pulls ratings toward a default by adding dummy votes, which hides real changes (Heron et al., 2018).
Analyst touch: Because Average is a running mean, you can work out the average of the new ratings added each month: (average_t × raters_t − average_(t−1) × raters_(t−1)) ÷ (raters_t − raters_(t−1)). This separates what new raters think from the historical average.
Analysis:
RQ1: average rating by months since entry. Use a panel regression with game fixed effects and dummies for months since entry (Python linearmodels or R fixest). Report the mean change from month 0 to months 12, 24 and 36, with confidence intervals.
RQ2: regress each game's 36-month change on its rater growth in the first six months, controlling for entry year and starting average.
Figures and tables:
Figure 1: average rating by months since entry (the key figure).
Figure 2: decline by quartile of rater growth.
Table 1: cohort sizes.
Table 2: regression results.
Tools
Purpose	Tool
Download	git clone or a Python requests loop over the file list
Storage and queries	DuckDB (read_csv('*.csv', filename=true)), then Parquet
Data handling	pandas / polars
Statistics	linearmodels (PanelOLS) or statsmodels; R fixest if you prefer R
Figures	matplotlib / seaborn; optionally a Streamlit or Tableau dashboard for the portfolio
Hardware	Any laptop. The monthly files total ~0.5 GB; all daily files are several GB.
Timeline and effort (~50 h)
Phase	Dates	Tasks	Hours
Pilot	24–30 Sep	Download monthly files; count cohorts; plot 5 example games	3
Proposal	1–16 Oct	Read and annotate 10 sources; write proposal	12
Data	17 Oct–1 Nov	Load into DuckDB; find entry months; calculate new-rating averages; quality checks	8
Practice talk	2–6 Nov	Preliminary Figure 1	3
Analysis	7–22 Nov	RQ1 and RQ2 models; robustness (daily vs monthly data; 2020–21 COVID entry years; very popular vs niche games)	12
Writing	23 Nov–6 Dec	Results, discussion, abstract; slides	8
Finish	7–18 Dec	Presentation; final paper	5
Risks and mitigations
Only ranked games are listed: a game enters only once it has enough ratings, so its earliest ratings are bundled into its first data point. State this and focus on changes after entry.
Users can edit old ratings: the new-rating average will then be approximate. Mention it and use only monthly steps.
Hype proxy is indirect: rater growth also reflects print run and distribution. Discuss this; use the crowdfunding flag as a second proxy if the Kaggle data covers your games.
Old games entering the ranking late: exclude them with the publication-year rule (done in the counts above).

Ethics: Only game-level aggregates; no personal data.

Limitations to state: one platform; BGG users are enthusiasts, not typical buyers; observational data, so no causal claims.

Portfolio value

This is product-ratings analytics: tracking products by launch cohort, separating new feedback from the running average, and segmenting by growth. It is the same analysis done on app-store, e-commerce and streaming ratings, and makes an ideal SQL/DuckDB showcase (~75M rows daily, ~2.5M monthly). A small dashboard ("rating trajectory of any game") would make a strong portfolio piece.

Core sources (verified on Google Scholar)
Li & Hitt (2008). Self-selection and information role of online product reviews. Information Systems Research. [1,784]
Godes & Silva (2012). Sequential and temporal dynamics of online opinion. Marketing Science. [655]
Moe & Schweidel (2012). Online product opinions: Incidence, evaluation, and evolution. Marketing Science. [972]
Kovács & Sharkey (2014). The paradox of publicity: How awards can negatively affect the evaluation of quality. Administrative Science Quarterly. [343]
Hu, Pavlou & Zhang (2017). On self-selection biases in online product reviews. MIS Quarterly. [446]
Askalidis, Kim & Malthouse (2017). Understanding and overcoming biases in online review systems. Decision Support Systems. [172]
Heron, Belford, Reid & Crabb (2018). Eighteen months of Meeple Like Us: An exploration into the state of board game accessibility. The Computer Games Journal. [37]
Butticè & Noonan (2020). Active backers, product commercialisation and product quality after a crowdfunding campaign. International Small Business Journal. [65]
Wachs & Vedres (2021). Does crowdfunding really foster innovation? Evidence from the board game industry. Technological Forecasting and Social Change. [68]
Samarasinghe et al. (2021). A data driven review of board game design and interactions of their mechanics. IEEE Access. [59]
Booth (2022). The cult of new (stuff). In Material game studies: A philosophy of analogue play (book chapter).
Nguyen, Kritz, Gaina et al. (2024). Unveiling modern board games: An ML-based approach to BoardGameGeek data analysis. IEEE Conference on Games. [6]
Herrero, Rodríguez-Álvarez et al. (2025). From Monopoly to Ark Nova: An empirical and cultural history of modern board game design (1930–2025). Simulation & Gaming.