import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import re

# ============ PAGE CONFIG ============
st.set_page_config(page_title="Silal Soil Health Report", layout="wide")

st.markdown("""
<style>
    .big-title {font-size: 36px; font-weight: bold; text-align: center; color: #006400;}
    .subtitle {font-size: 16px; text-align: center; color: #555; font-style: italic;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">Silal Soil Health Report</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Generated from Silal Soil Health Pro</div>', unsafe_allow_html=True)
st.markdown("---")

# ============ CHECK PAYLOAD ============
if "report_payload" not in st.session_state:
    st.error("No report data found. Please go back and click 'Generate Official Soil Health Report' first.")
    st.stop()

payload = st.session_state.report_payload
sample_info = payload.get("sample_info", {})
tables = payload.get("tables", {})
raw_data = payload.get("raw_data", {})

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
st.subheader("Analytical Results")

# Helper to normalize any df-like object
def to_dataframe(df_obj):
    if isinstance(df_obj, pd.DataFrame):
        return df_obj
    elif isinstance(df_obj, list):
        return pd.DataFrame(df_obj)
    elif isinstance(df_obj, dict):
        try:
            return pd.DataFrame(df_obj)
        except Exception:
            try:
                return pd.DataFrame.from_dict(df_obj, orient="index")
            except Exception:
                return pd.DataFrame([df_obj])
    else:
        return pd.DataFrame([{"value": df_obj}])

meta_cols = {"edited_rows", "added_rows", "deleted_rows"}

shown_any_table = False

# (1) لو فى أى جداول مفيدة حقيقيًا نعرضها، لكن نتجاهل الجداول الفاضية / الميتاداتا
if tables:
    for title, df_obj in tables.items():
        df = to_dataframe(df_obj)

        # لو الأعمدة كلها من نوع edited_rows / added_rows / deleted_rows → تجاهل الجدول
        col_set = {str(c) for c in df.columns}
        if col_set and col_set.issubset(meta_cols):
            continue

        # شيل الصفوف الفاضية بالكامل
        df = df.dropna(how="all")
        if df.empty:
            continue

        st.markdown(f"### {title}")
        st.dataframe(df, use_container_width=True)
        st.markdown("---")
        shown_any_table = True

# (2) لو ما فيش جداول مفيدة من فوق، اعرض جدول بكل الـ indicators الموجودة فى raw_data
if raw_data:
    # نحوله لجدول Parameter / Value
    raw_df = pd.DataFrame(list(raw_data.items()), columns=["Parameter", "Value"])
    st.markdown("### Extracted Indicators")
    st.dataframe(raw_df, use_container_width=True)
    st.markdown("---")
    shown_any_table = True

if not shown_any_table:
    st.info("No analytical tables with data were found for this report.")

# ============ SOIL HEALTH SCORE (PILOT) ============

st.subheader("Soil Health Score (pilot)")

# ---- definition of scoring logic ----

def score_ph(value: float) -> int:
    # 5: 6.5–7.0
    # 4: 6.0–6.5 or 7.0–7.5
    # 3: 5.5–6.0 or 7.5–8.0
    # 2: 5.0–5.5 or 8.0–8.5
    # 1: else
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
    # 0–2: 5, 2–4: 4, 4–8: 3, 8–16: 2, >16: 1
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
    # 3–6: 5, 2–3 & 6–8: 4, 1–2:3, 0.5–1:2, else:1
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
    # 0–3:5, 3–6:4, 6–13:3, 13–20:2, >20:1
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
    # 0–3:5, 3–6:4, 6–15:3, 15–25:2, >25:1
    if value <= 3:
        return 5
    if value <= 6:
        return 4
    if value <= 15:
        return 3
    if value <= 25:
        return 2
    return 1

# Specification of indicators we will try to score (can be extended later)
INDICATORS = {
    "ph": {
        "label": "Soil pH (H2O or paste)",
        "unit": "-",
        "weight": 7.0,
        "mandatory": True,
        "score_fn": score_ph,
        "patterns": [re.compile(r"\bpH\b", re.IGNORECASE)],
    },
    "ece": {
        "label": "Electrical Conductivity (ECe)",
        "unit": "dS/m",
        "weight": 6.0,
        "mandatory": True,
        "score_fn": score_ece,
        "patterns": [
            re.compile(r"ECe", re.IGNORECASE),
            re.compile(r"electrical conductivity", re.IGNORECASE),
        ],
    },
    "om": {
        "label": "Organic Matter (OM %)",
        "unit": "%",
        "weight": 8.0,
        "mandatory": True,
        "score_fn": score_om,
        "patterns": [
            re.compile(r"organic matter", re.IGNORECASE),
            re.compile(r"\bOM\b", re.IGNORECASE),
        ],
    },
    "sar": {
        "label": "Sodium Adsorption Ratio (SAR)",
        "unit": "-",
        "weight": 1.0,
        "mandatory": False,
        "score_fn": score_sar,
        "patterns": [re.compile(r"\bSAR\b", re.IGNORECASE)],
    },
    "esp": {
        "label": "Exchangeable Sodium (%) (ESP)",
        "unit": "%",
        "weight": 1.0,
        "mandatory": False,
        "score_fn": score_esp,
        "patterns": [
            re.compile(r"\bESP\b", re.IGNORECASE),
            re.compile(r"exchangeable sodium", re.IGNORECASE),
        ],
    },
}

def extract_first_number(x):
    """Try to get first numeric value from a cell or text."""
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

def extract_indicator_values_from_tables(tables_dict: dict) -> dict:
    """
    Scan all tables and try to extract numeric values for the indicators
    defined in INDICATORS based on pattern matching on the parameter name.
    """
    found = {}

    for _, df_obj in tables_dict.items():
        df = to_dataframe(df_obj)
        if df.empty:
            continue

        df_cols_lower = [str(c).lower() for c in df.columns]
        param_col = None
        value_col = None

        # detect parameter column
        for i, col in enumerate(df_cols_lower):
            if any(k in col for k in ["parameter", "test", "property", "analysis", "description", "item"]):
                param_col = df.columns[i]
                break

        # detect value column
        for i, col in enumerate(df_cols_lower):
            if any(k in col for k in ["result", "value", "reading", "conc", "measurement"]):
                value_col = df.columns[i]
                break

        # fallback: first = parameter, second = value
        if param_col is None and len(df.columns) >= 2:
            param_col = df.columns[0]
        if value_col is None and len(df.columns) >= 2:
            value_col = df.columns[1]

        if param_col is None or value_col is None:
            continue

        for _, row in df.iterrows():
            param_raw = row.get(param_col, "")
            val = extract_first_number(row.get(value_col, ""))
            if val is None:
                continue

            param_text = str(param_raw)
            for key, spec in INDICATORS.items():
                if key in found:
                    continue
                for pat in spec["patterns"]:
                    if pat.search(param_text):
                        found[key] = val
                        break

    return found

def fill_from_raw_data(found: dict, raw: dict) -> dict:
    """
    Fallback: if some indicators not found in tables, try to get them
    from raw_data (st.session_state.extracted copied into report_payload).
    """
    if not isinstance(raw, dict):
        return found

    for key, spec in INDICATORS.items():
        if key in found:
            continue  # already found from tables
        for raw_key, raw_val in raw.items():
            text = str(raw_key)
            for pat in spec["patterns"]:
                if pat.search(text):
                    val = extract_first_number(raw_val)
                    if val is not None:
                        found[key] = val
                        break
            if key in found:
                break
    return found

# ---- Do extraction ----
indicator_values = extract_indicator_values_from_tables(tables)
indicator_values = fill_from_raw_data(indicator_values, raw_data)

if not indicator_values:
    st.info("No matching analytical parameters found yet for the soil health scoring logic.")
else:
    rows = []
    weighted_sum = 0.0
    total_weight_used = 0.0
    missing_mandatory = []

    for key, spec in INDICATORS.items():
        label = spec["label"]
        unit = spec["unit"]
        weight = spec["weight"]
        mandatory = spec["mandatory"]
        value = indicator_values.get(key)

        if value is None:
            score = None
            weighted = None
            if mandatory:
                missing_mandatory.append(label)
        else:
            try:
                score = spec["score_fn"](float(value))
            except Exception:
                score = None
            if score is not None:
                weighted = (score / 5.0) * weight
                weighted_sum += weighted
                total_weight_used += weight
            else:
                weighted = None

        rows.append(
            {
                "Indicator": label,
                "Value": value,
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
            "Some important indicators were not found in the extracted data and were not included in the score:\n\n- "
            + "\n- ".join(missing_mandatory)
        )

    score_df = pd.DataFrame(rows)
    st.dataframe(score_df, use_container_width=True)
# ============ DOWNLOAD AS HTML ============
st.markdown("### Download Report")

if st.button("Download Report as HTML"):
    # Sample info table
    sample_rows = "".join(
        f"<tr><th align='left'>{k}</th><td>{v}</td></tr>"
        for k, v in sample_info.items()
    )

    tables_html_parts = []
    for title, df_obj in tables.items():
        df = to_dataframe(df_obj)
        tables_html_parts.append(f"<h2>{title}</h2>")
        try:
            tables_html_parts.append(df.to_html(index=False, border=1))
        except Exception:
            tables_html_parts.append(df.to_html(border=1))

    tables_html = "\n".join(tables_html_parts)

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
      {tables_html}
    </body>
    </html>
    """

    b64 = base64.b64encode(html.encode("utf-8")).decode()
    filename = f"Silal_Soil_Health_Report_{sample_info.get('report_no', 'sample')}.html"
    st.markdown(
        f'<a href="data:text/html;base64,{b64}" download="{filename}">Click here to download</a>',
        unsafe_allow_html=True,
    )
