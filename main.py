import streamlit as st
from datetime import datetime
import re
from pypdf import PdfReader

st.set_page_config(page_title="Silal Soil Health Pro", layout="centered")
# ==== HEADER WITH LOGOS ====
logo_col1, title_col, logo_col2 = st.columns([1, 3, 1])

with logo_col1:
    st.image("Silal_logo.jpeg", width=120)   # عدّل الاسم لو مختلف

with title_col:
    st.markdown(
        """
        <div style="text-align:center;">
            <h1 style="color:#006400; margin-bottom:0;">Silal Soil Health Pro</h1>
            <p style="color:#555; font-style:italic; margin-top:0;">
                Soil Health Assessment • Dr. Ahmed H. El-Naggar • 2025
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with logo_col2:
    st.image("IO_logo.png", width=120)       # عدّل الاسم لو مختلف



# ============== MASTER PARAMETER DEFINITIONS ==============

PARAMS = [
    # --- Basic soil properties ---
    {"key": "ph",        "label": "pH (paste extract)",        "unit": "-",        "section": "Basic Soil Properties"},
    {"key": "ece",       "label": "ECe",                       "unit": "dS/m",     "section": "Basic Soil Properties"},
    {"key": "om",        "label": "Organic Matter",            "unit": "%",        "section": "Basic Soil Properties"},
    {"key": "sar",       "label": "SAR",                       "unit": "-",        "section": "Basic Soil Properties"},
    {"key": "esp",       "label": "ESP",                       "unit": "%",        "section": "Basic Soil Properties"},
    {"key": "cec",       "label": "CEC",                       "unit": "cmolc/kg", "section": "Basic Soil Properties"},
    {"key": "caco3",     "label": "CaCO₃",                     "unit": "%",        "section": "Basic Soil Properties"},
    {"key": "sat_pct",   "label": "Saturation Percentage",     "unit": "%",        "section": "Basic Soil Properties"},
    {"key": "texture",   "label": "Soil Texture Class",        "unit": "",         "section": "Basic Soil Properties"},

    # --- Soluble ions ---
    {"key": "sol_ca",    "label": "Soluble Calcium (Ca²⁺)",    "unit": "ppm",      "section": "Soluble Ions"},
    {"key": "sol_mg",    "label": "Soluble Magnesium (Mg²⁺)",  "unit": "ppm",      "section": "Soluble Ions"},
    {"key": "sol_na",    "label": "Soluble Sodium (Na⁺)",      "unit": "ppm",      "section": "Soluble Ions"},
    {"key": "sol_k",     "label": "Soluble Potassium (K⁺)",    "unit": "ppm",      "section": "Soluble Ions"},
    {"key": "sol_cl",    "label": "Soluble Chloride (Cl⁻)",    "unit": "ppm",      "section": "Soluble Ions"},
    {"key": "sol_hco3",  "label": "Soluble Bicarbonate (HCO₃⁻)","unit": "ppm",     "section": "Soluble Ions"},
    {"key": "sol_so4",   "label": "Soluble Sulfate (SO₄²⁻)",   "unit": "ppm",      "section": "Soluble Ions"},

    # --- Exchangeable cations ---
    {"key": "exch_ca",   "label": "Exchangeable Calcium",      "unit": "ppm",      "section": "Exchangeable Cations"},
    {"key": "exch_mg",   "label": "Exchangeable Magnesium",    "unit": "ppm",      "section": "Exchangeable Cations"},
    {"key": "exch_na",   "label": "Exchangeable Sodium",       "unit": "ppm",      "section": "Exchangeable Cations"},
    {"key": "exch_k",    "label": "Exchangeable Potassium",    "unit": "ppm",      "section": "Exchangeable Cations"},

    # --- Available nutrients & micros ---
    {"key": "avail_n",   "label": "Available Nitrogen (N)",    "unit": "mg/kg",    "section": "Available Nutrients & Micronutrients"},
    {"key": "avail_p",   "label": "Available Phosphorus (P)",  "unit": "mg/kg",    "section": "Available Nutrients & Micronutrients"},
    {"key": "avail_k",   "label": "Available Potassium (K)",   "unit": "mg/kg",    "section": "Available Nutrients & Micronutrients"},
    {"key": "avail_s",   "label": "Available Sulfur (S)",      "unit": "mg/kg",    "section": "Available Nutrients & Micronutrients"},
    {"key": "fe",        "label": "Iron (Fe)",                 "unit": "mg/kg",    "section": "Available Nutrients & Micronutrients"},
    {"key": "zn",        "label": "Zinc (Zn)",                 "unit": "mg/kg",    "section": "Available Nutrients & Micronutrients"},
    {"key": "cu",        "label": "Copper (Cu)",               "unit": "mg/kg",    "section": "Available Nutrients & Micronutrients"},
    {"key": "mn",        "label": "Manganese (Mn)",            "unit": "mg/kg",    "section": "Available Nutrients & Micronutrients"},
    {"key": "b",         "label": "Boron (B)",                 "unit": "mg/kg",    "section": "Available Nutrients & Micronutrients"},
    {"key": "mo",        "label": "Molybdenum (Mo)",           "unit": "mg/kg",    "section": "Available Nutrients & Micronutrients"},

    # --- Physical ---
    {"key": "bd",        "label": "Bulk Density",              "unit": "g/cm³",    "section": "Soil Physical Properties"},
    {"key": "whc",       "label": "Water Holding Capacity",    "unit": "%",        "section": "Soil Physical Properties"},
    {"key": "infil",     "label": "Infiltration Rate",         "unit": "mm/h",     "section": "Soil Physical Properties"},

    # --- Biological (optional) ---
    {"key": "mic_c",     "label": "Microbial Biomass Carbon",  "unit": "mg/kg",    "section": "Soil Biological Properties (Optional)"},
    {"key": "resp",      "label": "Soil Respiration (CO₂)",    "unit": "mg CO₂/kg/day","section": "Soil Biological Properties (Optional)"},
    {"key": "worms",     "label": "Earthworm Count",           "unit": "per m²",   "section": "Soil Biological Properties (Optional)"},
]

PDF_NAME_MAP = {
    "pH (paste extract)": "ph",
    "ECe": "ece",
    "Organic Matter": "om",
    "SAR": "sar",
    "ESP": "esp",
    "CEC": "cec",
    "CaCO₃": "caco3",
    "Saturation Percentage": "sat_pct",
    "Soluble Calcium (Ca²⁺)": "sol_ca",
    "Soluble Magnesium (Mg²⁺)": "sol_mg",
    "Soluble Sodium (Na⁺)": "sol_na",
    "Soluble Potassium (K⁺)": "sol_k",
    "Soluble Chloride (Cl⁻)": "sol_cl",
    "Soluble Bicarbonate (HCO₃⁻)": "sol_hco3",
    "Soluble Sulfate (SO₄²⁻)": "sol_so4",
    "Exchangeable Calcium": "exch_ca",
    "Exchangeable Magnesium": "exch_mg",
    "Exchangeable Sodium": "exch_na",
    "Exchangeable Potassium": "exch_k",
    "Available Nitrogen (N)": "avail_n",
    "Available Phosphorus (P)": "avail_p",
    "Available Potassium (K)": "avail_k",
    "Available Sulfur (S)": "avail_s",
    "Iron (Fe)": "fe",
    "Zinc (Zn)": "zn",
    "Copper (Cu)": "cu",
    "Manganese (Mn)": "mn",
    "Boron (B)": "b",
    "Molybdenum (Mo)": "mo",
}

ESSENTIAL_KEYS = ["ph", "ece", "om", "sar", "texture", "avail_p", "avail_k"]

# ============== SESSION STATE INIT ==============

if "extracted" not in st.session_state:
    st.session_state.extracted = {}

if "sample_info" not in st.session_state:
    st.session_state.sample_info = {
        "customer": "",
        "report_no": "",
        "sample_ref": "",
        "description": "",
        "po_number": "",
        "received": "",
        "analyzed": "",
        "site": "",
    }

# ============== PDF UPLOAD & EXTRACTION ==============

st.markdown("### Option 1 – Upload Innovation Oasis Report (PDF)")
uploaded_file = st.file_uploader("Drag & drop or click to browse", type=["pdf"])


def extract_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t + "\n"

    data = {}
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # --- Header info ---
    if "Dr Ahmed - AK" in text:
        data["Customer Name"] = "Dr Ahmed - AK"
    elif "Dr Ahmed (AK)" in text:
        data["Customer Name"] = "Dr Ahmed (AK)"
    elif "Dr. Ahmad" in text:
        data["Customer Name"] = "Dr. Ahmad"
    elif "Dr Ahmed" in text:
        data["Customer Name"] = "Dr Ahmed"

    report_match = re.search(r"SP[-\s]*[\d]+[-\s]*25", text, re.IGNORECASE)
    if report_match:
        rep = report_match.group(0).replace("SP", "SP").replace("  ", " ").strip()
        rep = rep.replace("  ", " ")
        data["Test Report No."] = rep

    desc_match = re.search(r"Sample Description\s*\*\s*([^\n]+)", text)
    if desc_match:
        data["Sample Description"] = desc_match.group(1).strip()

    received_match = re.search(r"Received on\s*([0-9/ -]+)", text, re.IGNORECASE)
    if received_match:
        data["Received On"] = received_match.group(1).strip()

    analysed_match = re.search(r"Analysed on\s*([0-9/ -]+)", text, re.IGNORECASE)
    if analysed_match:
        data["Analyzed On"] = analysed_match.group(1).strip()

    site_match = re.search(r"Site\s*([^\n]+)", text)
    if site_match:
        data["Site"] = site_match.group(1).strip()

    # --- Main values & ions ---
    for line in lines:
        line_lower = line.lower()

        # pH
        if "ph" in line_lower and "ece" not in line_lower and "base saturation" not in line_lower:
            if "pH (paste extract)" not in data:
                m = re.search(r"([0-9]+\.?[0-9]*)", line)
                if m:
                    data["pH (paste extract)"] = m.group(1)

        # ECe (µS/cm → dS/m)
        if "ece" in line_lower:
            m = re.search(r"([0-9]+)", line)
            if m:
                ec_us = int(m.group(1))
                data["ECe"] = round(ec_us / 1000, 2)

        # Organic Matter
        if "organic matter" in line_lower:
            m = re.search(r"([0-9]+\.?[0-9]*)", line)
            if m:
                data["Organic Matter"] = m.group(1)

        # SAR
        if re.search(r"\bsar\b", line_lower):
            m = re.search(r"([0-9]+\.?[0-9]*)", line)
            if m:
                data["SAR"] = m.group(1)

        # ESP
        if re.search(r"\besp\b", line_lower):
            m = re.search(r"([0-9]+\.?[0-9]*)", line)
            if m:
                data["ESP"] = m.group(1)

        # CEC
        if "cation exchange capacity" in line_lower:
            m = re.search(r"([0-9]+\.?[0-9]*)", line)
            if m:
                data["CEC"] = m.group(1)

        # ===== Soluble Ions =====
        if "soluble" in line_lower and "calcium" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Soluble Calcium (Ca²⁺)"] = m.group(1)

        if "soluble" in line_lower and "magnesium" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Soluble Magnesium (Mg²⁺)"] = m.group(1)

        if "soluble" in line_lower and "sodium" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Soluble Sodium (Na⁺)"] = m.group(1)

        if "soluble" in line_lower and "potassium" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Soluble Potassium (K⁺)"] = m.group(1)

        if "soluble" in line_lower and "chloride" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Soluble Chloride (Cl⁻)"] = m.group(1)

        if "soluble" in line_lower and "bicarbonate" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Soluble Bicarbonate (HCO₃⁻)"] = m.group(1)

        if "soluble" in line_lower and ("sulfate" in line_lower or "sulphate" in line_lower):
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Soluble Sulfate (SO₄²⁻)"] = m.group(1)

        # ===== Exchangeable Cations =====
        if "exchangeable" in line_lower and "calcium" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Exchangeable Calcium"] = m.group(1)

        if "exchangeable" in line_lower and "magnesium" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Exchangeable Magnesium"] = m.group(1)

        if "exchangeable" in line_lower and "sodium" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Exchangeable Sodium"] = m.group(1)

        if "exchangeable" in line_lower and "potassium" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Exchangeable Potassium"] = m.group(1)

        # ===== Available Nutrients & Micronutrients =====
        # N
        if "available" in line_lower and "nitrogen" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Available Nitrogen (N)"] = m.group(1)

        # P  ✅ أكثر مرونة: أي سطر فيه available + phosphorus
        if "available" in line_lower and "phosph" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Available Phosphorus (P)"] = m.group(1)

        # K  ✅ نفس الفكرة
        if "available" in line_lower and "potass" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Available Potassium (K)"] = m.group(1)

        # S
        if "available" in line_lower and ("sulfur" in line_lower or "sulphur" in line_lower):
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Available Sulfur (S)"] = m.group(1)

        # Micronutrients: Fe, Zn, Cu, Mn, B, Mo
        if "available" in line_lower and "iron" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Iron (Fe)"] = m.group(1)

        if "available" in line_lower and "zinc" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Zinc (Zn)"] = m.group(1)

        if "available" in line_lower and "copper" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Copper (Cu)"] = m.group(1)

        if "available" in line_lower and "manganese" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Manganese (Mn)"] = m.group(1)

        if "available" in line_lower and "boron" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Boron (B)"] = m.group(1)

        if "available" in line_lower and "molybdenum" in line_lower:
            m = re.search(r"([<]?[0-9]*\.?[0-9]+)", line)
            if m:
                data["Molybdenum (Mo)"] = m.group(1)

    return data



if uploaded_file and st.button("Extract data from PDF", type="primary", use_container_width=True):
    with st.spinner("Extracting values from Innovation Oasis report..."):
        try:
            pdf_data = extract_from_pdf(uploaded_file)
            st.session_state.extracted = pdf_data

            # fill sample_info if available
            si = st.session_state.sample_info
            si["customer"]   = pdf_data.get("Customer Name", si["customer"])
            si["report_no"]  = pdf_data.get("Test Report No.", si["report_no"])
            si["description"]= pdf_data.get("Sample Description", si["description"])
            si["received"]   = pdf_data.get("Received On", si["received"])
            si["analyzed"]   = pdf_data.get("Analyzed On", si["analyzed"])
            si["site"]       = pdf_data.get("Site", si["site"])

            # map PDF names to our param keys
            for pdf_name, value in pdf_data.items():
                if pdf_name in PDF_NAME_MAP:
                    key = PDF_NAME_MAP[pdf_name]
                    ss_key = f"val_{key}"
                    st.session_state[ss_key] = str(value)

            st.success(f"Extracted {len(pdf_data)} values.")
        except Exception as e:
            st.error(f"Error while reading PDF: {e}")

with st.expander("DEBUG – Extracted from PDF"):
    st.json(st.session_state.extracted)

st.markdown("---")

# ============== SAMPLE INFORMATION ==============

st.markdown("### Sample Information")

si = st.session_state.sample_info
col1, col2 = st.columns(2)
with col1:
    si["customer"]   = st.text_input("Customer Name", value=si["customer"])
    si["report_no"]  = st.text_input("Test Report No.", value=si["report_no"])
    si["sample_ref"] = st.text_input("Customer Sample Reference", value=si["sample_ref"])
    si["description"]= st.text_input("Sample Description", value=si["description"])
with col2:
    si["po_number"]  = st.text_input("Purchase Order Number", value=si["po_number"])
    si["received"]   = st.text_input("Received On", value=si["received"])
    si["analyzed"]   = st.text_input("Analyzed On", value=si["analyzed"])
    si["site"]       = st.text_input("Site", value=si["site"])

st.session_state.sample_info = si

st.markdown("---")

# ============== MANUAL DATA ENTRY (Option 2) ==============

st.markdown("### Option 2 – Manual Data Entry / Edit Extracted Data")


def param_text_input(param_def):
    key = param_def["key"]
    label = param_def["label"]
    unit = param_def["unit"]
    ss_key = f"val_{key}"

    if ss_key not in st.session_state:
        st.session_state[ss_key] = ""

    show_label = f"{label}" + (f" [{unit}]" if unit else "")
    return st.text_input(show_label, key=ss_key)


TEXTURE_OPTIONS = [
    "Not specified",
    "Sand", "Loamy sand", "Sandy loam", "Loam", "Silt loam",
    "Sandy clay loam", "Clay loam", "Silty clay loam",
    "Sandy clay", "Silty clay", "Clay",
]

sections = []
for p in PARAMS:
    if p["section"] not in sections:
        sections.append(p["section"])

for section in sections:
    st.markdown(f"**{section}**")
    cols = st.columns(2)
    i = 0
    for p in [x for x in PARAMS if x["section"] == section]:
        with cols[i % 2]:
            if p["key"] == "texture":
                texture_key = "val_texture"

                # default from extracted or "Not specified"
                if texture_key not in st.session_state:
                    default_texture = st.session_state.extracted.get("Soil Texture Class", "Not specified")
                    if default_texture not in TEXTURE_OPTIONS:
                        default_texture = "Not specified"
                    st.session_state[texture_key] = default_texture

                val_texture = st.selectbox(
                    "Soil Texture Class",
                    options=TEXTURE_OPTIONS,
                    index=TEXTURE_OPTIONS.index(st.session_state[texture_key]),
                    key=texture_key,
                )

                st.session_state.extracted["Soil Texture Class"] = val_texture
            else:
                param_text_input(p)
        i += 1
    st.markdown("---")

# ============== GENERATE REPORT BUTTON ==============

st.markdown("### Generate Report")

btn = st.button("Generate Official Soil Health Report", type="primary", use_container_width=True)

if btn:
    missing = []

    def get_raw(key):
        return st.session_state.get(f"val_{key}", "").strip()

    if get_raw("ph") == "":
        missing.append("Soil pH")
    if get_raw("ece") == "":
        missing.append("ECe")
    if get_raw("om") == "":
        missing.append("Organic Matter")
    if get_raw("sar") == "":
        missing.append("SAR")
    if st.session_state.get("val_texture", "Not specified") == "Not specified":
        missing.append("Soil Texture Class")
    if get_raw("avail_p") == "":
        missing.append("Available P")
    if get_raw("avail_k") == "":
        missing.append("Available K")

    if missing:
        st.error(
            "Essential data missing. Please provide the following before generating the report:\n\n- "
            + "\n- ".join(missing)
        )
    else:
        raw_data = {}
        for p in PARAMS:
            key = p["key"]
            label = p["label"]
            if key == "texture":
                val = st.session_state.get("val_texture", "Not specified")
                if val == "Not specified":
                    raw_data[label] = "Not analyzed"
                else:
                    raw_data[label] = val
            else:
                val = st.session_state.get(f"val_{key}", "").strip()
                if val == "":
                    raw_data[label] = "Not analyzed"
                else:
                    raw_data[label] = val

        st.session_state.report_payload = {
            "sample_info": st.session_state.sample_info,
            "raw_data": raw_data,
        }

        st.success("Report data collected. Opening report page...")
        st.switch_page("pages/report_page.py")
