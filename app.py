import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import folium
from folium.plugins import Fullscreen
import json


st.set_page_config(
    page_title="Ladywood Dashboard",
    layout="wide"
)


# =========================================================
# DATA
# =========================================================

@st.cache_data
def load_data():

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

        elif name in ["c", "runoff c"]:
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


    return df


@st.cache_data
def load_boundary():

    with open(
        "ladywood_ward.geojson",
        "r",
        encoding="utf-8"
    ) as file:

        boundary = json.load(file)


    if boundary.get("type") == "Feature":

        boundary = {
            "type": "FeatureCollection",
            "features": [boundary]
        }


    return boundary


df = load_data()


required_columns = [
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
    col for col in required_columns
    if col not in df.columns
]


if missing:

    st.error(
        "Missing columns in Ladywood_Data.xlsx: "
        + ", ".join(missing)
    )

    st.stop()


df["Site"] = (
    df["Site Ref"].astype(str)
    + " - "
    + df["Location"].astype(str)
)


# =========================================================
# FUNCTIONS
# =========================================================

def priority_level(score):

    if score >= 8:
        return "Very High"

    elif score >= 6:
        return "High"

    elif score >= 4:
        return "Moderate"

    else:
        return "Low"


df["Priority Level"] = (
    df["Priority /10"]
    .apply(priority_level)
)


def marker_colour(score):

    if score >= 8:
        return "red"

    elif score >= 6:
        return "orange"

    elif score >= 4:
        return "gold"

    else:
        return "green"


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
            "Blue-green infrastructure combines stormwater storage with green space."
        )


    if row["Pollution /10"] >= 9:

        reasons.append(
            "The high pollution score supports a treatment-based solution."
        )


    return reasons


def get_bounds(geojson):

    coordinates = []


    def collect(values):

        if (
            isinstance(values, list)
            and len(values) >= 2
            and isinstance(values[0], (int, float))
            and isinstance(values[1], (int, float))
        ):

            longitude = values[0]
            latitude = values[1]

            coordinates.append(
                [latitude, longitude]
            )


        elif isinstance(values, list):

            for item in values:
                collect(item)


    for feature in geojson["features"]:

        collect(
            feature["geometry"]["coordinates"]
        )


    latitudes = [
        point[0]
        for point in coordinates
    ]

    longitudes = [
        point[1]
        for point in coordinates
    ]


    return [
        [
            min(latitudes),
            min(longitudes)
        ],
        [
            max(latitudes),
            max(longitudes)
        ]
    ]


# =========================================================
# PAGE
# =========================================================

st.title(
    "Ladywood Flooding and Pollution Decision-Support Dashboard"
)

st.caption(
    "Priority assessment of surface-water flooding, runoff, "
    "pollution risk and possible SuDS interventions."
)


overview, assessment, schedule, method = st.tabs(
    [
        "Overview",
        "Location Assessment",
        "Priority Schedule",
        "Engineering Method"
    ]
)


# =========================================================
# OVERVIEW
# =========================================================

