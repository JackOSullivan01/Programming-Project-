from pathlib import Path

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt


st.title("Return distributions")

#Load the cleaned dataset
filename = Path(__file__).parent / "industry_returns_clean.csv"

df = pd.read_csv(
    filename,
    parse_dates=["Date"],
    index_col="Date"
)

#Convert decimal returns into percentages
technology_returns = df["Technology"].dropna() * 100

# basic histogram
fig, ax = plt.subplots(figsize=(8, 4))

ax.hist(
    technology_returns,
    bins=30,
    color="#2563EB",
    edgecolor="white"
)

ax.set_title("Technology: daily returns")
ax.set_xlabel("Daily return (%)")
ax.set_ylabel("Number of trading days")

st.pyplot(fig)
plt.close(fig)