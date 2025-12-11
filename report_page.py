import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import re

st.set_page_config(page_title="Silal Soil Health Report", layout="wide")

st.markdown(
    """
<style>
    .big-title {
        font-size: 36px;
        font-weight: bold;
        text-align: center;
        color: #006400;
    }
    .subtitle {
        font-size: 16px;
        text-align: center;
        color: #555;
        font-style: italic;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="big-title">Silal Soil Health Report</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Generated from Silal Soil Health Pro</div>', unsafe_allow_html=True)
st.markdown("---")

if "report_payload" not in st.session_state:
    st.error("No report data found. Please go back and click 'Generate Official Soil Health Report' first.")
    st.stop()

payload = st.session_state.report_payload
sample_info = payload.get("sample_info", {})
raw_data = payload.get("raw_data", {})

# (اختياري) Debug
with st.expander("DEBUG – raw_data received"):
    st.json(raw_data)

# ============ SAMPLE INFO ============

st.subheader("Sample Information")

col1, col2 = st.columns(2)
with col1:
    st.write("**Customer Name:**", sample_info.get("customer", ""))
    st.write("**Test Report No.:**", sample_info.get("report_no", ""))
    st.write("**Customer Sample Reference:**", sample_info.get("sample_ref", ""))
    st.write("**Sample Description:**", sample_info.get("description", ""))
with col2:
    st.write("**Purchase Order Number:**", sample_info.get("po_number", ""))
    st.write("**Received On:**", sample_info.get("received", ""))
    st.write("**Analyzed On:**", sample_info.get("analyzed", ""))
    st.write("**Site:**", sample_info.get("site", ""))

st.caption(f"Report generated on {datetime.now():%Y-%m-%d %H:%M}")
st.markdown("---")

# ============ ANALYTICAL RESULTS ============

def extract_first_number(x):
    if x is None:
        return None
    s = str(x)
    if s.lower() == "not analyzed":
        return None
    m = re.search(r"[-+]?\d*\.?\d+", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None

# Optimum ranges
PARAM_SPECS = {
    "pH (paste extract)":       {"unit": "-",        "opt_min": 6.0,   "opt_max": 7.5},
    "ECe":                      {"unit": "dS/m",     "opt_min": 0.0,   "opt_max": 2.0},
    "Organic Matter":           {"unit": "%",        "opt_min": 3.0,   "opt_max": 6.0},
    "SAR":                      {"unit": "-",        "opt_min": 0.0,   "opt_max": 6.0},
    "ESP":                      {"unit": "%",        "opt_min": 0.0,   "opt_max": 6.0},
    "CEC":                      {"unit": "cmolc/kg", "opt_min": 10.0,  "opt_max": None},
    "Available Phosphorus (P)": {"unit": "mg/kg",    "opt_min": 15.0,  "opt_max": 30.0},
    "Available Potassium (K)":  {"unit": "mg/kg",    "opt_min": 100.0, "opt_max": 200.0},
    "Exchangeable Calcium":     {"unit": "ppm",      "opt_min": 1000.0,"opt_max": 2000.0},
    "Exchangeable Magnesium":   {"unit": "ppm",      "opt_min": 120.0, "opt_max": 240.0},
    "Available Sulfur (S)":     {"unit": "mg/kg",    "opt_min": 10.0,  "opt_max": 20.0},
    "Iron (Fe)":                {"unit": "mg/kg",    "opt_min": 4.5,   "opt_max": None},
    "Zinc (Zn)":                {"unit": "mg/kg",    "opt_min": 1.0,   "opt_max": None},
    "Copper (Cu)":              {"unit": "mg/kg",    "opt_min": 0.5,   "opt_max": None},
    "Manganese (Mn)":           {"unit": "mg/kg",    "opt_min": 5.0,   "opt_max": None},
    "Boron (B)":                {"unit": "mg/kg",    "opt_min": 0.5,   "opt_max": 1.0},
}

def format_range(opt_min, opt_max):
    if opt_min is None and opt_max is None:
        return ""
    if opt_min is not None and opt_max is not None:
        return f"{opt_min}–{opt_max}"
    if opt_min is not None:
        return f"≥ {opt_min}"
    return f"≤ {opt_max}"

st.subheader("Analytical Results")

rows = []

if isinstance(raw_data, dict) and raw_data:
    for key, val in raw_data.items():
        value_str = val
        num_val = extract_first_number(val)

        spec = PARAM_SPECS.get(key, None)
        unit = spec["unit"] if spec else ""
        opt_min = spec["opt_min"] if spec else None
        opt_max = spec["opt_max"] if spec else None
        opt_range = format_range(opt_min, opt_max) if spec else ""
        comment = ""

        if str(val).lower() == "not analyzed":
            comment = "Not analyzed"
        elif spec and num_val is not None and (opt_min is not None or opt_max is not None):
            if opt_min is not None and opt_max is not None:
                if opt_min <= num_val <= opt_max:
                    comment = "Within optimum range"
                elif num_val < opt_min:
                    comment = "Below optimum range"
                else:
                    comment = "Above optimum range"
            elif opt_min is not None:
                if num_val >= opt_min:
                    comment = "Within / above optimum range"
                else:
                    comment = "Below optimum range"
            elif opt_max is not None:
                if num_val <= opt_max:
                    comment = "Within / below optimum range"
                else:
                    comment = "Above optimum range"
        elif spec and num_val is None and opt_range and comment == "":
            comment = "No numeric value"

        rows.append(
            {
                "Parameter": key,
                "Value": value_str,
                "Unit": unit,
                "Optimum range": opt_range,
                "Comment": comment,
            }
        )

    analytical_df = pd.DataFrame(rows)

    def highlight_row(row):
        comment = str(row.get("Comment", "")).lower()
        if "within optimum" in comment:
            return ["background-color: #d4edda"] * len(row)   # green
        if "above" in comment:
            return ["background-color: #f8d7da"] * len(row)   # red
        if "below" in comment:
            return ["background-color: #fff3cd"] * len(row)   # orange
        if "not analyzed" in comment or "no numeric" in comment:
            return ["background-color: #e2e3e5"] * len(row)   # grey
        return [""] * len(row)

    styled_df = analytical_df.style.apply(highlight_row, axis=1)
    st.dataframe(styled_df, use_container_width=True)
else:
    analytical_df = pd.DataFrame(columns=["Parameter", "Value", "Unit", "Optimum range", "Comment"])
    st.info("No analytical indicators were found for this report.")

st.markdown("---")

# ============ BUTTON TO GO TO SOIL SCORE CARD ============

if st.button("Generate Soil Health Score Card", type="primary", use_container_width=True):
    st.switch_page("pages/soil_score_card.py")

st.markdown("---")

st.markdown("### Download Report")

# تجهيز صفوف معلومات العينة
sample_rows = "".join(
    f"<tr><th align='left'>{k}</th><td>{v}</td></tr>" for k, v in sample_info.items()
)

# استخدام الجدول الملوّن نفسه في الـ HTML
if isinstance(raw_data, dict) and not analytical_df.empty:
    html_df = styled_df.to_html()
else:
    html_df = "<p>No analytical indicators found.</p>"

report_html = f"""
<html>
<head>
  <meta charset="UTF-8">
  <title>Silal Soil Health Report</title>
</head>
<body style="font-family:Arial, sans-serif; margin:40px">
  <h1 style="color:#006400; text-align:center;">Silal Soil Health Report</h1>
  <p style="text-align:center;">Generated on {datetime.now():%Y-%m-%d %H:%M}</p>
  <hr>
  <h2>Sample Information</h2>
  <table border="1" cellspacing="0" cellpadding="4">
    {sample_rows}
  </table>
  <hr>
  <h2>Analytical Indicators</h2>
  {html_df}
</body>
</html>
"""

filename = f"Silal_Soil_Health_Report_{sample_info.get('report_no', 'sample')}.html"

st.download_button(
    label="⬇️ Download Report as HTML",
    data=report_html,
    file_name=filename,
    mime="text/html",
)
