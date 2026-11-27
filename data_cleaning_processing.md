# Data Cleaning and Sector Construction

## 1. Locate the value-weighted returns section

```python
filename = "49_Industry_Portfolios_Daily.csv"

with open(filename, "r", encoding="utf-8-sig") as file:
    lines = file.readlines()

section_start = None

for i in range(len(lines)):
    if "Average Value Weighted Returns" in lines[i]:
        section_start = i
        break

if section_start is None:
    raise ValueError("The value-weighted section was not found.")
```

The source file contains descriptive text and multiple sections, so it cannot be treated as one ordinary CSV table.

The script reads the file as text and searches for the value-weighted returns heading. The index of that heading identifies where the required section begins. `break` stops the search after the first match.

The `utf-8-sig` encoding handles a possible byte-order mark at the beginning of the file.

If the heading is absent, the script raises an error rather than continuing with an unidentified section.

## 2. Identify the column headings

```python
header_row = None

for i in range(section_start + 1, len(lines)):
    if "Agric" in lines[i] and "Softw" in lines[i]:
        header_row = i
        break

if header_row is None:
    raise ValueError("The industry column headings were not found.")
```

Starting after the selected section heading, the script searches for a line containing both `Agric` and `Softw`, two expected industry column names.

The resulting row becomes the header of the extracted table. This avoids relying on a fixed row number, which could change if introductory text is added to the source file.

An error is raised if the expected header cannot be found.

## 3. Extract the daily observations

```python
table_lines = [lines[header_row]]

for line in lines[header_row + 1:]:
    first_value = line.split(",")[0].strip()

    if first_value.isdigit() and len(first_value) == 8:
        table_lines.append(line)

    elif len(table_lines) > 1:
        break

if len(table_lines) == 1:
    raise ValueError("No daily returns were found.")
```

The extracted table starts with its column headings.

For each subsequent line, the script examines the first comma-separated value. A daily observation is recognised when this value contains exactly eight digits, matching the expected `YYYYMMDD` date structure.

This check identifies candidate data rows; the actual validity of each date is checked later.

Once observations have started, the first line that does not match this structure ends extraction. This prevents the following section of the source file from being included.

If only the header has been collected, the script raises an error because no daily observations were found.

## 4. Create the intermediate table and standardise column names

```python
with open(
    "value_weighted_returns.csv",
    "w",
    encoding="utf-8"
) as file:
    file.writelines(table_lines)

df = pd.read_csv("value_weighted_returns.csv")

df.columns = df.columns.str.strip()
df = df.rename(columns={df.columns[0]: "Date"})
```

The extracted lines are saved as a separate CSV containing only the selected table. Pandas then reads this file into a DataFrame.

Leading and trailing spaces are removed from column names. This allows later selections such as `"Softw"` to work even if the original heading contains surrounding whitespace.

The first column is renamed `Date` so subsequent processing uses a consistent name.

## 5. Convert the date column

```python
df["Date"] = pd.to_datetime(
    df["Date"].astype(str).str.strip(),
    format="%Y%m%d",
    errors="raise"
)
```

The date values are converted to strings, stripped of surrounding whitespace and parsed using the explicit `YYYYMMDD` format.

For example:

```text
20000103 → 2000-01-03
```

Converting the column to datetime values allows chronological filtering and sorting.

`errors="raise"` stops processing if a value cannot be interpreted as a valid date. Invalid dates are therefore not silently discarded or converted to missing values.

## 6. Define and validate the required industries

```python
sector_groups = {
    "Technology": ["Softw", "Hardw", "Chips"],
    "Financials": ["Banks", "Insur", "Fin"],
    "Healthcare": ["Hlth", "MedEq", "Drugs"],
    "Energy": ["Oil", "Coal"],
    "Consumer goods": ["Food", "Soda", "Beer", "Smoke", "Hshld", "Clths"],
    "Industrials": ["Mach", "ElcEq", "Steel", "FabPr", "Aero", "Ships"],
    "Utilities": ["Util"],
    "Real estate": ["RlEst"]
}

required_columns = []

for sector in sector_groups:
    for industry in sector_groups[sector]:
        required_columns.append(industry)

for column in required_columns:
    if column not in df.columns:
        raise ValueError("Missing industry column: " + column)

df = df[["Date"] + required_columns].copy()
```

The dictionary defines the source industries assigned to each of the eight custom sectors.

The nested loops collect the required industry names into one list. Each name is checked against the source table before the data is selected.

If an expected industry is absent, the script raises an error identifying it. This prevents a sector from being calculated using an unintended subset of its constituents.

The DataFrame is then restricted to the date and required industry columns. `.copy()` creates a separate DataFrame for the remaining cleaning operations.

These groups are project-defined combinations of the source industries.

## 7. Validate numeric returns and identify missing values

```python
for column in required_columns:
    df[column] = pd.to_numeric(df[column], errors="raise")

df[required_columns] = df[required_columns].replace(
    [-99.99, -999],
    float("nan")
)
```

Each return column is converted to numeric values. If a value cannot be converted, `errors="raise"` stops the script rather than silently treating the unexpected entry as missing.

The source dataset's missing-value codes, `-99.99` and `-999`, are then replaced with `NaN`.

