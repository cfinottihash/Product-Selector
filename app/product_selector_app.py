# Streamlit Product Configurator for Chardon - UNIFIED VERSION
# This app acts as a router for different product line selectors.
# It uses a "database" of CSV files from the /data directory.

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, Optional
import re

st.set_page_config(page_title="Chardon Product Configurator", page_icon="🛠️", layout="wide")

# Define paths for data and images
DATA_DIR = Path(__file__).parent.parent / "data"
IMAGES_DIR = Path(__file__).parent.parent / "images"


# --- Database Loading ---
@st.cache_data
def load_database() -> Dict[str, pd.DataFrame]:
    """
    Loads ALL required CSVs from the /data directory into a dictionary of DataFrames.
    It cleans column names by stripping whitespace.
    """
    if not DATA_DIR.exists():
        st.error(f"Diretório de dados não encontrado em: {DATA_DIR}")
        st.stop()

    db = {}
    # Load all CSV files from the data directory
    for csv_file in DATA_DIR.glob("*.csv"):
        key = csv_file.stem
        try:
            # Read CSV and strip whitespace from column names
            df = pd.read_csv(csv_file)
            df.columns = df.columns.str.strip()
            db[key] = df
        except Exception as e:
            st.error(f"Erro ao carregar ou processar o arquivo {csv_file.name}: {e}")
    
    # Check for essential files
    required_files = ["produtos_base", "bitola_to_od", "csto_selection_table", "csti_selection_table", "connector_selection_table"]
    for f in required_files:
        if f not in db:
            st.error(f"Arquivo de dados essencial não encontrado: {f}.csv na pasta 'data'.")
            st.stop()

    return db

# --- ################################################################## ---
# --- ### LOGIC AND UI FOR SEPARABLE CONNECTORS                      ### ---
# --- ################################################################## ---

def find_cable_range_code(diameter: float, voltage: int, current: int, db: Dict[str, pd.DataFrame]) -> str:
    """Finds the cable range code based on diameter, voltage, and current."""
    table_name = f"opcoes_range_cabo_{voltage}kv_600a" if current >= 600 else f"opcoes_range_cabo_{voltage}kv"
    if table_name not in db:
        st.warning(f"Tabela de range ('{table_name}.csv') não encontrada.")
        return "ERR"
    df_range = db[table_name]
    for _, row in df_range.iterrows():
        if row["min_mm"] <= diameter <= row["max_mm"]:
            return str(row["codigo_retorno"])
    return "N/A"

def find_conductor_code_200a(cond_type: str, cond_size: int, db: Dict[str, pd.DataFrame]) -> str:
    table_name = "opcoes_condutores_v1"
    if table_name not in db: return "ER"
    df_cond = db[table_name]
    match = df_cond[(df_cond["tipo_condutor"] == cond_type) & (df_cond["secao_mm2"] == cond_size)]
    return str(int(match.iloc[0]["codigo_retorno"])).zfill(2) if not match.empty else "NA"

def find_compression_lug_600a(cond_type: str, cond_size: int, db: Dict[str, pd.DataFrame]) -> str:
    table_name = "opcoes_condutores_600a_v1"
    if table_name not in db: return "ER"
    df_cond = db[table_name]
    match = df_cond[(df_cond["tipo_condutor"] == cond_type) & (df_cond["secao_mm2"] == cond_size)]
    return str(int(match.iloc[0]["codigo_retorno"])).zfill(4) if not match.empty else "NA"

def render_separable_connector_configurator(db: Dict[str, pd.DataFrame]):
    """Renders the entire UI and logic for the Separable Connector configurator."""
    st.header("1. Seleção Inicial do Conector")
    df_base = db["produtos_base"]
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

    st.header("2. Seleção do Produto")
    if df_filtered.empty:
        st.warning("Nenhum produto encontrado para a combinação inicial selecionada.")
        return

    product_options = df_filtered["nome_exibicao"].unique()
    product_name = st.selectbox("Família do Produto", product_options)
    
    if not product_name: return

    selected_product_series = df_filtered[df_filtered["nome_exibicao"] == product_name]
    if selected_product_series.empty: return
    
    selected_product = selected_product_series.iloc[0]
    st.header("3. Configuração do Produto")
    
    col_config, col_img = st.columns([2, 1])
    with col_img:
        image_filename = selected_product.get("imagem_arquivo")
        if image_filename and isinstance(image_filename, str):
            image_path = IMAGES_DIR / image_filename
            if image_path.exists():
                st.image(str(image_path), caption=product_name)
            else:
                st.warning(f"Imagem '{image_filename}' não encontrada.")
        else:
            st.info("Sem imagem cadastrada.")
    
    with col_config:
        base_code = selected_product["codigo_base"]
        logic_id = selected_product["id_logica"]
        st.info(f"Configurando produto: **{product_name}** (Base: `{base_code}`)")

        if logic_id == "LOGICA_COTOVELO_200A":
            # UI and logic for 200A Elbow
            # ... (omitted for brevity, it's the same as the previous version) ...
            st.info("Lógica para Cotovelo 200A aqui.")

        elif logic_id == "LOGICA_CORPO_T_600A":
            # UI and logic for 600A T-Body
            # ... (omitted for brevity, it's the same as the previous version) ...
            st.info("Lógica para Corpo em T 600A aqui.")

        else:
            st.warning(f"A lógica de configuração para '{logic_id}' ainda não foi implementada.")

# --- ################################################################## ---
# --- ### LOGIC AND UI FOR TERMINATIONS                            ### ---
# --- ################################################################## ---

def termination_tol(tensao_term: str) -> float:
    """Returns the tolerance in mm for a given termination voltage class."""
    return 2.0 if "15 kV" in tensao_term else 3.0

