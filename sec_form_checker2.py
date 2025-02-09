import pandas as pd
import streamlit as st
from edgar import Company, set_identity
from io import BytesIO

# Streamlit UI Layout
st.title("SEC Form 5.07 Finder")

# **Step 1: User Input for Identity**
st.sidebar.header("User Settings")
email = st.sidebar.text_input("Enter your email for SEC identity:", placeholder="example@domain.com")

# Set the identity only if an email is provided
if email:
    set_identity(email)
    st.sidebar.success("Identity set successfully!")

# **Step 2: Upload Excel File**
uploaded_file = st.file_uploader("Upload Excel file containing companies (with CIK column):", type=['xlsx'])

# **Step 3: Manual CIK Input**
manual_cik = st.text_input("Or enter a CIK number manually:", placeholder="Enter CIK number")

# **Step 4: Process File**
if uploaded_file or manual_cik:
    results = []

    # If file is uploaded, read data
    if uploaded_file:
        companies_df = pd.read_excel(uploaded_file)

        # Strip whitespace from column names
        companies_df.columns = companies_df.columns.str.strip()

        # Check required columns
        if 'CIK' not in companies_df.columns:
            st.error("Error: The uploaded file must contain a 'CIK' column.")
        else:
            st.success("File uploaded successfully!")
            process_list = companies_df.to_dict(orient='records')  # Convert to list of dictionaries

    else:
        process_list = [{"CIK": manual_cik, "Company Name": "Manual Entry", "Issuer id": "N/A", "Analyst name": "N/A"}]

    # **Step 5: Process Each Company**
    for row in process_list:
        cik = row.get('CIK', None)
        company_name = row.get('Company Name', 'Unknown')
        issuer_id = row.get('Issuer id', 'Unknown')
        analyst_name = row.get('Analyst name', 'Unknown')

        if not cik:
            st.warning(f"Skipping row: No CIK found.")
            results.append({
                "CIK": "Unknown",
                "Company Name": company_name,
                "Issuer ID": issuer_id,
                "Analyst Name": analyst_name,
                "Form_5.07_Available": "No CIK Found",
                "Form_5.07_Link": "Not Available"
            })
            continue

        st.write(f"Processing CIK: {cik} ({company_name})...")

        try:
            company = Company(cik)
            filings = company.get_filings(form="8-K")

            form_507_found = False
            form_507_link = None

            for filing in filings:
                if hasattr(filing, 'items') and '5.07' in filing.items:
                    if hasattr(filing, 'filing_date'):
                        filing_date = filing.filing_date.strftime('%Y-%m-%d')
                        if filing_date.startswith("2024"):
                            form_507_found = True
                            formatted_accession_number = filing.accession_number.replace('-', '')
                            form_507_link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{formatted_accession_number}/index.html"
                            break  

            results.append({
                "CIK": cik,
                "Company Name": company_name,
                "Issuer ID": issuer_id,
                "Analyst Name": analyst_name,
                "Form_5.07_Available": "Yes" if form_507_found else "No",
                "Form_5.07_Link": form_507_link if form_507_found else f"https://www.sec.gov/Archives/edgar/data/{cik}/NotFound.htm"
            })

        except Exception as e:
            st.error(f"Error processing CIK {cik}: {e}")
            results.append({
                "CIK": cik,
                "Company Name": company_name,
                "Issuer ID": issuer_id,
                "Analyst Name": analyst_name,
                "Form_5.07_Available": "Error",
                "Form_5.07_Link": None
            })

    # **Step 6: Display Results**
    results_df = pd.DataFrame(results)
    st.dataframe(results_df)

    # **Step 7: Provide Download Link**
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
