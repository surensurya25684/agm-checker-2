import pandas as pd
import streamlit as st
from sec_edgar_downloader import Downloader
from io import BytesIO

# Streamlit UI
st.title("SEC Form 5.07 Finder")

# Sidebar: Enter Email ID
st.sidebar.header("User Settings")
email = st.sidebar.text_input("Enter your email for SEC identity:", placeholder="example@domain.com")

# Initialize SEC Downloader
if email:
    dl = Downloader("data", email)
    st.sidebar.success("SEC Identity Set!")

# Upload Excel file
uploaded_file = st.file_uploader("Upload Excel file (.xlsx) with CIK numbers", type=['xlsx'])

# Manual CIK input
manual_cik = st.text_input("Or enter a CIK number manually:", placeholder="Enter CIK")

# Process SEC filings
if uploaded_file or manual_cik:
    results = []

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip()
        
        if 'CIK' not in df.columns:
            st.error("Error: The uploaded file must contain a 'CIK' column.")
        else:
            process_list = df.to_dict(orient='records')
    else:
        process_list = [{"CIK": manual_cik, "Company Name": "Manual Entry"}]

    for row in process_list:
        cik = str(row.get('CIK', '')).zfill(10)  # Ensure CIK is 10-digit format
        company_name = row.get('Company Name', 'Unknown')

        st.write(f"Processing CIK: {cik} ({company_name})...")

        try:
            dl.get("8-K", cik, after="2024-01-01", before="2024-12-31")
            st.success(f"Downloaded 8-K filings for {company_name} (CIK: {cik})")

            results.append({
                "CIK": cik,
                "Company Name": company_name,
                "Form_5.07_Available": "Yes",
                "Form_5.07_Link": f"https://www.sec.gov/edgar/browse/?CIK={cik}"
            })
        except Exception as e:
            st.error(f"Error processing CIK {cik}: {e}")
            results.append({
                "CIK": cik,
                "Company Name": company_name,
                "Form_5.07_Available": "No",
                "Form_5.07_Link": "Not Found"
            })

    results_df = pd.DataFrame(results)
    st.dataframe(results_df)

    # Download Results
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        results_df.to_excel(writer, index=False)
    output.seek(0)

    st.download_button(
        label="Download Results as Excel",
        data=output,
        file_name="Form_5.07_Results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
