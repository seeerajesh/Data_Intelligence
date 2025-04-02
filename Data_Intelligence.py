import streamlit as st
import pandas as pd
import plotly.express as px
import os

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
        df_cost_model = df_cost_model.rename(columns={
            "Origin": "Origin", "Destination": "Destination", "Lead Distance (KM)": "Lead Distance (KM)", 
            "TAT @300 KM/Day": "TAT @300 KM/Day", "Fixed Cost/Day": "Fixed Cost/Day", 
            "Variable Cost/KM": "Variable Cost/KM", "Total (Fixed+Variable) Cost/Trip": "Total Cost/Trip", 
            "Transporter Margin - 5%": "Transporter Margin - 5%", "Total Freight Cost/Trip": "Total Freight Cost/Trip", 
            "Truck Type": "Truck Type"
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
    if "Rate Type" in df_collective.columns and "Shipper" in df_collective.columns:
        shipper_rate = df_collective.groupby("Rate Type")["Shipper"].sum()
        fig1 = px.pie(shipper_rate, values="Shipper", names=shipper_rate.index, title="Shipper Rate Distribution")
        st.plotly_chart(fig1)

    if "Category" in df_collective.columns:
        vehicle_count = df_collective.groupby("Category").size()
        fig2 = px.pie(vehicle_count, values=vehicle_count.values, names=vehicle_count.index, title="Vehicle Category Distribution")
        st.plotly_chart(fig2)

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
    if "Rating" in df_collective.columns and "Transporter" in df_collective.columns:
        df_collective["Rating"] = pd.to_numeric(df_collective["Rating"], errors='coerce')
        filtered_df = df_collective[(df_collective["Rating"] >= transporter_rating[0]) &
                                    (df_collective["Rating"] <= transporter_rating[1])]
        if not filtered_df.empty:
            table_transporter = filtered_df.groupby("Transporter").agg(
                Mean_Rating=("Rating", "mean"),
                Total_Trips=("Transporter", "count"),
                Unique_Origin_Destination_Count=("Origin Locality", "nunique")
            )
            table_transporter.index.name = None  # Remove index name
            table_transporter.columns = ["Transporter Name", "Mean Rating", "Total Trips", "Unique Origin-Destination Count"]
            st.dataframe(table_transporter)
        else:
            st.warning("No matching transporters found for selected filters.")
    else:
        st.warning("Transporter data missing from dataset.")
