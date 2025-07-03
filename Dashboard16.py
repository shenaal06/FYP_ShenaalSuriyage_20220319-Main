import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_option_menu import option_menu
from datetime import date

# -----------------------------------------------------------------------------
# Page Config & Styles
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Pharma Inventory AI Dashboard", layout="wide")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] > .main {
    background-image: url('https://images.unsplash.com/photo-1588776814546-ec7c1a2f50c4?auto=format&fit=crop&w=1500&q=80');
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}
[data-testid="stHeader"] {background: rgba(0,0,0,0);}
.kpi-box {
    background: rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 20px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.18);
    text-align: center;
    margin-bottom: 20px;
}
.kpi-value {font-size: 2.1rem; font-weight: 600; color: #ffffff;}
.kpi-label {font-size: 0.9rem; color: #e0e0e0; letter-spacing: .4px;}
.section-card {
    background: rgba(0,0,0,0.40);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 18px;
    padding: 30px 25px;
    margin-bottom: 35px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Sidebar Upload and Navigation
# -----------------------------------------------------------------------------
with st.sidebar:
    selected = option_menu("Navigation", ["Home", "Expiry Risk", "Stock‑Out Risk", "Overstocked"],
                           icons=["house", "file-earmark-x", "exclamation-triangle", "box-seam"],
                           default_index=0)
    st.markdown("---")
    uploaded_file = st.file_uploader("Upload inventory CSV")

# Initialize datasets
user_df = expiry_df = stockout_df = overstock_df = None

# -----------------------------------------------------------------------------
# Upload logic: Auto-detect file type based on columns
# -----------------------------------------------------------------------------
def detect_dataset_type(df):
    col_sets = {
        "expiry": {"Expiry Risk", "Predicted Loss", "Opportunity lost from expired drugs"},
        "stockout": {"Stock-Out Risk", "Probability"},
        "overstock": {"Cluster", "Total of Stagnant Drugs", "Overstock_Cluster"}
    }
    for key, cols in col_sets.items():
        if any(col in df.columns for col in cols):
            return key
    return None

if uploaded_file:
    try:
        user_df = pd.read_csv(uploaded_file)
        detected_type = detect_dataset_type(user_df)
        if detected_type == "expiry":
            expiry_df = user_df
            st.sidebar.success("Expiry Risk data detected")
        elif detected_type == "stockout":
            stockout_df = user_df
            st.sidebar.success("Stock-Out Risk data detected")
        elif detected_type == "overstock":
            overstock_df = user_df
            st.sidebar.success("Overstock data detected")
        else:
            st.sidebar.warning("Unknown schema – preview only in Home tab")
    except Exception as e:
        st.sidebar.error(f"Upload error: {e}")

# -----------------------------------------------------------------------------
# Load default data if no upload overrides
# -----------------------------------------------------------------------------
try:
    if expiry_df is None:
        expiry_df = pd.read_csv("expiry_predictions.csv")
    if stockout_df is None:
        stockout_df = pd.read_csv("stockout_predictions_full.csv")
    if overstock_df is None:
        overstock_df = pd.read_csv("overstock_clusters.csv")
except Exception as e:
    st.error(f"Error loading default data: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# Helper function: KPI card
# -----------------------------------------------------------------------------
def kpi_box(label, value):
    if value is None or pd.isna(value):
        val_text = "N/A"
    elif isinstance(value, float):
        val_text = f"{value:,.2f}"
    else:
        val_text = f"{value:,}"
    st.markdown(f"""
        <div class='kpi-box'>
            <div class='kpi-label'>{label}</div>
            <div class='kpi-value'>{val_text}</div>
        </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# HOME TAB
# -----------------------------------------------------------------------------
if selected == "Home":
    st.title("Intelligent Inventory Management Dashboard")

    kpi_cols = st.columns(4)
    try:
        with kpi_cols[0]:
            if {"Purchasing", "Purchasing base price"}.issubset(overstock_df.columns):
                total_value = (overstock_df["Purchasing"] * overstock_df["Purchasing base price"]).sum()
                kpi_box("Total Stock Value ($)", total_value)
        with kpi_cols[1]:
            if {"Total of Stagnant Drugs", "Left Stock"}.issubset(overstock_df.columns):
                percent = overstock_df["Total of Stagnant Drugs"].sum() / overstock_df["Left Stock"].sum() * 100
                kpi_box("% Stagnant Inventory", percent)
        with kpi_cols[2]:
            if "Opportunity lost from expired drugs" in expiry_df.columns:
                lost = expiry_df["Opportunity lost from expired drugs"].sum()
                kpi_box("Expired Stock Value ($)", lost)
        with kpi_cols[3]:
            col = next((c for c in expiry_df.columns if "expired" in c.lower()), None)
            if col:
                kpi_box("Number of Expired Items", expiry_df[col].sum())
    except Exception as e:
        st.warning(f"KPI error: {e}")

    if user_df is not None:
        with st.expander("Uploaded Data Preview"):
            st.dataframe(user_df.head(), use_container_width=True)

    dl = st.columns(3)
    with dl[0]:
        st.download_button("Download Expiry Report", expiry_df.to_csv(index=False), "expiry_predictions.csv")
    with dl[1]:
        st.download_button("Download Stock-Out Report", stockout_df.to_csv(index=False), "stockout_predictions_full.csv")
    with dl[2]:
        st.download_button("Download Overstock Report", overstock_df.to_csv(index=False), "overstock_clusters.csv")

# -----------------------------------------------------------------------------
# EXPIRY RISK TAB
# -----------------------------------------------------------------------------
elif selected == "Expiry Risk":
    st.title("Expiry Risk Dashboard")
    df_exp = expiry_df.copy()

    drug_col = next((c for c in df_exp.columns if "drug" in c.lower()), None)
    loss_col = next((c for c in df_exp.columns if "loss" in c.lower()), None)

    if not drug_col or not loss_col:
        st.warning("Required columns (e.g., Drug name / Predicted loss) not found.")
    else:
        search_term = st.text_input("Search Drug Name")
        if search_term:
            df_exp = df_exp[df_exp[drug_col].str.contains(search_term, case=False, na=False)]

        if st.checkbox("Show High Expiry Risk Only") and "Expiry Risk" in df_exp.columns:
            df_exp = df_exp[df_exp["Expiry Risk"].str.lower() == "high"]

        col1, col2 = st.columns(2)
        with col1:
            kpi_box("Average Predicted Loss ($)", df_exp[loss_col].mean())
        with col2:
            kpi_box("Drugs at Risk", df_exp.shape[0])

        view = st.radio("View as:", ["Bar Chart", "Table"], horizontal=True)
        if view == "Bar Chart":
            fig = px.bar(df_exp.sort_values(loss_col, ascending=False).head(10),
                         x=drug_col, y=loss_col, title="Top 10 Expiry Risk Drugs")
            st.plotly_chart(fig, use_container_width=True)

            if "Category_Expired" in df_exp.columns:
                fig2 = px.pie(df_exp, names="Category_Expired", values=loss_col, title="Loss by Category")
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.dataframe(df_exp, use_container_width=True)

        st.download_button("Download Filtered Report", df_exp.to_csv(index=False), "filtered_expiry.csv")

# -----------------------------------------------------------------------------
# STOCK-OUT RISK TAB
# -----------------------------------------------------------------------------
elif selected == "Stock‑Out Risk":
    st.title("Stock-Out Risk Dashboard")
    df_so = stockout_df.copy()

    drug_col = next((c for c in df_so.columns if "drug" in c.lower()), None)
    prob_col = next((c for c in df_so.columns if "prob" in c.lower()), None)

    if not drug_col or not prob_col:
        st.warning("Required columns (Drug or Probability) not found.")
    else:
        search_term = st.text_input("Search Drug Name")
        if search_term:
            df_so = df_so[df_so[drug_col].str.contains(search_term, case=False, na=False)]

        if "Stock-Out Risk" in df_so.columns:
            df_so = df_so[df_so["Stock-Out Risk"].str.lower() == "yes"]

        col1, col2 = st.columns(2)
        with col1:
            kpi_box("Drugs at Risk", df_so.shape[0])
        with col2:
            kpi_box("Avg Stock-Out Probability", df_so[prob_col].mean())

        view = st.radio("View as:", ["Bar Chart", "Table"], horizontal=True)
        if view == "Bar Chart":
            fig = px.bar(df_so.sort_values(prob_col, ascending=False).head(15),
                         x=drug_col, y=prob_col, title="Top Stock-Out Risk Drugs")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(df_so, use_container_width=True)

        st.download_button("Download Filtered Report", df_so.to_csv(index=False), "filtered_stockout.csv")

# -----------------------------------------------------------------------------
# OVERSTOCKED TAB (ENHANCED)
# -----------------------------------------------------------------------------
elif selected == "Overstocked":
    st.title("Overstocked Inventory Dashboard")
    df_over = overstock_df.copy()

    drug_col = next((c for c in df_over.columns if "drug" in c.lower()), None)
    cluster_col = next((c for c in df_over.columns if "cluster" in c.lower()), None)
    purch_col = "Purchasing"
    price_col = "Purchasing base price"

    if not cluster_col:
        st.warning("Cluster column not found.")
    else:
        st.text_input("Search Drug Name", key="over_search")

        # Dropdown: select cluster
        clusters = df_over[cluster_col].unique()
        selected_cluster = st.selectbox("Select Cluster to Highlight", clusters)
        show_only = st.checkbox("Show only highlighted cluster", value=True)

        filtered_df = df_over[df_over[cluster_col] == selected_cluster] if show_only else df_over

        # KPIs
        col1, col2 = st.columns(2)
        with col1:
            kpi_box(f"Items in Cluster {selected_cluster}", df_over[df_over[cluster_col] == selected_cluster].shape[0])
        with col2:
            if purch_col in df_over and price_col in df_over:
                total_val = (df_over[df_over[cluster_col] == selected_cluster][purch_col] *
                             df_over[df_over[cluster_col] == selected_cluster][price_col]).sum()
                kpi_box("Total Overstock Value ($)", total_val)

        # View
        view = st.radio("View as:", ["Scatter Plot", "Table"], horizontal=True)
        if view == "Scatter Plot":
            fig = px.scatter(df_over,
                             x=purch_col, y=price_col, text=drug_col,
                             color=(df_over[cluster_col] == selected_cluster).map({True: "Highlighted", False: "Other"}),
                             color_discrete_map={"Highlighted": "red", "Other": "gray"},
                             title="Overstocked Items – Purchasing vs. Price")
            fig.update_traces(textposition='top center')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(filtered_df, use_container_width=True)

        st.download_button("Download Overstock Report", filtered_df.to_csv(index=False), "filtered_overstock.csv")

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.markdown("---")
st.caption("© 2025 Predictive Pharmaceutical Inventory | Designed by Shenaal Suriyage")