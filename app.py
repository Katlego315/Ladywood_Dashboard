import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------
# PAGE SETUP
# --------------------------------------------------

st.set_page_config(
    page_title="Ladywood Flooding and Pollution Dashboard",
    page_icon="🌧️",
    layout="wide"
)

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

def load_data():
    return pd.read_excel("Ladywood_Data.xlsx")

df = load_data()

# Clean column names
df.columns = (
    df.columns.astype(str)
    .str.strip()
    .str.replace(r"\s+", " ", regex=True)
)

# Standardise column names
for col in df.columns:

    if col.lower().startswith("runoff q"):
        df.rename(columns={col: "Runoff Q"}, inplace=True)

    if col.lower() == "c":
        df.rename(columns={col: "Runoff C"}, inplace=True)

# --------------------------------------------------
# PRIORITY CATEGORY
# --------------------------------------------------

def get_priority_category(score):

    if score >= 8:
        return "Very High"

    elif score >= 6:
        return "High"

    elif score >= 4:
        return "Moderate"

    else:
        return "Low"


df["Priority Category"] = df["Priority /10"].apply(
    get_priority_category
)

# --------------------------------------------------
# PAGE TITLE
# --------------------------------------------------

st.title("Ladywood Flooding and Pollution Decision-Support Dashboard")

st.info(
    """
    This dashboard identifies higher-priority locations in Ladywood,
    Birmingham by considering flood risk, drainage condition,
    population exposure, land cover, runoff potential and pollution risk.

    Select an area or location to understand the risk and view the
    recommended SuDS intervention.
    """
)

# --------------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------------

st.sidebar.title("Dashboard Filters")

area_options = ["All"] + sorted(
    df["Area"].dropna().unique().tolist()
)

selected_area = st.sidebar.selectbox(
    "Area",
    area_options
)

catchment_options = ["All"] + sorted(
    df["Catchment"].dropna().unique().tolist()
)

selected_catchment = st.sidebar.selectbox(
    "Catchment",
    catchment_options
)

priority_options = [
    "All",
    "Very High",
    "High",
    "Moderate",
    "Low"
]

selected_priority = st.sidebar.selectbox(
    "Priority Category",
    priority_options
)

# --------------------------------------------------
# APPLY FILTERS
# --------------------------------------------------

filtered_df = df.copy()

if selected_area != "All":
    filtered_df = filtered_df[
        filtered_df["Area"] == selected_area
    ]

if selected_catchment != "All":
    filtered_df = filtered_df[
        filtered_df["Catchment"] == selected_catchment
    ]

if selected_priority != "All":
    filtered_df = filtered_df[
        filtered_df["Priority Category"] == selected_priority
    ]

# --------------------------------------------------
# SECTION 1 - PROJECT SUMMARY
# --------------------------------------------------

st.header("1. Project Summary")

high_priority_count = len(
    filtered_df[
        filtered_df["Priority /10"] >= 6
    ]
)

highest_priority = (
    filtered_df["Priority /10"].max()
    if len(filtered_df) > 0
    else 0
)

average_flood = (
    filtered_df["Flood /10"].mean()
    if len(filtered_df) > 0
    else 0
)

average_pollution = (
    filtered_df["Pollution /10"].mean()
    if len(filtered_df) > 0
    else 0
)

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Locations Assessed",
    len(filtered_df)
)

c2.metric(
    "High Priority Locations",
    high_priority_count
)

c3.metric(
    "Highest Priority",
    round(highest_priority, 1)
)

c4.metric(
    "Average Flood Risk",
    round(average_flood, 1)
)

c5.metric(
    "Average Pollution Risk",
    round(average_pollution, 1)
)

st.divider()

# --------------------------------------------------
# SECTION 2 - TOP PRIORITY LOCATIONS
# --------------------------------------------------

st.header("2. Where Should Action Be Prioritised?")

st.write(
    """
    Locations with higher priority scores should be considered first
    for further investigation and possible drainage or SuDS intervention.
    """
)

top10 = (
    filtered_df
    .sort_values(
        "Priority /10",
        ascending=False
    )
    .head(10)
)

fig_priority = px.bar(
    top10,
    x="Priority /10",
    y="Location",
    orientation="h",
    hover_data=[
        "Area",
        "Flood /10",
        "Drainage /10",
        "Pollution /10",
        "Proposed SuDS"
    ],
    title="Top 10 Priority Locations"
)

