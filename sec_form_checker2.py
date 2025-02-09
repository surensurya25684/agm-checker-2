import pandas as pd
import streamlit as st
from sec_edgar_downloader import Downloader
from io import BytesIO
import os

# Initialize SEC Downloader with data directory
email = "your-email@example.com"  # SEC requires an email for identity
dl = Downloader("data", email)

# Streamlit UI
st.title("SEC Form 5.07 Finder")

# Sidebar: User Identity
st.sidebar.header("User Settings")
email_input = st.sidebar.text_input("Enter your email (required by SEC):", placeholder="example@domain.com")

if email_input:
    dl = Downloader("data", email_input)
    st.sidebar.success("Email Set Successfully!")

# Upload Excel File
uploaded_file = st.file_uploader("Upload an Excel file with CIK numbers", type=['xlsx'])

# Manual CIK input
manual_cik = st.text_input("Or enter a CIK number manually:", placeholder="Enter CIK")

# Process Data
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
        cik = str(row.get('CIK', '')).zfill(10)  # Ensure CIK is in 10-digit format
        company_name = row.get('Company Name', 'Unknown')

        st.write(f"Processing CIK: {cik} ({company_name})...")

        try:
            # Download 8-K filings for 2024
            dl.get("8-K", cik, after="2024-01-01", before="2024-12-31")

            # Check if any filings were downloaded
            filings_dir = f"data/sec-edgar-filings/{cik}/8-K/"
            if os.path.exists(filings_dir) and os.listdir(filings_dir):
                form_507_link = f"https://www.sec.gov/edgar/browse/?CIK={cik}"
                form_507_found = "Yes"
            else:
                form_507_link = "Not Found"
                form_507_found = "No"

            results.append({
                "CIK": cik,
                "Company Name": company_name,
                "Form_5.07_Available": form_507_found,
                "Form_5.07_Link": form_507_link
            })

        except Exception as e:
            st.error(f"Error processing CIK {cik}: {e}")
            results.append({
                "CIK": cik,
                "Company Name": company_name,
                "Form_5.07_Available": "Error",
                "Form_5.07_Link": "Not Found"
            })

    results_df = pd.DataFrame(results)
    st.dataframe(results_df)

    # Download Results as Excel
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
