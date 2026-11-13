import streamlit as st

st.set_page_config(
    page_title="Industry Performance Explorer",
    page_icon="📊",
    layout="wide"
)

# Main heading
with st.container(horizontal_alignment="center"):
    st.title("Industry Performance Explorer")
    st.caption("GROWTH  •  RISK  •  DIVERSIFICATION")
    st.write("Compare industries and explore investment performance.")

st.divider()

# Example choices until the real dataset is connected
industries = [
    "Technology",
    "Banking",
    "Energy",
    "Healthcare",
    "Retail",
    "Manufacturing"
]

top_left, top_right = st.columns(2, gap="large")

# PANEL 1 — INVESTMENT GROWTH
with top_left:
    with st.container(border=True):
        st.subheader("📈 Investment growth")
        st.caption("Explore how your investment could have grown.")

        growth_industries = st.multiselect(
            "Choose industries",
            options=industries,
            default=["Technology", "Banking"],
            key="growth_industries"
        )

        growth_years = st.slider(
            "Year range",
            min_value=2000,
            max_value=2025,
            value=(2010, 2025),
            key="growth_years"
        )

        investment_column, contribution_column = st.columns(2)

        with investment_column:
            starting_investment = st.number_input(
                "Starting investment ($)",
                min_value=100,
                value=1000,
                step=100,
                key="starting_investment"
            )

        with contribution_column:
            monthly_contribution = st.number_input(
                "Monthly contribution ($)",
                min_value=0,
                value=0,
                step=50,
                key="monthly_contribution"
            )

        growth_benchmark = st.checkbox(
            "Include a market benchmark",
            value=True,
            key="growth_benchmark"
        )

        st.divider()

        with st.container(height=300):
            st.info("The investment growth line chart will appear here.")
            st.caption(
                "The investment amount, contributions and benchmark "
                "will feed into this panel's calculations."
            )

# PANEL 2 — RISK VERSUS RETURN
with top_right:
    with st.container(border=True):
        st.subheader("🎯 Risk versus return")
        st.caption("Compare performance with different measures of risk.")

        risk_industries = st.multiselect(
            "Choose industries",
            options=industries,
            default=["Technology", "Banking"],
            key="risk_industries"
        )

        risk_years = st.slider(
            "Year range",
            min_value=2000,
            max_value=2025,
            value=(2010, 2025),
            key="risk_years"
        )

        risk_measure_column, frequency_column = st.columns(2)

        with risk_measure_column:
            risk_measure = st.selectbox(
                "Risk measure",
                options=["Annualised volatility", "Maximum drawdown"],
                key="risk_measure"
            )

        with frequency_column:
            risk_frequency = st.selectbox(
                "Return frequency",
                options=["Daily", "Monthly"],
                key="risk_frequency"
            )

        return_target = st.slider(
            "Annual return target (%)",
            min_value=-10,
            max_value=30,
            value=8,
            step=1,
            key="return_target"
        )

        st.divider()

        with st.container(height=300):
            st.info("The risk and return scatter plot will appear here.")
            st.caption(
                "Volatility measures fluctuations in returns. Maximum "
                "drawdown measures the largest peak-to-trough fall "
                "at the selected observation frequency."
            )

st.space("medium")

bottom_left, bottom_right = st.columns(2, gap="large")

# PANEL 3 — CORRELATIONS
with bottom_left:
    with st.container(border=True):
        st.subheader("🔗 Industry correlations")
        st.caption("Discover which industries tend to move together.")

        correlation_industries = st.multiselect(
            "Choose industries",
            options=industries,
            default=["Technology", "Banking", "Energy"],
            key="correlation_industries"
        )

        correlation_years = st.slider(
            "Year range",
            min_value=2000,
            max_value=2025,
            value=(2010, 2025),
            key="correlation_years"
        )

        correlation_frequency = st.selectbox(
            "Return frequency",
            options=["Daily", "Monthly"],
            key="correlation_frequency"
        )

        minimum_correlation = st.slider(
            "Minimum absolute correlation to display",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.05,
            key="minimum_correlation"
        )

        show_correlation_values = st.checkbox(
            "Show correlation values inside cells",
            value=True,
            key="show_correlation_values"
        )

        st.divider()

        with st.container(height=300):
            st.info("The correlation heatmap will appear here.")
            st.caption(
                "For example, a threshold of 0.60 will show values "
                "at or above +0.60 and at or below −0.60."
            )

# PANEL 4 — RETURN DISTRIBUTIONS
with bottom_right:
    with st.container(border=True):
        st.subheader("📊 Return distributions")
        st.caption("Explore typical returns and extreme gains or losses.")

        distribution_industries = st.multiselect(
            "Choose industries",
            options=industries,
            default=["Technology", "Energy"],
            key="distribution_industries"
        )

        distribution_years = st.slider(
            "Year range",
            min_value=2000,
            max_value=2025,
            value=(2010, 2025),
            key="distribution_years"
        )

        chart_type_column, distribution_frequency_column = st.columns(2)

        with chart_type_column:
            distribution_chart = st.selectbox(
                "Chart type",
                options=["Violin plot", "Box plot", "Histogram"],
                key="distribution_chart"
            )

        with distribution_frequency_column:
            distribution_frequency = st.selectbox(
                "Return frequency",
                options=["Daily", "Monthly"],
                key="distribution_frequency"
            )

        if distribution_chart == "Histogram":
            histogram_bins = st.slider(
                "Number of bins",
                min_value=10,
                max_value=100,
                value=30,
                step=5,
                key="histogram_bins"
            )

        loss_threshold = st.slider(
            "Highlight returns at or below (%)",
            min_value=-30,
            max_value=0,
            value=-5,
            step=1,
            key="loss_threshold"
        )

        st.divider()

        with st.container(height=300):
            st.info("The return distribution chart will appear here.")
            st.caption(
                "The loss threshold will identify extreme negative "
                "returns at the selected daily or monthly frequency."
            )

st.divider()
st.caption(
    "Layout preview · Industries and dates are examples · "
    "Controls are ready to connect to data and calculations."
)