import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import folium
from streamlit_folium import folium_static

# Set Streamlit Page Config (Must be first command)
st.set_page_config(page_title="FT Data Intelligence", layout="wide")

# Load Excel Data
def load_data():
    excel_file = "ODVT.xlsx"
    if not os.path.exists(excel_file):
        st.error("Excel file not found. Please upload the correct file.")
        return pd.DataFrame(), pd.DataFrame()
    
    try:
        xls = pd.ExcelFile(excel_file, engine='openpyxl')
        df_collective = xls.parse("Collective Data").dropna()
        df_cost_model = xls.parse("Cost Model").dropna()
        df_collective.columns = df_collective.columns.str.strip()  # Strip column names to avoid issues
        
        expected_columns = {"Origin Pin Code", "Destination Pin Code"}
        missing_columns = expected_columns - set(df_collective.columns)
        if missing_columns:
            st.error(f"Missing columns in dataset: {missing_columns}")
            return pd.DataFrame(), pd.DataFrame()
        
        df_collective["Origin Pin Code"] = df_collective["Origin Pin Code"].astype(str)
        df_collective["Destination Pin Code"] = df_collective["Destination Pin Code"].astype(str)
        return df_collective, df_cost_model
    except Exception as e:
        st.error(f"Error loading Excel file: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_collective, df_cost_model = load_data()

# Convert necessary columns to numeric
numeric_cols = ["ETA", "Toll Cost", "Lead Distance"]
for col in numeric_cols:
    if col in df_collective.columns:
        df_collective[col] = pd.to_numeric(df_collective[col], errors='coerce')

try:
    st.image("Logo.png", width=150)
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

    st.subheader("Top 10 Origin & Destination Pincodes by Trip Count")
    
    if "Origin Pin Code" in df_collective.columns and "Destination Pin Code" in df_collective.columns:
        origin_counts = df_collective["Origin Pin Code"].value_counts().reset_index()
        origin_counts.columns = ["Origin Pin Code", "Trip Count"]
        origin_counts = origin_counts.head(10)
        
        destination_counts = df_collective["Destination Pin Code"].value_counts().reset_index()
        destination_counts.columns = ["Destination Pin Code", "Trip Count"]
        destination_counts = destination_counts.head(10)
        
        st.dataframe(origin_counts)
        st.dataframe(destination_counts)
        
        # OpenStreetMap Visualization using Pincodes
        map_center = [20.5937, 78.9629]  # Approximate center of India
        m = folium.Map(location=map_center, zoom_start=5)

        for _, row in origin_counts.iterrows():
            folium.Marker(
                location=[map_center[0] + (hash(row["Origin Pin Code"]) % 100) * 0.01, 
                          map_center[1] + (hash(row["Origin Pin Code"]) % 100) * 0.01],
                popup=f"Origin: {row['Origin Pin Code']} - Trips: {row['Trip Count']}",
                icon=folium.Icon(color='green')
            ).add_to(m)
        
        for _, row in destination_counts.iterrows():
            folium.Marker(
                location=[map_center[0] + (hash(row["Destination Pin Code"]) % 100) * 0.01, 
                          map_center[1] + (hash(row["Destination Pin Code"]) % 100) * 0.01],
                popup=f"Destination: {row['Destination Pin Code']} - Trips: {row['Trip Count']}",
                icon=folium.Icon(color='red')
            ).add_to(m)
        
        folium_static(m)
    else:
        st.warning("Pincode columns not found in dataset. Please check the uploaded file.")

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

with tabs[2]:  # Transporter Discovery
    st.subheader("Transporter Discovery")
    filtered_df = df_collective[(df_collective["Rating"] >= transporter_rating[0]) & (df_collective["Rating"] <= transporter_rating[1])]
    st.dataframe(filtered_df[["Transporter", "Rating", "Origin Pin Code", "Destination Pin Code", "Shipper"]].sort_values(by="Rating", ascending=False))
