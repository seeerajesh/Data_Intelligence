import streamlit as st
import pandas as pd
import plotly.express as px

# Load Excel Data
def load_data():
    excel_file = "ODVT.xlsx"
    try:
        xls = pd.ExcelFile(excel_file)
        df_collective = xls.parse("Collective Data").dropna()
        df_cost_model = xls.parse("Cost Model").dropna()
        df_collective.columns = ["Origin Pin code", "Origin Locality", "Origin cluster name", "Origin State", "Destination Pin code", "Destination cluster name", "Destination Locality", "Destination State", "Truck type", "Vehicle Type (New)", "Vehicle Class", "Toll Vehicle Category", "created_at", "Shipper", "Fleet owner Rate", "LSP Rate", "Lead Distance", "ETA", "Toll Cost", "Transporter", "Category", "Rating", "Rate type"]
        df_cost_model.columns = ["Origin", "Destination", "Lead Distance (KM)", "TAT @300 KM/Day", "Fixed Cost/Day", "Variable Cost/KM", "Total (Fixed+Variable) Cost/Trip", "Transporter Margin - 5%", "Total Freight Cost/Trip", "Truck Type"]
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
except Exception as e:
    st.warning("Logo image not found. Please check the file path.")

st.title("FT Data Intelligence")

# Sidebar Filters
st.sidebar.header("Filters")
date_range = st.sidebar.selectbox("Date Range", ["One Year", "6 Months", "3 Months", "One Month", "Month to Date"])
origin_city = st.sidebar.multiselect("Origin City", df_collective.get("Origin State", pd.Series()).unique())
destination_city = st.sidebar.multiselect("Destination City", df_collective.get("Destination State", pd.Series()).unique())
transporter_name = st.sidebar.multiselect("Transporter Name", df_collective.get("Transporter", pd.Series()).unique())
transporter_rating = st.sidebar.slider("Transporter Rating", 1, 5, (2, 5))

# Tabs
tabs = st.tabs(["ODVT Trends", "Cost Model", "Transporter Discovery"])

with tabs[0]:  # ODVT Trends
    st.subheader("ODVT Trends")
    if "Rate type" in df_collective.columns and "Shipper" in df_collective.columns:
        shipper_rate = df_collective.groupby("Rate type")["Shipper"].sum().reset_index()
        fig1 = px.pie(shipper_rate, values="Shipper", names="Rate type", title="Shipper Rate Distribution")
        st.plotly_chart(fig1)

    if "Category" in df_collective.columns:
        vehicle_count = df_collective.groupby("Category").size().reset_index(name="Count")
        fig2 = px.pie(vehicle_count, values="Count", names="Category", title="Vehicle Category Distribution")
        st.plotly_chart(fig2)

    expected_columns = ["Origin Locality", "Destination Locality", "Shipper", "ETA", "Toll Cost", "Lead Distance"]
    if all(col in df_collective.columns for col in expected_columns):
        table_data = df_collective.groupby(["Origin Locality", "Destination Locality"], as_index=False).agg(
            {"Shipper": "mean", "ETA": "mean", "Toll Cost": "mean", "Lead Distance": "mean"}
        )
        st.dataframe(table_data)
    else:
        st.error("Missing required columns for ODVT Trends table.")

with tabs[1]:  # Cost Model
    st.subheader("Cost Model Upload")
    uploaded_file = st.file_uploader("Upload your cost model file", type=["xlsx"])
    if uploaded_file is not None:
        user_df = pd.read_excel(uploaded_file)
        if set(["Origin", "Destination", "Truck Type"]).issubset(user_df.columns) and \
           set(["Origin", "Destination", "Truck Type"]).issubset(df_cost_model.columns):
            merged_df = user_df.merge(df_cost_model, on=["Origin", "Destination", "Truck Type"], how="left")
            st.dataframe(merged_df)
        else:
            st.warning("Missing required columns in uploaded file or cost model data.")

with tabs[2]:  # Transporter Discovery
    st.subheader("Transporter Discovery")
    if "Rating" in df_collective.columns and "Transporter" in df_collective.columns:
        filtered_df = df_collective[(df_collective["Rating"] >= transporter_rating[0]) &
                                    (df_collective["Rating"] <= transporter_rating[1])]
        if not filtered_df.empty:
            table_transporter = filtered_df.groupby("Transporter").agg(
                {"Rating": "mean", "Transporter": "count", "Origin Locality": "nunique"}
            ).reset_index()
            table_transporter.columns = ["Transporter Name", "Mean Rating", "Total Trips", "Unique Origin-Destination Count"]
            st.dataframe(table_transporter)
        else:
            st.warning("No matching transporters found for selected filters.")
    else:
        st.warning("Transporter data missing from dataset.")
