# Streamlit Product Configurator for Chardon
# This app BUILDS a part number based on user selections, following a defined logic.
# It uses a "database" of CSV files from the /data directory.

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, Optional

st.set_page_config(page_title="Chardon Product Configurator", page_icon="🛠️", layout="wide")

DATA_DIR = Path(__file__).parent.parent / "data"

# --- Database Loading ---
@st.cache_data
def load_database() -> Dict[str, pd.DataFrame]:
    """
    Loads all required CSVs from the /data directory into a dictionary of DataFrames.
    'produtos_base' is the main table, others are option lookups.
    """
    if not DATA_DIR.exists():
        st.error(f"Diretório de dados não encontrado em: {DATA_DIR}")
        st.error("Por favor, verifique se a pasta 'data' está na raiz do projeto, ao lado da pasta 'app'.")
        st.stop()

    db = {}
    # Load the main product table
    base_path = DATA_DIR / "produtos_base.csv"
    if not base_path.exists():
        st.error(f"Arquivo principal não encontrado: {base_path}")
        st.stop()
    db["produtos_base"] = pd.read_csv(base_path)

    # Load all option tables (opcoes_*.csv)
    for csv_file in DATA_DIR.glob("opcoes_*.csv"):
        key = csv_file.stem  # Use filename without extension as key
        db[key] = pd.read_csv(csv_file)
        
    return db

# --- Helper Functions for Logic ---
def find_cable_range_code(diameter: float, voltage: int, db: Dict[str, pd.DataFrame]) -> str:
    """Finds the cable range code based on diameter and voltage."""
    table_name = f"opcoes_range_cabo_{voltage}kv"
    
    if table_name not in db:
        st.warning(f"Tabela de range para {voltage}kV ('{table_name}.csv') não encontrada.")
        return "ERR"
        
    df_range = db[table_name]
    for _, row in df_range.iterrows():
        min_val = row["min_mm"]
        max_val = row["max_mm"]
        code = row["codigo_retorno"]
        
        if min_val <= diameter <= max_val:
            return str(code)
            
    return "N/A" # Not Applicable / Not Found
 
def find_conductor_code(cond_type: str, cond_size: int, db: Dict[str, pd.DataFrame]) -> str:
    """Finds the two-digit conductor code."""
    table_name = "opcoes_condutores_v1" # Assuming one table for now
    if table_name not in db:
        st.warning(f"Tabela de condutores ('{table_name}.csv') não encontrada.")
        return "ER"

    df_cond = db[table_name]
    match = df_cond[
        (df_cond["tipo_condutor"] == cond_type) &
        (df_cond["secao_mm2"] == cond_size)
    ]
    if not match.empty:
        # Format as two digits (e.g., 3 -> "03")
        return str(int(match.iloc[0]["codigo_retorno"])).zfill(2)
    return "NA"


# --- Main App ---
st.title("🛠️ Chardon Product Configurator")
st.markdown("Selecione as opções para construir o Part Number do produto passo a passo.")

try:
    db = load_database()
    df_base = db["produtos_base"]
except Exception as e:
    st.error(f"Falha ao carregar os arquivos de dados. Verifique a estrutura das pastas e o conteúdo dos CSVs. Erro: {e}")
    st.stop()

# --- Level 1 & 2: Framework Selection ---
st.header("1. Seleção Inicial")
col1, col2, col3 = st.columns(3)

with col1:
    standards = sorted(df_base["padrao"].unique())
    standard = st.selectbox("Padrão Normativo", standards)

# Filter based on previous selections
df_filtered = df_base[df_base["padrao"] == standard]

with col2:
    voltages = sorted(df_filtered["classe_tensao"].unique())
    voltage = st.selectbox("Classe de Tensão (kV)", voltages)
    
df_filtered = df_filtered[df_filtered["classe_tensao"] == voltage]

with col3:
    currents = sorted(df_filtered["classe_corrente"].unique())
    current = st.selectbox("Classe de Corrente (A)", currents)

df_filtered = df_filtered[df_filtered["classe_corrente"] == current]

# --- Level 3: Product Family Selection ---
st.header("2. Seleção do Produto")
if df_filtered.empty:
    st.warning("Nenhum produto encontrado para a combinação inicial selecionada.")
    st.stop()
else:
    product_options = df_filtered["nome_exibicao"].unique()
    product_name = st.selectbox("Família do Produto", product_options)
    
    # Ensure a product is selected before proceeding
    if product_name:
        selected_product_series = df_filtered[df_filtered["nome_exibicao"] == product_name]
        if not selected_product_series.empty:
            selected_product = selected_product_series.iloc[0]
        
            # --- Level 4: Dynamic Product Configurator ---
            st.header("3. Configuração do Produto")
            
            base_code = selected_product["codigo_base"]
            logic_id = selected_product["id_logica"]
            
            # Initialize part number
            part_number = [base_code]
            
            st.info(f"Configurando produto: **{product_name}** (Base: `{base_code}`)")

            # --- Specific Logic for "LOGICA_COTOVELO_200A" ---
            if logic_id == "LOGICA_COTOVELO_200A":
                # Step 1: Test Point (W)
                has_tp = st.checkbox("Incluir Ponto de Teste Capacitivo?")
                if has_tp:
                    part_number.append("T")

                # Step 2: Cable Range (X)
                diameter = st.number_input("Diâmetro sobre a Isolação (mm)", min_value=0.0, step=0.1, format="%.2f", value=0.0)
                if diameter > 0:
                    range_code = find_cable_range_code(diameter, voltage, db)
                    part_number.append(range_code)

                # Step 3: Conductor Code (Y)
                st.markdown("**Especificações do Condutor:**")
                cond_col1, cond_col2 = st.columns(2)
                
                cond_table = db.get("opcoes_condutores_v1", pd.DataFrame())
                
                with cond_col1:
                    cond_types = sorted(cond_table["tipo_conductor"].unique()) if not cond_table.empty else []
                    cond_type = st.selectbox("Tipo de Condutor", cond_types, index=None, placeholder="Selecione...")
                
                with cond_col2:
                    # Filter sizes based on selected type
                    if cond_type and not cond_table.empty:
                        cond_sizes = sorted(cond_table[cond_table["tipo_conductor"] == cond_type]["secao_mm2"].unique())
                    else:
                        cond_sizes = []
                    cond_size = st.selectbox("Seção do Condutor (mm²)", cond_sizes, index=None, placeholder="Selecione...")

                if cond_type and cond_size:
                    conductor_code = find_conductor_code(cond_type, cond_size, db)
                    part_number.append(conductor_code)

                # Step 4: Connector Material (Z)
                connector_mat = st.radio(
                    "Material do Conector (Terminal)",
                    ["Cobre (para cabos de cobre)", "Bimetálico (para cabos de cobre ou alumínio)"],
                    index=None,
                    horizontal=True
                )
                if connector_mat:
                    if "Cobre" in connector_mat:
                        part_number.append("C")
                    else:
                        part_number.append("B")

            else:
                st.warning(f"A lógica de configuração para '{logic_id}' ainda não foi implementada.")

            # --- Final Result ---
            st.header("✅ Part Number Gerado")
            # Filter out any potential error codes or empty values before joining
            valid_parts = [str(p) for p in part_number if p and "ERR" not in str(p) and "N/A" not in str(p)]
            final_code = "".join(valid_parts)
            st.code(final_code, language="text")

