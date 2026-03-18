"""
Alcohol Onboarding Bulk Tools — MVP
Generates 5 CSVs from form inputs for DoorDash internal bulk tools.
"""

import csv
import io
import os
import re
import tempfile

import pandas as pd
import streamlit as st
from dateutil import parser as dateutil_parser

# Bulk tool links (order matches CSV order 1–5)
BULK_TOOL_LINKS = {
    "Bulk Tool 1 - Update Payment Account By Store ID": "https://admin-gateway.doordash.com/tools/bulk_tools/categories/store/update_payment_account_by_store_id",
    "Bulk Tool 2 - Create Mx Payment Policy": "https://admin-gateway.doordash.com/tools/bulk_tools/categories/category_expansion/create_mx_payment_policy",
    "Bulk Tool 3 - Update Stores By ID": "https://admin-gateway.doordash.com/tools/bulk_tools/categories/store/update_stores_by_id",
    "Bulk Tool 4 - Add Entity to Invoiceable Commission": "https://admin-gateway.doordash.com/tools/bulk_tools/categories/invoiceable_commissions/add_entity_to_invoiceable_commission",
    "Bulk Tool 5 - Update Alc Flat Fee": "https://admin-gateway.doordash.com/tools/bulk_tools/categories/category_expansion/update_alc_flat_fee",
}
BULK_TOOL_URLS_ORDERED = list(BULK_TOOL_LINKS.values())


def format_phone(raw: str) -> str:
    """Format as '+1' + 10 digits, no dashes."""
    digits = re.sub(r"\D", "", str(raw).strip())
    if len(digits) == 10:
        return "'+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "'+1" + digits[1:]
    return "'+1" + digits[-10:] if len(digits) >= 10 else raw


def format_ein(raw: str) -> str:
    """EIN with dash after first 2 digits (e.g. 72-0799611)."""
    s = str(raw).strip()
    digits = re.sub(r"\D", "", s)
    if len(digits) >= 9:
        return digits[:2] + "-" + digits[2:9]
    return s


def format_dob(raw: str) -> str:
    """Parse various date formats and return YYYY-MM-DD (e.g. 11-04-1981, 11/04/1981, Mar 7, 2026)."""
    s = str(raw).strip()
    if not s:
        return ""
    try:
        dt = dateutil_parser.parse(s)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        digits = re.sub(r"\D", "", s)
        if len(digits) == 8:
            # Ambiguous: could be YYYYMMDD or MMDDYYYY. Try YYYYMMDD first (year first).
            y, m, d = int(digits[:4]), int(digits[4:6]), int(digits[6:8])
            if 1 <= m <= 12 and 1 <= d <= 31:
                return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
            # Else assume MMDDYYYY
            m, d, y = int(digits[:2]), int(digits[2:4]), int(digits[4:8])
            if 1 <= m <= 12 and 1 <= d <= 31:
                return f"{y:04d}-{m:02d}-{d:02d}"
        return s


def parse_name(full_name: str) -> tuple[str, str]:
    """Split 'First Last' into (first_name, last_name)."""
    parts = str(full_name).strip().split(maxsplit=1)
    if not parts:
        return ("", "")
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], parts[1])


