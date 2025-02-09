import pandas as pd
import streamlit as st
from edgar_utils import get_filings
from io import BytesIO

# Streamlit UI
st.title("SEC Form 5.07 Finder")

# Sidebar: User Identity
st.sidebar.header("User Settings")
email = st.sidebar.text_input("Enter your email (not mandatory but recommended)", placeholder="example@domain.com")

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
            filings = get_filings(cik=cik, form_type="8-K", year=2024)

            # Check for Item 5.07 in the filings
            form_507_found = False
            form_507_link = None

            for filing in filings:
                if "5.07" in filing['items']:
                    form_507_found = True
                    form_507_link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{filing['accession_number'].replace('-', '')}/index.html"
                    break  # Stop after finding the first match

            results.append({
                "CIK": cik,
                "Company Name": company_name,
                "Form_5.07_Available": "Yes" if form_507_found else "No",
                "Form_5.07_Link": form_507_link if form_507_found else f"https://www.sec.gov/edgar/browse/?CIK={cik}"
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
