# Grain COT Research

This project tests whether extreme positioning by commercial hedgers in grain futures markets predicts subsequent mean reversion in price.

## Hypothesis

The theory this project tests comes from John Maynard Keynes' concept of normal backwardation, first laid out in *A Treatise on Money* (1930). Commercial hedgers, meaning producers, merchants, and processors, trade futures primarily to manage risk rather than to speculate on price direction.

Price can move away from its recent average for different reasons. A genuine shift in fundamentals, a drought that reduces supply for instance, can push price to a new level that persists. Short term speculative pressure with no real fundamental basis can also push price to an extreme, but that kind of move is more likely to fade once the pressure behind it eases. These two situations can look identical in the price data alone, both are simply a stretch away from the recent average.

Commercial hedgers respond mechanically to price level rather than to why price moved, a producer sells forward more aggressively whenever price is unusually attractive, regardless of the reason. The hypothesis this project tests is that this mechanical response causes hedgers to reach positioning extremes more reliably during the speculative kind of stretch than the fundamental kind, since a genuine repricing tends to persist and does not get met with the same rush back toward normal hedging levels that a speculative overshoot would produce once it fades. If that is true, weeks flagged by extreme commercial positioning should show a higher rate of subsequent reversion than a randomly selected stretched week does. This is a meaningfully different and testable claim from simply asking whether stretched prices tend to revert in general, which is a separate question answered by the baseline rate computed across the full dataset regardless of positioning.

This hypothesis is grounded in Keynes' theory directly rather than a specific empirical study replicating this exact test. The broader academic literature on whether COT positioning predicts returns is mixed, with some studies finding a measurable effect and others finding none, so a null result here is a plausible and informative outcome rather than a sign of a flawed test.

## Data

Positioning data comes from the CFTC's Commitments of Traders (Disaggregated) report, retrieved through the CFTC's public API. Price data comes from Yahoo Finance via the yfinance library. The dataset covers weekly observations for corn, soybeans, and wheat from 2006 through mid 2026, approximately 1,050 weeks per commodity.

## Methodology

Commercial hedger net position (long minus short) is calculated and normalized as a percentage of total open interest, making it comparable across time despite changes in overall market size. A rolling 52 week z-score is then computed on this normalized value, so that "extreme" positioning is defined relative to each commodity's own recent history rather than an arbitrary fixed threshold. A week is flagged as extreme when its z-score exceeds a chosen cutoff, and consecutive extreme weeks are collapsed into a single event so that one sustained episode is not counted multiple times.

Two parameters govern this test: the z-score threshold used to define an extreme, and the forward holding period used to measure whether price reverted. A looser threshold with a shorter holding period was used in early exploratory work, but the final specification settled on a stricter 2.5 z-score threshold held for 12 weeks. This choice was made independent of the results it would produce: a looser threshold flags more weeks as extreme, some only marginally so, and a shorter holding period gives price less time to actually revert, both of which make a test more likely to register false positives rather than a genuine effect. The stricter specification is the more conservative choice, which is the appropriate default when the goal is determining whether an effect is real.

For each flagged event, price is tracked 12 weeks forward. A hit is recorded if price moves back toward its own pre-event 52 week rolling average by more than one unit of trailing volatility. The identical test is run across every week in the dataset, not only event weeks, to establish a baseline hit rate for comparison. Given the small number of extreme events per market, 14 to 15 over 20 years, Fisher's exact test is used to assess significance rather than a method relying on large sample approximations.

## A methodological correction

The CFTC report is dated for the Tuesday it describes, but is not published until the following Friday. An initial version of this analysis joined COT data directly to that Tuesday's closing price, which meant the test was effectively using information three days before it was actually public. This is a lookahead bias that can make a backtest appear to have predictive power it does not actually have.

This was identified and corrected by introducing a publish date field, set to report date plus three days, and matching each week's positioning data to the next available trading day's price on or after that date. The correction was verified by confirming that matched price dates consistently fell after the corresponding report dates across the full dataset.

## Results

Results below reflect data through July 30, 2026. CFTC publishes new positioning data weekly, so rerunning this script against current data may produce slightly different figures as new weeks are added to the sample.