def build_tool1_csv(store_df: pd.DataFrame, form: dict, per_store: dict) -> pd.DataFrame:
    """Bulk Tool 1: update_payment_account_by_store_id."""
    cols = [
        "store_id", "business_name", "routing_number", "account_number",
        "street_address", "city", "state_code", "postal_code", "country_code",
        "business_phone", "business_tax_id", "business_representative_relationship",
        "business_representative_first_name", "business_representative_last_name",
        "business_representative_dob", "business_representative_address_line1",
        "business_representative_address_city", "business_representative_address_state_code",
        "business_representative_address_postal_code", "business_representative_address_country_code",
        "business_representative_email", "business_representative_phone", "statement_descriptor",
        "owner_email", "owner_phone", "business_representative_title",
        "business_representative_ssn_last_4", "card_payments",
    ]
    phone = format_phone(form["phone"])
    email = form["email"].strip()
    first_name, last_name = parse_name(form["legal_rep_name"])
    dob = format_dob(form["legal_rep_dob"])
    ssn4 = str(form["legal_rep_ssn4"]).strip()
    street = form["street_address"].strip()
    city = form["city"].strip()
    state = form["state_code"].strip()
    postal = str(form["postal_code"]).strip()
    country = form["country_code"].strip() or "US"

    rows = []
    for _, row in store_df.iterrows():
        sid = str(row["store_id"]).strip()
        bid = str(row["business_id"]).strip()
        business_name = per_store.get("business_name", {}).get(sid, form.get("legal_business_name", ""))
        routing = per_store.get("routing_number", {}).get(sid, form.get("routing_number", ""))
        account = per_store.get("account_number", {}).get(sid, form.get("account_number", ""))
        tax_id = per_store.get("business_tax_id", {}).get(sid, form.get("business_tax_id", ""))
        if tax_id:
            tax_id = format_ein(tax_id)
        rows.append({
            "store_id": sid,
            "business_name": business_name,
            "routing_number": routing,
            "account_number": account,
            "street_address": street,
            "city": city,
            "state_code": state,
            "postal_code": postal,
            "country_code": country,
            "business_phone": phone,
            "business_tax_id": tax_id,
            "business_representative_relationship": "executive",
            "business_representative_first_name": first_name,
            "business_representative_last_name": last_name,
            "business_representative_dob": dob,
            "business_representative_address_line1": street,
            "business_representative_address_city": city,
            "business_representative_address_state_code": state,
            "business_representative_address_postal_code": postal,
            "business_representative_address_country_code": country,
            "business_representative_email": email,
            "business_representative_phone": phone,
            "statement_descriptor": "WWW.DOORDASH.COM",
            "owner_email": email,
            "owner_phone": phone,
            "business_representative_title": "owner",
            "business_representative_ssn_last_4": ssn4,
            "card_payments": "true",
        })
    return pd.DataFrame(rows, columns=cols)


def build_tool2_csv(store_df: pd.DataFrame) -> pd.DataFrame:
    """Bulk Tool 2: create_mx_payment_policy."""
    cols = ["entity_id", "entity_type", "configuration_level", "merchant_payment_protocols", "creator_user_id"]
    rows = [
        {
            "entity_id": str(row["store_id"]).strip(),
            "entity_type": "ENTITY_STORE",
            "configuration_level": "ITEM",
            "merchant_payment_protocols": "RED_CARD, DIRECT_DEPOSIT",
            "creator_user_id": "1057694332",
        }
        for _, row in store_df.iterrows()
    ]
    return pd.DataFrame(rows, columns=cols)


def build_tool3_csv(store_df: pd.DataFrame) -> pd.DataFrame:
    """Bulk Tool 3: update_stores_by_id."""
    cols = ["store_id", "payment_protocol_id"]
    rows = [{"store_id": str(row["store_id"]).strip(), "payment_protocol_id": "1"} for _, row in store_df.iterrows()]
    return pd.DataFrame(rows, columns=cols)


def build_tool4_csv(store_df: pd.DataFrame) -> pd.DataFrame:
    """Bulk Tool 4: add_entity_to_invoiceable_commission — one row per unique business_id."""
    cols = ["entity_id", "entity_type", "jira_ticket"]
    business_ids = store_df["business_id"].astype(str).str.strip().unique()
    rows = [
        {"entity_id": bid, "entity_type": "business", "jira_ticket": "CATEX-0000"}
        for bid in business_ids
    ]
    return pd.DataFrame(rows, columns=cols)


def build_tool5_csv(store_df: pd.DataFrame) -> pd.DataFrame:
    """Bulk Tool 5: update_alc_flat_fee."""
    cols = ["store_id", "alc_flat_fee_operation"]
    rows = [{"store_id": str(row["store_id"]).strip(), "alc_flat_fee_operation": "ADD"} for _, row in store_df.iterrows()]
    return pd.DataFrame(rows, columns=cols)


