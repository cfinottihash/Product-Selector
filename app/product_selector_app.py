# Streamlit product selector for Chardon
# Save as app/product_selector_app.py and run:
#   python -m streamlit run app/product_selector_app.py --server.address 0.0.0.0
# CSV is expected at ../data/chardon_product_selections.csv (relative to this file)

import streamlit as st
import pandas as pd
from pathlib import Path

# ---------- Config ----------
CSV_PATH = Path(__file__).parents[1] / "data" / "chardon_product_selections.csv"
st.set_page_config(page_title="Chardon Product Selector (beta)", page_icon="🔌", layout="wide")

# ---------- Utils ----------
def norm_col(df: pd.DataFrame, col: str, default: str = "None") -> None:
    if col in df.columns:
        df[col] = df[col].fillna(default).astype(str)
    else:
        # se a coluna não existir, cria para não quebrar filtros opcionais
        df[col] = default

def uniq_opts(series: pd.Series):
    # opções limpas para os selectboxes
    return sorted([str(o) for o in series.dropna().unique() if str(o).strip() not in ("", "nan", "None")]) or ["None"]

def pick_option(label: str, series: pd.Series, error_msg: str) -> str:
    opts = uniq_opts(series)
    if not opts:
        st.error(error_msg)
        st.stop()
    return st.selectbox(label, opts, key=f"sel_{label}")

def stop_if_empty(df: pd.DataFrame, msg: str):
    if df.empty:
        st.error(msg)
        st.stop()