| Commodity | Usable Events | Event Hit Rate | Baseline Hit Rate | Odds Ratio | p-value |
|---|---|---|---|---|---|
| Corn | 15 | 6.7% | 23.0% | 0.24 | 0.213 |
| Soybeans | 14 | 21.4% | 22.1% | 0.96 | 1.000 |
| Wheat | 14 | 28.6% | 20.1% | 1.59 | 0.499 |

No statistically significant relationship was found in any of the three markets. Two things stand out beyond the p-values themselves.

Baseline hit rates were remarkably consistent across all three markets, landing between 20.1% and 23.0% despite corn, soybeans, and wheat being distinct markets with different fundamentals. This suggests the vol-adjusted reversion definition used here captures something close to a stable, structural base rate of reversion-like price behavior over any given 12 week window, largely independent of which grain is being measured.

The direction of the event effect relative to that baseline is inconsistent across markets. Corn's event hit rate falls well below its baseline, the opposite of what the hypothesis predicts. Soybeans shows no meaningful difference from baseline. Wheat shows a mild lean in the predicted direction. A genuine but underpowered effect would be expected to point in the same direction across related markets even if not statistically significant in each individually. This pattern instead resembles noise scattered around the same stable baseline.

To check whether commercial positioning was adding predictive information beyond what price movement alone already contains, an identical test was run using extreme price moves directly, with no positioning data involved. This price-only version outperformed the positioning-based test in every market and reached statistical significance in wheat (p = 0.028), indicating that commercial positioning is not simply a weaker echo of price extremity, it underperforms a considerably simpler signal built from price alone.

## Parameter Sensitivity

To confirm the results above are not an artifact of the specific threshold and holding period chosen, the full test was repeated across a grid of 9 threshold and holding period combinations per market (z-score thresholds of 2.0, 2.5, and 3.0, each paired with holding periods of 8, 12, and 16 weeks), 27 combinations in total.

Commercial positioning showed no statistically significant result in any of the 27 combinations tested, confirming the null finding holds regardless of the specific parameters chosen rather than being an artifact of one setting. The price-only signal reached statistical significance in 8 of the 27 combinations, concentrated mainly in wheat (5 of 9 settings) and to a lesser extent corn (2 of 9), and clustered at the looser 2.0 threshold paired with longer holding periods. This further supports the earlier finding that price extremity carries more information than commercial positioning does, while also showing that effect is not uniform across every market or parameter setting.

At the strictest threshold tested (3.0), event counts dropped to as few as 2 or 3 per market, too small a sample to draw a meaningful conclusion from at that specific setting; this does not affect the broader pattern observed across the rest of the grid.

The full grid of results is generated locally as `parameter_sweep_summary.csv` when the script is run.

Taken together, these results indicate that extreme commercial hedger positioning does not reliably distinguish reversion-prone price stretches from ordinary ones in these three grain markets, and this conclusion holds across a range of reasonable parameter choices rather than depending on one specific setting. What the data does support is that price behavior consistent with reversion happens at a fairly constant rate regardless of positioning, and that this reversion-like behavior is better explained by price extremity itself than by commercial hedger positioning.

## Limitations

Statistical extremes are rare by construction, 14 to 15 events per market at the primary threshold tested is a small sample, which limits how confidently a null result rules out a smaller real effect rather than simply failing to detect one. This becomes more pronounced at stricter thresholds in the sweep, where event counts drop further.

A substantial number of statistical tests were run in total across three markets, two signal types, and the parameter sweep, without a formal multiple-testing correction applied. Individual significant results, including wheat's, should be read with that in mind.

All results come from a single pass over the full dataset. No out-of-sample holdout period was used to confirm the pattern generalizes to data not used in this analysis.

## Running this analysis

```bash
pip install requests pandas yfinance scipy
python3 commercial_hedger_reversion.py
```

This produces a progress line for each commodity followed by a summary table, saved to grain_significance_summary.csv, followed by the parameter sweep across all three markets, saved to parameter_sweep_summary.csv.
