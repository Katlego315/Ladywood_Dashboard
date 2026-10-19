import json
from pathlib import Path

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from folium.plugins import Fullscreen

# The assessed results stay in Excel, as described in Progress Report 3.
FOLDER = Path(__file__).resolve().parent
st.set_page_config(page_title="Ladywood Dashboard", layout="wide")

@st.cache_data
def load_data():
    data = pd.read_excel(FOLDER / "Ladywood_Data.xlsx")
    data.columns = data.columns.astype(str).str.strip()
    for column in data.columns:
        if column.lower().startswith("runoff q"):
            data = data.rename(columns={column: "Runoff Q"})
        elif column.lower() in ("c", "runoff c"):
            data = data.rename(columns={column: "Runoff C"})
    numbers = ["Flood /10", "Drainage /10", "Population", "Pop /10",
               "Land Cover /10", "Runoff C", "Runoff Q", "Pollution /10",
               "Priority /10", "Area ha"]
    for column in numbers:
        if column in data:
            data[column] = pd.to_numeric(data[column].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    return data


def level(score):
    if score >= 8:
        return "Very High"
    if score >= 6:
        return "High"
    if score >= 4:
        return "Moderate"
    return "Low"


def show_chart(data, x, y, title, horizontal=False, colour=None):
    st.subheader(title)
    fig = px.bar(data, x=x, y=y, orientation="h" if horizontal else "v",
                 color=colour)
    st.plotly_chart(fig, use_container_width=True)


def make_map():
    with open(FOLDER / "ladywood_ward.geojson", encoding="utf-8") as file:
        boundary = json.load(file)
    if boundary["type"] == "Feature":
        boundary = {"type": "FeatureCollection", "features": [boundary]}
    m = folium.Map(location=[52.48, -1.91], zoom_start=13,
                   tiles="OpenStreetMap", control_scale=True)
    outline = folium.GeoJson(boundary, name="Ladywood Ward",
        style_function=lambda _: {"color": "#d35400", "weight": 5,
                                  "fillColor": "#f4a742", "fillOpacity": 0.28})
    outline.add_to(m)
    m.fit_bounds(outline.get_bounds())
    # Show the ward name permanently without changing the mapping data.
    centre = outline.get_bounds()
    lat = (centre[0][0] + centre[1][0]) / 2
    lon = (centre[0][1] + centre[1][1]) / 2
    folium.Marker([lat, lon], tooltip="Ladywood Ward",
                  icon=folium.DivIcon(html='<b style="background:white;padding:4px">LADYWOOD WARD</b>')).add_to(m)
    Fullscreen().add_to(m)
    folium.LayerControl().add_to(m)
    return m


def reasons(site):
    messages = []
    factors = [("Flood /10", 8, "High flood risk is a major contributor."),
               ("Drainage /10", 8, "Drainage increases the site's vulnerability."),
               ("Pop /10", 8, "Population exposure is high."),
               ("Land Cover /10", 9, "Hard surfaces increase runoff potential."),
               ("Pollution /10", 9, "Pollution risk is very high.")]
    for name, limit, message in factors:
        if site[name] >= limit:
            messages.append(message)
    if not messages:
        messages.append("Priority reflects the combination of all five factors.")
    return messages


def suds_explanation(site):
    proposed = str(site["Proposed SuDS"]).lower()
    explanations = [("detention", "Temporary storage reduces peak runoff."),
                    ("attenuation", "Temporary storage reduces peak runoff."),
                    ("permeable", "Permeable paving can reduce paved-surface runoff."),
                    ("rain garden", "Rain gardens support runoff and pollution control."),
                    ("bioretention", "Bioretention supports runoff and pollution control."),
                    ("drainage upgrade", "Drainage upgrades address drainage conditions."),
                    ("blue-green", "Blue-green measures combine water and green space.")]
    output = []
    for term, message in explanations:
        if term in proposed and message not in output:
            output.append(message)
    if site["Pollution /10"] >= 9:
        output.append("High pollution concern supports considering treatment.")
    return output


# Stop early if the spreadsheet is missing required information.
try:
    df = load_data()
except (FileNotFoundError, ValueError) as error:
    st.error(f"Cannot read Ladywood_Data.xlsx: {error}")
    st.stop()

required = ["Site Ref", "Area", "Location", "Catchment", "Flood Zone",
            "Flood /10", "Drainage /10", "Population", "Pop /10",
            "Land Cover /10", "Runoff C", "Runoff Q", "Pollution /10",
            "Priority /10", "Proposed SuDS"]
missing = [name for name in required if name not in df.columns]
if missing:
    st.error("Missing Excel columns: " + ", ".join(missing))
    st.stop()

df["Site"] = df["Site Ref"].astype(str) + " - " + df["Location"].astype(str)
df["Priority Level"] = df["Priority /10"].apply(level)

st.title("Ladywood Flooding and Pollution Decision-Support Dashboard")
st.caption("Preliminary assessment of surface-water flooding, polluted runoff and SuDS options.")
overview, assessment, schedule, method = st.tabs([
    "Overview", "Location Assessment", "Priority Schedule", "Engineering Method"])

# TAB 1: OVERVIEW
with overview:
    st.subheader("Project Summary")
    a, b, c, d = st.columns(4)
    a.metric("Locations Assessed", len(df))
    b.metric("High Priority Locations", int((df["Priority /10"] >= 6).sum()))
    c.metric("Average Priority", f"{df['Priority /10'].mean():.1f}/10")
    d.metric("Highest Priority", f"{df['Priority /10'].max():.1f}/10")
    highest = df.loc[df["Priority /10"].idxmax()]
    st.info(f"Highest current priority: {highest['Location']} — {highest['Priority /10']:.1f}/10")
    st.subheader("Ladywood Study Area")
    try:
        components.html(make_map().get_root().render(), height=620, scrolling=False)
    except (FileNotFoundError, ValueError, KeyError) as error:
        st.error(f"Cannot show Ladywood map: {error}")
    top = df.nlargest(10, "Priority /10").sort_values("Priority /10")
    show_chart(top, "Priority /10", "Site", "Highest Priority Locations",
               horizontal=True, colour="Priority Level")
    st.subheader("Flood Risk and Pollution Risk")
    fig = px.scatter(df, x="Flood /10", y="Pollution /10", size="Population",
                     color="Priority Level", hover_name="Site",
                     hover_data=["Priority /10", "Proposed SuDS"],
                     range_x=[0, 10], range_y=[0, 10])
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Bubble size represents population; upper-right sites have higher combined concerns.")

# TAB 2: LOCATION ASSESSMENT
with assessment:
    st.subheader("Location Assessment")
    selected = st.selectbox("Choose a site", df["Site"].tolist())
    site = df.loc[df["Site"] == selected].iloc[0]
    st.write(f"**Site Ref:** {site['Site Ref']} | **Area:** {site['Area']} | **Catchment:** {site['Catchment']} | "
             f"**Flood Zone:** {site['Flood Zone']}")
    indicators = {"Flood Risk": "Flood /10", "Drainage Risk": "Drainage /10",
                  "Population Exposure": "Pop /10", "Land Cover": "Land Cover /10",
                  "Pollution Risk": "Pollution /10"}
    for column, (label, name) in zip(st.columns(5), indicators.items()):
        column.metric(label, f"{site[name]:.0f}/10")
    left, right = st.columns([3, 2])
    with left:
        scores = pd.DataFrame({"Factor": list(indicators),
                               "Score": [site[name] for name in indicators.values()]})
        show_chart(scores, "Factor", "Score", "Site Risk Factors")
    with right:
        st.metric("Overall Priority", f"{site['Priority /10']:.1f}/10")
        st.write("**Priority Level:**", site["Priority Level"])
        st.metric("Estimated Peak Runoff", f"{site['Runoff Q']:.4f} m³/s")
        st.metric("Runoff Coefficient", f"{site['Runoff C']:.2f}")
        st.metric("Population", f"{site['Population']:,.0f}")
    st.subheader("Reason for Priority")
    for message in reasons(site):
        st.write("•", message)
    st.subheader("Proposed Intervention")
    st.success(str(site["Proposed SuDS"]))
    for message in suds_explanation(site):
        st.write("•", message)
    st.caption("The proposed SuDS intervention is based on the site's assessed "
               "flood risk, drainage conditions, land cover and pollution risk.")

# TAB 3: PRIORITY SCHEDULE
with schedule:
    st.subheader("Priority Schedule")
    columns = ["Site Ref", "Location", "Area", "Flood Zone", "Flood /10",
               "Pollution /10", "Priority /10", "Runoff Q", "Proposed SuDS"]
    st.dataframe(df[columns].sort_values("Priority /10", ascending=False),
                 hide_index=True, use_container_width=True)
    counts = df["Proposed SuDS"].value_counts().reset_index()
    counts.columns = ["Intervention", "Locations"]
    show_chart(counts.sort_values("Locations"), "Locations", "Intervention",
               "Proposed Interventions", horizontal=True)

# TAB 4: ENGINEERING METHOD
with method:
    st.subheader("Runoff Calculation")
    st.latex(r"Q=\frac{CiA}{360}")
    st.write("Q = peak runoff (m³/s); C = runoff coefficient; "
             "i = rainfall intensity (mm/h); A = area (ha).")
    st.write("The Excel assessment uses a common rainfall intensity of 30 mm/h.")
    st.subheader("Priority Score")
    st.latex(r"P=0.30F+0.20D+0.15E+0.15L+0.20R")
    st.write("F = flood; D = drainage; E = population exposure; "
             "L = land cover; R = pollution. Ratings use fixed ranges on a 0–10 scale.")
    st.subheader("Priority Levels")
    st.table(pd.DataFrame({"Score": ["8–10", "6 to below 8", "4 to below 6", "Below 4"],
                           "Priority": ["Very High", "High", "Moderate", "Low"]}))
    st.subheader("Engineering Basis")
    st.write("The assessment uses mapped environmental information and fixed-range ratings. "
             "Runoff coefficients represent interpreted land-cover conditions. "
             "The five weighted factors identify preliminary priorities; "
             "SuDS suggestions are options for further investigation.")
    st.subheader("Verification and Further Checks")
    st.write("**Completed:** Site CC107 priority = 8.8/10 and runoff = 0.0767 m³/s, "
             "both matching the workbook. The dataset contains 45 locations, "
             "28 High/Very High priorities and four implemented dashboard tabs.")
    st.write("**Next steps:** Record usability trials, check more calculations, "
             "compare selected sites with current official flood-risk mapping, "
             "and review classification thresholds and weighting sensitivity.")
