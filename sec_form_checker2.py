import streamlit as st
import pandas as pd
import io
from edgar import Company, set_identity

st.title("Form 5.07 Checker")

# Sidebar or main input for the SEC identity email
email = st.text_input("Enter your SEC EDGAR Identity Email", "suren.surya@msci.com")

# File uploader for the input Excel file
uploaded_file = st.file_uploader("Upload Excel file with companies", type=['xlsx', 'xls'])

if uploaded_file is not None:
    # Read and preview the input file
    companies_df = pd.read_excel(uploaded_file)
    companies_df.columns = companies_df.columns.str.strip()  # Clean up column names
    st.write("### Preview of Input File")
    st.dataframe(companies_df.head())

if st.button("Run Processing"):
    if uploaded_file is None:
        st.error("Please upload an Excel file to proceed.")
    else:
        # Set the SEC EDGAR identity email
        set_identity(email)
        results = []

        st.info("Processing companies. This may take a moment...")
        # Iterate through each company in the input DataFrame
        for index, row in companies_df.iterrows():
            cik = row.get('CIK', None)
            company_name = row.get('Company Name', 'Unknown')
            issuer_id = row.get('Issuer id', 'Unknown')
            analyst_name = row.get('Analyst name', 'Unknown')

            if cik is None:
                st.warning(f"CIK not found for row {index}. Skipping.")
                results.append({
                    "CIK": "Unknown",
                    "Issuer id": issuer_id,
                    "Company Name": company_name,
                    "Analyst Name": analyst_name,
                    "Form_5.07_Available": "No CIK Found",
                    "Form_5.07_Link1": "Not Available"
                })
                continue

            st.write(f"Processing company with CIK: {cik} ({company_name})")
            try:
                company = Company(cik)
                filings = company.get_filings(form="8-K")

                # List to store all matching Form 5.07 links
                links = []
                for filing in filings:
                    try:
                        if hasattr(filing, 'items') and '5.07' in filing.items:
                            if hasattr(filing, 'filing_date'):
                                filing_date = filing.filing_date.strftime('%Y-%m-%d')
                                if filing_date.startswith("2024"):
                                    formatted_accession_number = filing.accession_number.replace('-', '')
                                    link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{formatted_accession_number}/index.html"
                                    links.append(link)
                    except Exception as e:
                        st.write(f"Error processing a filing for CIK {cik}: {e}")

                # Build result dictionary with base fields
                result = {
                    "CIK": cik,
                    "Issuer id": issuer_id,
                    "Company Name": company_name,
                    "Analyst Name": analyst_name,
                    "Form_5.07_Available": "Yes" if links else "No"
                }

                # Add each link to its own column (Form_5.07_Link1, Form_5.07_Link2, etc.)
                if links:
                    for idx, link in enumerate(links, start=1):
                        result[f"Form_5.07_Link{idx}"] = link
                else:
                    result["Form_5.07_Link1"] = f"https://www.sec.gov/Archives/edgar/data/{cik}/NotFound.htm"

                results.append(result)
            except Exception as e:
                st.write(f"Error processing company with CIK {cik}: {e}")
                results.append({
                    "CIK": cik,
                    "Issuer id": issuer_id,
                    "Company Name": company_name,
                    "Analyst Name": analyst_name,
                    "Form_5.07_Available": "Error",
                    "Form_5.07_Link1": None
                })

        # Convert results to a DataFrame
        results_df = pd.DataFrame(results)

        # Reorder columns: placing "Issuer id" as the second column
        base_columns = ['CIK', 'Issuer id', 'Company Name', 'Analyst Name', 'Form_5.07_Available']
        link_columns = sorted(
            [col for col in results_df.columns if col.startswith('Form_5.07_Link')],
            key=lambda x: int(x.replace('Form_5.07_Link', ''))
        )
        ordered_columns = base_columns + link_columns
        results_df = results_df[ordered_columns]

        # Create an in-memory Excel file
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            results_df.to_excel(writer, index=False)
        output.seek(0)

        st.success("Processing complete!")
        st.download_button(
            label="Download Output Excel",
            data=output,
            file_name="output_file.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
