import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import folium
from streamlit_folium import folium_static

# Load Excel Data
def load_data():
    excel_file = "ODVT.xlsx"
    if not os.path.exists(excel_file):
        st.error("Excel file not found. Please upload the correct file.")
        return pd.DataFrame(), pd.DataFrame()
    
    try:
        xls = pd.ExcelFile(excel_file)
        df_collective = xls.parse("Collective Data").dropna()
        df_cost_model = xls.parse("Cost Model").dropna()
        df_collective = df_collective.rename(columns={
            "Origin Pin code": "Origin Pin Code", "Origin Locality": "Origin Locality", 
            "Origin cluster name": "Origin Cluster Name", "Origin State": "Origin State", 
            "Destination Pin code": "Destination Pin Code", "Destination cluster name": "Destination Cluster Name", 
            "Destination Locality": "Destination Locality", "Destination State": "Destination State", 
            "Truck type": "Truck Type", "Vehicle Type (New)": "Vehicle Type", "Vehicle Class": "Vehicle Class", 
            "Toll Vehicle Category": "Toll Vehicle Category", "created_at": "Created At", 
            "Shipper": "Shipper", "Fleet owner Rate": "Fleet Owner Rate", "LSP Rate": "LSP Rate", 
            "Lead Distance": "Lead Distance", "ETA": "ETA", "Toll Cost": "Toll Cost", 
            "Transporter": "Transporter", "Category": "Category", "Rating": "Rating", "Rate type": "Rate Type"
        })
        return df_collective, df_cost_model
    except Exception as e:
        st.error(f"Error loading Excel file: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_collective, df_cost_model = load_data()

# Convert necessary columns to numeric
df_collective[["Shipper", "ETA", "Toll Cost", "Lead Distance"]] = df_collective[["Shipper", "ETA", "Toll Cost", "Lead Distance"]].apply(pd.to_numeric, errors='coerce')

# Streamlit UI
st.set_page_config(page_title="FT Data Intelligence", layout="wide")
try:
    st.image("Logo.PNG", width=150)
except Exception:
    st.warning("Logo image not found. Please check the file path.")

st.title("FT Data Intelligence")

# Sidebar Filters
st.sidebar.header("Filters")
date_range = st.sidebar.selectbox("Date Range", ["One Year", "6 Months", "3 Months", "One Month", "Month to Date"])
origin_city = st.sidebar.multiselect("Origin City", df_collective.get("Origin State", pd.Series(dtype=str)).unique())
destination_city = st.sidebar.multiselect("Destination City", df_collective.get("Destination State", pd.Series(dtype=str)).unique())
transporter_name = st.sidebar.multiselect("Transporter Name", df_collective.get("Transporter", pd.Series(dtype=str)).unique())
transporter_rating = st.sidebar.slider("Transporter Rating", 1, 5, (2, 5))

# Tabs
tabs = st.tabs(["ODVT Trends", "Cost Model", "Transporter Discovery"])

with tabs[0]:  # ODVT Trends
    st.subheader("ODVT Trends")
    col1, col2 = st.columns(2)
    
    if "Rate Type" in df_collective.columns and "Shipper" in df_collective.columns:
        shipper_rate = df_collective.groupby("Rate Type")["Shipper"].sum().reset_index()
        fig1 = px.pie(shipper_rate, values="Shipper", names="Rate Type", title="Shipper Rate Distribution", hover_data=["Shipper"], hole=0.3)
        col1.plotly_chart(fig1)
    
    if "Category" in df_collective.columns:
        vehicle_count = df_collective.groupby("Category").size().reset_index(name="Count")
        fig2 = px.pie(vehicle_count, values="Count", names="Category", title="Vehicle Category Distribution", hover_data=["Count"], hole=0.3)
        col2.plotly_chart(fig2)

    avg_table = df_collective.groupby(["Origin Locality", "Destination Locality"], as_index=False).agg(
        Avg_Shipper_Rate=("Shipper", "mean"),
        Avg_ETA=("ETA", "mean"),
        Avg_Toll_Cost=("Toll Cost", "mean"),
        Avg_Lead_Distance=("Lead Distance", "mean")
    ).round(1)
    st.dataframe(avg_table)
    
    top_states = ["Maharastra", "Gujarat", "Tamil Nadu", "Karnataka", "Uttar Pradesh"]
    bubble_data = df_collective[df_collective["Origin State"].isin(top_states) & df_collective["Destination State"].isin(top_states)]
    bubble_chart = bubble_data.groupby(["Origin State", "Destination State"]).size().reset_index(name="Count")
    fig3 = px.scatter(bubble_chart, x="Origin State", y="Destination State", size="Count", hover_name="Count", title="Trips between Top States")
    st.plotly_chart(fig3)
    
    # OpenStreetMap
    st.subheader("Top 10 Origin & Destination Localities")
    top_origins = df_collective["Origin Locality"].value_counts().head(10).index
    top_destinations = df_collective["Destination Locality"].value_counts().head(10).index
    m = folium.Map(location=[20.5937, 78.9629], zoom_start=5)
    for loc in top_origins:
        folium.CircleMarker([df_collective[df_collective["Origin Locality"] == loc]["Origin Pin Code"].mean(), df_collective[df_collective["Origin Locality"] == loc]["Lead Distance"].mean()], 
                            radius=10, color='blue', fill=True, fill_color='blue').add_to(m)
    for loc in top_destinations:
        folium.CircleMarker([df_collective[df_collective["Destination Locality"] == loc]["Destination Pin Code"].mean(), df_collective[df_collective["Destination Locality"] == loc]["Lead Distance"].mean()], 
                            radius=10, color='orange', fill=True, fill_color='orange').add_to(m)
    folium_static(m)
    
    # Trend Chart
    st.subheader("Month-on-Month Trip Trend")
    df_collective["Created At"] = pd.to_datetime(df_collective["Created At"], errors='coerce')
    trip_trend = df_collective.groupby(df_collective["Created At"].dt.to_period("M")).size().reset_index(name="Trip Count")
    fig4 = px.line(trip_trend, x="Created At", y="Trip Count", title="Trips Month on Month", markers=True)
    st.plotly_chart(fig4)

with tabs[1]:  # Cost Model
    st.subheader("Cost Model Upload")
    uploaded_file = st.file_uploader("Upload your cost model file", type=["xlsx"])
    if uploaded_file is not None:
        user_df = pd.read_excel(uploaded_file)
        required_cols = {"Origin", "Destination", "Truck Type"}
        if required_cols.issubset(user_df.columns) and required_cols.issubset(df_cost_model.columns):
            merged_df = user_df.merge(df_cost_model, on=["Origin", "Destination", "Truck Type"], how="left")
            st.dataframe(merged_df)
        else:
            st.warning("Missing required columns in uploaded file or cost model data.")
