# Streamlit Product Configurator for Chardon - UNIFIED & FIXED VERSION
# This app acts as a router for different product line selectors.
# It uses a "database" of CSV files from the /data directory.

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, Optional
import re
import unicodedata
st.set_page_config(page_title="Chardon Product Configurator", page_icon="🛠️", layout="wide")

# Define paths for data and images
DATA_DIR = Path(__file__).parent.parent / "data"
IMAGES_DIR = Path(__file__).parent.parent / "images"


# --- Database Loading ---
@st.cache_data
# --- Helpers de normalização de schema ---


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", s.lower())

def _rename_like(df: pd.DataFrame, canonical: str, aliases: list[str]) -> None:
    """Se alguma coluna bater com algum alias (normalizado), renomeia para o nome canônico."""
    current = { _norm(c): c for c in df.columns }
    canon_norm = _norm(canonical)
    for a in aliases:
        if _norm(a) in current:
            df.rename(columns={ current[_norm(a)]: canonical }, inplace=True)
            return
    # se já tiver a canônica, nada a fazer
    if canon_norm in current and current[canon_norm] != canonical:
        df.rename(columns={ current[canon_norm]: canonical }, inplace=True)

def _normalize_bitola_to_od(df: pd.DataFrame) -> pd.DataFrame:
    """
    Garante colunas canônicas esperadas pelo seletor de terminações:
    ['Cable Voltage','S_mm2','Brand','Cable','OD_iso_mm','D_cond_mm','T_iso_mm']
    Aceita vários sinônimos/PT-PT/PT-BR.
    """
    df = df.copy()
    # Mapear sinônimos -> nomes canônicos
    _rename_like(df, "Cable Voltage", [
        "Cable Voltage", "Voltage Class", "Classe de Tensão do Cabo", "Classe de Tensão",
        "Tensão do Cabo", "Tensao do Cabo", "Classe de tensao", "Classe tensão"
    ])
    _rename_like(df, "S_mm2", [
        "S_mm2", "S (mm2)", "Seção (mm²)", "Secao (mm2)", "Seção nominal (mm²)",
        "Secao nominal (mm2)", "secao_mm2", "Bitola (mm2)"
    ])
    _rename_like(df, "Brand", ["Brand", "Marca", "Fabricante"])
    _rename_like(df, "Cable", ["Cable", "Modelo", "Tipo de Cabo", "Cabo"])
    _rename_like(df, "OD_iso_mm", [
        "OD_iso_mm", "OD sobre isolação (mm)", "OD sobre isolacao (mm)",
        "O.D. sobre isolação (mm)", "Ø sobre isolação (mm)", "OD_isol_mm", "OD isol mm"
    ])
    _rename_like(df, "D_cond_mm", ["D_cond_mm", "Øcond (mm)", "Diametro condutor (mm)", "Diâmetro do condutor (mm)"])
    _rename_like(df, "T_iso_mm", ["T_iso_mm", "Espessura Isol (mm)", "Espessura de isolação (mm)", "Espessura de isolacao (mm)"])

    # Tipagem numérica onde necessário
    for c in ["S_mm2", "OD_iso_mm", "D_cond_mm", "T_iso_mm"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Tira espaços
    df.columns = df.columns.str.strip()
    return df

def _normalize_connector_table(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nomes e tipos da tabela de lugs/conectores para colunas canônicas."""
    df = df.copy()

    # Canônicos finais que vamos usar:
    # Type | Material | Conductor Min (mm2) | Conductor Max (mm2)

    _rename_like(df, "Type", [
        "Type", "Tipo", "Categoria", "Connector Type", "Tipo de Terminal"
    ])

    _rename_like(df, "Material", [
        "Material", "Material do Terminal", "Material Terminal"
    ])

    # MIN - inclua todas as variantes que você tem no CSV
    _rename_like(df, "Conductor Min (mm2)", [
        "Conductor Min (mm2)", "Min (mm2)", "Min Conductor (mm2)",
        "Min Conductor (mm²)", "Min(mm2)", "Seção Min (mm²)", "Secao Min (mm2)",
        "Conductor_Min_mm2", "Conductor_Min_(mm2)"
    ])

    # MAX
    _rename_like(df, "Conductor Max (mm2)", [
        "Conductor Max (mm2)", "Max (mm2)", "Max Conductor (mm2)",
        "Max Conductor (mm²)", "Max(mm2)", "Seção Max (mm²)", "Secao Max (mm2)",
        "Conductor_Max_mm2", "Conductor_Max_(mm2)"
    ])

    # Tipagem: garanta string para filtros por .str e numérico para faixas
    if "Type" in df.columns:
        df["Type"] = df["Type"].astype(str)
    if "Material" in df.columns:
        df["Material"] = df["Material"].astype(str)

    for c in ["Conductor Min (mm2)", "Conductor Max (mm2)"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df.columns = df.columns.str.strip()
    return df


@st.cache_data
def load_database() -> Dict[str, pd.DataFrame]:
    """
    Carrega todos os CSVs de /data em um dict, normaliza headers e schemas
    para evitar KeyError por nomes diferentes de colunas.
    """
    if not DATA_DIR.exists():
        st.error(f"Diretório de dados não encontrado em: {DATA_DIR}")
        st.stop()

    db: Dict[str, pd.DataFrame] = {}
    for csv_file in DATA_DIR.glob("*.csv"):
        key = csv_file.stem
        try:
            df = pd.read_csv(csv_file)
            df.columns = df.columns.str.strip()
            db[key] = df
        except Exception as e:
            st.error(f"Erro ao carregar ou processar o arquivo {csv_file.name}: {e}")

    # Essenciais
    required_files = [
        "produtos_base", "bitola_to_od",
        "csto_selection_table", "csti_selection_table", "connector_selection_table"
    ]
    for f in required_files:
        if f not in db:
            st.error(f"Arquivo de dados essencial não encontrado: {f}.csv na pasta 'data'.")
            st.stop()

    # Normalizações específicas
    db["bitola_to_od"] = _normalize_bitola_to_od(db["bitola_to_od"])
    db["connector_selection_table"] = _normalize_connector_table(db["connector_selection_table"])

    # Sanidade mínima para evitar KeyError no seletor de terminações
    missing_cols = [c for c in ["Cable Voltage", "S_mm2", "OD_iso_mm"] if c not in db["bitola_to_od"].columns]
    if missing_cols:
        st.error(f"O arquivo 'bitola_to_od.csv' está sem as colunas necessárias (faltam: {missing_cols}). "
                 f"Após normalização, ainda não foi possível inferir esses nomes.")
        st.stop()

    return db


# --- ################################################################## ---
# --- ### LOGIC AND UI FOR SEPARABLE CONNECTORS                      ### ---
# --- ################################################################## ---

def find_cable_range_code(diameter: float, voltage: int, current: int, db: Dict[str, pd.DataFrame]) -> str:
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

def find_shear_bolt_lug(cond_size: float, db: Dict[str, pd.DataFrame]) -> str:
    table_name = "opcoes_shear_bolt_v1"
    if table_name not in db: return "ER"
    df_shear = db[table_name]
    for _, row in df_shear.iterrows():
        if row["min_mm2"] <= cond_size <= row["max_mm2"]:
            return str(row["codigo_retorno"])
    return "N/A"

def _hifen_join(*parts) -> str:
    parts = [str(p).strip("-") for p in parts if p and str(p).upper() not in {"NA", "N/A", "ER", "ERR"}]
    return "-".join(parts)

def render_separable_connector_configurator(db: Dict[str, pd.DataFrame]):
    """UI completa do configurador de Conectores Separáveis (200A e 600A)"""
    st.header("1. Seleção Inicial do Conector")
    df_base = db["produtos_base"].copy()

    col1, col2, col3 = st.columns(3)
    with col1:
        standards = sorted(df_base["padrao"].dropna().unique())
        standard = st.selectbox("Padrão Normativo", standards)
    df_filtered = df_base[df_base["padrao"] == standard]

    with col2:
        voltages = sorted(df_filtered["classe_tensao"].dropna().unique())
        voltage = st.selectbox("Classe de Tensão (kV)", voltages)
    df_filtered = df_filtered[df_filtered["classe_tensao"] == voltage]

    with col3:
        currents = sorted(df_filtered["classe_corrente"].dropna().unique())
        current = st.selectbox("Classe de Corrente (A)", currents)
    df_filtered = df_filtered[df_filtered["classe_corrente"] == current]

    st.header("2. Seleção do Produto")
    if df_filtered.empty:
        st.warning("Nenhum produto encontrado para a combinação inicial selecionada.")
        return

    product_options = df_filtered["nome_exibicao"].dropna().unique()
    product_name = st.selectbox("Família do Produto", product_options)

    if not product_name:
        return

    selected_product_series = df_filtered[df_filtered["nome_exibicao"] == product_name]
    if selected_product_series.empty:
        return

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
        base_code = selected_product.get("codigo_base", "")
        logic_id = selected_product.get("id_logica", "")
        st.info(f"Configurando produto: **{product_name}**  \nBase: `{base_code}`  \nLógica: `{logic_id}`")

        # Entradas comuns
        v_int = int(float(voltage)) if pd.notna(voltage) else 0
        i_int = int(float(current)) if pd.notna(current) else 0

        # Campos de diâmetro sobre isolação (faixa de cabo)
        d_iso = st.number_input("Ø sobre isolação do cabo (mm)", min_value=0.0, step=0.1, value=25.0)

        # Seleção de tipo de condutor e seção (para formar sufixos/códigos)
        # Para 200A usamos opcoes_condutores_v1; para 600A, opcoes_condutores_600a_v1
        df_cond_200 = db.get("opcoes_condutores_v1")
        df_cond_600 = db.get("opcoes_condutores_600a_v1")

        if logic_id == "LOGICA_COTOVELO_200A":
            if df_cond_200 is None:
                st.error("Tabela 'opcoes_condutores_v1.csv' não encontrada em /data.")
                return

            tipos = sorted(df_cond_200["tipo_condutor"].dropna().unique())
            tipo_cond = st.selectbox("Tipo de Condutor", tipos)
            tamanhos = sorted(df_cond_200[df_cond_200["tipo_condutor"] == tipo_cond]["secao_mm2"].dropna().astype(int).unique())
            secao = st.selectbox("Seção (mm²)", tamanhos)

            if st.button("Gerar Código do Cotovelo 200A"):
                range_code = find_cable_range_code(d_iso, v_int, i_int, db)   # usa tabelas opcoes_range_cabo_XXkv
                cond_code  = find_conductor_code_200a(tipo_cond, int(secao), db)  # 2 dígitos

                # Montagem do PN: Base + range + código condutor
                # Ex.: 15-LE200 + - + A/B/C... + - + 01/02...
                part_number = _hifen_join(base_code, range_code, cond_code)

                # Saída
                st.success(f"**Código final sugerido:** `{part_number}`")
                with st.expander("Detalhes da composição"):
                    st.write(f"- Base: `{base_code}`")
                    st.write(f"- Range (por Ø {d_iso:.1f} mm @ {v_int} kV): `{range_code}`")
                    st.write(f"- Condutor ({tipo_cond} {secao} mm²): `{cond_code}`")

                # Alertas de consistência
                if range_code in {"N/A", "ERR"}:
                    st.warning("Não foi possível determinar o **range de cabo** para o diâmetro informado.")
                if cond_code in {"NA", "ER"}:
                    st.warning("Não foi possível determinar o **código do condutor** com os parâmetros escolhidos.")

        elif logic_id == "LOGICA_CORPO_T_600A":
            if df_cond_600 is None:
                st.error("Tabela 'opcoes_condutores_600a_v1.csv' não encontrada em /data.")
                return

            tipos = sorted(df_cond_600["tipo_condutor"].dropna().unique())
            tipo_cond = st.selectbox("Tipo de Condutor", tipos)
            tamanhos = sorted(df_cond_600[df_cond_600["tipo_condutor"] == tipo_cond]["secao_mm2"].dropna().astype(int).unique())
            secao = st.selectbox("Seção (mm²)", tamanhos)

            if st.button("Gerar Código do Corpo em T 600A"):
                range_code = find_cable_range_code(d_iso, v_int, i_int, db)   # usa tabelas _600a quando corrente>=600
                lug_code   = find_compression_lug_600a(tipo_cond, int(secao), db)  # 4 dígitos

                # Montagem do PN: Base + range + código do lug
                part_number = _hifen_join(base_code, range_code, lug_code)

                st.success(f"**Código final sugerido:** `{part_number}`")
                with st.expander("Detalhes da composição"):
                    st.write(f"- Base: `{base_code}`")
                    st.write(f"- Range (por Ø {d_iso:.1f} mm @ {v_int} kV / {i_int} A): `{range_code}`")
                    st.write(f"- Lug ({tipo_cond} {secao} mm²): `{lug_code}`")

                if range_code in {"N/A", "ERR"}:
                    st.warning("Não foi possível determinar o **range de cabo** para o diâmetro informado.")
                if lug_code in {"NA", "ER"}:
                    st.warning("Não foi possível determinar o **código do lug** com os parâmetros escolhidos.")

        else:
            st.warning(f"A lógica de configuração para '{logic_id}' ainda não foi implementada.\n"
                       f"Cadastre o campo `id_logica` no 'produtos_base.csv' como "
                       f"`LOGICA_COTOVELO_200A` ou `LOGICA_CORPO_T_600A` para ativar as UIs acima.")


# --- ################################################################## ---
# --- ### LOGIC AND UI FOR TERMINATIONS                            ### ---
# --- ################################################################## ---

def termination_tol(tensao_term: str) -> float:
    return 2.0 if "15 kV" in tensao_term else 3.0

def suggest_termination_connector(s_mm2: int, kind: str, db: Dict[str, pd.DataFrame], material: Optional[str] = None) -> pd.DataFrame:
    """Sugere lugs para a seção informada."""
    df_conn = db["connector_selection_table"].copy()
    df_conn.columns = df_conn.columns.str.strip()

    # Garante colunas esperadas (após a normalização feita no load_database)
    need = ["Type", "Conductor Min (mm2)", "Conductor Max (mm2)"]
    missing = [c for c in need if c not in df_conn.columns]
    if missing:
        st.error(f"connector_selection_table.csv sem colunas: {missing}. Colunas: {list(df_conn.columns)}")
        return pd.DataFrame()

    # Tipos seguros
    df_conn["Type"] = df_conn["Type"].astype(str).str.lower()
    if "Material" in df_conn.columns:
        df_conn["Material"] = df_conn["Material"].astype(str).str.lower()
    df_conn["Conductor Min (mm2)"] = pd.to_numeric(df_conn["Conductor Min (mm2)"], errors="coerce")
    df_conn["Conductor Max (mm2)"] = pd.to_numeric(df_conn["Conductor Max (mm2)"], errors="coerce")

    # Filtros
    filtered = df_conn[df_conn["Type"] == kind.lower()]
    if kind.lower() == "compression" and material:
        filtered = filtered[filtered["Material"] == str(material).lower()]

    matches = filtered[
        (filtered["Conductor Min (mm2)"] <= s_mm2) &
        (filtered["Conductor Max (mm2)"] >= s_mm2)
    ].copy()

    if not matches.empty:
        matches["_span"] = matches["Conductor Max (mm2)"] - matches["Conductor Min (mm2)"]
        matches = matches.sort_values(by=["_span", "Conductor Min (mm2)"]).drop(columns=["_span"], errors="ignore")

    return matches

def render_termination_selector(db: Dict[str, pd.DataFrame]):
    """UI do seletor de terminações com estado de 'busca feita' persistente."""
    # Estado inicial
    st.session_state.setdefault("term_searched", False)
    st.session_state.setdefault("term_query_signature", "")

    st.header("1. Seleção do Cabo e Aplicação")

    df_cable = db["bitola_to_od"]
    CABLE_VOLTAGE_COL = "Cable Voltage"

    if CABLE_VOLTAGE_COL not in df_cable.columns:
        st.error(f"Coluna '{CABLE_VOLTAGE_COL}' não encontrada em bitola_to_od.csv.")
        return

    TENS_MAP = {"8.7/15 kV":"15 kV", "12/20 kV":"25 kV", "15/25 kV":"25 kV", "20/35 kV":"35 kV"}
    def _order_kv(t: str) -> float:
        m = re.match(r"([\d.]+)", t); return float(m.group(1)) if m else 1e9
    CABLE_VOLTAGES = sorted(df_cable[CABLE_VOLTAGE_COL].unique(), key=_order_kv)

    # Entradas (com keys para manter estado)
    env_choice = st.radio("Aplicação da terminação:", ("Externa (Outdoor)", "Interna (Indoor)"),
                          horizontal=True, key="env_term")
    know_iso = st.radio("Você já sabe o Ø sobre isolação do cabo?",
                        ("Não, preciso estimar pela bitola", "Sim, digitar valor real"),
                        key="know_iso")
    cabo_tensao = st.selectbox("Classe de tensão do cabo:", CABLE_VOLTAGES, key="volt_term")
    tensao_term = TENS_MAP.get(cabo_tensao, "")
    tolerance = termination_tol(tensao_term)

    # Derivados
    d_iso, s_mm2 = 0.0, 0.0
    if know_iso.startswith("Sim"):
        d_iso = st.number_input("Ø sobre isolação (mm)", min_value=0.0, step=0.1, key="dia_term")
        s_mm2 = st.selectbox("Seção nominal (mm²) para escolher lug:",
                             sorted(df_cable["S_mm2"].astype(float).unique()),
                             key="s_mm2_term_real")
        st.info(f"Ø sobre isolação informado: **{d_iso:.1f} mm**")
    else:
        filtro = df_cable[df_cable[CABLE_VOLTAGE_COL] == cabo_tensao]
        bitolas = sorted(filtro["S_mm2"].astype(float).unique())
        s_mm2 = st.selectbox("Seção nominal (mm²):", bitolas, key="s_mm2_term_est")
        linha = filtro[filtro["S_mm2"].astype(float) == float(s_mm2)]
        if not linha.empty:
            d_iso = float(linha.iloc[0]["OD_iso_mm"])
            st.info(f"Ø sobre isolação ESTIMADA: **{d_iso:.1f} mm ± {tolerance} mm**")
        else:
            st.warning("Não foi possível estimar o diâmetro para a bitola selecionada.")
            return

    # Assinatura dos parâmetros que DEFINEM a busca (não inclui material)
    signature = f"{env_choice}|{cabo_tensao}|{know_iso}|{s_mm2}|{d_iso:.3f}"

    # Se o usuário mudou algum parâmetro base, resetamos o estado da busca
    if signature != st.session_state.get("term_query_signature", ""):
        st.session_state["term_query_signature"] = signature
        st.session_state["term_searched"] = False

    col_a, col_b = st.columns([1,1])
    with col_a:
        if st.button("Buscar Terminação", key="btn_buscar"):
            st.session_state["term_searched"] = True
    with col_b:
        if st.button("Alterar parâmetros / Limpar resultados", key="btn_reset"):
            st.session_state["term_searched"] = False

    # RESULTADOS — ficam visíveis enquanto term_searched=True,
    # mesmo quando o usuário muda "Material" depois.
    if st.session_state["term_searched"]:
        st.header("2. Resultados da Busca")
        df_term = db["csto_selection_table"] if env_choice.startswith("Externa") else db["csti_selection_table"]
        family = "CSTO" if env_choice.startswith("Externa") else "CSTI"

        matches = df_term[
            (df_term["Voltage Class"] == tensao_term) &
            (df_term["OD Min (mm)"] <= d_iso + tolerance) &
            (df_term["OD Max (mm)"] >= d_iso - tolerance)
        ]

        if matches.empty:
            st.error(f"Nenhuma terminação {family} encontrada para ~{d_iso:.1f} mm.")
            return

        st.success(f"{len(matches)} terminação(ões) {family} compatível(is):")
        st.table(matches[["Part Number", "OD Min (mm)", "OD Max (mm)"]])

        st.header("3. Sugestão de Terminais (Lugs)")
        df_conn_table = db["connector_selection_table"].copy()

        # Opções de material só para compressão
        if "Type" in df_conn_table.columns:
            mask_comp = df_conn_table["Type"].astype(str).str.lower() == "compression"
            LUG_MATERIALS = sorted(df_conn_table.loc[mask_comp, "Material"].dropna().astype(str).unique())
        else:
            LUG_MATERIALS = sorted(df_conn_table.get("Material", pd.Series([], dtype=str)).dropna().astype(str).unique())

        conn_ui = st.selectbox("Tipo de Terminal:", ["Compressão", "Torquimétrico"], key="lug_type_term")
        kind = "compression" if conn_ui == "Compressão" else "shear-bolt"
        mat = st.selectbox("Material do terminal:", LUG_MATERIALS, key="lug_mat_term") if kind == "compression" else None

        # Chamada permanece estável — mudar 'mat' não derruba o bloco
        conn_df = suggest_termination_connector(int(float(s_mm2)), kind, db, mat)
        if conn_df.empty:
            st.error("Nenhum terminal/lug encontrado para a seção selecionada.")
        else:
            st.table(conn_df)


# --- ################################################################## ---
# --- ### MAIN APP ROUTER                                          ### ---
# --- ################################################################## ---

st.title("🛠️ Chardon Product Configurator Unificado")
# Simple text logo if image is not found
st.markdown("### Chardon")

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
    render_separable_connector_configurator(db) 
else:
    render_termination_selector(db)

