# Streamlit Product Configurator for Chardon
# This app BUILDS a part number based on user selections, following a defined logic.
# It uses a "database" of CSV files from the /data directory.

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, Optional

st.set_page_config(page_title="Chardon Product Configurator", page_icon="🛠️", layout="wide")

# Define paths for data and images
DATA_DIR = Path(__file__).parent.parent / "data"
IMAGES_DIR = Path(__file__).parent.parent / "images"


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
def find_cable_range_code(diameter: float, voltage: int, current: int, db: Dict[str, pd.DataFrame]) -> str:
    """Finds the cable range code based on diameter, voltage, and current."""
    if current >= 600:
        table_name = f"opcoes_range_cabo_{voltage}kv_600a"
    else: # Default to 200A style
        table_name = f"opcoes_range_cabo_{voltage}kv"
    
    if table_name not in db:
        st.warning(f"Tabela de range ('{table_name}.csv') não encontrada.")
        return "ERR"
        
    df_range = db[table_name]
    for _, row in df_range.iterrows():
        if row["min_mm"] <= diameter <= row["max_mm"]:
            return str(row["codigo_retorno"])
            
    return "N/A"

def find_conductor_code_200a(cond_type: str, cond_size: int, db: Dict[str, pd.DataFrame]) -> str:
    """Finds the two-digit conductor code for 200A elbows."""
    table_name = "opcoes_condutores_v1"
    if table_name not in db:
        st.warning(f"Tabela de condutores ('{table_name}.csv') não encontrada.")
        return "ER"

    df_cond = db[table_name]
    match = df_cond[(df_cond["tipo_condutor"] == cond_type) & (df_cond["secao_mm2"] == cond_size)]
    if not match.empty:
        return str(int(match.iloc[0]["codigo_retorno"])).zfill(2)
    return "NA"

def find_compression_lug_600a(cond_type: str, cond_size: int, db: Dict[str, pd.DataFrame]) -> str:
    """Finds the four-digit compression lug code for 600A T-Bodies."""
    table_name = "opcoes_condutores_600a_v1"
    if table_name not in db:
        st.warning(f"Tabela de condutores 600A ('{table_name}.csv') não encontrada.")
        return "ER"
    
    df_cond = db[table_name]
    match = df_cond[(df_cond["tipo_condutor"] == cond_type) & (df_cond["secao_mm2"] == cond_size)]
    if not match.empty:
        return str(int(match.iloc[0]["codigo_retorno"])).zfill(4)
    return "NA"

def find_shear_bolt_lug(cond_size: float, db: Dict[str, pd.DataFrame]) -> str:
    """Finds the Shear Bolt connector code based on conductor size."""
    table_name = "opcoes_shear_bolt_v1"
    if table_name not in db:
        st.warning(f"Tabela Shear Bolt ('{table_name}.csv') não encontrada.")
        return "ER"
        
    df_shear = db[table_name]
    for _, row in df_shear.iterrows():
        if row["min_mm2"] <= cond_size <= row["max_mm2"]:
            return str(row["codigo_retorno"])
            
    return "N/A"

# --- Main App ---
st.title("🛠️ Chardon Product Configurator")
st.markdown("Selecione as opções para construir o Part Number do produto passo a passo.")

try:
    db = load_database()
    df_base = db["produtos_base"]
except Exception as e:
    st.error(f"Falha ao carregar os arquivos de dados. Erro: {e}")
    st.stop()

# --- Level 1 & 2: Framework Selection ---
st.header("1. Seleção Inicial")
col1, col2, col3 = st.columns(3)

