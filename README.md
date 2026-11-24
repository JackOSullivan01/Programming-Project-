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