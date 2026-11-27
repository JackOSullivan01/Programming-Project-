# Return Distributions Data Processing and Calculations

## 1. Loading and organising the dataset

```python
filename = Path(__file__).parent / "industry_returns_clean.csv"

df = pd.read_csv(
    filename,
    parse_dates=["Date"],
    index_col="Date"
).sort_index()
```

The dataset is read from the same folder as the Python file.

`parse_dates=["Date"]` converts the date column into datetime values.
`index_col="Date"` makes those dates the DataFrame index, allowing
date-based selection and calendar resampling.

`.sort_index()` arranges observations chronologically.

Each remaining column contains a sector's daily simple returns,
stored as decimals:

```text
0.01 = 1%
−0.02 = −2%
```

## 2. Converting and validating input dates

**Function: `parse_input_date(value)`**

```python
text = str(value).strip()

date_format = "%Y-%m-%d" if "-" in text else "%d/%m/%Y"

return pd.to_datetime(
    text,
    format=date_format,
    errors="coerce"
)
```

The input is converted into text and surrounding spaces are removed.

The function selects the expected format based on whether the input
contains a hyphen:

- `YYYY-MM-DD` for ISO dates.
- `DD/MM/YYYY` for Irish-style dates.

`errors="coerce"` converts an invalid date into `NaT`, representing a
missing datetime value.

Inside `draw_histogram(...)`, the parsed dates are checked:

```python
start = parse_input_date(start_date)
end = parse_input_date(end_date)

if pd.isna(start) or pd.isna(end):
    return None, "Enter dates as DD/MM/YYYY, for example 24/11/2026."

if start > end:
    return None, "Choose a start date before the end date."
```

These checks prevent invalid or reversed dates from being used to
construct the analysis sample.

## 3. Selecting daily returns and removing incomplete observations

**Function: `draw_histogram(...)`**

```python
sector_returns = df.loc[start:end, sector].dropna() * 100
```

`sector` contains the selected sector names.
`df.loc[start:end, sector]` selects their observations within the
requested dates, including both date boundaries where observations
exist.

`.dropna()` removes any row containing a missing return in one or more
selected sectors.

This produces a common sample: every selected sector is analysed over
the same retained dates. Adding another sector with missing values can
therefore reduce the sample for all selected sectors.

Multiplication by 100 converts decimal returns into percentage returns:

```text
Percentage return = decimal return × 100
```

For example:

```text
0.025 × 100 = 2.5%
```

The prepared percentage values are used in both the charts and the
summary calculations.

## 4. Compounding daily returns into monthly returns

**Function: `draw_histogram(...)`**

```python
monthly = (1 + df[sector]).resample("ME").prod(min_count=1) - 1
```

A simple return represents a proportional change in value:

```math
r_t = \frac{V_t - V_{t-1}}{V_{t-1}}
```

Therefore, the growth factor for that observation is:

```math
1 + r_t = \frac{V_t}{V_{t-1}}
```

Multiplying the daily growth factors gives the cumulative growth factor
for the month. Subtracting one produces the monthly return:

```math
R_m = \prod_{t \in m}(1+r_t)-1
```

Here, `r_t` is a daily decimal return and `R_m` is the monthly decimal
return.

The code implements this in three stages:

1. `1 + df[sector]` converts daily returns into growth factors.
2. `.resample("ME").prod(...)` groups observations by calendar month and
   multiplies their growth factors.
3. Subtracting one converts the cumulative factor back into a return.

For example, a gain of 10% followed by a loss of 10% gives:

```math
(1+0.10)(1-0.10)-1
= 1.10 \times 0.90 - 1
= -0.01
```

The combined return is −1%, not zero. Adding or averaging the daily
returns would not calculate the compounded return.

`min_count=1` requires at least one valid observation for the monthly
product. A month with no valid observations remains missing rather than
receiving an artificial zero return.

This calculation uses the trading observations present in the dataset;
it does not insert zero returns for weekends.

## 5. Preventing incomplete monthly calculations

**Function: `draw_histogram(...)`**

```python
missing = df[sector].isna().resample("ME").sum()

monthly = monthly.mask(missing > 0)
```

Pandas normally skips missing values when calculating a product. Without
an additional check, a month containing an unknown daily return could
still receive a compounded result based on the remaining observations.

`.isna()` produces a Boolean DataFrame:

```text
True  = missing return
False = available return
```

When summed, `True` counts as one and `False` as zero.
Resampling and summing therefore counts missing observations separately
for each sector and month.

`.mask(missing > 0)` replaces the monthly result with `NaN` whenever
that sector-month contains at least one recorded missing return.

This preserves the distinction between an unknown return and a return
of zero.