fig_priority.update_layout(
    yaxis={
        "categoryorder": "total ascending"
    },
    xaxis_title="Overall Priority Score /10",
    yaxis_title=""
)

st.plotly_chart(
    fig_priority,
    use_container_width=True
)

st.divider()

# --------------------------------------------------
# SECTION 3 - INDIVIDUAL LOCATION
# --------------------------------------------------

st.header("3. Individual Location Assessment")

st.write(
    """
    Select a location to see why it received its priority score
    and which intervention is recommended.
    """
)

location_options = sorted(
    filtered_df["Location"]
    .dropna()
    .unique()
)

if len(location_options) > 0:

    selected_location = st.selectbox(
        "Select Location",
        location_options
    )

    row = filtered_df[
        filtered_df["Location"] == selected_location
    ].iloc[0]

    st.subheader(selected_location)

    st.write(
        f"**Area:** {row['Area']}  |  "
        f"**Catchment:** {row['Catchment']}  |  "
        f"**Flood Zone:** {row['Flood Zone']}"
    )

    priority_score = row["Priority /10"]
    priority_category = get_priority_category(
        priority_score
    )

    st.markdown(
        f"""
        ### Overall Priority: {priority_score}/10 — {priority_category}
        """
    )

    # Risk factor cards
    r1, r2, r3, r4, r5 = st.columns(5)

    r1.metric(
        "Flood Risk",
        f"{row['Flood /10']}/10"
    )

    r2.metric(
        "Drainage Risk",
        f"{row['Drainage /10']}/10"
    )

    r3.metric(
        "Population Exposure",
        f"{row['Pop /10']}/10"
    )

    r4.metric(
        "Impervious Surface Risk",
        f"{row['Land Cover /10']}/10"
    )

    r5.metric(
        "Pollution Risk",
        f"{row['Pollution /10']}/10"
    )

    # Runoff information
    st.subheader("Estimated Runoff")

    a, b, c = st.columns(3)

    a.metric(
        "Runoff Coefficient",
        round(row["Runoff C"], 2)
    )

    b.metric(
        "Estimated Peak Runoff",
        f"{row['Runoff Q']:.4f} m³/s"
    )

    c.metric(
        "Local Population",
        int(row["Population"])
    )

    # --------------------------------------------------
    # AUTOMATIC EXPLANATION
    # --------------------------------------------------

    st.subheader("Why is this location a priority?")

    reasons = []

    if row["Flood /10"] >= 8:
        reasons.append(
            "The location has high or very high flood risk."
        )

    if row["Drainage /10"] >= 8:
        reasons.append(
            "Drainage conditions may restrict how quickly stormwater can leave the site."
        )

    if row["Land Cover /10"] >= 8:
        reasons.append(
            "The area is highly urbanised, meaning a large proportion of rainfall may become surface runoff."
        )

    if row["Pollution /10"] >= 8:
        reasons.append(
            "Urban runoff has a high pollution-risk score."
        )

    if row["Pop /10"] >= 8:
        reasons.append(
            "A relatively large population may be exposed to the effects of flooding."
        )

    if len(reasons) == 0:
        reasons.append(
            "The combined risk factors produce a moderate overall priority."
        )

    for reason in reasons:
        st.write("• " + reason)

    # --------------------------------------------------
    # RECOMMENDED INTERVENTION
    # --------------------------------------------------

    st.subheader("Recommended Intervention")

    st.success(
        row["Proposed SuDS"]
    )

    st.write(
        """
        This recommendation is a screening-level intervention.
        Detailed site investigation would be required before construction.
        """
    )

st.divider()

# --------------------------------------------------
# SECTION 4 - FLOOD VS POLLUTION
# --------------------------------------------------

st.header("4. How Do Flood Risk and Pollution Risk Compare?")

st.write(
    """
    This graph helps identify locations where both flooding and
    pollution are important concerns.
    """
)

fig_risk = px.scatter(
    filtered_df,
    x="Flood /10",
    y="Pollution /10",
    size="Population",
    hover_name="Location",
    hover_data=[
        "Area",
        "Priority /10",
        "Proposed SuDS"
    ],
    title="Flood Risk vs Pollution Risk"
)

