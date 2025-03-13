import streamlit as st
import pandas as pd
import requests
import openpxyl
from datetime import datetime
from collections import defaultdict
import io

# -------------------------------------------------
# Dictionaries for categories and form baselines
# -------------------------------------------------
FILING_CATEGORIES = {
    "Annual & Quarterly Reports": ["10-K", "10-K/A", "10-Q", "10-Q/A"],
    "Current Reports (8-K)": ["8-K", "8-K/A"],
    "Proxy Statements": [
        "DEF 14A", "DEFA14A", "DFAN14A",
        "DEFN14A", "DEFR14A", "DEFM14A",
        "PRE 14A", "PRER14A", "PREC14A"
    ],
    "Ownership Forms": [
        "3", "3/A", "4", "4/A", "5", "5/A",
        "SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A"
    ]
}

FORM_BASE = {
    # 10-K
    "10-K":   "10-K", 
    "10-K/A": "10-K",
    # 10-Q
    "10-Q":   "10-Q", 
    "10-Q/A": "10-Q",
    # 8-K
    "8-K":    "8-K",  
    "8-K/A":  "8-K",

    # Proxy forms -> "Proxy"
    "DEF 14A":   "Proxy",  "DEFA14A":  "Proxy",
    "DFAN14A":   "Proxy",  "DEFN14A":  "Proxy",
    "DEFR14A":   "Proxy",  "DEFM14A":  "Proxy",
    "PRE 14A":   "Proxy",  "PRER14A":  "Proxy",
    "PREC14A":   "Proxy",

    # Ownership forms -> "Ownership"
    "3":         "Ownership",
    "3/A":       "Ownership",
    "4":         "Ownership",
    "4/A":       "Ownership",
    "5":         "Ownership",
    "5/A":       "Ownership",
    "SC 13D":    "Ownership",
    "SC 13D/A":  "Ownership",
    "SC 13G":    "Ownership",
    "SC 13G/A":  "Ownership",
}

def zero_pad_cik(cik):
    """
    Ensures the CIK is a zero-padded string of length 10.
    e.g. 1156375 -> '0001156375'
    """
    try:
        val = int(cik)  # if it's purely numeric
        return f"{val:010d}"
    except ValueError:
        # If cik is not strictly numeric, just return as-is (left-padded).
        return str(cik).rjust(10, "0")

def fetch_sec_json(cik_str, headers):
    """
    Given a zero-padded CIK string like '0001156375',
    fetch JSON from https://data.sec.gov/submissions/CIK0001156375.json
    Returns a dict or None if error/not found.
    """
    base_url = "https://data.sec.gov/submissions/CIK{}.json"
    url = base_url.format(cik_str)
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        else:
            st.warning(f"CIK JSON fetch returned {resp.status_code} for {url}.")
            return None
    except Exception as ex:
        st.warning(f"Error fetching {url}: {ex}")
        return None