The check detects missing values in existing rows. It does not detect a
trading date that is entirely absent from the dataset.

## 6. Restricting monthly analysis to complete calendar periods

**Function: `draw_histogram(...)`**

```python
month_starts = monthly.index.to_period("M").to_timestamp()

sector_returns = monthly.loc[
    (month_starts >= start) & (monthly.index <= end)
].dropna() * 100
```

Monthly observations are labelled with their calendar month-end dates.

`.to_period("M").to_timestamp()` obtains the first calendar day of each
corresponding month.

Two conditions determine whether a month is retained:

```math
\text{Month start} \geq \text{Selected start}
```

```math
\text{Month end} \leq \text{Selected end}
```

Both must be true. This avoids including a monthly return whose calendar
period extends outside the selected dates.

For example, a start date of `03/01/2000` excludes January 2000 because
its calendar start is `01/01/2000`.

After filtering, `.dropna()` removes months with missing returns in any
selected sector. The remaining sectors consequently share the same
monthly sample.

The final multiplication converts the monthly decimal returns into
percentages.

Calendar-boundary checks do not independently establish that every
expected trading observation exists in the source data.

## 7. Checking sample size and variation

**Function: `draw_histogram(...)`**

```python
if sector_returns.empty:
    return None, "There are no observations in this period."

observation_counts = sector_returns.count()
```

The first check prevents calculations on an empty sample.

`.count()` counts non-missing observations in each sector column.

The required minimum depends on the analysis:

```python
minimum_observations = 1

if chart_type == "Box plot":
    minimum_observations = 2

elif chart_type in ["Violin plot", "Normal Q-Q"]:
    minimum_observations = 3

insufficient = observation_counts[
    observation_counts < minimum_observations
].index.tolist()
```

If any selected sector has too few observations, the function returns
guidance requesting a longer period.

For violin plots, the code also checks variation:

```python
constant_sectors = [
    selected_sector
    for selected_sector in sector_returns.columns
    if sector_returns[selected_sector].dropna().nunique() < 2
]
```

`.nunique()` counts distinct values. A sector with fewer than two
distinct returns cannot support the intended density estimate and is
rejected for this chart.

These are implementation requirements. Meeting them does not mean a
small sample provides reliable statistical estimates.

## 8. Calculating quartiles and the interquartile range

**Function: `distribution_statistics(...)`**

```python
values = returns[name].dropna()

q1, median, q3 = values.quantile([0.25, 0.5, 0.75])
```

The function extracts one sector's prepared percentage returns and
calculates:

```math
Q_1 = Q(0.25), \qquad
\text{Median} = Q(0.50), \qquad
Q_3 = Q(0.75)
```

The median describes the centre of the ordered observations.

The middle-50% range, also called the interquartile range, is:

```python
iqr = q3 - q1
```

```math
IQR = Q_3 - Q_1
```

Because the inputs are percentage returns, the difference is expressed
in percentage points.

For example, if the lower quartile is −3% and the upper quartile is 5%:

```math
IQR = 5 - (-3) = 8 \text{ percentage points}
```

Pandas uses linear interpolation by default. For ordered observations,
an intermediate quantile can fall between adjacent values rather than
equal an observed return.

The interquartile range describes the spread of the middle half of the
sample. It is not the same measure as standard deviation.

## 9. Calculating the historical lower-tail cutoff

**Functions: `distribution_statistics(...)` and
`draw_interactive_distribution(...)`**

```python
alpha = 1 - confidence / 100

cutoff = values.quantile(alpha)
```

The confidence setting determines the lower-tail probability:

```math
\alpha = 1 - \frac{C}{100}
```

At 95% confidence:

```math
\alpha = 1 - 0.95 = 0.05
```

The cutoff is the empirical 5th percentile:

```math
q_\alpha = Q(\alpha)
```

It marks the lower-tail boundary of the selected historical sample.
The code reports it as a signed percentage return.

It is not the maximum possible loss or a guarantee about future
returns. Quantile interpolation and ties also mean that the share of
observations at or below the cutoff need not be exactly equal to
`alpha`.

The renderer repeats this calculation to position the historical-tail
overlays consistently with the numerical statistics.

## 10. Calculating the tail mean

**Functions: `distribution_statistics(...)` and
`draw_interactive_distribution(...)`**

```python
tail_mean = values[values <= cutoff].mean()
```

The code selects all returns at or below the estimated cutoff and
calculates their arithmetic mean.

If there are `k` selected tail observations:

```math
\text{Tail mean}
=
\frac{1}{k}
\sum_{i:\,x_i \leq q_\alpha} x_i
```

For example, if the selected tail contains returns of −12%, −10% and
−8%:

```math
\text{Tail mean}
=
\frac{-12-10-8}{3}
=
-10\%
```

