# Streamlit product selector for Chardon (minimal, CSV-driven)
# Run (Codespaces-friendly):
#   python -m streamlit run app/product_selector_app.py --server.address 0.0.0.0
# O app lê o CSV da pasta ../data com prefixo 'chardon_product_selections'
# Ex.: data/chardon_product_selections.csv ou data/chardon_product_selections (1).csv

import streamlit as st
import pandas as pd
from pathlib import Path
import re
from typing import Optional, List

st.set_page_config(page_title="Chardon Product Selector", page_icon="🔌", layout="wide")

DATA_DIR = Path(__file__).parents[1] / "data"

# -------- CSV discovery (prioriza arquivo enviado por você) --------
def discover_csv() -> Optional[Path]:
    """Procura arquivos que começam com 'chardon_product_selections' em /data.
       Escolhe o mais recente por mtime (p.ex., 'chardon_product_selections (1).csv')."""
    if not DATA_DIR.exists():
        return None
    candidates: List[Path] = sorted(
        DATA_DIR.glob("chardon_product_selections*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None

CSV_PATH = discover_csv()

# -------- Helpers --------
def tp_truthy(v) -> bool:
    """Normaliza Test Point para booleano respeitando o que vier do CSV."""
    s = str(v).strip().upper()
    return s in {"T", "TP", "YES", "Y", "TRUE", "1"}

def uniq_opts(series: pd.Series):
    vals = [str(o) for o in series.dropna().unique() if str(o).strip() not in ("", "nan")]
    return sorted(vals)

def pick_option(label: str, options: list, help_msg: str = None):
    if not options:
        st.error(f"No options available for '{label}'.")
        st.stop()
    return st.selectbox(label, options, help=help_msg, key=f"sel_{label}")

def parse_int_safe(x, fallback=999):
    try:
        return int(re.sub(r"[^0-9]", "", str(x))) if re.search(r"\d", str(x)) else fallback
    except Exception:
        return fallback

def range_rank(val):
    # 'A' < 'B' < 'C' ... ; None/empty -> big rank
    if not isinstance(val, str) or not val:
        return 999
    m = re.search(r"[A-Z]", val.upper())
    if not m:
        return 999
    return ord(m.group(0)) - ord('A') + 1

def connector_rank(val):
    # Prefer 'C' (plated copper), then 'B' (bi-metal), depois outros/None
    v = str(val).upper()
    if v == "C": return 1
    if v == "B": return 2
    if v in ("NONE", "", "NAN"): return 99
    return 50

def suggest_row(df: pd.DataFrame) -> pd.Series:
    """
    Se ainda sobrarem múltiplas linhas (ex.: variações de range/condutor/conector),
    escolhe UMA sugestão estável:
      1) Menor Cable_Range_Code (A < B < C …)
      2) Menor Conductor_Code (numérico)
      3) Conector preferido (C < B < outros)
      4) Primeiro por Final_Product_Code (ordem alfabética)
    """
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

# -------- Load CSV (obrigatório) --------
@st.cache_data
def load_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    # Colunas mínimas esperadas do seu CSV
    required = ["Standard", "Product_Group", "Final_Product_Code"]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"Missing required column in CSV: {c}")

    # Normaliza tipos básicos
    if "Voltage_kV" in df.columns:
        df["Voltage_kV"] = pd.to_numeric(df["Voltage_kV"], errors="coerce")
    else:
        df["Voltage_kV"] = None

    if "Current_A" in df.columns:
        df["Current_A"] = pd.to_numeric(df["Current_A"], errors="coerce")
    else:
        df["Current_A"] = None

    # Cria coluna booleana a partir do Test_Point do CSV (sem mudar o dado original)
    if "Test_Point" in df.columns:
        df["_TP_Flag"] = df["Test_Point"].map(tp_truthy)
    else:
        # Se não existir, assume False e não filtra por TP
        df["_TP_Flag"] = False

    return df

if CSV_PATH is None:
    st.error("CSV não encontrado em ./data (esperado prefixo 'chardon_product_selections').")
    st.stop()

try:
    df = load_data(CSV_PATH)
except Exception as e:
    st.error(f"Erro ao carregar CSV '{CSV_PATH.name}':\n{e}")
    st.stop()

st.title("🔌 Chardon Product Selector (CSV-driven)")

with st.sidebar:
    st.markdown("**CSV carregado:**")
    st.code(str(CSV_PATH), language="text")
    st.caption("Este app usa *exatamente* os campos do seu CSV (incluindo Test Point).")
    st.caption("Filtros: Standard, Product Group, Voltage, Current, Test Point.")

# -------- Filtros mínimos (5 fatores) --------
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
        voltage = None

    currents = sorted([c for c in filtered["Current_A"].dropna().unique().tolist()])
    if currents:
        current = st.selectbox("Current (A)", currents)
        filtered = filtered[filtered["Current_A"] == current]
    else:
        current = None

# Test Point (depende do CSV; checkbox só aparece se a coluna existir no arquivo)
if "_TP_Flag" in filtered.columns and "Test_Point" in df.columns:
    # Descobre se existem variantes com e sem TP para essa combinação
    sub = filtered.copy()
    has_true = sub["_TP_Flag"].any()
    has_false = (~sub["_TP_Flag"]).any()

    # Só mostra o checkbox se fizer diferença nessa filtragem
    if has_true or has_false:
        need_tp = st.checkbox("Capacitive test point?", value=False)
        filtered = filtered[filtered["_TP_Flag"] == bool(need_tp)]

# -------- Resultado: apenas o part number sugerido --------
if filtered.empty:
    st.error("No matching SKU with the selected combination.")
else:
    row = suggest_row(filtered)
    sku = str(row.get("Final_Product_Code", "UNKNOWN")).strip()
    st.subheader("✅ Suggested Part Number")
    st.code(sku, language="text")