def run_bulk_uploads(dfs: list, names: list) -> tuple[bool, list[str]]:
    """
    Open a browser, go to each bulk tool URL, upload the matching CSV, and click Submit.
    Returns (success, list of error messages). User may need to log in with SSO on first page.
    """
    try:
        from playwright.sync_api import sync_playwright, Error as PlaywrightError
        from playwright._impl._errors import TargetClosedError
    except ImportError:
        return (False, ["Playwright not installed. Run: pip install playwright && playwright install chromium"])

    def to_csv(df: pd.DataFrame, quoting: int = csv.QUOTE_MINIMAL) -> str:
        buf = io.StringIO()
        df.to_csv(buf, index=False, quoting=quoting)
        return buf.getvalue()

    errors = []
    # Write CSVs to temp files (Playwright needs real paths)
    temp_dir = tempfile.mkdtemp()
    paths = []
    try:
        for i, (df, name) in enumerate(zip(dfs, names)):
            path = os.path.join(temp_dir, name)
            csv_content = to_csv(df, quoting=csv.QUOTE_ALL if i == 0 else csv.QUOTE_MINIMAL)
            with open(path, "w", encoding="utf-8") as f:
                f.write(csv_content)
            paths.append(path)
        with sync_playwright() as p:
            context = None
            page = None
            browser = None
            # Try your real Chrome profile first (so you're already logged in). Requires Chrome to be fully quit.
            chrome_user_data = os.path.expanduser("~/Library/Application Support/Google/Chrome")
            try:
                context = p.chromium.launch_persistent_context(
                    chrome_user_data,
                    channel="chrome",
                    headless=False,
                )
                page = context.pages[0] if context.pages else context.new_page()
            except PlaywrightError as e:
                if "ProcessSingleton" in str(e) or "profile" in str(e).lower() or "SingletonLock" in str(e):
                    # Profile in use (Chrome still running or lock left behind). Fall back to fresh Chrome.
                    errors.append("Could not use your Chrome profile (Chrome may still be running). Using a fresh Chrome window — you may need to log in with SSO.")
                    browser = p.chromium.launch(headless=False, channel="chrome")
                    context = browser.new_context()
                    page = context.new_page()
                else:
                    raise
            if page is None:
                raise RuntimeError("Failed to create browser page")
            try:
                for (url, csv_path, name) in zip(BULK_TOOL_URLS_ORDERED, paths, names):
                    try:
                        page.goto(url, wait_until="domcontentloaded")
                    except TargetClosedError:
                        errors.append("The browser window was closed before uploads finished. Please try again and leave the Chrome window open until all 5 uploads complete.")
                        break
                    # Wait for file input (up to 60s so user can log in with SSO if prompted)
                    try:
                        page.wait_for_selector('input[type="file"]', state="attached", timeout=60_000)
                    except TargetClosedError:
                        errors.append("The browser window was closed. Leave Chrome open until all 5 uploads complete, then try again.")
                        break
                    except Exception:
                        errors.append(f"{name}: Timed out waiting for upload area. Log in with SSO in the browser, then try again.")
                        continue
                    # Attach the CSV (no need to click "Upload Files" — we set the input directly)
                    try:
                        page.locator('input[type="file"]').first.set_input_files(csv_path)
                    except TargetClosedError:
                        errors.append("The browser window was closed. Leave Chrome open until all 5 uploads complete, then try again.")
                        break
                    # Wait for View Data step and Submit button (page may auto-advance or show Next first)
                    try:
                        submit = page.get_by_role("button", name="Submit")
                        submit.wait_for(state="visible", timeout=20_000)
                        submit.click()
                    except TargetClosedError:
                        errors.append("The browser window was closed. Leave Chrome open until all 5 uploads complete, then try again.")
                        break
                    except Exception:
                        # Try clicking "Next" if Submit isn't visible yet
                        try:
                            next_btn = page.get_by_role("button", name="Next")
                            if next_btn.is_visible():
                                next_btn.click()
                                page.wait_for_timeout(2000)
                                submit = page.get_by_role("button", name="Submit")
                                submit.wait_for(state="visible", timeout=15_000)
                                submit.click()
                        except TargetClosedError:
                            errors.append("The browser window was closed. Leave Chrome open until all 5 uploads complete, then try again.")
                            break
                    page.wait_for_timeout(1500)
            finally:
                try:
                    if context:
                        context.close()
                except Exception:
                    pass
                try:
                    if browser:
                        browser.close()
                except Exception:
                    pass
    finally:
        for p in paths:
            try:
                os.unlink(p)
            except OSError:
                pass
        try:
            os.rmdir(temp_dir)
        except OSError:
            pass

    return (len(errors) == 0, errors)


