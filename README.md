# Investment Growth Panel

This panel uses historical industry returns to show how the same investment would have grown in different industries. You can change the industries, date range, starting investment, monthly contribution, and investment goal.

## Reproduce a result

Use these settings to check that the chart and comparison table agree:

1. Select Technology, Financials, and Energy.
2. Set the years to 2010–2025, the starting investment to USD 1,000, and the monthly contribution to USD 100.
3. Set the investment goal to USD 50,000.

With all 192 months from January 2010 to December 2025 included, the Money paid in line should finish at USD 20,200 for each industry (`1,000 + 192 × 100`). The table ranks the selected industries by ending value. Each industry's gain or loss equals its ending value minus USD 20,200. The goal column shows the first month its balance reached USD 50,000, if it reached that amount.

For a second check, set the monthly contribution to USD 0. The Money paid in line should stay flat at **USD 1,000**, while the industry lines still move with historical returns.

## How the calculation works

The panel compounds daily returns into calendar-month returns. It plots the starting investment before the first month's return, then applies this calculation each month:

```text
New balance = previous balance × (1 + monthly return) + monthly contribution
```

Contributions are added at the end of each month, so each contribution starts earning returns the following month. The chart replays historical returns and excludes fees, taxes, and inflation.

## Data and input requirements

The panel uses the supplied `industry_returns_clean.csv`. You can run it with that file as provided. If you need to regenerate the dataset, run `python clean_data.py` from the project folder.

The CSV needs a `Date` column and one column of daily returns per industry. Returns are stored as decimals, so `0.01` represents 1%. The panel requires monthly returns for every selected industry throughout the chosen date range.

Select at least one industry, enter a start year no later than the end year, and use non-negative amounts. The panel starts with Technology, Financials, and Energy when those columns are available. It uses the portion of 2010–2025 covered by the dataset.

## Dashboard integration

[`investment_growth_graph.py`](./investment_growth_graph.py) provides `make_growth_preview()` for the dashboard overview and `build_growth_panel(app)` for the Explore view. The underlying `build_panel(csv_path)` function builds the interactive controls, chart, and comparison table.


# Risk vs Return Panel

This panel uses historical industry returns to compare how much each industry earned on average and how much its returns varied. You can change the industries, date range, return frequency, risk measure, and targets. Each point represents one industry, with risk on the horizontal axis and average return on the vertical axis.

## Reproduce a result

Use these settings to check that the chart, target summary, and industry statistics table agree:

1. Select all eight industries and use the full date range in the supplied dataset.
2. Set the frequency to **Annual** and the risk measure to **Volatility**.
3. Set the minimum return to **10%** and the maximum volatility to **20%**.

The summary should show **3 of 8 industries meet both targets**. Consumer goods, Healthcare, and Utilities should appear in the shaded area. Each had an average annual return of at least 10% and annual volatility of at most 20%.

For a second check, raise the maximum volatility to **21%**. Financials should now qualify, bringing the count to **4 of 8**. Its volatility is about 20.68%, so the new threshold includes it while the figures in the table stay the same.

## How the calculation works

The panel uses daily returns directly for Daily frequency. For Weekly, Monthly, or Annual frequency, it compounds the daily returns within each period:

~~~text
Period return = product of (1 + each daily return) − 1
~~~

It then calculates the arithmetic mean of the period returns and one of two risk measures:

- **Volatility** is the sample standard deviation of the period returns.
- **Downside deviation** is the square root of the average squared negative return, counting zero and positive returns as zero in that average.

The chart and table display the results as percentages. The targets use the selected frequency, so a 1% return target in Monthly mode means an average monthly return of 1%. The maximum volatility target applies in Volatility mode.

## Data and input requirements

The panel uses the supplied `industry_returns_clean.csv`. You can run it with that file as provided. If you need to regenerate the dataset, run `python clean_data.py` from the project folder.