with col1:
    standards = sorted(df_base["padrao"].unique())
    standard = st.selectbox("Padrão Normativo", standards)
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
    
    if product_name:
        selected_product_series = df_filtered[df_filtered["nome_exibicao"] == product_name]
        if not selected_product_series.empty:
            selected_product = selected_product_series.iloc[0]
            st.header("3. Configuração do Produto")
            
            # --- NEW: Create columns for Image and Configurator ---
            col_config, col_img = st.columns([2, 1]) # Configurator takes 2/3 of the space

            with col_img:
                # NEW: Logic to find and display the product image
                image_filename = selected_product.get("imagem_arquivo")
                if image_filename and isinstance(image_filename, str):
                    image_path = IMAGES_DIR / image_filename
                    if image_path.exists():
                        st.image(str(image_path), caption=product_name)
                    else:
                        st.warning(f"Imagem '{image_filename}' não encontrada na pasta 'images'.")
                else:
                    st.info("Sem imagem cadastrada para este produto.")
            
            # All configuration UI and logic goes into the left column
            with col_config:
                base_code = selected_product["codigo_base"]
                logic_id = selected_product["id_logica"]
                part_number = [base_code]
                
                st.info(f"Configurando produto: **{product_name}** (Base: `{base_code}`)")

                # --- Logic for "LOGICA_COTOVELO_200A" ---
                if logic_id == "LOGICA_COTOVELO_200A":
                    # UI Components
                    has_tp = st.checkbox("Incluir Ponto de Teste Capacitivo?")
                    diameter = st.number_input("Diâmetro sobre a Isolação (mm)", min_value=0.0, step=0.1, format="%.2f", value=0.0)
                    st.markdown("**Especificações do Condutor:**")
                    cond_col1_inner, cond_col2_inner = st.columns(2)
                    cond_table = db.get("opcoes_condutores_v1", pd.DataFrame())
                    with cond_col1_inner:
                        cond_types = sorted(cond_table["tipo_condutor"].unique()) if not cond_table.empty else []
                        cond_type = st.selectbox("Tipo de Condutor", cond_types, index=None, placeholder="Selecione...")
                    with cond_col2_inner:
                        cond_sizes = sorted(cond_table[cond_table["tipo_condutor"] == cond_type]["secao_mm2"].unique()) if cond_type and not cond_table.empty else []
                        cond_size = st.selectbox("Seção do Condutor (mm²)", cond_sizes, index=None, placeholder="Selecione...")
                    connector_mat = st.radio("Material do Conector (Terminal)", ["Cobre", "Bimetálico"], index=None, horizontal=True)
                    
                    # Final Result Generation
                    all_fields_filled = (diameter > 0 and cond_type and cond_size and connector_mat)
                    if all_fields_filled:
                        if has_tp: part_number.append("T")
                        part_number.append(find_cable_range_code(diameter, voltage, current, db))
                        part_number.append(find_conductor_code_200a(cond_type, cond_size, db))
                        part_number.append("C" if connector_mat == "Cobre" else "B")
                        
                        st.header("✅ Part Number Gerado")
                        final_code = "".join(p for p in part_number if p and "ERR" not in p and "N/A" not in p and "NA" not in p)
                        st.code(final_code, language="text")
                    else:
                        st.info("ℹ️ Preencha todos os campos da configuração para gerar o Part Number.")

                # --- Logic for "LOGICA_CORPO_T_600A" ---
                elif logic_id == "LOGICA_CORPO_T_600A":
                    # UI Components
                    step1_col1, step1_col2 = st.columns(2)
                    with step1_col1:
                        amp_rating = st.radio("Classe de Corrente (Step 1)", ["600A", "900A"], index=None)
                    with step1_col2:
                        has_tp_600a = st.checkbox("Incluir Ponto de Teste?", value=True)
                    
                    diameter = st.number_input("Diâmetro sobre a Isolação (mm) (Step 2)", min_value=0.0, step=0.1, format="%.2f", value=0.0)
                    
                    st.markdown("**Especificações do Terminal (Step 3):**")
                    lug_type = st.radio("Tipo de Terminal", ["Compression Connector", "Shear Bolt Connector"], index=None)

                    # Final Result Generation
                    final_lug_code = None
                    if lug_type == "Compression Connector":
                        comp_col1, comp_col2, comp_col3 = st.columns(3)
                        comp_table = db.get("opcoes_condutores_600a_v1", pd.DataFrame())
                        with comp_col1:
                            cond_types = sorted(comp_table["tipo_condutor"].unique()) if not comp_table.empty else []
                            cond_type = st.selectbox("Tipo de Condutor", cond_types, index=None, placeholder="Selecione...")
                        with comp_col2:
                            cond_sizes = sorted(comp_table[comp_table["tipo_condutor"] == cond_type]["secao_mm2"].unique()) if cond_type and not comp_table.empty else []
                            cond_size = st.selectbox("Seção (mm²)", cond_sizes, index=None, placeholder="Selecione...")
                        with comp_col3:
                            comp_mat = st.radio("Material", ["Cobre", "Alumínio/Bimetálico"], index=None, horizontal=True)
                        
                        if cond_type and cond_size and comp_mat:
                            comp_code = find_compression_lug_600a(cond_type, cond_size, db)
                            suffix = "CC" if comp_mat == "Cobre" else "A" # Assuming 'A' for Aluminum
                            final_lug_code = f"{comp_code}{suffix}"

                    elif lug_type == "Shear Bolt Connector":
                        shear_table = db.get("opcoes_shear_bolt_v1", pd.DataFrame())
                        # For Shear Bolt, we need to ask for a number and find the range
                        cond_size_shear_input = st.number_input("Seção do Condutor (mm²)", min_value=0.0, step=1.0, value=0.0)
                        if cond_size_shear_input > 0:
                            final_lug_code = find_shear_bolt_lug(cond_size_shear_input, db)

                    all_fields_filled = (amp_rating and diameter > 0 and lug_type and final_lug_code)
                    if all_fields_filled:
                        part_number = [base_code] # Reset part number
                        part_number.append(amp_rating.replace("A", "T" if has_tp_600a else ""))
                        part_number.append(find_cable_range_code(diameter, voltage, current, db))
                        part_number.append(final_lug_code)
                        
                        st.header("✅ Part Number Gerado")
                        final_code = "".join(p for p in part_number if p and "ERR" not in p and "N/A" not in p and "NA" not in p)
                        st.code(final_code, language="text")
                    else:
                        st.info("ℹ️ Preencha todos os campos da configuração para gerar o Part Number.")

                else:
                    st.warning(f"A lógica de configuração para '{logic_id}' ainda não foi implementada.")
