import streamlit as st
import pandas as pd
import plotly.express as px
import os

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
        df_cost_model.columns = df_cost_model.columns.str.strip()
        
        expected_columns = {"Rating", "Transporter", "Shipper"}
        missing_columns = expected_columns - set(df_collective.columns)
        if missing_columns:
            st.error(f"Missing columns in dataset: {missing_columns}")
            return pd.DataFrame(), pd.DataFrame()
        
        return df_collective, df_cost_model
    except Exception as e:
        st.error(f"Error loading Excel file: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_collective, df_cost_model = load_data()

# Convert necessary columns to numeric
numeric_cols = ["ETA", "Toll Cost", "Lead Distance", "Rating", "Shipper"]
for col in numeric_cols:
    if col in df_collective.columns:
        df_collective[col] = pd.to_numeric(df_collective[col], errors='coerce')

try:
    st.image("Logo.PNG", width=150)
except Exception:
    st.warning("Logo image not found. Please check the file path.")

st.title("FT Data Intelligence")

# Sidebar Filters
st.sidebar.header("Filters")
date_range = st.sidebar.selectbox("Date Range", ["One Year", "6 Months", "3 Months", "One Month", "Month to Date"])
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
    
    if "Origin cluster name" in df_collective.columns and "Destination cluster name" in df_collective.columns:
        avg_table = df_collective.groupby(["Origin cluster name", "Destination cluster name"], as_index=False).agg(
            Avg_Shipper_Rate=("Shipper", "mean"),
            Avg_ETA=("ETA", "mean"),
            Avg_Toll_Cost=("Toll Cost", "mean"),
            Avg_Lead_Distance=("Lead Distance", "mean")
        )
        st.dataframe(avg_table)

with tabs[1]:  # Cost Model
    st.subheader("Cost Model")
    uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx", "xls"])
    
    if uploaded_file is not None:
        try:
            df_user_data = pd.read_excel(uploaded_file, engine='openpyxl')
            df_user_data.columns = df_user_data.columns.str.strip()
            
            required_columns = {"Origin", "Destination", "Truck Type"}
            if not required_columns.issubset(df_user_data.columns):
                st.error(f"Uploaded file must contain columns: {required_columns}")
            else:
                merged_df = pd.merge(df_user_data, df_cost_model, on=["Origin", "Destination", "Truck Type"], how="left")
                st.dataframe(merged_df)
        except Exception as e:
            st.error(f"Error processing uploaded file: {e}")

with tabs[2]:  # Transporter Discovery
    st.subheader("Transporter Discovery")
    if "Transporter" in df_collective.columns and "Rating" in df_collective.columns and "Shipper" in df_collective.columns:
        transporter_summary = df_collective.groupby("Transporter").agg(
            Mean_Rating=("Rating", "mean"),
            Total_Shipper_Rate=("Shipper", "sum"),
            Trip_Count=("Transporter", "count")
        ).reset_index()
        st.dataframe(transporter_summary.sort_values(by="Mean_Rating", ascending=False))
    else:
        st.warning("Required columns for Transporter Discovery not found in dataset.")
