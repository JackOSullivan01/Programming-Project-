import pandas as pd

# 1. Open the original dataset
filename = "49_Industry_Portfolios_Daily.csv"
with open(filename, "r", encoding="utf-8-sig") as file:
    lines = file.readlines()

# 2. Find the value-weighted section using ordinary loops
section_start = None

for i in range(len(lines)):
    if "Average Value Weighted Returns" in lines[i]:
        section_start = i
        break

if section_start is None:
    raise ValueError("The value-weighted section was not found.")

# 3. Find the column headings within that section
header_row = None

for i in range(section_start + 1, len(lines)):
    if "Agric" in lines[i] and "Softw" in lines[i]:
        header_row = i
        break

if header_row is None:
    raise ValueError("The industry column headings were not found.")

# 4. Collect the headings and daily data rows
table_lines = [lines[header_row]]

for line in lines[header_row + 1:]:
    first_value = line.split(",")[0].strip()

    if first_value.isdigit() and len(first_value) == 8:
        table_lines.append(line)

    elif len(table_lines) > 1:
        break

if len(table_lines) == 1:
    raise ValueError("No daily returns were found.")

# 5. Save the extracted table as a separate CSV
with open(
    "value_weighted_returns.csv",
    "w",
    encoding="utf-8"
) as file:
    file.writelines(table_lines)

# 6. Read that CSV into pandas
df = pd.read_csv("value_weighted_returns.csv")

# 7. Clean the column names and rename the first column
df.columns = df.columns.str.strip()
df = df.rename(columns={df.columns[0]: "Date"})

# 8. Convert the dates
df["Date"] = pd.to_datetime(
    df["Date"].astype(str).str.strip(),
    format="%Y%m%d",
    errors="raise"
)

# 9. Define our eight custom sector groups
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

# 10. Make a list of all the industry columns we need
required_columns = []

for sector in sector_groups:
    for industry in sector_groups[sector]:
        required_columns.append(industry)

# Check that those columns exist
for column in required_columns:
    if column not in df.columns:
        raise ValueError("Missing industry column: " + column)

# Keep only the date and required industries
df = df[["Date"] + required_columns].copy()

# 11. Convert returns to numbers
for column in required_columns:
    df[column] = pd.to_numeric(df[column], errors="raise")

# 12. Replace missing-value codes with NaN
df[required_columns] = df[required_columns].replace([-99.99, -999], float("nan"))

# 13. Keep available data from 2000 through 2026
df = df.loc[(df["Date"] >= "2000-01-01")& (df["Date"] < "2027-01-01")].copy()

if df.empty:
    raise ValueError("No observations exist in the selected date range.")

# 14. Sort dates and check for duplicates
df = df.sort_values("Date")

if df["Date"].duplicated().any():
    raise ValueError("Duplicate dates found. Check the original dataset.")

# 15. Convert percentage returns into decimal returns
df[required_columns] = df[required_columns] / 100

# 16. Create the new sector dataset
sector_df = df[["Date"]].copy()

for sector in sector_groups:
    industry_columns = sector_groups[sector]

    # Average across the industries for each date.
    # If any constituent return is missing, keep the sector missing.
    sector_df[sector] = df[industry_columns].mean(axis=1, skipna=False)

# 17. Inspect the result
print("\nFirst five rows:")
print(sector_df.head())

print("\nLast five rows:")
print(sector_df.tail())

print("\nMissing values by sector:")
print(sector_df.isna().sum())

print("\nRows and columns:", sector_df.shape)
print("First date:", sector_df["Date"].min())
print("Last date:", sector_df["Date"].max())

# 18. Save the cleaned sector dataset
sector_df.to_csv("industry_returns_clean.csv", index=False)

print("\nSaved: industry_returns_clean.csv")