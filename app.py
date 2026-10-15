import streamlit as st
import pandas as pd
import plotly.express as px
import pydeck as pdk
import json

st.set_page_config(
    page_title="Ladywood Dashboard",
    layout="wide"
)

df = pd.read_excel("Ladywood_Data.xlsx")

df.columns = (
    df.columns.astype(str)
    .str.strip()
    .str.replace(r"\s+", " ", regex=True)
)

for col in df.columns:
    name = col.lower().strip()

    if name.startswith("runoff q"):
        df.rename(columns={col: "Runoff Q"}, inplace=True)

    elif name == "c" or name == "runoff c":
        df.rename(columns={col: "Runoff C"}, inplace=True)

    elif name.startswith("rainfall"):
        df.rename(columns={col: "Rainfall mm/h"}, inplace=True)


number_cols = [
    "Flood /10",
    "Drainage /10",
    "Population",
    "Pop /10",
    "Land Cover /10",
    "Runoff C",
    "Rainfall mm/h",
    "Area ha",
    "Runoff Q",
    "Pollution /10",
    "Priority /10"
]

for col in number_cols:
    if col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", ".", regex=False)
        )

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )


needed = [
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
    "Proposed SuDS"
]

missing = [
    col for col in needed
    if col not in df.columns
]

if missing:
    st.error(
        "Missing columns: "
        + ", ".join(missing)
    )
    st.stop()


df["Site"] = (
    df["Site Ref"].astype(str)
    + " - "
    + df["Location"].astype(str)
)


def priority_level(score):

    if score >= 8:
        return "Very High"

    elif score >= 6:
        return "High"

    elif score >= 4:
        return "Moderate"

    else:
        return "Low"


def priority_reasons(row):

    reasons = []

    if row["Flood /10"] >= 8:
        reasons.append(
            "High flood risk is a major contributor."
        )

    elif row["Flood /10"] >= 5:
        reasons.append(
            "Flood risk contributes to the overall priority."
        )


    if row["Drainage /10"] >= 8:
        reasons.append(
            "Drainage conditions increase the site's vulnerability."
        )


    if row["Pop /10"] >= 8:
        reasons.append(
            "Population exposure is high."
        )

    elif row["Pop /10"] >= 5:
        reasons.append(
            "Population exposure contributes to the ranking."
        )


    if row["Land Cover /10"] >= 9:
        reasons.append(
            "Extensive hard surfaces increase runoff potential."
        )

    elif row["Land Cover /10"] >= 7:
        reasons.append(
            "Built surfaces contribute to surface runoff."
        )


    if row["Pollution /10"] >= 9:
        reasons.append(
            "Pollution risk is very high."
        )

    elif row["Pollution /10"] >= 7:
        reasons.append(
            "Urban runoff pollution is also important."
        )


    return reasons


def intervention_reasons(row):

    proposal = str(
        row["Proposed SuDS"]
    ).lower()

    reasons = []


    if "detention" in proposal or "attenuation" in proposal:

        reasons.append(
            "Temporary storage helps reduce peak runoff."
        )


    if "permeable paving" in proposal:

        reasons.append(
            "Permeable paving reduces runoff from paved surfaces."
        )


    if "rain garden" in proposal or "bioretention" in proposal:

        reasons.append(
            "Bioretention provides runoff storage and pollutant treatment."
        )


    if "drainage upgrade" in proposal:

        reasons.append(
            "A drainage upgrade responds to the drainage-risk score."
        )


    if "blue-green" in proposal:

        reasons.append(
            "Blue-green infrastructure combines storage with green space."
        )


    if row["Pollution /10"] >= 9:

        reasons.append(
            "The high pollution score supports a treatment-based solution."
        )


    return reasons


st.title(
    "Ladywood Flooding and Pollution Dashboard"
)

st.caption(
    "Flood-priority screening and SuDS decision support for Ladywood, Birmingham."
)


tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Overview",
        "Location Assessment",
        "Priority Schedule",
        "Engineering Method"
    ]
)


# OVERVIEW