def run_app():
    st.title("SEC Filing Search (Streamlit)")

    # 1) User email for the SEC "User-Agent"
    user_email = st.text_input(
        "Enter your email (used in SEC User-Agent per compliance)",
        value="someone@example.com"
    )
    HEADERS = {"User-Agent": user_email.strip()}

    # 2) Choose category -> forms_we_want
    category_choice = st.selectbox(
        "Which category of SEC filings do you want?",
        list(FILING_CATEGORIES.keys())
    )
    forms_we_want = FILING_CATEGORIES[category_choice]

    # 3) Date range pickers (both optional)
    st.write("**Optionally select a Start and End date.**")
    start_date = st.date_input("Start Date (optional)", value=None)
    end_date = st.date_input("End Date (optional)", value=None)

    # Convert Streamlit date to actual datetime or None
    start_date_val = None if not start_date else datetime.combine(start_date, datetime.min.time())
    end_date_val = None if not end_date else datetime.combine(end_date, datetime.min.time())

    # 4) 8-K item filter
    item_filter = []
    if any(f.startswith("8-K") for f in forms_we_want):
        st.write("Optionally enter 8-K items to filter by (comma-separated). e.g. `5.02, 5.07`")
        items_str = st.text_input("8-K Items (blank = none)")
        if items_str:
            item_filter = [x.strip() for x in items_str.split(",") if x.strip()]

    st.write("---")

    # 5) Let the user pick how to input CIKs
    st.write("**Choose how to provide CIKs**:")
    input_mode = st.radio(
        "Mode:",
        ("Upload Excel with CIKs", "Manually enter CIKs")
    )

    uploaded_file = None
    manual_ciks = []
    df = None  # eventually read from Excel if user uploads

    if input_mode == "Upload Excel with CIKs":
        # This uses openpyxl to read .xlsx
        uploaded_file = st.file_uploader("Upload an Excel file (XLS or XLSX)")
    else:
        # Manually input CIKs, comma- or line-separated
        manual_ciks_str = st.text_area("Enter CIK(s), separated by commas or line breaks.")
        if manual_ciks_str:
            splitted = manual_ciks_str.replace("\n", ",").split(",")
            manual_ciks = [x.strip() for x in splitted if x.strip()]

    run_button = st.button("Run")

    if run_button:
        # If user uploads an Excel file
        if input_mode == "Upload Excel with CIKs":
            if not uploaded_file:
                st.error("Please upload an Excel file before running.")
                return
            else:
                try:
                    # Pandas will use openpyxl behind the scenes
                    df = pd.read_excel(uploaded_file, engine="openpyxl")
                    df.columns = df.columns.str.strip()
                except Exception as e:
                    st.error(f"Error reading Excel file: {e}")
                    return
        else:
            # Create a minimal DataFrame from user-provided CIKs
            df = pd.DataFrame({
                "CIK": manual_ciks,
                "Company Name": ["Unknown"] * len(manual_ciks),
                "Issuer id": ["Unknown"] * len(manual_ciks),
                "Analyst name": ["Unknown"] * len(manual_ciks)
            })

        if df is None or df.empty:
            st.warning("No data to process.")
            return

        results = []
        for idx, row in df.iterrows():
            cik_raw = row.get('CIK', None)
            company_name = row.get('Company Name', 'Unknown')
            issuer_id    = row.get('Issuer id', 'Unknown')
            analyst_name = row.get('Analyst name', 'Unknown')

            # Initialize a result dict with standard info
            result = {
                "Issuer ID": issuer_id,
                "CIK": cik_raw,
                "Company Name": company_name,
                "FilingAvailable": "No"
            }

            if not cik_raw:
                # Skip if no CIK
                results.append(result)
                continue

            # Convert CIK to zero-padded
            cik_padded = zero_pad_cik(cik_raw)

            # Fetch JSON from SEC
            sec_data = fetch_sec_json(cik_padded, HEADERS)
            if not sec_data or "filings" not in sec_data or "recent" not in sec_data["filings"]:
                results.append(result)
                continue

            recent = sec_data["filings"]["recent"]
            form_list   = recent.get("form", [])
            date_list   = recent.get("filingDate", [])
            accno_list  = recent.get("accessionNumber", [])
            items_list  = recent.get("items", [])

            link_tracker = defaultdict(list)

            # Loop through recent filings
            for i in range(len(form_list)):
                form_type = form_list[i]
                filing_dt_str = date_list[i]
                accno_str     = accno_list[i]
                items_str     = items_list[i] if i < len(items_list) else ""

                # 1) Filter by form_type
                if form_type not in forms_we_want:
                    continue

                # 2) Parse date
                try:
                    fdate = datetime.strptime(filing_dt_str, "%Y-%m-%d")
                except ValueError:
                    continue

                # 3) Check date filters
                if start_date_val and fdate < start_date_val:
                    continue
                if end_date_val and fdate > end_date_val:
                    continue

                # 4) Build link
                accno_nodashes = accno_str.replace('-', '')
                link = f"https://www.sec.gov/Archives/edgar/data/{int(cik_padded)}/{accno_nodashes}/index.html"

                # 5) Determine base form
                base_form = FORM_BASE.get(form_type, form_type)

                # 6) If 8-K and user wants item filter
                if base_form == "8-K" and item_filter:
                    splitted_items = [x.strip() for x in items_str.split(",") if x.strip()]
                    for it in item_filter:
                        if it in splitted_items:
                            col_name = f"8-K({it})"
                            link_tracker[col_name].append(link)
                else:
                    link_tracker[base_form].append(link)

            if link_tracker:
                result["FilingAvailable"] = "Yes"
                for col_name, link_list in link_tracker.items():
                    if len(link_list) == 1:
                        result[col_name] = link_list[0]
                    else:
                        # first link
                        result[col_name] = link_list[0]
                        # subsequent => col_name_2, col_name_3, ...
                        for j, lnk in enumerate(link_list[1:], start=2):
                            result[f"{col_name}_{j}"] = lnk

            results.append(result)

        # Convert results to a DataFrame
        results_df = pd.DataFrame(results)

        # Convert the final DF to an Excel in-memory (using openpyxl for writing)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            results_df.to_excel(writer, index=False, sheet_name="Results")
        processed_data = output.getvalue()

        st.success("Processing complete! Download your results below:")
        st.download_button(
            label="Download Excel",
            data=processed_data,
            file_name="SEC_filings_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ----------------------------------------------------------
# Streamlit will run everything on import. We wrap logic in
# a function and call it under __name__ == "__main__".
# ----------------------------------------------------------
if __name__ == "__main__":
    run_app()
