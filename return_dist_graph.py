from pathlib import Path

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt


st.title("Return distributions")

# Find the cleaned CSV beside this Python file
filename = Path(__file__).parent / "industry_returns_clean.csv"

# Load the dataset and use dates as the row index
df = pd.read_csv(
    filename,
    parse_dates=["Date"],
    index_col="Date"
)

# Arrange from oldest to newest
df = df.sort_index()

# Let the user choose one sector
sector = st.selectbox(
    "Choose a sector",
    options=list(df.columns)
)

# Place the date inputs beside each other
left, right = st.columns(2)

with left:
    start_date = st.date_input(
        "Start date",
        value=df.index.min().date(),
        min_value=df.index.min().date(),
        max_value=df.index.max().date()
    )

with right:
    end_date = st.date_input(
        "End date",
        value=df.index.max().date(),
        min_value=df.index.min().date(),
        max_value=df.index.max().date()
    )

# Stop if the dates are in the wrong order
if start_date > end_date:
    st.info("Choose a start date before the end date.")
    st.stop()

#Rows within the chosen dates
selected_data = df.loc[pd.Timestamp(start_date):pd.Timestamp(end_date)]

#Select the sector, omit missing returns and convert to percentages
sector_returns = selected_data[sector].dropna() * 100

#No trading on weekends 
if sector_returns.empty:
    st.info("There are no trading observations in this period.")
    st.stop()

# Creating histogram
fig, ax = plt.subplots(figsize=(8, 4))

ax.hist(
    sector_returns,
    bins=30,
    color="#2563EB",
    edgecolor="white"
)

#Label and display graph
ax.set_title(f"{sector}: daily returns")
ax.set_xlabel("Daily return (%)")
ax.set_ylabel("Number of trading days")

st.pyplot(fig)
plt.close(fig)