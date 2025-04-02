import streamlit as st
import pandas as pd
import plotly.express as px
import os

# Load Excel Data
def load_data():
    excel_file = "ODVT.xlsx"
    xls = pd.ExcelFile(excel_file)
    df_collective = xls.parse("Collective Data").dropna()
    df_cost_model = xls.parse("Cost Model").dropna()
    return df_collective, df_cost_model

df_collective, df_cost_model = load_data()

# Streamlit UI
st.set_page_config(page_title="FT Data Intelligence", layout="wide")

# Handle missing logo file
if os.path.exists("Logo.png"):
    st.image("Logo.png", width=150)
else:
    st.warning("Logo.png not found! Please upload it to the repository.")

st.title("FT Data Intelligence")

# Sidebar Filters
st.sidebar.header("Filters")
date_range = st.sidebar.selectbox("Date Range", ["One Year", "6 Months", "3 Months", "One Month", "Month to Date"])
origin_city = st.sidebar.multiselect("Origin City", df_collective["Origin State"].unique())
destination_city = st.sidebar.multiselect("Destination City", df_collective["Destination State"].unique())
transporter_name = st.sidebar.multiselect("Transporter Name", df_collective["Transporter"].unique())
transporter_rating = st.sidebar.slider("Transporter Rating", 1, 5, (2, 5))

# Tabs
tabs = st.tabs(["ODVT Trends", "Cost Model", "Transporter Discovery"])

with tabs[0]:  # ODVT Trends
    st.subheader("ODVT Trends")
    shipper_rate = df_collective.groupby("Rate type")["Shipper"].sum().reset_index()
    fig1 = px.pie(shipper_rate, values="Shipper", names="Rate type", title="Shipper Rate Distribution")
    st.plotly_chart(fig1)

    vehicle_count = df_collective.groupby("Category").size().reset_index(name="Count")
    fig2 = px.pie(vehicle_count, values="Count", names="Category", title="Vehicle Category Distribution")
    st.plotly_chart(fig2)

    table_data = df_collective.groupby(["Origin Locality", "Destination Locality"]).agg(
        {"Shipper": "mean", "ETA": "mean", "Toll Cost": "mean", "Lead Distance": "mean"}).reset_index()
    st.dataframe(table_data)

with tabs[1]:  # Cost Model
    st.subheader("Cost Model Upload")
    uploaded_file = st.file_uploader("Upload your cost model file", type=["xlsx"])
    if uploaded_file is not None:
        user_df = pd.read_excel(uploaded_file)
        merged_df = user_df.merge(df_cost_model, left_on=["Origin city", "Destination City", "Vehicle Type"], 
                                  right_on=["Origin", "Destination", "Truck Type"], how="left")
        st.dataframe(merged_df)

with tabs[2]:  # Transporter Discovery
    st.subheader("Transporter Discovery")
    filtered_df = df_collective[(df_collective["Rating"] >= transporter_rating[0]) & 
                                (df_collective["Rating"] <= transporter_rating[1])]
    table_transporter = filtered_df.groupby("Transporter").agg({"Rating": "mean", "Transporter": "count", "ETA": "mean", "Shipper": "mean"}).reset_index()
    table_transporter.columns = ["Transporter Name", "Transporter Rating", "Total Vehicles", "Average ETA", "Average Shipper Rate"]
    st.dataframe(table_transporter)

    selected_origins = st.multiselect("Select Origin State", df_collective["Origin State"].unique())
    selected_destinations = st.multiselect("Select Destination State", df_collective["Destination State"].unique())
    bubble_data = df_collective[df_collective["Origin State"].isin(selected_origins) & df_collective["Destination State"].isin(selected_destinations)]
    bubble_chart = bubble_data.groupby(["Origin State", "Destination State", "Transporter"]).size().reset_index(name="Trip Count")
    fig3 = px.scatter(bubble_chart, x="Origin State", y="Destination State", size="Trip Count", hover_name="Transporter", title="Transporter Activity")
    st.plotly_chart(fig3)
