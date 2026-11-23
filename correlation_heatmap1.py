import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
import gradio as gr


# ==============================================================================
# 1. DATA LOADING & PREPROCESSING ENGINE
# ==============================================================================
def load_and_prepare_data(filepath: str = "industry_returns_clean.csv") -> pd.DataFrame:
    """
    Loads daily industry return series, parses datetime index,
    and ensures clean numeric formatting across all sector columns.
    """
    df = pd.read_csv(filepath)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    return df


def resample_returns(df: pd.DataFrame, frequency: str) -> pd.DataFrame:
    """
    Compounds daily simple returns into the chosen return frequency
    (Daily, Weekly, Monthly, or Quarterly) using geometric linking:
    R_period = prod(1 + r_t) - 1
    """
    freq_map = {
        "Daily": None,
        "Weekly": "W-FRI",
        "Monthly": "ME",
        "Quarterly": "QE",
    }
    rule = freq_map.get(frequency)
    if rule is None:
        return df

    # Compound daily returns accurately across each period
    compounded = (1.0 + df).resample(rule).prod() - 1.0
    return compounded.dropna(how="all")


# ==============================================================================
# 2. STATISTICAL CORRELATION & P-VALUE MATRIX COMPUTATION
# ==============================================================================


def compute_correlation_and_pvalues(
    df: pd.DataFrame, method: str = "pearson"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Computes both the pairwise correlation matrix and the corresponding
    two-tailed p-value matrix for statistical significance filtering.
    """
    cols = df.columns
    n = len(cols)
    corr_matrix = pd.DataFrame(np.eye(n), index=cols, columns=cols, dtype=float)
    pval_matrix = pd.DataFrame(np.zeros((n, n)), index=cols, columns=cols, dtype=float)

    for i in range(n):
        for j in range(i + 1, n):
            valid = df[[cols[i], cols[j]]].dropna()
            if len(valid) < 3:
                r, p = np.nan, 1.0
            elif method.lower() == "spearman":
                r, p = stats.spearmanr(valid[cols[i]], valid[cols[j]])
            else:
                r, p = stats.pearsonr(valid[cols[i]], valid[cols[j]])

            corr_matrix.iloc[i, j] = corr_matrix.iloc[j, i] = r
            pval_matrix.iloc[i, j] = pval_matrix.iloc[j, i] = p

    return corr_matrix, pval_matrix


# ==============================================================================
# 3. INTERACTIVE PLOTLY HEATMAP & INSIGHT GENERATOR
# ==============================================================================


RAW_DF = load_and_prepare_data("industry_returns_clean.csv")
ALL_SECTORS = list(RAW_DF.columns)
MIN_YEAR = int(RAW_DF.index.year.min())
MAX_YEAR = int(RAW_DF.index.year.max())

def update_correlation_panel(
    selected_sectors: list[str],
    start_year: int,
    end_year: int,
    frequency: str,
    corr_method: str,
    abs_threshold: float,
    show_values: bool,
    hide_insignificant: bool,
    triangle_mode: str,
):
    """
    Callback triggered whenever any UI control in the Industry Correlations
    panel changes. Returns an interactive Plotly Figure and an analytical summary.
    """
    # Guard against fewer than 2 sectors or inverted year bounds
    if not selected_sectors or len(selected_sectors) < 2:
        empty_fig = go.Figure()
        empty_fig.add_annotation(
            text="Select at least 2 industries to compute correlations.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color="#64748b"),
        )
        empty_fig.update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            template="plotly_dark",
            plot_bgcolor="#111827",
            paper_bgcolor="#111827",
            height=460,
        )
        return empty_fig, "**Selection Notice:** Please choose at least two sectors."

    if start_year > end_year:
        start_year, end_year = end_year, start_year

    # Filter date window and selected industries
    filtered = RAW_DF.loc[f"{start_year}-01-01":f"{end_year}-12-31", selected_sectors]
    resampled = resample_returns(filtered, frequency)

    # Calculate correlations & significance
    corr_df, pval_df = compute_correlation_and_pvalues(resampled, method=corr_method)

    # Build display matrix & custom hover metadata
    z_vals = corr_df.values.copy()
    text_labels = np.empty(z_vals.shape, dtype=object)
    hover_text = np.empty(z_vals.shape, dtype=object)

    n = len(selected_sectors)
    for i in range(n):
        for j in range(n):
            r_val = corr_df.iloc[i, j]
            p_val = pval_df.iloc[i, j]
            sec_y = selected_sectors[i]
            sec_x = selected_sectors[j]

            # Apply structural triangle mask if selected
            is_masked = False
            if triangle_mode == "Upper Triangle Only" and i > j:
                is_masked = True
            elif triangle_mode == "Lower Triangle Only" and i < j:
                is_masked = True

            # Apply threshold and p-value filters (off-diagonal pairs)
            if i != j:
                if abs(r_val) < abs_threshold:
                    is_masked = True
                if hide_insignificant and p_val >= 0.05:
                    is_masked = True

            if is_masked or np.isnan(r_val):
                z_vals[i, j] = np.nan
                text_labels[i, j] = ""
                hover_text[i, j] = ""
            else:
                text_labels[i, j] = f"{r_val:.2f}" if show_values else ""
                sig_tag = "Significant (p < 0.05)" if p_val < 0.05 else "Not significant"
                hover_text[i, j] = (
                    f"<b>{sec_y} vs. {sec_x}</b><br>"
                    f"Correlation ({corr_method}): <b>{r_val:.3f}</b><br>"
                    f"p-value: {p_val:.4f} ({sig_tag})<br>"
                    f"Period: {start_year}–{end_year} ({frequency})"
                )

    # Build diverging RdBu heatmap or 3D Surface matching the Industry Performance Explorer palette
    if triangle_mode == "3D Surface":
        fig = go.Figure(
            data=go.Surface(
                z=z_vals,
                x=list(range(n)),
                y=list(range(n)),
                cmin=-1.0,
                cmax=1.0,
                cmid=0.0,
                colorscale="RdBu_r",
                text=hover_text,
                hoverinfo="text",
                colorbar=dict(
                    title=dict(text="Correlation", side="right"),
                    tickvals=[-1.0, -0.5, 0.0, 0.5, 1.0],
                    tickformat=".2f",
                    thickness=14,
                    len=0.85,
                ),
            )
        )

        fig.update_layout(
            title=dict(
                text=(
                    f"<b>3D Industry Correlations ({frequency} Returns, {start_year}–{end_year})</b>"
                    f"<br><span style='font-size:12px;color:#64748b;'>"
                    f"{corr_method} r | Threshold |r| ≥ {abs_threshold:.2f} | N = {len(resampled):,} observations"
                    f"</span>"
                ),
                x=0.14,
                y=0.96,
            ),
            scene=dict(
                xaxis=dict(
                    title="",
                    tickvals=list(range(n)),
                    ticktext=selected_sectors,
                    backgroundcolor="#111827",
                    gridcolor="#374151",
                ),
                yaxis=dict(
                    title="",
                    tickvals=list(range(n)),
                    ticktext=selected_sectors,
                    backgroundcolor="#111827",
                    gridcolor="#374151",
                ),
                zaxis=dict(
                    title="Correlation (r)",
                    range=[-1.0, 1.0],
                    backgroundcolor="#111827",
                    gridcolor="#374151",
                ),
            ),
            template="plotly_dark",
            plot_bgcolor="#111827",
            paper_bgcolor="#111827",
            font=dict(color="#f3f4f6"),
            margin=dict(l=20, r=20, t=95, b=20),
            height=550,
        )
    else:
        fig = go.Figure(
            data=go.Heatmap(
                z=z_vals,
                x=selected_sectors,
                y=selected_sectors,
                zmin=-1.0,
                zmax=1.0,
                zmid=0.0,
                colorscale="RdBu_r",  # Red = strong positive (+1), Blue = negative (-1)
                text=text_labels,
                texttemplate="%{text}" if show_values else None,
                textfont=dict(size=11, family="Inter, Arial, sans-serif"),
                hovertext=hover_text,
                hoverinfo="text",
                xgap=2,
                ygap=2,
                colorbar=dict(
                    title=dict(text="Correlation", side="right"),
                    tickvals=[-1.0, -0.5, 0.0, 0.5, 1.0],
                    tickformat=".2f",
                    thickness=14,
                    len=0.85,
                ),
            )
        )

        fig.update_layout(
            title=dict(
                text=(
                    f"<b>Industry Correlations ({frequency} Returns, {start_year}–{end_year})</b>"
                    f"<br><span style='font-size:12px;color:#9ca3af;'>"
                    f"{corr_method} r | Threshold |r| ≥ {abs_threshold:.2f} | N = {len(resampled):,} observations"
                    f"</span>"
                ),
                x=0.14,
                y=0.96,
            ),
            xaxis=dict(
                side="top",
                tickangle=-25,
                showgrid=False,
                zeroline=False,
            ),
            yaxis=dict(
                autorange="reversed",  # Keeps diagonal running top-left to bottom-right
                showgrid=False,
                zeroline=False,
            ),
            template="plotly_dark",
            plot_bgcolor="#111827",
            paper_bgcolor="#111827",
            font=dict(color="#f3f4f6"),
            margin=dict(l=90, r=40, t=115, b=30),
            height=490,
        )
    # Extract strongest and weakest off-diagonal pairs for automated storytelling
    upper_indices = np.triu_indices(n, k=1)
    pair_records = []
    for i, j in zip(*upper_indices):
        r_val = corr_df.iloc[i, j]
        if not np.isnan(r_val):
            pair_records.append((selected_sectors[i], selected_sectors[j], r_val))

    if pair_records:
        pair_records.sort(key=lambda item: item[2], reverse=True)
        top_pair = pair_records[0]
        low_pair = pair_records[-1]
        avg_corr = np.mean([p[2] for p in pair_records])
        summary_md = (
            f"**Diversification & Co-Movement Summary ({start_year}–{end_year}, {frequency}):** "
            f"Average cross-sector correlation is **{avg_corr:.2f}**. "
            f"Highest co-movement: **{top_pair[0]} & {top_pair[1]} ({top_pair[2]:.2f})** | "
            f"Best diversification pair: **{low_pair[0]} & {low_pair[1]} ({low_pair[2]:.2f})**."
        )
    else:
        summary_md = "**Summary:** No visible off-diagonal correlations under current filter settings."

    return fig, summary_md

# ==============================================================================
# 4. MODULAR GRADIO PANEL BUILDER (INTEGRATES INTO 4-PANEL DASHBOARD)
# ==============================================================================
def build_correlation_panel() -> gr.Column:
    """
    Constructs the self-contained bottom-left 'Industry correlations' card
    so it can be imported directly into the main 2x2 Gradio dashboard layout.
    """
    with gr.Column(variant="panel") as panel:
        gr.Markdown("### 🔗 Industry correlations")

        # Row 1: Multi-select Industries
        sector_selector = gr.Dropdown(
            choices=ALL_SECTORS,
            value=ALL_SECTORS,
            multiselect=True,
            label="Industries",
            info="Add or remove sectors from the correlation matrix",
        )

        # Row 2: Threshold Slider, Date Window, and Frequency Controls
        with gr.Row():
            threshold_slider = gr.Slider(
                minimum=0.0,
                maximum=0.95,
                value=0.0,
                step=0.05,
                label="Absolute correlation threshold |r|",
            )
            start_year_dd = gr.Dropdown(
                choices=list(range(MIN_YEAR, MAX_YEAR + 1)),
                value=MIN_YEAR,
                label="Start year",
            )
            end_year_dd = gr.Dropdown(
                choices=list(range(MIN_YEAR, MAX_YEAR + 1)),
                value=MAX_YEAR,
                label="End year",
            )
            freq_dd = gr.Dropdown(
                choices=["Daily", "Weekly", "Monthly", "Quarterly"],
                value="Daily",
                label="Frequency",
            )

        # Row 3: Display & Statistical Controls
        with gr.Row():
            show_vals_chk = gr.Checkbox(value=True, label="Show values")
            sig_only_chk = gr.Checkbox(value=False, label="Significant only (p < 0.05)")
            method_radio = gr.Radio(
                choices=["Pearson", "Spearman"],
                value="Pearson",
                label="Method",
            )
            triangle_dd = gr.Dropdown(
               choices=["Full Matrix", "Upper Triangle Only", "Lower Triangle Only", "3D Surface"],
                value="Full Matrix",
                label="Matrix view",
            )

        # Main Interactive Chart & Automated Story Callout
        heatmap_plot = gr.Plot(label="Correlation Matrix")
        insight_text = gr.Markdown()

        # Wire all UI controls to the update callback
        controls = [
            sector_selector,
            start_year_dd,
            end_year_dd,
            freq_dd,
            method_radio,
            threshold_slider,
            show_vals_chk,
            sig_only_chk,
            triangle_dd,
        ]

        for ctrl in controls:
            ctrl.change(
                fn=update_correlation_panel,
                inputs=controls,
                outputs=[heatmap_plot, insight_text],
            )

        # Trigger initial render when dashboard loads
        panel_inputs = controls
        panel_outputs = [heatmap_plot, insight_text]

    return panel, panel_inputs, panel_outputs

# ==============================================================================
# 5. STANDALONE EXECUTION ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    with gr.Blocks(title="Industry Performance Explorer - Correlation Module") as demo:
        gr.Markdown(
            "# Industry Performance Explorer\n"
            "### Growth • Risk • Diversification *(Bottom-Left Panel Preview)*"
        )
        _, init_inputs, init_outputs = build_correlation_panel()
        demo.load(
            fn=update_correlation_panel,
            inputs=init_inputs,
            outputs=init_outputs,
        )

    demo.launch()
