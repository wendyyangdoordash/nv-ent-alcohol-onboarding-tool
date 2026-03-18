# Alcohol Onboarding Bulk Tools

Internal tool for DoorDash employees: collect onboarding inputs and generate 5 CSVs for bulk tools upload.

## Setup

```bash
cd alcohol-onboarding-tool
pip install -r requirements.txt
```

**One-time: install browser for automatic uploads**

If you want to use **Upload to bulk tools** (browser automation), run once:

```bash
playwright install chromium
```

## Run locally

```bash
streamlit run app.py
```

Open the URL shown in the terminal (usually http://localhost:8501).

## Usage

1. Fill out the landing form (address, phone, email, legal rep info).
2. For each variable field (Legal Business Name, EIN, Routing #, Account #), choose whether it's the same for all stores or per-store. If per-store, upload a CSV with `store_id` and the corresponding column.
3. Upload your store list CSV with columns `store_id` and `business_id`.
4. Click **Generate CSVs**.
5. Either:
   - **Download** each of the 5 CSVs and upload manually via the bulk tool links, or
   - Click **Upload to bulk tools** to open a browser and upload all 5 files automatically (log in with SSO when the first page opens if prompted).

## Files

- `app.py` — Streamlit app (form + CSV generation).
- `requirements.txt` — Python dependencies.

All generated CSVs use exact bulk tool column names and preserve leading zeros (plain text).