# ---------- Data ----------
@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Normalizações usadas nos filtros
    for c in ("Test_Point", "Fuse_Manufacturer", "Connector_Type"):
        norm_col(df, c, "None")
    # Garantir tipos consistentes
    for c in ("Voltage_kV", "Current_A"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# Carregar
try:
    df = load_data(CSV_PATH)
except Exception as e:
    st.error(f"Erro ao carregar CSV em {CSV_PATH}: {e}")
    st.stop()

st.title("🔌 Chardon Product Selector (beta)")

# ---------- Header / Info ----------
with st.expander("Commercial info (opcional)"):
    dest_state = st.selectbox("UF destino", ["SP", "MG", "RJ", "PR", "RS", "BA", "PE", "OUTROS"])
    client_type = st.selectbox("Tipo de cliente", ["Revenda", "Distribuidor", "OEM Prysmian", "OEM Geral", "Utility"])
    discount = st.number_input("Desconto %", min_value=0.0, max_value=50.0, value=0.0, step=0.5, format="%.1f")

# ---------- Core technical filters ----------
# Standard
standard = pick_option("Standard", df["Standard"], "Nenhum item com essa Norma.")
filtered = df[df["Standard"].astype(str) == standard]
stop_if_empty(filtered, "Sem itens após filtrar por Norma.")

# Family
family = pick_option("Family", filtered["Family"], "Nenhum item nessa família.")
filtered = filtered[filtered["Family"].astype(str) == family]
stop_if_empty(filtered, "Sem itens após filtrar por Family.")

# Product group
product_group = pick_option("Product group", filtered["Product_Group"], "Nenhum produto neste grupo.")
filtered = filtered[filtered["Product_Group"].astype(str) == product_group]
stop_if_empty(filtered, "Sem itens após filtrar por Product group.")

# Voltage
if "Voltage_kV" in filtered.columns:
    volt_opts = sorted(filtered["Voltage_kV"].dropna().unique().tolist())
    voltage = st.selectbox("Voltage (kV)", volt_opts, key="sel_voltage")
    filtered = filtered[filtered["Voltage_kV"] == voltage]
    stop_if_empty(filtered, "Sem itens após filtrar por Voltage (kV).")

# Current
if "Current_A" in filtered.columns and product_group.lower().find("elbow") != -1:
    curr_opts = sorted(filtered["Current_A"].dropna().unique().tolist())
    current = st.selectbox("Current (A)", curr_opts, key="sel_current")
    filtered = filtered[filtered["Current_A"] == current]
    stop_if_empty(filtered, "Sem itens após filtrar por Current (A).")

# ---------- Option-specific inputs ----------
# Marcar quais colunas existem
has_tp = "Test_Point" in filtered.columns
has_cable_code = "Cable_Range_Code" in filtered.columns
has_fuse = "Fuse_Manufacturer" in filtered.columns
has_cond = "Conductor_Code" in filtered.columns
has_conn = "Connector_Type" in filtered.columns
has_od = {"Cable_OD_Min_mm", "Cable_OD_Max_mm"}.issubset(filtered.columns)

# Produtos com lógica "elbow"
if product_group in ("Loadbreak Elbow", "Fused Loadbreak Elbow"):
    # Test point (se existir)
    if has_tp:
        need_tp = st.checkbox("Capacitive test point?", value=False)
        tp_label = "T" if need_tp else "None"
        filtered = filtered[filtered["Test_Point"].fillna("None").astype(str) == tp_label]
        stop_if_empty(filtered, "Não há variações com/sem Test Point para essa combinação.")

    # Cable range code
    if has_cable_code:
        cable_code = pick_option("Cable range code", filtered["Cable_Range_Code"], "Sem faixas de diâmetro disponíveis.")
        filtered = filtered[filtered["Cable_Range_Code"].astype(str) == cable_code]
        stop_if_empty(filtered, "Nenhum SKU para essa faixa de diâmetro.")

        # Mostrar faixa OD (se existir)
        if has_od:
            # após filtrar por cable_code deve existir alguma linha
            od_min = filtered["Cable_OD_Min_mm"].iloc[0]
            od_max = filtered["Cable_OD_Max_mm"].iloc[0]
            try:
                st.caption(f"Insulation Ø range: {float(od_min):.2f} – {float(od_max):.2f} mm")
            except Exception:
                st.caption(f"Insulation Ø range: {od_min} – {od_max} mm")

    # Fused elbow: fabricante do fusível
    if product_group == "Fused Loadbreak Elbow" and has_fuse:
        fuse_mfr = pick_option("Fuse manufacturer", filtered["Fuse_Manufacturer"], "Nenhuma opção de fabricante de fusível.")
        filtered = filtered[filtered["Fuse_Manufacturer"].astype(str) == fuse_mfr]
        stop_if_empty(filtered, "Combinação inválida de faixa + fabricante de fusível.")

    # Conductor code
    if has_cond:
        conductor_code = pick_option("Conductor code", filtered["Conductor_Code"], "Nenhum código de condutor disponível.")
        filtered = filtered[filtered["Conductor_Code"].astype(str) == conductor_code]
        stop_if_empty(filtered, "Combinação inválida de condutor.")

    # Connector type (se existir no CSV)
    if has_conn:
        connector_type = pick_option("Connector type", filtered["Connector_Type"], "Nenhuma opção de conector disponível.")
        filtered = filtered[filtered["Connector_Type"].astype(str) == connector_type]
        stop_if_empty(filtered, "Combinação inválida de conector.")

# Produtos “fixos” (sem opções) não precisam de inputs adicionais

qty = st.number_input("Quantity", min_value=1, value=1, step=1)

# ---------- Result ----------
if filtered.empty:
    st.error("No matching SKU with the selected combination.")
else:
    # Pode haver mais de uma linha (ex.: duplicidade por legado). Mostre a(s) opção(ões)
    show_cols = [c for c in [
        "Final_Product_Code", "Standard", "Family", "Product_Group",
        "Voltage_kV", "Current_A", "Base_Code",
        "Test_Point", "Cable_Range_Code", "Conductor_Code", "Connector_Type",
        "Fuse_Manufacturer", "Cable_OD_Min_mm", "Cable_OD_Max_mm"
    ] if c in filtered.columns]
    result_df = filtered[show_cols].drop_duplicates().reset_index(drop=True)

    # Mensagem principal
    if "Final_Product_Code" in result_df.columns:
        sku_list = result_df["Final_Product_Code"].dropna().unique().tolist()
        if len(sku_list) == 1:
            st.success(f"Resolved part number: **{sku_list[0]}**")
        else:
            st.success(f"{len(sku_list)} SKUs possíveis para a combinação atual.")
    else:
        st.info("Combinação encontrada, mas a coluna 'Final_Product_Code' não está no CSV.")

    # Tabela e download
    st.dataframe(result_df, use_container_width=True)
    csv_bytes = result_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download resultado (CSV)", data=csv_bytes, file_name="selector_result.csv", mime="text/csv")

    # Botão RFQ (stub)
    if st.button("Send RFQ"):
        # Em produção, integrar com backend/email/CRM
        if "Final_Product_Code" in result_df.columns and not result_df["Final_Product_Code"].isna().all():
            sku_preview = ", ".join(result_df["Final_Product_Code"].dropna().astype(str).tolist()[:5])
            st.info(f"RFQ para {qty}× [{sku_preview}] enviado para sales@chardon.com (simulado).")
        else:
            st.info(f"RFQ para {qty}× itens (sem coluna de SKU) enviado para sales@chardon.com (simulado).")