A more negative tail mean indicates more severe outcomes within the
selected historical lower tail.

The implementation includes every observation tied at the cutoff.
It therefore averages the cutoff-selected observations rather than
forcing an exact fixed number of observations into the tail.

## 11. Calculating loss frequency and loss count

**Function: `distribution_statistics(...)`**

```python
valid_threshold = (
    loss_threshold is not None
    and np.isfinite(loss_threshold)
)
```

The threshold must be present and finite before loss statistics are
calculated.

```python
loss_rate = (values <= loss_threshold).mean() * 100

loss_count = int((values <= loss_threshold).sum())
```

Each comparison produces `True` or `False`. Their sum counts returns
at or below the threshold; their mean gives the proportion.

For threshold `L` and sample size `n`:

```math
\text{Loss count}
=
\sum_{i=1}^{n} \mathbf{1}(x_i \leq L)
```

```math
\text{Loss frequency}
=
\frac{\text{Loss count}}{n} \times 100
```

For example, 20 qualifying observations out of 100 give a loss
frequency of 20%.

This is different from the historical tail calculation:

- The loss threshold is selected by the user.
- The tail cutoff is estimated from the data using confidence.

Hiding the reference lines changes the display, not these calculations.

## 12. Calculating histogram density

**Function: `draw_interactive_distribution(...)`**

```python
counts, _ = np.histogram(values, bins=edges)

widths = np.diff(edges)

density = counts / (len(values) * widths)
```

The histogram counts observations within shared bin boundaries.
`np.diff(edges)` calculates each bin's width.

For bin `j`, containing `n_j` observations from a sample of size `n`,
the density is:

```math
d_j = \frac{n_j}{n\,w_j}
```

Here, `w_j` is the bin width.

The area of the bar equals its sample proportion:

```math
d_j w_j = \frac{n_j}{n}
```

For example, 20 observations out of 100 in a bin two percentage points
wide give:

```math
d_j = \frac{20}{100 \times 2} = 0.10
```

The bar's area is `0.10 × 2 = 0.20`, representing 20% of the sample.

This normalisation matters because density is not the same as a count,
and bins can have different widths. Across the full set of bins, the
total area is one.

## 13. Calculating the central histogram window

**Function: `draw_interactive_distribution(...)`**

```python
all_values = returns.to_numpy().ravel()

low, high = np.quantile(all_values, [0.01, 0.99])
```

`.ravel()` pools the selected sectors' returns into one array.

The initial Central 98% window is:

```math
[\;Q_{\text{pooled}}(0.01),\;Q_{\text{pooled}}(0.99)\;]
```

All sector panels use these common bounds. This does not guarantee that
98% of each sector's observations are individually visible.

If Full range is selected, or the pooled quantiles are equal:

```python
low, high = all_values.min(), all_values.max()
```

If all values are identical, the code expands the bounds to avoid a
zero-width range:

```python
if low == high:
    low, high = low - 0.5, high + 0.5
```

When the loss line is enabled, the central bounds expand if necessary
to include the selected threshold:

```python
padding = max((high - low) * 0.025, 0.05)

low = min(low, loss_threshold - padding)
high = max(high, loss_threshold + padding)
```

The padding is at least 0.05 percentage points.

### Retaining extreme observations

```python
edges = np.linspace(low, high, int(bins) + 1)

if all_values.min() < low:
    edges = np.r_[all_values.min(), edges]

if all_values.max() > high:
    edges = np.r_[edges, all_values.max()]
```

The code creates evenly spaced bins within the window and adds outer
bins when the sample extends beyond it. This preserves extreme
observations in the histogram's normalisation.

The number of observations outside the visible range is:

```python
outside = int(((values < low) | (values > high)).sum())
```

Changing the window can change bin edges and bar heights. It does not
remove observations from the sample used for tail measures or summary
statistics.

## 14. Estimating a smooth density curve

**Function: `draw_interactive_distribution(...)`**

```python
x = np.linspace(low, high, 500)

curve_density = stats.gaussian_kde(values)(x)
```

The first line creates 500 evaluation points across the visible range.

`gaussian_kde()` estimates the distribution using Gaussian kernel
density estimation:

```math
\widehat{f}(x)
=
\frac{1}{nh}
\sum_{i=1}^{n}
K\left(\frac{x-x_i}{h}\right)
```

For a Gaussian kernel:

```math
K(u)
=
\frac{1}{\sqrt{2\pi}}
\exp\left(-\frac{u^2}{2}\right)
```

Each observation contributes a smooth curve. Their combination
estimates where returns are concentrated.

SciPy selects the bandwidth using its default method; the code does
not supply a custom bandwidth.

