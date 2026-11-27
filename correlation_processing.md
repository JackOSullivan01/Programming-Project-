# Industry Correlations Panel — How the Calculation Works

1. **Date and industry filtering:** The panel first filters `industry_returns_clean.csv` to the selected **Start year** and **End year** (automatically swapping the bounds if inverted) and keeps only the chosen **Industries** (requiring at least two).
2. **Return compounding across frequencies:**
   - For **Daily** frequency, raw daily simple returns are used directly.
   - For **Weekly** (`W-FRI`), **Monthly** (`ME`), or **Quarterly** (`QE`) frequency, daily returns within each period are geometrically compounded:
     `Period return = product of (1 + each daily return) - 1`
3. **Pairwise correlation and significance testing:** For every pair of selected industries, dates with missing values in either industry are dropped. If at least 3 overlapping observations remain, the panel computes both the correlation coefficient (*r*) and two-tailed *p*-value using the chosen method:
   - **Pearson** measures linear co-movement between two return series.
   - **Spearman** measures rank-order (monotonic) co-movement, making it less sensitive to extreme single-period market shocks.
   - Diagonal self-correlations are fixed at `1.0` (`p = 0.0`).
4. **Display filtering and matrix views:**
   - Off-diagonal cells whose absolute correlation falls below the **Absolute correlation threshold |r|** slider are hidden (`NaN`).
   - When **Significant only (p < 0.05)** is checked, off-diagonal pairs with a two-tailed *p*-value of `0.05` or higher are hidden.
   - The **Matrix view** dropdown optionally masks the lower triangle (`i > j`), masks the upper triangle (`i < j`), or renders the full matrix as an interactive **3D Surface**.
5. **Automated diversification summary:** The summary line below the chart extracts all unique upper-triangle pairs (`i < j`), calculates their mean correlation, and identifies the highest-correlating pair (strongest co-movement) and lowest-correlating pair (strongest diversification benefit).