with overview:

    st.subheader(
        "Project Summary"
    )


    high_priority = (
        df["Priority /10"] >= 6
    ).sum()


    c1, c2, c3, c4 = st.columns(4)


    c1.metric(
        "Locations Assessed",
        len(df)
    )


    c2.metric(
        "High Priority Locations",
        int(high_priority)
    )


    c3.metric(
        "Average Priority",
        f"{df['Priority /10'].mean():.1f}/10"
    )


    c4.metric(
        "Highest Priority",
        f"{df['Priority /10'].max():.1f}/10"
    )


    highest = df.loc[
        df["Priority /10"].idxmax()
    ]


    st.info(
        f"Highest current priority: "
        f"{highest['Location']} — "
        f"{highest['Priority /10']:.1f}/10."
    )


    st.divider()


    # =====================================================
    # LADYWOOD MAP
    # =====================================================

    st.subheader(
        "Ladywood Study Area"
    )


    try:

        ladywood = load_boundary()

        bounds = get_bounds(
            ladywood
        )


        centre_lat = (
            bounds[0][0]
            + bounds[1][0]
        ) / 2


        centre_lon = (
            bounds[0][1]
            + bounds[1][1]
        ) / 2


        ladywood_map = folium.Map(

            location=[
                centre_lat,
                centre_lon
            ],

            zoom_start=14,

            tiles=None,

            control_scale=True
        )


        # Street map
        folium.TileLayer(
            tiles="OpenStreetMap",
            name="Street Map",
            show=True
        ).add_to(
            ladywood_map
        )


        # Optional lighter background
        folium.TileLayer(
            tiles="CartoDB positron",
            name="Light Map",
            show=False
        ).add_to(
            ladywood_map
        )


        # -------------------------------------------------
        # LADYWOOD BOUNDARY
        # -------------------------------------------------

        boundary_group = folium.FeatureGroup(
            name="Ladywood Boundary",
            show=True
        )


        folium.GeoJson(

            ladywood,

            name="Ladywood Ward",

            style_function=lambda feature: {

                "fillColor": "#f4a742",

                "color": "#d35400",

                "weight": 6,

                "opacity": 1,

                "fillOpacity": 0.28
            },

            highlight_function=lambda feature: {

                "fillColor": "#ffcc66",

                "color": "#b03a00",

                "weight": 7,

                "fillOpacity": 0.38
            },

            tooltip=folium.GeoJsonTooltip(

                fields=[
                    "name"
                ],

                aliases=[
                    "Study area:"
                ],

                sticky=True
            )

        ).add_to(
            boundary_group
        )


        boundary_group.add_to(
            ladywood_map
        )


        # -------------------------------------------------
        # PERMANENT LADYWOOD LABEL
        # -------------------------------------------------

        folium.Marker(

            location=[
                centre_lat,
                centre_lon
            ],

            icon=folium.DivIcon(
                html="""
                <div style="
                    font-size:17px;
                    font-weight:700;
                    color:#7a3100;
                    background:white;
                    border:2px solid #d35400;
                    border-radius:5px;
                    padding:5px 9px;
                    white-space:nowrap;
                    box-shadow:0 1px 4px rgba(0,0,0,0.35);
                ">
                    LADYWOOD WARD
                </div>
                """
            )

        ).add_to(
            ladywood_map
        )


        # -------------------------------------------------
        # OPTIONAL SITE MARKERS
        # -------------------------------------------------

        latitude_col = None
        longitude_col = None


        for col in df.columns:

            if col.lower() in [
                "latitude",
                "lat"
            ]:

                latitude_col = col


            if col.lower() in [
                "longitude",
                "lon",
                "lng"
            ]:

                longitude_col = col


        markers_available = False


        if (
            latitude_col is not None
            and longitude_col is not None
        ):

            sites = df.copy()


            sites[latitude_col] = pd.to_numeric(
                sites[latitude_col],
                errors="coerce"
            )


            sites[longitude_col] = pd.to_numeric(
                sites[longitude_col],
                errors="coerce"
            )


            sites = sites.dropna(
                subset=[
                    latitude_col,
                    longitude_col
                ]
            )


            if len(sites) > 0:

                markers_available = True


                site_layer = folium.FeatureGroup(
                    name="Priority Locations",
                    show=True
                )


                for _, site in sites.iterrows():

                    colour = marker_colour(
                        site["Priority /10"]
                    )


                    popup_text = (

                        f"<b>{site['Location']}</b><br>"

                        f"Site Ref: {site['Site Ref']}<br>"

                        f"Priority: {site['Priority /10']:.1f}/10<br>"

                        f"Flood Risk: {site['Flood /10']:.0f}/10<br>"

                        f"Pollution Risk: {site['Pollution /10']:.0f}/10<br>"

                        f"Proposed: {site['Proposed SuDS']}"
                    )


                    folium.CircleMarker(

                        location=[
                            site[latitude_col],
                            site[longitude_col]
                        ],

                        radius=7,

                        color=colour,

                        weight=2,

                        fill=True,

                        fill_color=colour,

                        fill_opacity=0.9,

                        tooltip=(
                            f"{site['Site Ref']} - "
                            f"{site['Location']}"
                        ),

                        popup=folium.Popup(
                            popup_text,
                            max_width=300
                        )

                    ).add_to(
                        site_layer
                    )


                site_layer.add_to(
                    ladywood_map
                )


        # -------------------------------------------------
        # MAP LEGEND
        # -------------------------------------------------

        if markers_available:

            legend = """
            <div style="
                position: fixed;
                bottom: 40px;
                left: 40px;
                width: 195px;
                background-color: white;
                border: 2px solid #777;
                z-index: 9999;
                padding: 11px;
                font-size: 13px;
                border-radius: 5px;
                box-shadow: 0 1px 5px rgba(0,0,0,0.3);
            ">

            <b>Map Key</b><br><br>

            <span style="
                display:inline-block;
                width:22px;
                border-top:5px solid #d35400;
            "></span>
            Ladywood boundary<br><br>

            <b>Priority locations</b><br>

            <span style="color:red;">●</span>
            Very High<br>

            <span style="color:orange;">●</span>
            High<br>

            <span style="color:#d4aa00;">●</span>
            Moderate<br>

            <span style="color:green;">●</span>
            Low

            </div>
            """

        else:

            legend = """
            <div style="
                position: fixed;
                bottom: 40px;
                left: 40px;
                width: 190px;
                background-color: white;
                border: 2px solid #777;
                z-index: 9999;
                padding: 11px;
                font-size: 13px;
                border-radius: 5px;
                box-shadow: 0 1px 5px rgba(0,0,0,0.3);
            ">

            <b>Map Key</b><br><br>

            <span style="
                display:inline-block;
                width:24px;
                height:12px;
                background:#f4a742;
                border:3px solid #d35400;
            "></span>

            &nbsp;Ladywood Ward

            </div>
            """


        ladywood_map.get_root().html.add_child(
            folium.Element(
                legend
            )
        )


        # Full screen button
        Fullscreen(
            position="topright"
        ).add_to(
            ladywood_map
        )


        # Layer control
        folium.LayerControl(
            collapsed=False
        ).add_to(
            ladywood_map
        )


        # Fit the whole Ladywood boundary
        ladywood_map.fit_bounds(
            bounds,
            padding=[
                20,
                20
            ]
        )


        components.html(

            ladywood_map.get_root().render(),

            height=620,

            scrolling=False
        )


        st.caption(
            "Ladywood Ward is outlined and shaded on the street map."
        )


    except FileNotFoundError:

        st.error(
            "ladywood_ward.geojson was not found in the project folder."
        )


    except Exception as error:

        st.error(
            "The Ladywood map could not be displayed."
        )

        st.write(
            error
        )


    st.divider()


    # =====================================================
    # HIGHEST PRIORITY LOCATIONS
    # =====================================================

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

        color="Priority Level",

        color_discrete_map={
            "Very High": "#d62728",
            "High": "#ff7f0e",
            "Moderate": "#e0b000",
            "Low": "#2ca02c"
        },

        category_orders={
            "Priority Level": [
                "Very High",
                "High",
                "Moderate",
                "Low"
            ]
        },

        hover_data={
            "Priority /10": ":.2f",
            "Flood /10": True,
            "Drainage /10": True,
            "Pollution /10": True,
            "Proposed SuDS": True,
            "Priority Level": False
        }
    )


    priority_fig.update_layout(

        xaxis_title="Priority score /10",

        yaxis_title="",

        height=480,

        legend_title="Priority Level"
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
        "Locations are ordered by combined priority. "
        "Hover over a bar to view the detailed scores."
    )


    st.divider()


    # =====================================================
    # FLOOD AND POLLUTION
    # =====================================================

    st.subheader(
        "Flood Risk and Pollution Risk"
    )


    risk_fig = px.scatter(

        df,

        x="Flood /10",

        y="Pollution /10",

        size="Population",

        color="Priority Level",

        hover_name="Site",

        hover_data=[
            "Priority /10",
            "Proposed SuDS"
        ],

        color_discrete_map={
            "Very High": "#d62728",
            "High": "#ff7f0e",
            "Moderate": "#e0b000",
            "Low": "#2ca02c"
        },

        category_orders={
            "Priority Level": [
                "Very High",
                "High",
                "Moderate",
                "Low"
            ]
        }
    )


    risk_fig.update_layout(

        xaxis_title="Flood risk /10",

        yaxis_title="Pollution risk /10",

        height=440,

        legend_title="Priority Level"
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
        "Upper-right locations combine high flood risk "
        "with high pollution risk. Bubble size represents population."
    )


