import streamlit as st
import json
import base64
import pandas as pd
import re
import os
from openai import OpenAI
from dotenv import load_dotenv
import streamlit.components.v1 as components  # ✅ لطباعة الصفحة

load_dotenv()

# =============== OpenAI client ===============
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="Soil Health Score Card", layout="wide")

# =============== Header with logos ===============
logo_col1, title_col, logo_col2 = st.columns([1, 3, 1])

with logo_col1:
    st.image("Silal_logo.jpeg", width=120)

with title_col:
    st.markdown(
        """
        <div style="text-align:center;">
            <h1 style="color:#006400; margin-bottom:0;">Silal Soil Health Report</h1>
            <p style="color:#555; font-style:italic; margin-top:0;">
                Generated from Silal Soil Health Pro
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with logo_col2:
    st.image("IO_logo.png", width=120)

st.markdown("---")
st.markdown(
    """
<style>
    .big-title {
        font-size: 32px;
        font-weight: bold;
        text-align: center;
        color: #006400;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="big-title">Soil Health Score Card</div>', unsafe_allow_html=True)
st.markdown("---")

# =============== Get payload from main page ===============
if "report_payload" not in st.session_state:
    st.error("No report data found. Please generate the main report first.")
    st.stop()

payload = st.session_state.report_payload
raw_data = payload.get("raw_data", {})
sample_info = payload.get("sample_info", {})

# =====================================================
#  Helper: extract numeric value from raw string
# =====================================================
def extract_first_number(x):
    if x is None:
        return None
    s = str(x)
    if s.strip() == "":
        return None
    if s.lower() in ["not analyzed", "not analysed", "na", "n/a"]:
        return None
    m = re.search(r"[-+]?\d*\.?\d+", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None

# =====================================================
#  Scoring functions
# =====================================================

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

# Mapping between parameter labels from report and scoring
PARAM_TO_INDICATOR = {
    "pH (paste extract)":       ("pH",       score_ph, "-",        7.0,  True),
    "ECe":                      ("ECe",      score_ece,"dS/m",     6.0,  True),
    "Organic Matter":           ("OM",       score_om, "%",        8.0,  True),
    "SAR":                      ("SAR",      score_sar,"-",        1.0,  True),
    "ESP":                      ("ESP",      score_esp,"%",        1.0,  False),
    "CEC":                      ("CEC",      score_cec,"cmolc/kg", 4.0,  False),
    "Available Phosphorus (P)": ("Avail P",  score_p,  "mg/kg",    2.0,  True),
    "Available Potassium (K)":  ("Avail K",  score_k,  "mg/kg",    2.0,  True),
    "Iron (Fe)":                ("Fe",       score_fe, "mg/kg",    1.0,  False),
    "Zinc (Zn)":                ("Zn",       score_zn, "mg/kg",    0.5,  False),
    "Copper (Cu)":              ("Cu",       score_cu, "mg/kg",    0.5,  False),
    "Manganese (Mn)":           ("Mn",       score_mn, "mg/kg",    0.5,  False),
    "Boron (B)":                ("B",        score_b,  "mg/kg",    0.5,  False),
}

# =====================================================
#  Build scoring table
# =====================================================

rows = []
weighted_sum = 0.0
total_weight_used = 0.0
missing_mandatory = []

for label, meta in PARAM_TO_INDICATOR.items():
    ind_name, score_fn, unit, weight, mandatory = meta
    raw_val = raw_data.get(label, None)
    num_val = extract_first_number(raw_val)

    if num_val is None:
        score = None
        weighted = None
        if mandatory:
            missing_mandatory.append(label)
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

    rows.append(
        {
            "Indicator": ind_name,
            "Parameter (report label)": label,
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

# ===== Centered, large overall score =====
if overall_score is not None:
    st.markdown(
        f"""
        <div style="text-align:center; margin-top:10px; margin-bottom:5px;">
          <span style="font-size:46px; font-weight:bold; color:#006400;">
            {overall_score:.1f}
          </span>
          <span style="font-size:22px; color:#555;"> / 100</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ===== Graphical bar from green to red =====
    st.markdown(
        """
        <style>
        .score-container {
            margin-top: 0.3rem;
            margin-bottom: 1rem;
        }
        .score-bar-bg {
            width: 100%;
            height: 22px;
            border-radius: 999px;
            background: linear-gradient(90deg, #2e7d32, #f9a825, #c62828); /* green → yellow → red */
            position: relative;
            overflow: hidden;
        }
        .score-bar-mask {
            position: absolute;
            top: 0;
            right: 0;
            height: 100%;
            background: rgba(255,255,255,0.7);
        }
        .score-label {
            margin-top: 0.25rem;
            font-size: 0.8rem;
            color: #555;
            display: flex;
            justify-content: space-between;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="score-container">
          <div class="score-bar-bg">
            <div class="score-bar-mask" style="width:{100 - overall_score:.1f}%;"></div>
          </div>
          <div class="score-label">
            <span>0 (Poor)</span>
            <span>{overall_score:.1f}</span>
            <span>100 (Excellent)</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.info("Unable to compute soil health score – no usable parameters found.")

if missing_mandatory:
    st.warning(
        "Some mandatory indicators are missing or not analyzed:\n\n- "
        + "\n- ".join(missing_mandatory)
    )

score_df = pd.DataFrame(rows)
st.dataframe(score_df, width="stretch")

st.markdown("---")

# =====================================================
#  AI Bilingual Recommendations (HTML table, wrapped)
# =====================================================

st.subheader("Soil Management Recommendations / التوصيات الذكية لإدارة التربة")
st.caption(
    "Automatically generated, bilingual, and tailored to UAE sandy soils / "
    "توصيات ثنائية اللغة ومصممة لظروف التربة الرملية في دولة الإمارات."
)

components_list = [
    "Overall interpretation",
    "Key soil constraints",
    "Vegetables",
    "Field crops",
    "Fruit trees",
    "Short-term actions",
    "Long-term actions",
]

def build_ai_context(raw_data: dict, overall_score: float | None) -> str:
    lines = []
    lines.append("Soil analysis summary (parameters with values):")

    for k, v in raw_data.items():
        if v and str(v).strip().lower() not in [
            "not analyzed",
            "not analysed",
            "غير محللة",
            "غير مُحلَّلة",
            "na",
            "n/a",
        ]:
            lines.append(f"- {k}: {v}")

    if overall_score is not None:
        lines.append(f"\nCalculated Soil Health Score (0–100): {overall_score:.1f}")

    lines.append("\nSite context:")
    lines.append("- Country: United Arab Emirates (UAE).")
    lines.append("- Climate: Arid, hot, high evaporative demand, risk of salinity build-up.")
    lines.append("- Typical soils: Sandy, very low organic matter, low CEC, often calcareous.")
    lines.append("- Irrigation water may be saline or marginal in quality.")
    lines.append("- Biochar is NOT to be recommended (not commercially available locally).")
    lines.append("- Focus on compost, manures, green waste compost, gypsum, elemental sulfur, balanced mineral fertilizers, and micronutrients.")
    return "\n".join(lines)

context = build_ai_context(raw_data, overall_score)

SYSTEM_PROMPT_JSON = """
You are an expert soil fertility and crop nutrition specialist working in arid, sandy soils of the UAE.

You will receive:
- Soil test data (pH, ECe, OM, SAR, ESP, CEC, texture, macro- and micronutrients, etc.).
- A soil health score (0–100).

You MUST return ONLY valid JSON (no markdown, no commentary, no code fences) with the following structure:

{
  "Overall interpretation": {
    "en": "...",
    "ar": "..."
  },
  "Key soil constraints": {
    "en": "...",
    "ar": "..."
  },
  "Vegetables": {
    "en": "...",
    "ar": "..."
  },
  "Field crops": {
    "en": "...",
    "ar": "..."
  },
  "Fruit trees": {
    "en": "...",
    "ar": "..."
  },
  "Short-term actions": {
    "en": "...",
    "ar": "..."
  },
  "Long-term actions": {
    "en": "...",
    "ar": "..."
  }
}

RULES:
1. Each "en" value: 3–6 concise bullet-like sentences separated by line breaks.
2. Each "ar" value: Modern Standard Arabic, accurate translation of the same ideas, also 3–6 bullet-like sentences separated by line breaks.
3. NO English words inside the Arabic text; NO Arabic words inside the English text.
4. DO NOT mention biochar at all.
5. Use realistic, literature-based soil test target ranges for vegetables, field crops, and fruit trees in calcareous, sandy soils.
6. Explicitly account for salinity, sodicity, low OM, low CEC, high pH and bicarbonate.
7. Distinguish between vegetables, field crops, and fruit trees under UAE conditions.
8. Focus on compost, manures, green waste compost, gypsum, elemental sulfur, micronutrients, foliar sprays, optimized fertigation.
9. NO specific kg/ha fertilizer rates.
"""

@st.cache_data(show_spinner="Generating bilingual AI recommendations...", ttl=3600)
def generate_bilingual_json(context: str) -> dict:
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.25,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_JSON},
            {"role": "user", "content": context},
        ],
    )
    content = resp.choices[0].message.content
    return json.loads(content)

def html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

try:
    ai_json = generate_bilingual_json(context)

    table_html = """
<style>
.soil-reco-table {
  width: 100%;
  border-collapse: collapse;
}
.soil-reco-table th, .soil-reco-table td {
  border: 1px solid #ddd;
  padding: 0.6rem;
  vertical-align: top;
  font-size: 0.9rem;
}
.soil-reco-table th {
  background-color: #f5f5f5;
  text-align: center;
}
.soil-reco-comp {
  width: 12rem;
  white-space: nowrap;
}
.soil-reco-en {
  text-align: left;
  direction: ltr;
  white-space: pre-wrap;
}
.soil-reco-ar {
  text-align: right;
  direction: rtl;
  white-space: pre-wrap;
}
</style>
<table class="soil-reco-table">
  <tr>
    <th>Component</th>
    <th>Summary / Recommendations</th>
    <th>الخلاصة والتوصيات</th>
  </tr>
"""
    for comp in components_list:
        block = ai_json.get(comp, {})
        en = html_escape(block.get("en", "").strip())
        ar = html_escape(block.get("ar", "").strip())
        table_html += f"""
  <tr>
    <td class="soil-reco-comp">{html_escape(comp)}</td>
    <td class="soil-reco-en">{en}</td>
    <td class="soil-reco-ar">{ar}</td>
  </tr>
"""
    table_html += "</table>"

    st.markdown(table_html, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error while generating AI recommendations: {e}")

# =====================================================
#  Fertilizer requirement: element kg/ha
# =====================================================

st.markdown("---")
st.subheader("Fertilizer Requirements (kg/ha of nutrient) / احتياجات التسميد (كجم عنصر/هكتار)")

crop_group = st.selectbox(
    "Select crop group / اختر المجموعة المحصولية",
    ["Vegetables", "Field crops", "Fruit trees"],
)

col_depth, col_bd = st.columns(2)
with col_depth:
    depth_m = st.number_input(
        "Rooting depth used for calculation (m) / عمق الجذور المستخدم في الحساب (متر)",
        min_value=0.1,
        max_value=1.0,
        value=0.3,
        step=0.05,
    )
with col_bd:
    bulk_density = st.number_input(
        "Bulk density (t/m³) / الكثافة الظاهرية (طن/م³)",
        min_value=1.2,
        max_value=1.8,
        value=1.5,
        step=0.05,
    )

soil_mass_t_ha = 10000 * depth_m * bulk_density

TARGET_LEVELS = {
    "Vegetables": {
        "N":  25,
        "P":  20,
        "K":  150,
        "Ca": 2000,
        "Mg": 200,
        "S":  15,
        "Fe": 5,
        "Zn": 1.5,
        "Cu": 0.6,
        "Mn": 3,
        "B":  0.7,
    },
    "Field crops": {
        "N":  20,
        "P":  15,
        "K":  120,
        "Ca": 2000,
        "Mg": 180,
        "S":  12,
        "Fe": 4,
        "Zn": 1.0,
        "Cu": 0.4,
        "Mn": 2.5,
        "B":  0.6,
    },
    "Fruit trees": {
        "N":  20,
        "P":  18,
        "K":  160,
        "Ca": 2500,
        "Mg": 220,
        "S":  15,
        "Fe": 5,
        "Zn": 1.5,
        "Cu": 0.6,
        "Mn": 3,
        "B":  0.7,
    },
}

EFFICIENCY = {
    "N":  0.30,
    "P":  0.25,
    "K":  0.60,
    "Ca": 0.50,
    "Mg": 0.50,
    "S":  0.50,
    "Fe": 0.40,
    "Zn": 0.40,
    "Cu": 0.40,
    "Mn": 0.40,
    "B":  0.40,
}

ELEMENT_MAP = {
    "N":  "Available Nitrogen (N)",
    "P":  "Available Phosphorus (P)",
    "K":  "Available Potassium (K)",
    "Ca": "Exchangeable Calcium",
    "Mg": "Exchangeable Magnesium",
    "S":  "Available Sulfur (S)",
    "Fe": "Iron (Fe)",
    "Zn": "Zinc (Zn)",
    "Cu": "Copper (Cu)",
    "Mn": "Manganese (Mn)",
    "B":  "Boron (B)",
}

def extract_first_number_safe(v):
    if v is None:
        return None
    s = str(v).strip()
    if s.lower() in ["", "not analyzed", "not analysed", "na", "n/a"]:
        return None
    m = re.search(r"[-+]?\d*\.?\d+", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None

rows_fert = []
targets = TARGET_LEVELS[crop_group]

for elem, target in targets.items():
    data_key = ELEMENT_MAP.get(elem)
    if not data_key:
        continue

    measured = extract_first_number_safe(raw_data.get(data_key))
    if measured is None:
        deficit = None
        elem_kg_ha = None
    else:
        deficit = max(target - measured, 0)
        if deficit <= 0:
            elem_kg_ha = 0.0
        else:
            E = EFFICIENCY.get(elem, 0.4)
            elem_kg_ha = (deficit * soil_mass_t_ha) / (1000 * E)

    rows_fert.append(
        {
            "Element": elem,
            "Soil parameter": data_key,
            "Measured (mg/kg)": measured,
            "Target (mg/kg)": target,
            "Deficit (mg/kg)": deficit,
            "Required nutrient (kg/ha)": None if elem_kg_ha is None else round(elem_kg_ha, 1),
        }
    )

fert_df = pd.DataFrame(rows_fert)
st.dataframe(fert_df, width="stretch")

st.caption(
    "Note: 'Required nutrient (kg/ha)' refers to pure element. To convert to a specific "
    "fertilizer product, divide by the nutrient fraction.  \n"
    "ملحوظة: القيم بالكجم/هكتار تمثل العنصر الخالص، وللتحويل إلى سماد تجاري يتم القسمة على "
    "نسبة العنصر في السماد."
)

# =====================================================
#  Convert nutrient kg/ha → fertilizer products
# =====================================================

st.markdown("---")
st.subheader("Fertilizer Products (kg/ha) / كميات الأسمدة التجارية (كجم/هكتار)")

FERTILIZER_PRODUCTS = {
    "Urea (46% N)":                     ("N", 0.46),
    "Ammonium nitrate (34% N)":         ("N", 0.34),
    "DAP 18-46-0 (P as P)":             ("P", 0.20),
    "MAP 12-61-0 (P as P)":             ("P", 0.27),
    "MOP 0-0-60 (K as K)":              ("K", 0.50),
    "SOP 0-0-50 (K as K)":              ("K", 0.42),
    "Gypsum (23% Ca, 18% S)":           ("Ca", 0.23),
    "Calcium nitrate (19% Ca)":         ("Ca", 0.19),
    "Kieserite (16% Mg, 13% S)":        ("Mg", 0.16),
    "Magnesium sulfate heptahydrate":   ("Mg", 0.10),
    "Ferrous sulfate (20% Fe)":         ("Fe", 0.20),
    "Zinc sulfate (35% Zn)":            ("Zn", 0.35),
    "Copper sulfate (25% Cu)":          ("Cu", 0.25),
    "Manganese sulfate (30% Mn)":       ("Mn", 0.30),
    "Borax (11% B)":                    ("B", 0.11),
}

product_rows = []

for fert_name, (elem, frac) in FERTILIZER_PRODUCTS.items():
    row_match = next((r for r in rows_fert if r["Element"] == elem), None)
    if row_match is None:
        continue

    nutrient_kg = row_match["Required nutrient (kg/ha)"]
    if nutrient_kg is None:
        fert_kg = None
    else:
        fert_kg = 0.0 if nutrient_kg == 0 else round(nutrient_kg / frac, 1)

    product_rows.append(
        {
            "Fertilizer product": fert_name,
            "Main element": elem,
            "Nutrient fraction": frac,
            "Required nutrient (kg/ha)": nutrient_kg,
            "Required fertilizer (kg/ha)": fert_kg,
        }
    )

products_df = pd.DataFrame(product_rows)
st.dataframe(products_df, width="stretch")

# =====================================================
#  FINAL HTML REPORT + DOWNLOAD BUTTON
# =====================================================

st.markdown("---")
st.subheader("⬇️ Download Final Soil Health Report / تحميل التقرير النهائي")

# 1) تحويل الجداول إلى HTML بسيط
score_table_html = score_df.to_html(index=False)
fert_table_html = fert_df.to_html(index=False)
products_table_html = products_df.to_html(index=False)

# 2) تمثيل بياني للسكور (نفس اللي في الصفحة)
if overall_score is not None:
    score_bar_html = f"""
    <div style="margin-top:5px; margin-bottom:10px;">
      <div style="
            width:100%;
            height:22px;
            border-radius:999px;
            background:linear-gradient(90deg,#2e7d32,#f9a825,#c62828);
            position:relative;
            overflow:hidden;
        ">
        <div style="
              position:absolute;
              top:0;
              right:0;
              height:100%;
              width:{100 - overall_score:.1f}%;
              background:rgba(255,255,255,0.7);
        "></div>
      </div>
      <div style="
            margin-top:3px;
            font-size:0.8rem;
            color:#555;
            display:flex;
            justify-content:space-between;
        ">
        <span>0 (Poor)</span>
        <span>{overall_score:.1f}</span>
        <span>100 (Excellent)</span>
      </div>
    </div>
    """
    score_str = f"{overall_score:.1f}"
else:
    score_bar_html = "<p>No soil health score calculated.</p>"
    score_str = "N/A"

# 3) HTML كامل للتقرير (مبسّط)
report_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Silal Soil Health Report</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      font-size: 12px;
      margin: 20px;
      color: #222;
    }}
    h1 {{
      color:#006400;
      font-size:22px;
      text-align:center;
      margin-bottom:4px;
    }}
    h2 {{
      color:#006400;
      margin-top:18px;
      margin-bottom:6px;
      font-size:16px;
    }}
    .score-center {{
      text-align:center;
      margin-top:10px;
      margin-bottom:5px;
    }}
    .score-center .main {{
      font-size:40px;
      font-weight:bold;
      color:#006400;
    }}
    .score-center .sub {{
      font-size:20px;
      color:#555;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      margin-bottom: 12px;
    }}
    table, th, td {{
      border: 1px solid #ccc;
    }}
    th, td {{
      padding: 4px 6px;
      font-size: 11px;
    }}
  </style>
</head>
<body>

  <h1>Silal Soil Health Report</h1>

  <h2>Soil Health Score</h2>
  <div class="score-center">
    <span class="main">{score_str}</span>
    <span class="sub"> / 100</span>
  </div>
  {score_bar_html}

  <h2>Analysis Results</h2>
  {score_table_html}

  <h2>AI Soil Management Recommendations / التوصيات الذكية لإدارة التربة</h2>
  {table_html}

  <h2>Fertilizer Requirements (kg/ha of nutrient)</h2>
  {fert_table_html}

  <h2>Fertilizer Products (kg/ha)</h2>
  {products_table_html}

</body>
</html>
"""

# 4) زر تحميل التقرير (HTML)
st.download_button(
    label="⬇️ Download Final Report (HTML) / تحميل التقرير النهائي",
    data=report_html,
    file_name="Silal_Soil_Health_Report.html",
    mime="text/html",
)