The estimate uses the full selected sample, even when only the central
window is displayed. The code draws it only when there are at least
three observations and more than one distinct value.

## 15. Calculating the normal reference distribution

**Function: `draw_interactive_distribution(...)`**

```python
normal_density = stats.norm.pdf(
    x,
    loc=values.mean(),
    scale=values.std(ddof=1)
)
```

The reference distribution uses the sample mean:

```math
\bar{x} = \frac{1}{n}\sum_{i=1}^{n}x_i
```

and sample standard deviation:

```math
s =
\sqrt{
\frac{1}{n-1}
\sum_{i=1}^{n}(x_i-\bar{x})^2
}
```

`ddof=1` selects the `n − 1` denominator.

The normal probability density is:

```math
f(x)
=
\frac{1}{s\sqrt{2\pi}}
\exp\left(
-\frac{(x-\bar{x})^2}{2s^2}
\right)
```

The code requires at least three observations and a positive sample
standard deviation before displaying this curve.

This distribution provides a visual reference. It is not used to
calculate the historical cutoff or tail mean.

## 16. Calculating box-plot whiskers and outliers

**Function: `draw_interactive_distribution(...)`**

```python
q1, median, q3 = np.quantile(values, [0.25, 0.5, 0.75])

iqr = q3 - q1

lower = float(values[values >= q1 - 1.5 * iqr].min())

upper = float(values[values <= q3 + 1.5 * iqr].max())

outliers = values[(values < lower) | (values > upper)]
```

The theoretical lower and upper fences are:

```math
F_L = Q_1 - 1.5\,IQR
```

```math
F_U = Q_3 + 1.5\,IQR
```

The whiskers end at actual observed returns within those fences:

```math
W_L = \min\{x_i:x_i \geq F_L\}
```

```math
W_U = \max\{x_i:x_i \leq F_U\}
```

Values below the lower whisker or above the upper whisker are displayed
as outliers. They remain in the dataset and other statistical
calculations.

Quartiles use linear interpolation, matching the box trace's
`quartilemethod="linear"` setting.

## 17. Calculating empirical cumulative probabilities

**Function: `draw_interactive_distribution(...)`**

```python
values, counts = np.unique(
    returns[name].dropna().to_numpy(),
    return_counts=True
)

probabilities = np.cumsum(counts) / counts.sum()
```

`np.unique()` sorts the distinct returns and counts how often each
occurs.

`np.cumsum(counts)` accumulates the counts. Dividing by the total gives
the proportion of observations at or below each distinct return.

The empirical cumulative distribution is:

```math
F_n(x)
=
\frac{1}{n}
\sum_{i=1}^{n}\mathbf{1}(x_i \leq x)
```

For example, with observations `[-2, 0, 0, 3]`, the cumulative
probabilities are:

| Return | Proportion at or below |
|---|---:|
| −2% | 25% |
| 0% | 75% |
| 3% | 100% |

Counting repeated values before accumulating probabilities ensures
that tied returns are handled correctly.

## 18. Calculating the Normal Q-Q reference

**Function: `draw_interactive_distribution(...)`**

```python
quantiles, fitted = stats.probplot(values, dist="norm")

theoretical, observed = quantiles

slope, intercept, correlation = fitted
```

SciPy orders the observed returns and calculates theoretical
standard-normal quantiles using its probability-plot positions.

It then fits a least-squares reference line:

```math
\widehat{x}_i = a + b z_i
```

Here, `z_i` is a theoretical normal quantile, `a` is the intercept and
`b` is the slope.

The fitted line is calculated in the code as:

```python
slope * theoretical + intercept
```

The horizontal axis contains theoretical normal quantiles, while the
vertical axis contains observed percentage returns.

Systematic departures from the line suggest differences from a normal
distribution. Although SciPy also returns a fit correlation, the panel
does not present it as a formal normality-test result or p-value.

## 19. Selecting findings and rounding results

**Function: `sample_findings(...)`**

The function builds a DataFrame from the calculated statistics and
identifies:

- The largest and smallest interquartile ranges.
- The lowest historical tail mean.
- The highest loss frequency.

Selections use the original, unrounded values.

```python
matches = np.isclose(
    table[column].to_numpy(),
    value,
    rtol=1e-9,
    atol=1e-10
)
```

`np.isclose()` identifies numerical ties using relative and absolute
tolerances. This allows tied sectors to be reported together rather
than selecting one arbitrarily.

Its comparison is approximately:

```math
|a-b| \leq \text{atol} + \text{rtol}|b|
```

The comparison table rounds numerical values only for presentation:

```python
for name in columns[1:]:
    display[name] = display[name].round(3)
```

Rounding after ranking prevents displayed precision from changing
which sector is identified in the findings.