def main():
    st.set_page_config(page_title="Alcohol Onboarding Bulk Tools", layout="wide")
    if "generated_dfs" not in st.session_state:
        st.session_state.generated_dfs = None

    st.title("Alcohol Onboarding — Bulk CSV Generator")
    st.markdown("Fill out the form below. Then upload your store list (CSV with `store_id` and `business_id`). Click **Generate CSVs** to download the 5 bulk tool files.")

    # If we already have generated CSVs (e.g. from a previous submit), keep showing them so download clicks don't reset the page
    if st.session_state.generated_dfs is not None:
        dfs = st.session_state.generated_dfs
        st.success("CSVs generated. Download any file below, then use the bulk tool links to upload.")
        def to_csv(df: pd.DataFrame, quoting: int = csv.QUOTE_MINIMAL) -> str:
            buf = io.StringIO()
            df.to_csv(buf, index=False, quoting=quoting)
            return buf.getvalue()
        names = [
            "1_update_payment_account_by_store_id.csv",
            "2_create_mx_payment_policy.csv",
            "3_update_stores_by_id.csv",
            "4_add_entity_to_invoiceable_commission.csv",
            "5_update_alc_flat_fee.csv",
        ]
        for i, (name, df) in enumerate(zip(names, dfs)):
            # Bulk Tool 1 requires lowercase "true" in column AB; bulk tool rejects leading apostrophe.
            # Double-quote all fields (like Google Sheets export) so value is "true" in file, no apostrophe.
            data = to_csv(df, quoting=csv.QUOTE_ALL if i == 0 else csv.QUOTE_MINIMAL)
            st.download_button(f"Download {name}", data=data, file_name=name, mime="text/csv", key=name)
        st.subheader("Upload to bulk tools (automatic)")
        st.caption(
            "**Important:** Quit Chrome completely (Cmd+Q) before clicking. We'll open Chrome with your profile so you're already logged in (no security key). Leave the window open until all 5 uploads finish."
        )
        if st.button("Upload to bulk tools"):
            with st.spinner("Opening browser and uploading… Log in with SSO if prompted."):
                ok, errs = run_bulk_uploads(dfs, names)
            if ok:
                st.success("All 5 files were uploaded. Check the browser for any confirmation or errors.")
            else:
                for e in errs:
                    st.error(e)
        st.subheader("Bulk tool links")
        for label, url in BULK_TOOL_LINKS.items():
            st.markdown(f"- **{label}:** [{url}]({url})")
        if st.button("Start over — generate a new set"):
            st.session_state.generated_dfs = None
            st.rerun()
        return

    # Yes/No + per-store uploads live OUTSIDE the form so the page updates as soon as you pick "No"
    # (Inside a form, dropdown changes don't refresh until you click Generate — so uploads never appeared.)
    st.subheader("Variable inputs — same across all stores?")
    st.caption("Choose Yes or No below. If you pick **No**, upload a CSV with **store_id** and that value for each store.")
    same_business_name = st.selectbox("Same Legal Business Name across all stores?", ["Yes", "No"], key="same_business_name")
    legal_business_name = None
    upload_business_name = None
    if same_business_name == "Yes":
        legal_business_name = st.text_input("Legal Business Name", key="legal_business_name")
    else:
        upload_business_name = st.file_uploader("Upload CSV: columns **store_id** + legal_business_name (or business_name)", type=["csv"], key="ubn")

    same_tax_id = st.selectbox("Same Business Tax ID / EIN across all stores?", ["Yes", "No"], key="same_tax_id")
    business_tax_id = None
    upload_tax_id = None
    if same_tax_id == "Yes":
        business_tax_id = st.text_input("Business Tax ID / EIN", key="business_tax_id", help="Dash added after first 2 digits")
    else:
        upload_tax_id = st.file_uploader("Upload CSV: columns **store_id** + business_tax_id (or ein)", type=["csv"], key="utax")

    same_routing = st.selectbox("Same Bank Routing Number across all stores?", ["Yes", "No"], key="same_routing")
    routing_number = None
    upload_routing = None
    if same_routing == "Yes":
        routing_number = st.text_input("Bank Routing Number", key="routing_number", help="Leading zeros preserved")
    else:
        upload_routing = st.file_uploader("Upload CSV: columns **store_id** + **routing_number**", type=["csv"], key="uroute")

    same_account = st.selectbox("Same Bank Account Number across all stores?", ["Yes", "No"], key="same_account")
    account_number = None
    upload_account = None
    if same_account == "Yes":
        account_number = st.text_input("Bank Account Number", key="account_number", help="Leading zeros preserved")
    else:
        upload_account = st.file_uploader("Upload CSV: columns **store_id** + **account_number**", type=["csv"], key="uacct")

    st.divider()

    with st.form("onboarding_form"):
        st.subheader("Address (used for business and legal rep)")
        street_address = st.text_input("Street Address", key="street")
        col1, col2, col3 = st.columns(3)
        with col1:
            city = st.text_input("City", key="city")
        with col2:
            state_code = st.text_input("State Code (e.g. LA)", key="state")
        with col3:
            postal_code = st.text_input("Postal Code", key="postal")
        country_code = st.text_input("Country Code (default US)", value="US", key="country")

        st.subheader("Contact & Legal Rep")
        phone = st.text_input("Phone Number", key="phone", help="Will be formatted as +1XXXXXXXXXX")
        email = st.text_input("Email Address", key="email")
        legal_rep_name = st.text_input("Legal Rep First & Last Name", key="legal_rep_name")
        legal_rep_dob = st.text_input("Legal Rep Date of Birth (will format as YYYY-MM-DD)", key="legal_rep_dob")
        legal_rep_ssn4 = st.text_input("Legal Rep Last 4 SSN", key="legal_rep_ssn4", max_chars=4)

        st.subheader("Store list")
        store_list_file = st.file_uploader("Upload CSV with columns: store_id, business_id", type=["csv"], key="store_list")

        submitted = st.form_submit_button("Generate CSVs")

    if not submitted:
        st.info("Fill the form and click **Generate CSVs**.")
        return

    if store_list_file is None:
        st.error("Please upload a CSV with store_id and business_id.")
        return

    store_df = pd.read_csv(store_list_file)
    store_df.columns = [c.strip().lower().replace(" ", "_") for c in store_df.columns]
    if "store_id" not in store_df.columns or "business_id" not in store_df.columns:
        st.error("CSV must have columns 'store_id' and 'business_id'.")
        return

    # Build per-store lookups for "No" fields
    def load_per_store(upload, id_col: str, value_col: str) -> dict:
        if upload is None:
            return {}
        df = pd.read_csv(upload)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        id_col = next((c for c in df.columns if "store" in c or c == "store_id"), df.columns[0])
        val_col = next((c for c in df.columns if c != id_col), df.columns[1])
        return dict(zip(df[id_col].astype(str).str.strip(), df[val_col].astype(str)))

    per_store = {
        "business_name": load_per_store(upload_business_name, "store_id", "legal_business_name"),
        "business_tax_id": load_per_store(upload_tax_id, "store_id", "business_tax_id"),
        "routing_number": load_per_store(upload_routing, "store_id", "routing_number"),
        "account_number": load_per_store(upload_account, "store_id", "account_number"),
    }

    form = {
        "street_address": street_address or "",
        "city": city or "",
        "state_code": state_code or "",
        "postal_code": postal_code or "",
        "country_code": country_code or "US",
        "phone": phone or "",
        "email": email or "",
        "legal_rep_name": legal_rep_name or "",
        "legal_rep_dob": legal_rep_dob or "",
        "legal_rep_ssn4": legal_rep_ssn4 or "",
        "legal_business_name": legal_business_name if same_business_name == "Yes" else "",
        "business_tax_id": business_tax_id if same_tax_id == "Yes" else "",
        "routing_number": routing_number if same_routing == "Yes" else "",
        "account_number": account_number if same_account == "Yes" else "",
    }

    if same_business_name == "No" and not per_store["business_name"]:
        st.warning("You said Legal Business Name differs per store but no upload provided. Blank will be used.")
    if same_tax_id == "No" and not per_store["business_tax_id"]:
        st.warning("You said Business Tax ID differs per store but no upload provided.")
    if same_routing == "No" and not per_store["routing_number"]:
        st.warning("You said Routing Number differs per store but no upload provided.")
    if same_account == "No" and not per_store["account_number"]:
        st.warning("You said Account Number differs per store but no upload provided.")

    try:
        df1 = build_tool1_csv(store_df, form, per_store)
        df2 = build_tool2_csv(store_df)
        df3 = build_tool3_csv(store_df)
        df4 = build_tool4_csv(store_df)
        df5 = build_tool5_csv(store_df)
    except Exception as e:
        st.exception(e)
        return

    # Save to session so download button clicks don't clear the results
    st.session_state.generated_dfs = [df1, df2, df3, df4, df5]
    st.rerun()


if __name__ == "__main__":
    main()