This happens before percentage conversion and sector averaging. Otherwise, these codes could be interpreted as genuine large negative returns and distort the results.

Missing values are not replaced with zero. A zero return would indicate no change in value, whereas `NaN` records an unknown observation.

## 8. Select the analysis period

```python
df = df.loc[
    (df["Date"] >= "2000-01-01")
    & (df["Date"] < "2027-01-01")
].copy()

if df.empty:
    raise ValueError("No observations exist in the selected date range.")
```

The script retains available observations from 1 January 2000 up to, but excluding, 1 January 2027.

The selection rule is:

```math
\text{1 January 2000} \leq t < \text{1 January 2027}
```

The upper bound includes all dates within 2026 without requiring a separate end-of-year timestamp.

This operation filters existing observations. It does not create dates or guarantee that the source contains data through the end of 2026.

An error is raised if the selected period contains no observations.

## 9. Sort observations and check for duplicate dates

```python
df = df.sort_values("Date")

if df["Date"].duplicated().any():
    raise ValueError("Duplicate dates found. Check the original dataset.")
```

Sorting places the observations in chronological order.

The duplicate check identifies repeated dates within the selected period. If any exist, processing stops so the source can be investigated.

Duplicate dates could cause a day's return to be counted more than once during later monthly compounding. The script therefore reports them rather than automatically choosing which row to retain.

This check does not identify dates entirely absent from the dataset.

## 10. Convert percentage returns into decimal returns

```python
df[required_columns] = df[required_columns] / 100
```

The source returns are expressed in percentage units. Dividing by 100 converts them into decimal returns:

```math
r_{i,t} = \frac{p_{i,t}}{100}
```

Where:

- \(p_{i,t}\) is the source percentage return for industry \(i\) on date \(t\).
- \(r_{i,t}\) is the corresponding decimal return.

For example:

```text
1.5 → 0.015
-2.0 → -0.020
```

Decimal returns can be used directly in growth calculations such as:

```math
V_t = V_{t-1}(1+r_t)
```

The cleaning script performs the unit conversion. Investment growth and monthly compounding are calculated later by the dashboard panels.

## 11. Construct the custom sector returns

```python
sector_df = df[["Date"]].copy()

for sector in sector_groups:
    industry_columns = sector_groups[sector]

    sector_df[sector] = df[industry_columns].mean(
        axis=1,
        skipna=False
    )
```

A new DataFrame is created with one date column and one return column for each custom sector.

`axis=1` calculates the arithmetic mean across the constituent industries on each date:

```math
R_{s,t} = \frac{1}{k_s}\sum_{i \in G_s} r_{i,t}
```

Where:

- \(R_{s,t}\) is the custom return for sector \(s\) on date \(t\).
- \(G_s\) is the set of industries assigned to that sector.
- \(k_s\) is the number of constituent industries.
- \(r_{i,t}\) is an industry's decimal daily return.

For Technology:

```math
R_{\text{Technology},t}
=
\frac{
r_{\text{Softw},t}
+
r_{\text{Hardw},t}
+
r_{\text{Chips},t}
}{3}
```

If those returns were `0.01`, `0.02` and `-0.015`, the resulting sector return would be:

```math
\frac{0.01+0.02-0.015}{3}
=
0.005
=
0.5\%
```

Each constituent industry receives equal weight within its custom sector. The source industry portfolios are value-weighted, but the custom sector calculation does not apply market-capitalisation weights across those portfolios.

For Utilities and Real estate, which each contain one source industry, the sector return equals that industry's return.

### Missing constituent returns

`skipna=False` means that a missing constituent makes the sector return missing for that date:

```math
R_{s,t}
=
\begin{cases}
\frac{1}{k_s}\sum_{i \in G_s}r_{i,t},
& \text{if all constituent returns are available}\\
\mathrm{NaN},
& \text{otherwise}
\end{cases}
```

This avoids calculating the sector from a changing number of industries.

The date remains in the output even when a sector return is missing. Individual dashboard panels subsequently determine which observations can be used in their analysis.

## 12. Inspect missing values and export the prepared dataset

```python
print("\nFirst five rows:")
print(sector_df.head())

print("\nLast five rows:")
print(sector_df.tail())

print("\nMissing values by sector:")
print(sector_df.isna().sum())

print("\nRows and columns:", sector_df.shape)
print("First date:", sector_df["Date"].min())
print("Last date:", sector_df["Date"].max())

sector_df.to_csv(
    "industry_returns_clean.csv",
    index=False
)

print("\nSaved: industry_returns_clean.csv")
```

The first and last rows support a visual check of the output structure and date order.

`isna()` identifies missing values, and `.sum()` counts them separately for each column:

```math
M_s = \sum_{t=1}^{N}
\mathbf{1}\left(R_{s,t}\text{ is missing}\right)
```

Where \(M_s\) is the number of missing observations for sector \(s\), and the indicator equals 1 when a return is missing and 0 otherwise.

The shape reports the number of rows and columns. The minimum and maximum dates show the actual period available after filtering.

These printed checks report the output; they do not automatically remove missing observations or establish that the dataset contains every expected trading date.

Finally, the prepared data is saved to `industry_returns_clean.csv`. `index=False` prevents pandas from adding an unnecessary row-number column. The output contains `Date` and the eight custom sector return columns, with returns stored as decimals.