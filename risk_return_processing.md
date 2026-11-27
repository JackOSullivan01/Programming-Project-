Risk vs Return Data Processing
From the source file to the panel
The project’s source file, 49_Industry_Portfolios_Daily.csv, comes from the Kenneth R. French Data Library. The Risk vs Return panel receives the prepared file industry_returns_clean.csv. The supplied copy contains 6,726 distinct dates from 3 January 2000 to 30 September 2026 and one daily return column for each of eight industry groups. Returns are stored as decimals, so 0.01 represents 1%.

The upstream cleaning belongs to clean_data.py. The exact source block, portfolio-to-industry mapping, weighting rule and treatment of missing-value codes need to be confirmed against that script. The steps below describe the transformation from the prepared CSV to the graph.

Select the observations
1. Convert the Date column to dates, sort the rows chronologically and use Date as the DataFrame index.
2. Select the date range and industry columns using returns.loc[start_date:end_date, selected]. Both dates are inclusive.
3. Use the daily returns directly in Daily mode. For Weekly, Monthly and Annual, group the selected observations into Friday-ending weeks, calendar months and calendar years respectively.
The code filters dates before grouping, so the first or last group may cover only part of the calendar period. For example, the 2026 observation in the full-range annual comparison uses the available returns through 30 September.

Compound daily returns
For each industry and period, convert each daily return into a growth factor, multiply those factors, then subtract one.
Period return = (1 + daily return 1) × ... × (1 + daily return k) − 1
For example, a gain of 10% followed by a loss of 10% gives 1.10 × 0.90 − 1 = −0.01, or −1%. The code implements this as:
(1 + period_returns).resample(rule).prod(min_count=1) - 1
The product skips missing daily values. With min_count=1, a group with no valid returns stays missing. The panel retains industries with at least two usable period returns and drops rows with missing summary statistics.

Calculate the coordinates
Let r₁, …, rₙ be the usable returns for one industry at the selected frequency. The panel calculates the following statistics separately for each industry.
Statistics:
- Arithmetic mean
  - Formula: mean = sum(r_i) / n
  - Vertical coordinate
- Sample volatility
  - Formula: volatility = sqrt(sum((r_i - mean)^2) / (n - 1))
  - Horizontal coordinate in Volatility mode
- Downside deviation relative to zero
  - Formula: downside deviation = sqrt(sum(min(r_i, 0)^2) / n)
  - Horizontal coordinate in Downside deviation mode


The panel uses pandas .mean() for the average and .std() for sample volatility. For downside deviation, .clip(upper=0).pow(2).mean() ** 0.5 replaces positive returns with zero, squares the resulting values, takes their mean and takes the square root. Positive and zero returns contribute zero to the numerator and still count in the denominator.

The panel multiplies both statistics by 100 before plotting. For example, an average return of 0.10793 appears as approximately 10.793%. The statistics describe the selected observation frequency. Annual values come from the compounded calendar-year observations.
Apply the targets and display the results
In Volatility mode, the panel compares the full-precision percentage figures with the slider values. A point qualifies when both comparisons are true:
Average return (%) ≥ minimum return (%)
Volatility (%) ≤ maximum volatility (%)
The horizontal dashed line marks the minimum return. The vertical dashed line marks the maximum volatility. The shaded region covers the intersection on or above the return line and on or to the left of the volatility line. The summary counts qualifying industries out of the industries with usable statistics. In Downside deviation mode, the return line can still be shown and the volatility target is disabled.

The scatter and Industry statistics table use the same underlying figures. The table sorts by average return from highest to lowest and displays values rounded to three decimal places. Moving a target changes the lines, shaded region and qualifying count. Changing the dates, frequency or risk measure changes the statistics shown on the graph.
