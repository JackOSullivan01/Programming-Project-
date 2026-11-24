import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

# 1. Load the CSV file (with quotes and .csv)
df = pd.read_csv("industry_returns_clean.csv", index_col="Date")

# 2. Calculate correlation matrix
corr = df.corr()

# 3. Mask the lower triangle and diagonal
mask = np.tril(np.ones(corr.shape, dtype=bool))

# 4. Plot the heatmap
fig, ax = plt.subplots(figsize=(9, 7))
sns.heatmap(
    corr,
    mask=mask,
    annot=True,
    fmt=".2f",
    cmap="RdBu",
    vmin=-1,
    vmax=1,
    center=0,
    square=True,
    ax=ax
)

ax.set_title("Industry Returns Correlation Matrix")
plt.tight_layout()

# 5. Save the chart as an image in your folder
plt.savefig("correlation_heatmap.png", dpi=300)
print("Done! Heatmap saved.")
pd.read_csv(industry_returns_clean)

