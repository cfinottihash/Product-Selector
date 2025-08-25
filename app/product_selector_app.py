# Streamlit product selector for Chardon (minimal)
# Run:
#   python -m streamlit run app/product_selector_app.py --server.address 0.0.0.0
# Expects CSV at ../data/chardon_product_selections.csv (relative to this file)

import streamlit as st
import pandas as pd
from pathlib import Path
import re

st.set_page_config(page_title="Chardon Product Selector (minimal)", page_icon="🔌", layout="wide")

# ---------- Paths ----------
CSV_PATH = Path(__file__).parents[1] / "data" / "chardon_product_selections.csv"

# ---------- Helpers ----------
def norm_col(df: pd.DataFrame, col: str, default: str = "None") -> None:
    if col in df.columns:
        df[col] = df[col].fillna(default).astype(str)
    else:
        df[col] = default

def uniq_opts(series: pd.Series):
    vals = [str(o) for o in series.dropna().unique() if str(o).strip() not in ("", "nan")]
    return sorted(vals)

def parse_int_safe(x, fallback=999):
    try:
        return int(re.sub(r"[^0-9]", "", str(x))) if re.search(r"\d", str(x)) else fallback
    except Exception:
        return fallback

def range_rank(val):
    # 'A' < 'B' < 'C' ... ; None/empty -> big rank
    if not isinstance(val, str) or not val:
        return 999
    # If value like 'A1' or 'A/B', take first letter A-Z
    m = re.search(r"[A-Z]", val.upper())
    if not m:
        return 999
    return ord(m.group(0)) - ord('A') + 1

def connector_rank(val):
    # Prefer 'C' (plated copper), then 'B' (bi-metal), then others/None
    v = str(val).upper()
    if v == "C": return 1
    if v == "B": return 2
    if v in ("NONE", "", "NAN"): return 99
    return 50

def pick_option(label: str, options: list, help_msg: str = None):
    if not options:
        st.error(f"No options available for '{label}'.")
        st.stop()
    return st.selectbox(label, options, help=help_msg)

def suggest_row(df: pd.DataFrame) -> pd.Series:
    """
    With potentially multiple rows remaining (due to cable range, conductor code, connector, etc.),
    pick a single deterministic 'suggested' SKU by a stable priority:
      1) Lowest Cable_Range_Code (A < B < C ...)
      2) Lowest Conductor_Code (numeric)
      3) Preferred Connector_Type (C < B < others)
      4) First by Final_Product_Code alphabetically
    Columns are optional; missing ones get neutral high ranks.
    """
    # Ensure expected columns exist with safe defaults
    for c in ("Cable_Range_Code", "Conductor_Code", "Connector_Type", "Final_Product_Code"):
        if c not in df.columns:
            df[c] = "None"

    ranked = df.copy()
    ranked["__r_range"] = ranked["Cable_Range_Code"].map(range_rank)
    ranked["__r_cond"]  = ranked["Conductor_Code"].map(parse_int_safe)
    ranked["__r_conn"]  = ranked["Connector_Type"].map(connector_rank)
    ranked["__r_sku"]   = ranked["Final_Product_Code"].astype(str)

    ranked = ranked.sort_values(
        by=["__r_range", "__r_cond", "__r_conn", "__r_sku"],
        ascending=[True, True, True, True],
        kind="mergesort"
    )
    return ranked.iloc[0]

# ---------- Data ----------
@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Normalize common option columns so filters don't break
    for c in ("Test_Point", "Fuse_Manufacturer", "Connector_Type"):
        norm_col(df, c, "None")

    # Normalize basic columns
    if "Standard" not in df.columns: df["Standard"] = "IEEE/ANSI"
    if "Product_Group" not in df.columns: df["Product_Group"] = "Unknown"
    for c in ("Voltage_kV", "Current_A"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        else:
            df[c] = None

    # Ensure final code column exists
    if "Final_Product_Code" not in df.columns:
        df["Final_Product_Code"] = df.get("Base_Code", "UNKNOWN")

    return df

# Load
try:
    df = load_data(CSV_PATH)
except Exception as e:
    st.error(f"Erro ao carregar CSV em {CSV_PATH}:\n{e}")
    st.stop()

st.title("🔌 Chardon Product Selector (minimal)")

# ---------- Sidebar: context ----------
with st.sidebar:
    st.markdown("**Filtros mínimos** para sugerir o part number final.")
    st.caption("Fatores usados: Standard, Product Group, Voltage (kV), Current (A) e Test Point.")

# ---------- Filters (only the 5 factors you requested) ----------
col1, col2 = st.columns(2)

with col1:
    standards = uniq_opts(df["Standard"])
    standard = pick_option("Standard", standards)
    filtered = df[df["Standard"].astype(str) == standard]

    groups = uniq_opts(filtered["Product_Group"])
    product_group = pick_option("Product Group", groups)
    filtered = filtered[filtered["Product_Group"].astype(str) == product_group]

with col2:
    voltages = sorted([v for v in filtered["Voltage_kV"].dropna().unique().tolist()])
    if voltages:
        voltage = st.selectbox("Voltage (kV)", voltages)
        filtered = filtered[filtered["Voltage_kV"] == voltage]
    else:
        voltage = None  # Some products might not have Voltage_kV in CSV

    currents = sorted([c for c in filtered["Current_A"].dropna().unique().tolist()])
    # Current may not exist for some product groups; make it optional
    if currents:
        current = st.selectbox("Current (A)", currents)
        filtered = filtered[filtered["Current_A"] == current]
    else:
        current = None

# Test point flag (applies if column exists; otherwise ignored)
need_tp = st.checkbox("Capacitive test point?", value=False)
tp_label = "T" if need_tp else "None"
if "Test_Point" in filtered.columns:
    filtered = filtered[filtered["Test_Point"].fillna("None").astype(str) == tp_label]

# ---------- Resolve result ----------
if filtered.empty:
    st.error("No matching SKU with the selected combination.")
else:
    row = suggest_row(filtered)
    sku = str(row.get("Final_Product_Code", "UNKNOWN")).strip()
    st.subheader("✅ Suggested Part Number")
    st.code(sku, language="text")
    # Optionally show a tiny hint about what drove the suggestion
    hint_parts = []
    if "Cable_Range_Code" in row: hint_parts.append(f"Range={row['Cable_Range_Code']}")
    if "Conductor_Code" in row:   hint_parts.append(f"Cond={row['Conductor_Code']}")
    if "Connector_Type" in row:   hint_parts.append(f"Conn={row['Connector_Type']}")
    if hint_parts:
        st.caption("Heurística de desempate: " + " · ".join(hint_parts))
