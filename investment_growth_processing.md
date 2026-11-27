# Investment Growth - Data Processing

The Investment Growth panel uses historical daily industry returns to simulate how the same starting investment and monthly contribution would have grown in each selected industry. Each industry is a separate scenario. The chart shows dollar balances over time, and the comparison table summarises the final balance, gain or loss, and first date the balance reaches the goal.

## 1. Load the daily returns

The project's source is the Kenneth R. French industry portfolio data. The panel takes its input from the prepared `industry_returns_clean.csv`, which has a `Date` column and one daily return column per industry. The upstream cleaning step prepares this CSV for the dashboard. When a source return is expressed in percentage units, the conversion to decimal form is:

```text
Decimal return = return in percentage units / 100
Example: 2.00% is stored as 0.02
```

The panel uses the decimal returns already in the CSV. It parses `Date` as a date, sets it as the index, and sorts the rows chronologically. The detailed panel checks that dates are valid and industry return columns are numeric.

## 2. Compound daily returns into monthly returns

For each industry, the panel groups daily returns by calendar month. It adds 1 to each daily return to turn it into a growth factor, multiplies the factors in that month, then subtracts 1 to get the monthly return.

```text
Monthly return =
    (1 + day 1 return)
    × (1 + day 2 return)
    × ...
    × (1 + last day return)
    - 1
```

For example, if the only two returns in a month are +2% and -1%, the monthly return is:

```text
1.02 × 0.99 - 1 = 0.0098 = 0.98%
```

Multiplication accounts for the second day's return applying to the value left after the first day.

```python
monthly = (
    (1 + daily)
    .resample("ME")
    .prod(min_count=1)
    - 1
)
```

`ME` labels each group with its calendar month-end date. The product uses available daily observations, with `min_count=1` leaving a missing monthly return if an industry has no valid daily return in that month. The detailed panel then selects the chosen industry columns and the months in the selected start and end years, inclusive. It asks for a different selection if the selected range is empty or contains a missing monthly return for any selected industry.

## 3. Calculate each industry's investment balance

The starting balance is the amount entered as the starting investment. For each month, the panel applies that industry's monthly return to the previous balance and then adds the contribution.

```text
Starting balance = starting investment

End-of-month balance =
    previous balance × (1 + monthly return)
    + monthly contribution
```

The contribution is added at month-end, so it first earns a return in the following month. Each month's closing balance becomes the next month's opening balance.

For example, with a starting investment of USD 1,000, a USD 100 monthly contribution and example returns of +5% and -2%:

```text
+-------------------------+----------------------------+-------------+
| Point in time           | Calculation                | Balance     |
+-------------------------+----------------------------+-------------+
| Before the first month  | Starting investment        | USD 1,000   |
| End of month 1          | 1,000 × 1.05 + 100         | USD 1,150   |
| End of month 2          | 1,150 × 0.98 + 100         | USD 1,227   |
+-------------------------+----------------------------+-------------+
```

## 4. Build the chart

The x-axis uses month-end dates. The first plotted point is dated one month-end before the first selected return and shows the starting investment. After that, each point shows the balance after that month's return and contribution. For `N` months of returns, each line therefore has `N + 1` points.

- **Industry lines** show the calculated balances in USD.
- **Money paid in** starts at the initial investment and increases by the contribution each month.
- **Investment goal** is a horizontal line at the dollar amount entered by the user.

After month `t`, the money paid in equals:

```text
Money paid in =
    starting investment
    + t × monthly contribution
```

At `t = 0`, the starting point equals the initial investment.

The goal is used to compare against balances and does not enter the balance formula. The dashboard preview uses the same balance calculation with fixed inputs of USD 1,000 upfront and USD 100 per month.

## 5. Calculate the comparison table

```text
+---------------------+------------------------------------------------------------+
| Table column        | Calculation                                                |
+---------------------+------------------------------------------------------------+
| Ending value        | Industry balance at the last plotted month-end             |
| Gain/loss           | Ending value - Total money paid in                         |
| First reached goal  | Earliest date when Industry balance >= Investment goal     |
+---------------------+------------------------------------------------------------+
```

Total money paid in equals:

```text
Total money paid in =
    starting investment
    + monthly contribution × number of months
```

The first reached goal includes the starting point if the starting investment already meets the goal. If no plotted balance reaches it, the table shows `Not reached`.

In the two-month example:

```text
Money paid in = 1,000 + (2 × 100) = USD 1,200

Gain/loss = 1,227 - 1,200 = USD 27
```

A goal of USD 1,200 is first reached at the end of month 2. The first goal date is recorded even if a later balance falls below the goal.

## 6. Reproduce a result

Choose **2010-2025**, set the starting investment to **USD 1,000**, the monthly contribution to **USD 100**, and the goal to **USD 50,000**. With all 192 months available, the **Money paid in** line should end at:

```text
1,000 + (192 × 100) = USD 20,200
```

Set the monthly contribution to **USD 0** and the line should stay flat at **USD 1,000**. With a zero contribution, each industry's balance changes only with its monthly returns.

`Panel implementation`
