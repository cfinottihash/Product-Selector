# Streamlit product selector for Chardon
# Save as product_selector_app.py and run:
#   streamlit run product_selector_app.py --server.address 0.0.0.0
# CSV must be in the same folder as this script

import streamlit as st
import pandas as pd
from pathlib import Path

CSV_PATH = Path(__file__).parents[1] / "data" / "chardon_product_selections.csv"

@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Normalise option strings for easier filtering
    df['Test_Point'] = df['Test_Point'].fillna('None')
    df['Fuse_Manufacturer'] = df['Fuse_Manufacturer'].fillna('None')
    df['Connector_Type'] = df['Connector_Type'].fillna('None')
    return df

df = load_data(CSV_PATH)

st.title("Chardon Product Selector (beta)")

# --- Step 1: Destination / client type (placeholder) ---
with st.expander("Commercial info (optional)"):
    dest_state = st.selectbox("UF destino", ["SP", "MG", "RJ", "PR", "RS", "BA", "PE", "OUTROS"])
    client_type = st.selectbox("Tipo de cliente", ["Revenda", "Distribuidor", "OEM Prysmian", "OEM Geral", "Utility"])
    discount = st.number_input("Desconto %", min_value=0.0, max_value=50.0, value=0.0, step=0.5, format="%.1f")

# --- Step 2: Core technical filters ---
standard = st.selectbox("Standard", sorted(df['Standard'].unique()))
filtered = df[df['Standard'] == standard]

family = st.selectbox("Family", sorted(filtered['Family'].unique()))
filtered = filtered[filtered['Family'] == family]

product_group = st.selectbox("Product group", sorted(filtered['Product_Group'].unique()))
filtered = filtered[filtered['Product_Group'] == product_group]

voltage = st.selectbox("Voltage (kV)", sorted(filtered['Voltage_kV'].unique()))
filtered = filtered[filtered['Voltage_kV'] == voltage]

current = st.selectbox("Current (A)", sorted(filtered['Current_A'].unique()))
filtered = filtered[filtered['Current_A'] == current]

# --- Option-specific inputs ---
if product_group in ("Loadbreak Elbow", "Fused Loadbreak Elbow"):
    need_tp = st.checkbox("Capacitive test point?", value=False)
    tp_label = "T" if need_tp else "None"
    filtered = filtered[filtered['Test_Point'] == tp_label]

    cable_code = st.selectbox("Cable range code", sorted(filtered['Cable_Range_Code'].unique()))
    filtered = filtered[filtered['Cable_Range_Code'] == cable_code]

    # show OD range
    od_min = filtered['Cable_OD_Min_mm'].iloc[0]
    od_max = filtered['Cable_OD_Max_mm'].iloc[0]
    st.caption(f"Insulation Ø range: {od_min:.2f} – {od_max:.2f} mm")

    if product_group == "Fused Loadbreak Elbow":
        fuse_mfr = st.selectbox("Fuse manufacturer", sorted(filtered['Fuse_Manufacturer'].unique()))
        filtered = filtered[filtered['Fuse_Manufacturer'] == fuse_mfr]

    conductor_code = st.selectbox("Conductor code", sorted(filtered['Conductor_Code'].unique()))
    filtered = filtered[filtered['Conductor_Code'] == conductor_code]

    connector_type = st.selectbox("Connector type", sorted(filtered['Connector_Type'].unique()))
    filtered = filtered[filtered['Connector_Type'] == connector_type]

else:
    # non-configurable product, nothing extra
    pass

qty = st.number_input("Quantity", min_value=1, value=1, step=1)

# --- Result ---
if filtered.empty:
    st.error("No matching SKU with the selected combination.")
else:
    sku = filtered['Final_Product_Code'].iloc[0]
    st.success(f"Resolved part number: **{sku}**")

    if st.button("Send RFQ"):
        # In production, call backend / email; here just show stub
        st.info(f"RFQ for {qty}× {sku} sent to sales@chardon.com (simulado).")