with tab1:

    st.subheader(
        "Project Summary"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Locations",
        len(df)
    )

    c2.metric(
        "Average Priority",
        f"{df['Priority /10'].mean():.1f}/10"
    )

    c3.metric(
        "Highest Flood Score",
        f"{df['Flood /10'].max():.0f}/10"
    )

    c4.metric(
        "Average Pollution Risk",
        f"{df['Pollution /10'].mean():.1f}/10"
    )


    st.divider()


    st.subheader(
        "Ladywood Study Area"
    )

    try:

        with open(
            "boundaries-constituencies-2024-birmingham.geojson",
            "r",
            encoding="utf-8"
        ) as file:

            boundary_data = json.load(file)


        ladywood_feature = None

        for feature in boundary_data["features"]:

            if (
                feature["properties"].get("pcon24nm")
                == "Birmingham Ladywood"
            ):

                ladywood_feature = feature
                break


        if ladywood_feature is None:

            st.error(
                "Birmingham Ladywood was not found in the boundary file."
            )

        else:

            ladywood = {
                "type": "FeatureCollection",
                "features": [ladywood_feature]
            }


            centre = ladywood_feature[
                "properties"
            ].get(
                "geo_point_2d",
                {
                    "lat": 52.48,
                    "lon": -1.92
                }
            )


            boundary_layer = pdk.Layer(
                "GeoJsonLayer",

                ladywood,

                stroked=True,
                filled=True,

                get_fill_color=[
                    30,
                    120,
                    200,
                    60
                ],

                get_line_color=[
                    0,
                    80,
                    180
                ],

                line_width_min_pixels=3,

                pickable=True
            )


            view = pdk.ViewState(
                latitude=centre["lat"],
                longitude=centre["lon"],
                zoom=11.5
            )


            deck = pdk.Deck(
                layers=[
                    boundary_layer
                ],

                initial_view_state=view,

                map_style=(
                    "https://basemaps.cartocdn.com/"
                    "gl/positron-gl-style/style.json"
                ),

                tooltip={
                    "text": "Birmingham Ladywood"
                }
            )


            st.pydeck_chart(
                deck,
                use_container_width=True
            )


            st.caption(
                "Birmingham Ladywood parliamentary constituency boundary, 2024."
            )


    except FileNotFoundError:

        st.error(
            "The Birmingham boundary file is not in the project folder."
        )

    except Exception as error:

        st.error(
            "The Ladywood map could not be displayed."
        )

        st.write(error)


    st.divider()


    st.subheader(
        "Highest Priority Locations"
    )


    top10 = (
        df.sort_values(
            "Priority /10",
            ascending=False
        )
        .head(10)
        .sort_values(
            "Priority /10"
        )
    )


    priority_fig = px.bar(
        top10,

        x="Priority /10",
        y="Site",

        orientation="h",

        hover_data=[
            "Flood /10",
            "Drainage /10",
            "Pollution /10",
            "Proposed SuDS"
        ]
    )


    priority_fig.update_layout(
        xaxis_title="Priority score /10",
        yaxis_title="",
        height=470
    )

    priority_fig.update_xaxes(
        range=[
            0,
            10
        ]
    )


    st.plotly_chart(
        priority_fig,
        use_container_width=True
    )


    st.caption(
        "Higher scores indicate locations requiring greater attention."
    )


    st.divider()


    st.subheader(
        "Flood Risk and Pollution Risk"
    )


    risk_fig = px.scatter(
        df,

        x="Flood /10",
        y="Pollution /10",

        size="Population",

        hover_name="Site",

        hover_data=[
            "Priority /10",
            "Proposed SuDS"
        ]
    )


    risk_fig.update_layout(
        xaxis_title="Flood risk /10",
        yaxis_title="Pollution risk /10",
        height=430
    )


    risk_fig.update_xaxes(
        range=[
            0,
            10
        ]
    )

    risk_fig.update_yaxes(
        range=[
            0,
            10
        ]
    )


    st.plotly_chart(
        risk_fig,
        use_container_width=True
    )


    st.caption(
        "Upper-right locations combine high flood and pollution risk."
    )


# LOCATION ASSESSMENT

with tab2:

    st.subheader(
        "Location Assessment"
    )


    selected = st.selectbox(
        "Select a site",
        df["Site"].tolist()
    )


    row = df[
        df["Site"]
        == selected
    ].iloc[0]


    st.markdown(
        f"### {row['Location']}"
    )


    st.write(
        f"**Site Ref:** {row['Site Ref']}  |  "
        f"**Area:** {row['Area']}  |  "
        f"**Catchment:** {row['Catchment']}  |  "
        f"**Flood Zone:** {row['Flood Zone']}"
    )


    c1, c2, c3, c4, c5 = st.columns(5)


    c1.metric(
        "Flood",
        f"{row['Flood /10']:.0f}/10"
    )

    c2.metric(
        "Drainage",
        f"{row['Drainage /10']:.0f}/10"
    )

    c3.metric(
        "Population",
        f"{row['Pop /10']:.0f}/10"
    )

    c4.metric(
        "Land Cover",
        f"{row['Land Cover /10']:.0f}/10"
    )

    c5.metric(
        "Pollution",
        f"{row['Pollution /10']:.0f}/10"
    )


    left, right = st.columns(
        [
            1.4,
            1
        ]
    )


    with left:

        factors = pd.DataFrame(
            {
                "Factor": [
                    "Flood",
                    "Drainage",
                    "Population",
                    "Land Cover",
                    "Pollution"
                ],

                "Score": [
                    row["Flood /10"],
                    row["Drainage /10"],
                    row["Pop /10"],
                    row["Land Cover /10"],
                    row["Pollution /10"]
                ]
            }
        )


        factor_fig = px.bar(
            factors,

            x="Factor",
            y="Score",

            text_auto=".0f"
        )


        factor_fig.update_layout(
            xaxis_title="",
            yaxis_title="Score /10",
            height=380
        )

        factor_fig.update_yaxes(
            range=[
                0,
                10
            ]
        )


        st.plotly_chart(
            factor_fig,
            use_container_width=True
        )


    with right:

        level = priority_level(
            row["Priority /10"]
        )


        st.metric(
            "Overall Priority",
            f"{row['Priority /10']:.1f}/10",
            level
        )


        st.metric(
            "Peak Runoff",
            f"{row['Runoff Q']:.4f} m³/s"
        )


        st.metric(
            "Runoff Coefficient",
            f"{row['Runoff C']:.2f}"
        )


        st.metric(
            "Population",
            f"{row['Population']:,.0f}"
        )


    st.subheader(
        "Reason for Priority"
    )


    reasons = priority_reasons(
        row
    )


    if reasons:

        for reason in reasons:

            st.write(
                "• " + reason
            )


    else:

        st.write(
            "The priority results from the combined effect of the assessed factors."
        )


    st.divider()


    st.subheader(
        "Proposed Intervention"
    )


    st.success(
        row["Proposed SuDS"]
    )


    for reason in intervention_reasons(
        row
    ):

        st.write(
            "• " + reason
        )


    st.caption(
        "The recommendation represents the preferred first-stage intervention "
        "for the assessed site conditions."
    )


