/**
 * Beginner-friendly explanations for every page section. Each entry is the
 * `info` prop fed to <Panel> / <StatTile> / <InfoIcon>. The "Ask AI" button
 * inside the modal forwards the title + explanation to Claude as context.
 *
 * Tone: explain it like the reader has never traded a stock before. Keep
 * jargon defined the first time it appears. Plain prose, short paragraphs.
 */
import type { InfoContent } from "@/components/ui/InfoIcon";

export const INFO: Record<string, InfoContent> = {
  // ─── Macro page ────────────────────────────────────────────────────────
  macro_series: {
    title: "Macro Series",
    explanation:
      "A 'macro series' is a single big-picture economic indicator — beef prices, gas prices, consumer confidence, the unemployment rate, etc. The big number is how much it has changed over the last 90 days; the chart underneath shows the last year so you can see the trend.\n\nThe 'Exposure' tag tells you which restaurant tickers in our universe are most affected by this series (e.g. high beef prices hit steakhouse stocks first). 'ALL' means everyone is exposed.\n\nData comes from FRED (the Federal Reserve's free economic-data service).",
  },

  // ─── Simulate page ─────────────────────────────────────────────────────
  simulate_overview: {
    title: "Simulations Overview",
    explanation:
      "Three Monte-Carlo simulations live on this page:\n\n• Price paths — we run the recent price chart through a math model thousands of times to see a range of plausible futures (not predictions, just a distribution).\n• Earnings bootstrap — we look at how similar companies' stocks moved after past earnings reports and resample those moves to estimate this one.\n• DCF — Discounted Cash Flow. We model the company's future cash flows under many different assumptions (growth, margins, discount rates) to estimate what one share is 'really worth'.\n\nNothing here is a prediction. Each is a distribution of outcomes given the data we have.",
  },

  // ─── Correlations page ─────────────────────────────────────────────────
  correlations_scatter: {
    title: "Correlation Lab",
    explanation:
      "A scatter plot tests whether two things move together. Each dot is one earnings event: the X axis is some 'feature' (e.g. average news sentiment in the 30 days before earnings) and the Y axis is what you want to predict (e.g. EPS surprise %).\n\nIf the dots form a clear up-and-to-the-right cloud, the feature predicts the target positively. If they're a random blob, the feature is noise.\n\nThe 'r' value (correlation coefficient) summarizes that pattern: +1 = perfect upward, 0 = none, -1 = perfect downward.",
  },
  correlations_heatmap: {
    title: "Feature × Feature Heatmap",
    explanation:
      "A grid showing how every feature correlates with every other feature. Bright squares = tightly related (often redundant). Dim squares = independent.\n\nWhy you care: if two features are 95% correlated they're carrying the same information, so a model only needs one. The heatmap helps you spot duplicate signals.\n\nMethod 'Pearson' measures straight-line correlation; 'Spearman' measures rank-order correlation (less sensitive to outliers).",
  },
  correlations_table: {
    title: "Ranked Univariate Correlations",
    explanation:
      "Every feature/target pair we tested, ranked by statistical significance. Quick glossary:\n\n• n — sample size (more is better).\n• r — correlation strength, between -1 and +1.\n• 95% CI — the range we're 95% sure the true r falls into.\n• p — probability we'd see this much correlation by chance. Lower is stronger evidence.\n• p-adj — p adjusted for the fact we're testing many features at once. Below 0.05 (highlighted) means it's likely a real signal, not luck.",
  },

  // ─── Earnings page ─────────────────────────────────────────────────────
  earnings_upcoming: {
    title: "Upcoming Earnings",
    explanation:
      "Companies that will report their quarterly results soon. Glossary:\n\n• EPS Est = analysts' estimate of earnings per share.\n• Rev Est = analysts' estimate of total revenue.\n• Period = which fiscal quarter this report covers.\n• Hypothesis = our model's lean. Bullish/Neutral/Bearish + a confidence number.\n\nStocks often jump or drop sharply right after these reports — this is the calendar to plan around.",
  },
  earnings_past: {
    title: "Past Earnings",
    explanation:
      "How the most recent earnings reports actually played out. Glossary:\n\n• EPS Actual — the real number reported (green if it beat the estimate, red if it missed).\n• Surprise — how far off the estimate was, in percent.\n• 1D / 5D — the stock's return the next day, and the next 5 trading days.\n• Reaction — a label combining surprise + price move (e.g. 'beat_rally', 'miss_sell', 'beat_fade').\n\nBeating estimates doesn't always mean the stock goes up — markets care about guidance and tone too.",
  },

  // ─── Hypotheses page ───────────────────────────────────────────────────
  hypotheses_events_tracked: {
    title: "Events Tracked",
    explanation:
      "How many earnings events our hypothesis model has scored over the selected date range. Each one is a prediction: 'Bullish', 'Neutral', or 'Bearish' before the report came out.",
  },
  hypotheses_scored: {
    title: "Scored Events",
    explanation:
      "Of the events we predicted on, how many now have an actual result we can grade against (BEAT or MISS). Recent events that haven't reported yet stay 'PENDING'.",
  },
  hypotheses_correct: {
    title: "Correct Predictions",
    explanation:
      "How many of our scored predictions matched the actual result. We count 'Bullish + BEAT' or 'Bearish + MISS' as correct; mismatches as wrong.",
  },
  hypotheses_accuracy: {
    title: "Accuracy %",
    explanation:
      "Correct ÷ Scored, as a percentage. A coin flip is 50%. Anything meaningfully above 50% on a decent sample size suggests the model is finding real signal. Below 50% means it's worse than random — a sign to retrain or rethink features.",
  },
  hypotheses_history: {
    title: "Historical Predictions",
    explanation:
      "Every past prediction we made, side-by-side with what actually happened. The 'Top drivers' column shows which features pushed our prediction up or down — green chips were positive contributors, red chips were negative.\n\nThis is essentially a transparency log — it lets you see whether the model has been honest, lucky, or just consistently wrong.",
  },

  // ─── Holders page ──────────────────────────────────────────────────────
  holders_concentration: {
    title: "Ownership Concentration",
    explanation:
      "Who owns each company we track. Glossary:\n\n• Inst % — percent of all shares held by institutions (mutual funds, pensions, hedge funds).\n• Top holder — the single biggest institutional shareholder.\n• Biggest buyer/seller QoQ — institutions that added or trimmed the most shares since last quarter.\n• Insider net 90d — net shares bought (+) or sold (−) by company executives in the last 90 days. Insiders selling can be normal (10b5-1 plans) or a signal — context matters.\n\nHigh concentration + activist holders can mean upcoming volatility.",
  },
  holders_top_institutions: {
    title: "Top Institutions",
    explanation:
      "The biggest institutional holders across our entire universe. 'Kind' tells you what type of investor: index fund (passive), hedge fund, activist (often pushes for changes), etc.\n\nAUM = Assets Under Management — how much money the firm runs in total. Larger firms move markets more when they buy or sell.",
  },

  // ─── Commodities page ──────────────────────────────────────────────────
  commodity_card: {
    title: "Commodity Card",
    explanation:
      "A single commodity (raw material) we track because it affects restaurant costs. The big number is the latest price; the percentages show how it has changed over 30, 90 and 365 days. The chart is the history over your selected date range.\n\n'Exposure' lists which tickers in our universe care most about this commodity (e.g. cattle prices → steakhouses; coffee → SBUX; wheat → DPZ).",
  },

  // ─── Trends page ───────────────────────────────────────────────────────
  trends_card: {
    title: "Google Trends Series",
    explanation:
      "A time series of how often people Google a particular term. Trends data is normalized 0-100, where 100 is the all-time peak interest for that query.\n\nWhy we care: rising search interest in a brand or menu item often leads same-store sales by a few weeks. Falling interest can be an early warning. We track per-ticker brand queries, signature menu items, and broader consumer-behavior queries.",
  },

  // ─── Ops page ──────────────────────────────────────────────────────────
  ops_runs: {
    title: "Recent Source Runs",
    explanation:
      "An operational log: every time one of our background data jobs ran, what status it returned, and how many rows it fetched.\n\n• success — completed cleanly.\n• skipped — ran but had nothing to do (e.g. weekend, no API key set).\n• failed — errored out; check the Error column.\n• running — still in flight.\n\nUse this page to debug stale data on the dashboard.",
  },

  // ─── Company page ──────────────────────────────────────────────────────
  company_hypothesis: {
    title: "Pre-Earnings Hypothesis",
    explanation:
      "Our model's overall lean for this stock heading into its next earnings report. The composite score (between -1 and +1) blends several inputs:\n\n• Relative strength — how the stock has performed vs the broader sector.\n• Sentiment 7D — average tone of news in the last week.\n• Social vol Z — how unusual the social-media volume is, in standard deviations.\n• Jobs Δ 30D — change in open job postings (a leading indicator of expansion).\n• News volume — how much the company is in the news vs its baseline.\n\nThe label (Bullish / Neutral / Bearish) is just the score bucketed into a category.",
  },
  company_price: {
    title: "Price · Events · 90D",
    explanation:
      "A candlestick chart of the last 90 days of trading. Each bar is one day's open, high, low and close. Green = closed higher than it opened; red = closed lower.\n\nThe little markers on the chart are events: earnings dates, analyst rating changes, big news, etc. Hover over them to see what they were. This is a good place to see whether news actually moved the stock.",
  },
  company_features: {
    title: "Feature Vector",
    explanation:
      "The raw signals our hypothesis model uses for this company, all in one place. Each row is one feature with its current value and a colored bar showing direction.\n\nThink of it as the ingredients list for the prediction above.",
  },
};