fig_risk.update_layout(
    xaxis_title="Flood Risk /10",
    yaxis_title="Pollution Risk /10"
)

st.plotly_chart(
    fig_risk,
    use_container_width=True
)

st.divider()

# --------------------------------------------------
# SECTION 5 - PRIORITY BY AREA
# --------------------------------------------------

st.header("5. Which Areas Have the Highest Average Priority?")

area_priority = (
    filtered_df
    .groupby(
        "Area",
        as_index=False
    )["Priority /10"]
    .mean()
    .sort_values(
        "Priority /10",
        ascending=False
    )
)

fig_area = px.bar(
    area_priority,
    x="Area",
    y="Priority /10",
    title="Average Priority Score by Area"
)

fig_area.update_layout(
    xaxis_title="Ladywood Area",
    yaxis_title="Average Priority /10"
)

st.plotly_chart(
    fig_area,
    use_container_width=True
)

st.divider()

# --------------------------------------------------
# SECTION 6 - SUDS RECOMMENDATIONS
# --------------------------------------------------

st.header("6. Which Interventions Are Recommended Most Often?")

suds_summary = (
    filtered_df["Proposed SuDS"]
    .value_counts()
    .reset_index()
)

suds_summary.columns = [
    "Recommended Intervention",
    "Number of Locations"
]

fig_suds = px.bar(
    suds_summary,
    x="Number of Locations",
    y="Recommended Intervention",
    orientation="h",
    title="Recommended SuDS Interventions"
)

fig_suds.update_layout(
    yaxis={
        "categoryorder": "total ascending"
    }
)

st.plotly_chart(
    fig_suds,
    use_container_width=True
)

st.divider()

# --------------------------------------------------
# SECTION 7 - FULL DATA
# --------------------------------------------------

with st.expander(
    "7. View Full Ladywood Dataset"
):

    display_columns = [
        "Site Ref",
        "Area",
        "Location",
        "Catchment",
        "Flood Zone",
        "Flood /10",
        "Drainage /10",
        "Population",
        "Pop /10",
        "Land Cover /10",
        "Runoff C",
        "Runoff Q",
        "Pollution /10",
        "Priority /10",
        "Priority Category",
        "Proposed SuDS"
    ]

    st.dataframe(
        filtered_df[
            display_columns
        ],
        use_container_width=True
    )

# --------------------------------------------------
# SECTION 8 - METHODOLOGY
# --------------------------------------------------

with st.expander(
    "8. Methodology and Assumptions"
):

    st.subheader("Purpose")

    st.write(
        """
        The dashboard is a screening-level decision-support tool.
        It is intended to compare locations and identify where
        further investigation should be prioritised.
        """
    )

    st.subheader("Runoff Calculation")

    st.latex(
        r"Q=\frac{CiA}{360}"
    )

    st.write(
        """
        Where:

        Q = estimated peak runoff rate in m³/s

        C = runoff coefficient

        i = rainfall intensity in mm/h

        A = contributing area in hectares
        """
    )

    st.write(
        """
        A common prototype rainfall intensity of 30 mm/h is used.

        Runoff coefficients and contributing areas are estimated
        according to the apparent site type and level of urbanisation.

        These values are screening assumptions and are not detailed
        hydraulic design values.
        """
    )

    st.subheader("Priority Score")

    st.latex(
        r"""
        Priority =
        0.30F+
        0.20D+
        0.15P+
        0.15L+
        0.20R
        """
    )

    st.write(
        """
        F = Flood Risk

        D = Drainage Risk

        P = Population Exposure

        L = Land Cover / Impervious Surface Risk

        R = Pollution Risk
        """
    )

    st.subheader("Priority Categories")

    st.write(
        """
        Very High: 8.0 - 10

        High: 6.0 - 7.9

        Moderate: 4.0 - 5.9

        Low: below 4.0
        """
    )

    st.subheader("SuDS Selection")

    st.write(
        """
        The recommended intervention is selected using a
        rule-based screening approach.

        High flood risk and poor drainage:
        detention / attenuation.

        Dense hardstanding:
        permeable paving.

        Available open or green space:
        rain garden, bioretention or swale.

        Poor infiltration and constrained sites:
        attenuation or engineered drainage improvement.
        """
    )

# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "Ladywood Flooding and Pollution Decision-Support Dashboard | Screening-Level Prototype"
)