# =========================================================
# LOCATION ASSESSMENT
# =========================================================

with assessment:

    st.subheader(
        "Location Assessment"
    )


    selected = st.selectbox(
        "Select a site",
        df["Site"].tolist()
    )


    row = df[
        df["Site"] == selected
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
        "Flood Risk",
        f"{row['Flood /10']:.0f}/10"
    )


    c2.metric(
        "Drainage Risk",
        f"{row['Drainage /10']:.0f}/10"
    )


    c3.metric(
        "Population Exposure",
        f"{row['Pop /10']:.0f}/10"
    )


    c4.metric(
        "Land Cover",
        f"{row['Land Cover /10']:.0f}/10"
    )


    c5.metric(
        "Pollution Risk",
        f"{row['Pollution /10']:.0f}/10"
    )


    left, right = st.columns(
        [
            1.5,
            1
        ]
    )


    with left:

        site_scores = pd.DataFrame(
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


        site_fig = px.bar(

            site_scores,

            x="Factor",

            y="Score",

            color="Score",

            color_continuous_scale="YlOrRd"
        )


        site_fig.update_layout(

            xaxis_title="",

            yaxis_title="Score /10",

            height=390,

            coloraxis_showscale=False
        )


        site_fig.update_yaxes(
            range=[
                0,
                10
            ]
        )


        st.plotly_chart(
            site_fig,
            use_container_width=True
        )


    with right:

        level = priority_level(
            row["Priority /10"]
        )


        st.metric(
            "Overall Priority",
            f"{row['Priority /10']:.1f}/10"
        )


        st.write(
            f"**Priority Level:** {level}"
        )


        st.metric(
            "Estimated Peak Runoff",
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
            "The priority results from the combined effect "
            "of the assessed factors."
        )


    st.divider()


    st.subheader(
        "Proposed Intervention"
    )


    st.success(
        str(
            row["Proposed SuDS"]
        )
    )


    for reason in intervention_reasons(
        row
    ):

        st.write(
            "• " + reason
        )


    st.caption(
        "Preferred first-stage intervention for the assessed site conditions."
    )


# =========================================================
# PRIORITY SCHEDULE
# =========================================================

with schedule:

    st.subheader(
        "Priority Schedule"
    )


    schedule_df = (

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

        schedule_df,

        use_container_width=True,

        hide_index=True
    )


    st.divider()


    st.subheader(
        "Proposed Interventions"
    )


    interventions = (

        df["Proposed SuDS"]

        .value_counts()

        .reset_index()
    )


    interventions.columns = [
        "Intervention",
        "Locations"
    ]


    interventions = (
        interventions
        .sort_values(
            "Locations",
            ascending=True
        )
    )


    intervention_fig = px.bar(

        interventions,

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


# =========================================================
# ENGINEERING METHOD
# =========================================================

with method:

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


    priority_table = pd.DataFrame(
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
        priority_table
    )


    st.divider()


    st.subheader(
        "Engineering Basis"
    )


    st.write(
        "• A consistent rainfall intensity is applied across the study area "
        "so locations are compared under the same rainfall condition."
    )


    st.write(
        "• Runoff coefficients reflect differences in urbanisation "
        "and impermeable land cover."
    )


    st.write(
        "• The Rational Method is applied consistently using runoff "
        "coefficient, rainfall intensity and contributing area."
    )


    st.write(
        "• Pollution risk is expressed on a common 0–10 scale "
        "to compare relative urban-runoff concern."
    )


    st.write(
        "• SuDS recommendations consider flood risk, drainage, runoff "
        "potential, land cover and pollution risk."
    )


    st.write(
        "• Priority is determined from several indicators rather "
        "than flood risk alone."
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
        "• Birmingham flood-risk information provides an additional "
        "check on the ranking."
    )


    st.write(
        "• Peak runoff is independently checked using the Rational Method."
    )


    st.write(
        "• Priority weighting can be varied to confirm that the "
        "highest-ranked locations remain reasonably stable."
    )