The CSV needs a `Date` column and one column of daily returns per industry. Returns are stored as decimals, so `0.01` represents 1%. An industry needs at least two usable period returns to appear in the chart and table.

Select at least one industry, choose a start date no later than the end date, and use a non-negative maximum volatility. The panel starts with all industries selected, the full available date range, Monthly frequency, a 1% minimum return, and a 5% maximum volatility.

## Dashboard integration

[`risk_vs_return.py`](./risk_vs_return.py) provides `make_risk_preview()` for the dashboard overview and `build_risk_panel(app)` for the Explore view. The underlying `risk_vs_return_panel(returns)` function builds the interactive controls, chart, target summary, and industry statistics table.



# Industry Correlations Panel

This panel uses historical industry returns to show how closely different industries move together over time and where portfolio diversification opportunities exist. You can change the industries, date range, return frequency, correlation method, minimum correlation threshold, statistical significance filter, value labels, and matrix layout. Each cell compares two industries, with colour and numeric values showing the direction and strength of their relationship from -1.00 (opposite movement) to +1.00 (identical movement).

## Reproduce a result

Use these settings to check that the heatmap and diversification summary agree:

1. Select all eight industries and set the start year to 2000 and end year to 2026.
2. Set the frequency to Monthly and the method to Pearson.
3. Set the absolute correlation threshold `|r|` to 0.00, check **Show values**, leave **Significant only (p < 0.05)** unchecked, and set the matrix view to **Full Matrix**.

With all eight industries included over the full monthly sample, the summary below the chart should report an average cross-sector correlation of **0.55**, with **Financials & Industrials (0.79)** as the highest co-moving pair and **Technology & Utilities (0.26)** as the best diversification pair. Every diagonal cell should display **1.00**, and off-diagonal cells should match the overview preview card.

For a second check, raise the absolute correlation threshold `|r|` to **0.70**. Only pairs with a correlation magnitude of at least 0.70 (such as Financials & Industrials at 0.79, Financials & Real estate at 0.74, and Industrials & Real estate at 0.75) remain visible off the diagonal, while weaker relationships are hidden.

## How the calculation works

The panel uses daily returns directly for Daily frequency. For Weekly, Monthly, or Quarterly frequency, it compounds the daily returns within each period:

`Period return = product of (1 + each daily return) − 1`

It then computes pairwise correlations and two-tailed *p*-values across every pair of selected industries using the chosen method:

* **Pearson** measures linear co-movement between two return series.
* **Spearman** measures rank-order (monotonic) co-movement, making it less sensitive to extreme single-period market shocks.

Any pair with fewer than 3 overlapping return observations is excluded. When **Significant only (p < 0.05)** is checked, off-diagonal pairs whose two-tailed *p*-value is 0.05 or higher are hidden from the matrix. The summary sentence below the chart averages all unique off-diagonal pairs (`i < j`) and identifies the highest-correlating and lowest-correlating pairs.

## Data and input requirements

The panel uses the supplied `industry_returns_clean.csv`. You can run it with that file as provided. If you need to regenerate the dataset, run `python clean_data.py` from the project folder.

The CSV needs a `Date` column and one column of daily returns per industry. Returns are stored as decimals, so `0.01` represents 1%.

Select at least two industries to compute a correlation matrix. If the start year is entered after the end year, the panel automatically swaps the two bounds so a valid date window is always evaluated. The Explore panel starts with all industries selected, the full available year range, Daily frequency, Pearson method, a `0.00` threshold, value labels enabled, and Full Matrix view.

## Dashboard integration

`correlation_graph.py` provides `make_correlation_preview()` for the dashboard overview (returning a static Matplotlib heatmap rendered at 10 × 4 inches and 150 DPI) and `build_correlation_panel()` for the Explore view. The underlying `update_correlation_panel(...)` callback updates the interactive Plotly heatmap or 3D surface and the diversification summary whenever any control changes.