def suggest_termination_connector(s_mm2: int, kind: str, db: Dict[str, pd.DataFrame], material: Optional[str] = None) -> pd.DataFrame:
    """Re-implementation of the connector suggestion logic."""
    df_conn = db["connector_selection_table"]
    
    # Filter by type (compression or shear-bolt)
    filtered = df_conn[df_conn["Type"].str.lower() == kind.lower()]
    
    # Filter by material if it's a compression lug
    if kind.lower() == "compression" and material:
        filtered = filtered[filtered["Material"].str.lower() == material.lower()]
        
    # Find matches where the conductor size is within the range
    matches = filtered[
        (filtered["Conductor Min (mm2)"] <= s_mm2) &
        (filtered["Conductor Max (mm2)"] >= s_mm2)
    ]
    return matches

def render_termination_selector(db: Dict[str, pd.DataFrame]):
    """Renders the entire UI and logic for the Termination selector."""
    st.header("1. Seleção do Cabo e Aplicação")
    
    df_cable = db["bitola_to_od"]
    
    TENS_MAP = {"8.7/15 kV":"15 kV", "12/20 kV":"25 kV", "15/25 kV":"25 kV", "20/35 kV":"35 kV"}
    def _order_kv(t:str) -> float:
        m = re.match(r"([\d.]+)", t); return float(m.group(1)) if m else 1e9
    CABLE_VOLTAGES = sorted(df_cable["Cable Voltage"].unique(), key=_order_kv)

    env_choice = st.radio("Aplicação da terminação:", ("Externa (Outdoor)", "Interna (Indoor)"), horizontal=True)
    know_iso = st.radio("Você já sabe o Ø sobre isolação do cabo?", ("Não, preciso estimar pela bitola", "Sim, digitar valor real"))
    cabo_tensao = st.selectbox("Classe de tensão do cabo:", CABLE_VOLTAGES)
    tensao_term = TENS_MAP[cabo_tensao]
    tolerance = termination_tol(tensao_term)

    d_iso, s_mm2 = None, None

    if know_iso.startswith("Sim"):
        d_iso = st.number_input("Ø sobre isolação (mm)", min_value=0.0, step=0.1)
        s_mm2 = st.selectbox("Seção nominal (mm²) para escolher lug:", sorted(df_cable["S_mm2"].astype(float).unique()))
        st.info(f"Ø sobre isolação informado: **{d_iso:.1f} mm**")
    else:
        filtro = df_cable[df_cable["Cable Voltage"] == cabo_tensao]
        bitolas = sorted(filtro["S_mm2"].astype(float).unique())
        s_mm2 = st.selectbox("Seção nominal (mm²):", bitolas)
        linha = filtro[filtro["S_mm2"].astype(float) == float(s_mm2)]
        if not linha.empty:
            d_iso = linha.iloc[0]["OD_iso_mm"]
            st.info(f"Ø sobre isolação ESTIMADA: **{d_iso:.1f} mm ± {tolerance} mm**")
        else:
            st.error("Não foi possível estimar o diâmetro para a bitola selecionada.")
            return

    if st.button("Buscar Terminação"):
        st.header("2. Resultados da Busca")
        df_term = db["csto_selection_table"] if env_choice.startswith("Externa") else db["csti_selection_table"]
        family = "CSTO" if env_choice.startswith("Externa") else "CSTI"

        matches = df_term[
            (df_term["Voltage Class"] == tensao_term) &
            (df_term["OD Min (mm)"] <= d_iso + tolerance) &
            (df_term["OD Max (mm)"] >= d_iso - tolerance)
        ]

        if matches.empty:
            st.error(f"Nenhuma terminação {family} encontrada para um diâmetro de ~{d_iso:.1f} mm.")
        else:
            st.success(f"Encontrada(s) {len(matches)} terminação(ões) {family} compatível(is):")
            st.table(matches[["Part Number", "OD Min (mm)", "OD Max (mm)"]])

            st.header("3. Sugestão de Terminais (Lugs)")
            df_conn_table = db["connector_selection_table"]
            LUG_MATERIALS = sorted(df_conn_table["Material"].dropna().unique())
            
            conn_ui = st.selectbox("Tipo de Terminal:", ["Compressão", "Torquimétrico"])
            kind = "compression" if conn_ui == "Compressão" else "shear-bolt"
            mat = st.selectbox("Material do terminal:", LUG_MATERIALS) if kind == "compression" else None
            
            conn_df = suggest_termination_connector(int(float(s_mm2)), kind, db, mat)
            if conn_df.empty:
                st.error("Nenhum terminal/lug encontrado para a seção selecionada.")
            else:
                st.table(conn_df)

# --- ################################################################## ---
# --- ### MAIN APP ROUTER                                          ### ---
# --- ################################################################## ---

st.title("🛠️ Chardon Product Configurator Unificado")
logo_path = IMAGES_DIR.parent / "app" / "assets" / "logo-chardon.png" # Path to logo
if logo_path.exists():
    st.image(str(logo_path), width=200)

try:
    db = load_database()
except Exception as e:
    st.error(f"Falha crítica ao carregar os arquivos de dados. Verifique a pasta 'data'. Erro: {e}")
    st.stop()

product_line = st.selectbox(
    "**Selecione a Linha de Produto:**",
    ["Conectores Separáveis", "Terminações"]
)

if product_line == "Conectores Separáveis":
    # NOTE: The full code for this function is in the previous versions.
    # To keep this example clean, I'm calling a placeholder.
    # You should copy the full logic from the previous file here.
    render_separable_connector_configurator(db) 
else:
    render_termination_selector(db)