# PRIORITY SCHEDULE

with tab3:

    st.subheader(
        "Priority Schedule"
    )


    schedule = (
        df[
            [
                "Site Ref",
                "Location",
                "Area",
                "Flood Zone",
                "Flood /10",
                "Pollution /10",
                "Priority /10",
                "Runoff Q",
                "Proposed SuDS"
            ]
        ]
        .sort_values(
            "Priority /10",
            ascending=False
        )
    )


    st.dataframe(
        schedule,
        use_container_width=True,
        hide_index=True
    )


    st.divider()


    st.subheader(
        "Proposed Interventions"
    )


    intervention_count = (
        df[
            "Proposed SuDS"
        ]
        .value_counts()
        .reset_index()
    )


    intervention_count.columns = [
        "Intervention",
        "Locations"
    ]


    intervention_fig = px.bar(
        intervention_count,

        x="Locations",
        y="Intervention",

        orientation="h"
    )


    intervention_fig.update_layout(
        xaxis_title="Number of locations",
        yaxis_title="",
        height=450
    )


    st.plotly_chart(
        intervention_fig,
        use_container_width=True
    )


# ENGINEERING METHOD

with tab4:

    st.subheader(
        "Runoff Calculation"
    )


    st.latex(
        r"Q=\frac{CiA}{360}"
    )


    st.write(
        "**Q** = peak runoff (m³/s)  |  "
        "**C** = runoff coefficient  |  "
        "**i** = rainfall intensity (mm/h)  |  "
        "**A** = catchment area (ha)"
    )


    st.divider()


    st.subheader(
        "Priority Score"
    )


    st.latex(
        r"P=0.30F+0.20D+0.15E+0.15L+0.20R"
    )


    st.write(
        "**F** = Flood  |  "
        "**D** = Drainage  |  "
        "**E** = Population exposure  |  "
        "**L** = Land cover  |  "
        "**R** = Pollution"
    )


    st.divider()


    st.subheader(
        "Priority Levels"
    )


    levels = pd.DataFrame(
        {
            "Score": [
                "8.0 - 10",
                "6.0 - 7.9",
                "4.0 - 5.9",
                "Below 4"
            ],

            "Priority": [
                "Very High",
                "High",
                "Moderate",
                "Low"
            ]
        }
    )


    st.table(
        levels
    )


    st.divider()


    st.subheader(
        "Engineering Basis"
    )


    st.write(
        "• A consistent rainfall intensity is applied across the study area "
        "so that locations can be compared on the same basis."
    )


    st.write(
        "• Runoff coefficients reflect the relative degree of urbanisation "
        "and impermeable land cover."
    )


    st.write(
        "• Catchment areas are represented consistently to allow direct "
        "comparison of peak runoff between locations."
    )


    st.write(
        "• Pollution risk is expressed on a common 0–10 scale to compare "
        "the relative urban-runoff concern between sites."
    )


    st.write(
        "• SuDS recommendations use the combined flood, drainage, runoff, "
        "land-cover and pollution characteristics of each location."
    )


    st.write(
        "• Priority is based on several indicators rather than a single "
        "risk factor."
    )


    st.divider()


    st.subheader(
        "Validation"
    )


    st.write(
        "• Priority results are compared with Environment Agency "
        "surface-water flood information."
    )


    st.write(
        "• Birmingham flood-risk information is used as an additional "
        "check on the ranking."
    )


    st.write(
        "• Peak runoff is independently checked using the Rational Method."
    )


    st.write(
        "• Priority weighting can be varied to test whether the "
        "highest-ranked locations remain stable."
    )
