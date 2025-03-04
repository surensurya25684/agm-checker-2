import streamlit as st
import datetime
from secedgar.filings import Filing, FilingType
from secedgar.client import NetworkClient
from secedgar.utils import get_cik_map

# Optional: A small helper dict to map user-friendly form labels to FilingType
FORM_TYPE_MAP = {
    "10-K": FilingType.FILING_10K,
    "10-Q": FilingType.FILING_10Q,
    "8-K" : FilingType.FILING_8K,
    "DEF 14A": FilingType.FILING_DEFA14A,
    # Add others as needed
}

def main():
    st.title("Bulk SEC Filings Search")
    st.write("Search EDGAR for multiple tickers and specific filing types.")

    # --- 1) Collect user inputs ---
    # A) EDGAR Identity
    user_agent = st.text_input(
        "Enter your EDGAR user agent identity (required by SEC)",
        "MyApp/1.0 (your_email@example.com)"
    )
    
    # B) Tickers Input (bulk)
    tickers_input = st.text_area(
        "Enter ticker symbols (one per line):",
        value="AAPL\nMSFT\nAMZN",
        help="Enter as many tickers as you like. Example:\nAAPL\nMSFT\nAMZN"
    )

    # C) Form Types
    form_options = list(FORM_TYPE_MAP.keys())  # e.g., ["10-K", "10-Q", "8-K", ...]
    selected_form_types = st.multiselect(
        "Select form types to retrieve:",
        form_options,
        default=["10-K"]
    )

    # D) Date Range (optional)
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start date:", datetime.date(2020, 1, 1))
    with col2:
        end_date = st.date_input("End date:", datetime.date.today())

    # --- 2) Trigger search on button click ---
    if st.button("Search Filings"):
        # Clean up user inputs
        tickers = [
            t.strip().upper() for t in tickers_input.split("\n") 
            if t.strip()
        ]

        # Create a NetworkClient with your user agent (identity)
        client = NetworkClient(user_agent=user_agent)

        # Prepare a container for search results
        search_results = []

        # --- 3) For each ticker, retrieve the desired filings ---
        for ticker in tickers:
            st.write(f"### Results for {ticker}")
            try:
                # Convert ticker to CIK (if valid)
                # get_cik_map returns a dict { "TICKER": "CIK" }
                cik_map = get_cik_map([ticker])
                cik = cik_map[ticker]  # May raise KeyError if not found

                # For each selected form type, gather filing metadata/urls
                for form_name in selected_form_types:
                    filing_type_obj = FORM_TYPE_MAP.get(form_name)
                    if not filing_type_obj:
                        continue

                    # Create Filing object
                    filing = Filing(
                        cik_lookup=cik,
                        filing_type=filing_type_obj,
                        start_date=start_date,
                        end_date=end_date,
                        client=client
                    )

                    # `get_urls()` returns a list of filing URLs (no local download).
                    # If you need more detail, use `get_metadata()` or call `.save()`.
                    urls = filing.get_urls()

                    # Append to our results list
                    search_results.append({
                        "ticker": ticker,
                        "cik": cik,
                        "form_type": form_name,
                        "urls": urls
                    })

                    # Display in Streamlit
                    st.subheader(f"{form_name} Filings:")
                    if not urls:
                        st.write(f"No {form_name} filings found in this date range.")
                    else:
                        for link in urls:
                            st.write(link)

            except Exception as e:
                st.error(f"Error fetching data for {ticker}: {str(e)}")

        # Optionally do something with `search_results` here (export to CSV, etc.)

if __name__ == "__main__":
    main()
