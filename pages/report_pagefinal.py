import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import re

# ============ PAGE CONFIG ============
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

# ============ CHECK PAYLOAD ============
if "report_payload" not in st.session_state:
    st.error("No report data found. Please go back and click 'Generate Official Soil Health Report' first.")
    st.stop()

payload = st.session_state.report_payload
sample_info = payload.get("sample_info", {})
raw_data = payload.get("raw_data", {})

# (اختياري) لعينك كده تشوف إيه اللي واصل:
with st.expander("DEBUG – raw_data coming from main page"):
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

# ============ ANALYTICAL RESULTS + OPTIMUM RANGE ============

def extract_first_number(x):
    if x is None:
        return None
    s = str(x)
    m = re.search(r"[-+]?\d*\.?\d+", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None

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

        if spec and num_val is not None and (opt_min is not None or opt_max is not None):
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
        elif spec and num_val is None and opt_range:
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
            return ["background-color: #d4edda"] * len(row)
        if "above" in comment:
            return ["background-color: #f8d7da"] * len(row)
        if "below" in comment:
            return ["background-color: #fff3cd"] * len(row)
        if "no numeric" in comment:
            return ["background-color: #e2e3e5"] * len(row)
        return [""] * len(row)

    styled_df = analytical_df.style.apply(highlight_row, axis=1)
    st.dataframe(styled_df, use_container_width=True)
else:
    analytical_df = pd.DataFrame(columns=["Parameter", "Value", "Unit", "Optimum range", "Comment"])
    st.info("No analytical indicators were found for this report.")

st.markdown("---")

# ============ SOIL HEALTH SCORE (DIRECT MAPPING) ============

st.subheader("Soil Health Score (pilot)")

# --- scoring functions (زي ما عندك) ---
def score_ph(value: float) -> int:
    if 6.5 <= value <= 7.0:
        return 5
    if (6.0 <= value < 6.5) or (7.0 < value <= 7.5):
        return 4
    if (5.5 <= value < 6.0) or (7.5 < value <= 8.0):
        return 3
    if (5.0 <= value < 5.5) or (8.0 < value <= 8.5):
        return 2
    return 1

def score_ece(value: float) -> int:
    if value <= 2:
        return 5
    if value <= 4:
        return 4
    if value <= 8:
        return 3
    if value <= 16:
        return 2
    return 1

def score_om(value: float) -> int:
    if 3 <= value <= 6:
        return 5
    if (2 <= value < 3) or (6 < value <= 8):
        return 4
    if 1 <= value < 2:
        return 3
    if 0.5 <= value < 1:
        return 2
    return 1

def score_sar(value: float) -> int:
    if value <= 3:
        return 5
    if value <= 6:
        return 4
    if value <= 13:
        return 3
    if value <= 20:
        return 2
    return 1

def score_esp(value: float) -> int:
    if value <= 3:
        return 5
    if value <= 6:
        return 4
    if value <= 15:
        return 3
    if value <= 25:
        return 2
    return 1

def score_cec(value: float) -> int:
    if value >= 15:
        return 5
    if value >= 10:
        return 4
    if value >= 5:
        return 3
    if value >= 3:
        return 2
    return 1

def score_p(value: float) -> int:
    if 15 <= value <= 30:
        return 5
    if (10 <= value < 15) or (30 < value <= 40):
        return 4
    if 5 <= value < 10:
        return 3
    if 3 <= value < 5:
        return 2
    return 1

def score_k(value: float) -> int:
    if 120 <= value <= 200:
        return 5
    if (80 <= value < 120) or (200 < value <= 250):
        return 4
    if 60 <= value < 80:
        return 3
    if 40 <= value < 60:
        return 2
    return 1

def score_ca(value: float) -> int:
    if 1000 <= value <= 2000:
        return 5
    if (800 <= value < 1000) or (2000 < value <= 2500):
        return 4
    if 600 <= value < 800:
        return 3
    if 400 <= value < 600:
        return 2
    return 1

def score_mg(value: float) -> int:
    if 120 <= value <= 240:
        return 5
    if (80 <= value < 120) or (240 < value <= 300):
        return 4
    if 60 <= value < 80:
        return 3
    if 40 <= value < 60:
        return 2
    return 1

def score_s(value: float) -> int:
    if 10 <= value <= 20:
        return 5
    if (7 <= value < 10) or (20 < value <= 30):
        return 4
    if 5 <= value < 7:
        return 3
    if 3 <= value < 5:
        return 2
    return 1

def score_fe(value: float) -> int:
    if value > 6:
        return 5
    if value >= 4.5:
        return 4
    if value >= 3:
        return 3
    if value >= 1:
        return 2
    return 1

def score_zn(value: float) -> int:
    if value > 1.5:
        return 5
    if value >= 1:
        return 4
    if value >= 0.7:
        return 3
    if value >= 0.5:
        return 2
    return 1

def score_cu(value: float) -> int:
    if value > 0.8:
        return 5
    if value >= 0.5:
        return 4
    if value >= 0.3:
        return 3
    if value >= 0.1:
        return 2
    return 1

def score_mn(value: float) -> int:
    if value > 8:
        return 5
    if value >= 5:
        return 4
    if value >= 3:
        return 3
    if value >= 1:
        return 2
    return 1

def score_b(value: float) -> int:
    if 0.5 <= value <= 1.0:
        return 5
    if (0.3 <= value < 0.5) or (1.0 < value <= 1.5):
        return 4
    if 0.2 <= value < 0.3:
        return 3
    if 0.1 <= value < 0.2:
        return 2
    return 1

# mapping between parameter names in raw_data and indicator keys
PARAM_TO_INDICATOR = {
    "pH (paste extract)":       ("ph", score_ph, "-",        7.0,  True),
    "ECe":                      ("ece", score_ece, "dS/m",   6.0,  True),
    "Organic Matter":           ("om",  score_om,  "%",      8.0,  True),
    "SAR":                      ("sar", score_sar, "-",      1.0,  True),
    "ESP":                      ("esp", score_esp, "%",      1.0,  True),
    "CEC":                      ("cec", score_cec, "cmolc/kg",4.0, False),
    "Available Phosphorus (P)": ("p_avail", score_p,  "mg/kg",2.0, False),
    "Available Potassium (K)":  ("k_avail", score_k,  "mg/kg",2.0, False),
    "Exchangeable Calcium":     ("ca_exch", score_ca, "ppm", 1.0,  False),
    "Exchangeable Magnesium":   ("mg_exch", score_mg, "ppm", 1.0,  False),
    "Available Sulfur (S)":     ("s_avail", score_s,  "mg/kg",1.0, False),
    "Iron (Fe)":                ("fe",      score_fe, "mg/kg",1.0, False),
    "Zinc (Zn)":                ("zn",      score_zn, "mg/kg",0.5, False),
    "Copper (Cu)":              ("cu",      score_cu, "mg/kg",0.5, False),
    "Manganese (Mn)":           ("mn",      score_mn, "mg/kg",0.5, False),
    "Boron (B)":                ("b",       score_b,  "mg/kg",0.5, False),
}

rows_score = []
weighted_sum = 0.0
total_weight_used = 0.0
missing_mandatory = []

for pname, meta in PARAM_TO_INDICATOR.items():
    ind_key, score_fn, unit, weight, mandatory = meta
    raw_val = raw_data.get(pname, None)
    num_val = extract_first_number(raw_val)

    if num_val is None:
        score = None
        weighted = None
        if mandatory:
            missing_mandatory.append(pname)
    else:
        try:
            score = score_fn(float(num_val))
        except Exception:
            score = None
        if score is not None:
            weighted = (score / 5.0) * weight
            weighted_sum += weighted
            total_weight_used += weight
        else:
            weighted = None

    rows_score.append(
        {
            "Indicator": pname,
            "Value": num_val,
            "Unit": unit,
            "Score (0–5)": score,
            "Weight": weight,
            "Weighted score": weighted,
            "Mandatory": "Yes" if mandatory else "No",
        }
    )

if total_weight_used > 0:
    overall_score = (weighted_sum / total_weight_used) * 100.0
else:
    overall_score = None

if overall_score is not None:
    st.metric("Overall Soil Health Score (pilot, 0–100)", f"{overall_score:.1f}")
else:
    st.info("Unable to compute soil health score – no usable parameters found.")

if missing_mandatory:
    st.warning(
        "Some important indicators were not found or have no numeric value:\n\n- "
        + "\n- ".join(missing_mandatory)
    )

score_df = pd.DataFrame(rows_score)
st.dataframe(score_df, use_container_width=True)

st.markdown("---")

# ============ DOWNLOAD AS HTML ============
st.markdown("### Download Report")

if st.button("Download Report as HTML"):
    sample_rows = "".join(
        f"<tr><th align='left'>{k}</th><td>{v}</td></tr>" for k, v in sample_info.items()
    )

    if not analytical_df.empty:
        html_df = analytical_df.to_html(index=False, border=1)
    else:
        html_df = "<p>No analytical indicators found.</p>"

    html = f"""
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

    b64 = base64.b64encode(html.encode("utf-8")).decode()
    filename = f"Silal_Soil_Health_Report_{sample_info.get('report_no', 'sample')}.html"
    st.markdown(
        f'<a href="data:text/html;base64,{b64}" download="{filename}">Click here to download</a>',
        unsafe_allow_html=True,
    )
