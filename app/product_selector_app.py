# Streamlit Product Configurator for Chardon - UNIFIED & FIXED VERSION
import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, Optional
import re
import unicodedata
st.set_page_config(page_title="Chardon Product Configurator", page_icon=None, layout="wide")
import base64

def _read_file_as_b64(path: Path) -> str:
    if not path.exists():
        return ""
    return base64.b64encode(path.read_bytes()).decode()

def inject_global_css(bg_image: Path | None = None):
    st.markdown(
        """
        <style>
        .appview-container .main .block-container{ padding-top:2rem; padding-bottom:2rem; }
        .glass{ background:rgba(255,255,255,.66); border:1px solid rgba(0,0,0,.06);
                border-radius:16px; padding:18px 18px 12px; box-shadow:0 6px 18px rgba(0,0,0,.06);
                margin-bottom:12px; }
        .section-title{ font-weight:700; font-size:1.15rem; letter-spacing:.01em; margin:0 0 8px 0; }
        .section-sub{ margin-top:-6px; margin-bottom:8px; font-size:.9rem; opacity:.8; }
        .stButton>button{ border-radius:999px !important; padding:.55rem 1.05rem !important; }
        .chip{ display:inline-block; padding:.32rem .6rem; border-radius:999px; font-weight:700;
               letter-spacing:.02em; color:#fff; background:#10B981; margin-right:.5rem; }
        .code-pill{ display:inline-block; padding:.28rem .55rem; border-radius:10px;
                    background:rgba(0,0,0,.04); border:1px solid rgba(0,0,0,.08);
                    font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
        </style>
        """,
        unsafe_allow_html=True,
    )

def glass_header(title: str, subtitle: str = "", logo_b64: str | None = None):
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:40px;margin-right:12px;border-radius:6px;" />' if logo_b64 else ""
    st.markdown(
        f"""
        <div class="glass" style="display:flex;align-items:center;gap:12px;">
            {logo_html}
            <div>
                <div class="section-title">{title}</div>
                {f'<div class="section-sub">{subtitle}</div>' if subtitle else ''}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def section(title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div class="glass">
            <div class="section-title">{title}</div>
            {f'<div class="section-sub">{subtitle}</div>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True
    )

def chip_result(label: str, value: str):
    st.markdown(
        f"""
        <div class="glass">
            <span class="chip">{label}</span>
            <span class="code-pill">{value}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

DATA_DIR = Path(__file__).parent.parent / "data"
IMAGES_DIR = Path(__file__).parent.parent / "images"

inject_global_css(IMAGES_DIR / "bg-grid-dark.png")
logo64 = _read_file_as_b64(IMAGES_DIR / "logo-chardon.png")
glass_header("Chardon Product Configurator", "Separable Connectors · Terminations", logo64)

# ----------------------------- normalization -----------------------------
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", s.lower())

def _rename_like(df: pd.DataFrame, canonical: str, aliases: list[str]) -> None:
    current = { _norm(c): c for c in df.columns }
    canon_norm = _norm(canonical)
    for a in aliases:
        if _norm(a) in current:
            df.rename(columns={ current[_norm(a)]: canonical }, inplace=True)
            return
    if canon_norm in current and current[canon_norm] != canonical:
        df.rename(columns={ current[canon_norm]: canonical }, inplace=True)

def _normalize_bitola_to_od(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    _rename_like(df, "Cable Voltage", [
        "Cable Voltage","Voltage Class","Cable Voltage Class","Classe de Tensão",
        "Tensão do Cabo","Tensao do Cabo","Classe de tensao","Classe tensão"
    ])
    _rename_like(df, "S_mm2", ["S_mm2","S (mm2)","Seção (mm²)","Secao (mm2)","Seção nominal (mm²)","Secao nominal (mm2)","secao_mm2","Bitola (mm2)"])
    _rename_like(df, "Brand", ["Brand","Marca","Fabricante"])
    _rename_like(df, "Cable", ["Cable","Modelo","Tipo de Cabo","Cabo"])
    _rename_like(df, "OD_iso_mm", ["OD_iso_mm","OD sobre isolação (mm)","OD sobre isolacao (mm)","O.D. sobre isolação (mm)","Ø sobre isolação (mm)","OD_isol_mm","OD isol mm"])
    _rename_like(df, "D_cond_mm", ["D_cond_mm","Øcond (mm)","Diametro condutor (mm)","Diâmetro do condutor (mm)"])
    _rename_like(df, "T_iso_mm", ["T_iso_mm","Espessura Isol (mm)","Espessura de isolação (mm)","Espessura de isolacao (mm)"])
    for c in ["S_mm2","OD_iso_mm","D_cond_mm","T_iso_mm"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
    df.columns = df.columns.str.strip()
    return df

def _normalize_connector_table(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    _rename_like(df, "Type", ["Type","Tipo","Categoria","Connector Type","Tipo de Terminal"])
    _rename_like(df, "Material", ["Material","Material do Terminal","Material Terminal"])
    _rename_like(df, "Conductor Min (mm2)", ["Conductor Min (mm2)","Min (mm2)","Min Conductor (mm2)","Min Conductor (mm²)","Min(mm2)","Seção Min (mm²)","Secao Min (mm2)","Conductor_Min_mm2","Conductor_Min_(mm2)"])
    _rename_like(df, "Conductor Max (mm2)", ["Conductor Max (mm2)","Max (mm2)","Max Conductor (mm2)","Max Conductor (mm²)","Max(mm2)","Seção Max (mm²)","Secao Max (mm2)","Conductor_Max_mm2","Conductor_Max_(mm2)"])
    if "Type" in df.columns: df["Type"] = df["Type"].astype(str)
    if "Material" in df.columns: df["Material"] = df["Material"].astype(str)
    for c in ["Conductor Min (mm2)","Conductor Max (mm2)"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
    df.columns = df.columns.str.strip()
    return df

@st.cache_data
def load_database() -> Dict[str, pd.DataFrame]:
    if not DATA_DIR.exists():
        st.error(f"Data directory not found at: {DATA_DIR}")
        st.stop()
    db: Dict[str, pd.DataFrame] = {}
    for csv_file in DATA_DIR.glob("*.csv"):
        key = csv_file.stem
        try:
            df = pd.read_csv(csv_file); df.columns = df.columns.str.strip()
            db[key] = df
        except Exception as e:
            st.error(f"Error loading {csv_file.name}: {e}")
    required = ["produtos_base","bitola_to_od","csto_selection_table","csti_selection_table","connector_selection_table"]
    for f in required:
        if f not in db:
            st.error(f"Required file missing: {f}.csv"); st.stop()
    db["bitola_to_od"] = _normalize_bitola_to_od(db["bitola_to_od"])
    db["connector_selection_table"] = _normalize_connector_table(db["connector_selection_table"])
    missing = [c for c in ["Cable Voltage","S_mm2","OD_iso_mm"] if c not in db["bitola_to_od"].columns]
    if missing:
        st.error(f"'bitola_to_od.csv' is missing columns: {missing}"); st.stop()
    return db

# ----------------------------- common logic -----------------------------
def find_cable_range_code(
    diameter: float,
    voltage: int,
    current: int,
    db: Dict[str, pd.DataFrame],
    table_basename: str | None = None,
    *,
    cross_section_mm2: float | None = None,
) -> str:
    table_name = table_basename if table_basename else (f"opcoes_range_cabo_{voltage}kv_600a" if current >= 600 else f"opcoes_range_cabo_{voltage}kv")
    # alias: 15 kV / 600A uses the same as 25 kV / 600A
    alias_redirects = {
        "opcoes_range_cabo_15kv_600a": "opcoes_range_cabo_25kv_600a",
    }
    # alternative filenames that might appear in the data folder
    alternative_candidates = {
        "opcoes_range_cabo_iec_36kv_400a": [
            "options_range_cable_iec_36kv_400a",
            "option_range_cable_iec_36kv_400a",
            "options_range_cable_iec_36kV_400A",
            "option_range_cable_iec_36kV_400A",
        ],
    }

    if table_name not in db and table_name in alias_redirects:
        redirected = alias_redirects[table_name]
        if redirected in db:
            table_name = redirected

    if table_name not in db:
        for alt in alternative_candidates.get(table_name, []):
            if alt in db:
                table_name = alt
                break

    if table_name not in db:
        st.warning(f"Range table ('{table_name}.csv') not found.")
        return "ERR"
    df_range = db[table_name].copy()

    _rename_like(
        df_range,
        "min_mm",
        [
            "min_mm",
            "min (mm)",
            "minimo_mm",
            "min diameter",
            "diametro minimo (mm)",
            "diametro_min_mm",
        ],
    )
    _rename_like(
        df_range,
        "max_mm",
        [
            "max_mm",
            "max (mm)",
            "maximo_mm",
            "max diameter",
            "diametro maximo (mm)",
            "diametro_max_mm",
        ],
    )
    _rename_like(
        df_range,
        "min_mm2",
        [
            "min_mm2",
            "min (mm2)",
            "min_mm^2",
            "minimo_mm2",
            "secao_min_mm2",
            "bitola_min_mm2",
        ],
    )
    _rename_like(
        df_range,
        "max_mm2",
        [
            "max_mm2",
            "max (mm2)",
            "max_mm^2",
            "maximo_mm2",
            "secao_max_mm2",
            "bitola_max_mm2",
        ],
    )
    _rename_like(
        df_range,
        "codigo_retorno",
        [
            "codigo_retorno",
            "codigo",
            "code",
            "range_code",
        ],
    )

    has_diameter_bounds = {"min_mm", "max_mm"}.issubset(df_range.columns)
    has_cross_section_bounds = {"min_mm2", "max_mm2"}.issubset(df_range.columns)

    if "codigo_retorno" not in df_range.columns:
        st.warning(
            "Range table is missing the 'codigo_retorno' column. Please update the CSV."
        )
        return "ERR"

    if not has_diameter_bounds and not has_cross_section_bounds:
        st.warning(
            "Range table is missing required bounds (expected 'min_mm'/'max_mm' or 'min_mm2'/'max_mm2')."
        )
        return "ERR"

    if has_cross_section_bounds and not has_diameter_bounds:
        if cross_section_mm2 is None:
            st.warning(
                "This range table is defined in mm², but no conductor cross-section was provided."
            )
            return "ERR"
        comparison_value = cross_section_mm2
        min_col, max_col = "min_mm2", "max_mm2"
    else:
        comparison_value = diameter
        min_col, max_col = "min_mm", "max_mm"

    for col in (min_col, max_col):
        df_range[col] = pd.to_numeric(df_range[col], errors="coerce")

    df_range = df_range.dropna(subset=[min_col, max_col, "codigo_retorno"])

    for _, row in df_range.iterrows():
        try:
            min_val = float(row[min_col])
            max_val = float(row[max_col])
        except (TypeError, ValueError):
            continue
        if min_val <= comparison_value <= max_val:
            return str(row["codigo_retorno"]).strip()
    return "N/A"

def find_conductor_code_200a(cond_type: str, cond_size: int, db: Dict[str, pd.DataFrame]) -> str:
    if "opcoes_condutores_v1" not in db: return "ER"
    df_cond = db["opcoes_condutores_v1"]
    match = df_cond[(df_cond["tipo_condutor"] == cond_type) & (df_cond["secao_mm2"] == cond_size)]
    return str(int(match.iloc[0]["codigo_retorno"])).zfill(2) if not match.empty else "NA"

def find_compression_lug_600a(cond_type: str, cond_size: int, db: Dict[str, pd.DataFrame]) -> str:
    if "opcoes_condutores_600a_v1" not in db: return "ER"
    df_cond = db["opcoes_condutores_600a_v1"]
    match = df_cond[(df_cond["tipo_condutor"] == cond_type) & (df_cond["secao_mm2"] == cond_size)]
    return str(int(match.iloc[0]["codigo_retorno"])).zfill(4) if not match.empty else "NA"

def find_shear_bolt_lug(
    cond_size: float,
    db: Dict[str, pd.DataFrame],
    table_name: str | None = None
) -> str:
    """
    Busca o código do shear-bolt pela seção (mm²).
    table_name permite escolher a tabela (ex.: 'opcoes_shear_bolt_tb15_25' ou 'opcoes_shear_bolt_tb35').
    Se não for informado, cai no padrão 'opcoes_shear_bolt_v1'.
    """
    tn = table_name or "opcoes_shear_bolt_v1"
    if tn not in db:
        st.warning(f"Shear-bolt table ('{tn}.csv') not found.")
        return "ER"

    df_shear = db[tn].copy()
    for c in ["min_mm2", "max_mm2"]:
        if c in df_shear.columns:
            df_shear[c] = pd.to_numeric(df_shear[c], errors="coerce")

    for _, row in df_shear.iterrows():
        if row["min_mm2"] <= cond_size <= row["max_mm2"]:
            return str(row["codigo_retorno"])

    return "N/A"

def find_tsbc_lug_iec_36kv_400a(cond_size: float, db: Dict[str, pd.DataFrame]) -> str:
    """Return the TSBC lug code for the IEC 36 kV / 400 A product range."""
    table_candidates = [
        "opcoes_lugs_tsbc_iec_36kv_400a",
        "options_lugs_tsbc_iec_36kv_400a",
        "options_lugs_iec_36kv_400a",
    ]
    table_name = next((name for name in table_candidates if name in db), table_candidates[0])
    if table_name not in db:
        st.warning(f"TSBC table ('{table_name}.csv') not found.")
        return "ER"

    df = db[table_name].copy()
    _rename_like(df, "codigo_retorno", ["codigo_retorno", "codigo", "code", "tsbc_code"])
    _rename_like(
        df,
        "min_mm2",
        [
            "min_mm2",
            "min (mm2)",
            "minimo_mm2",
            "secao_min_mm2",
            "bitola_min_mm2",
        ],
    )
    _rename_like(
        df,
        "max_mm2",
        [
            "max_mm2",
            "max (mm2)",
            "maximo_mm2",
            "secao_max_mm2",
            "bitola_max_mm2",
        ],
    )

    for col in ("min_mm2", "max_mm2"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if not {"min_mm2", "max_mm2", "codigo_retorno"}.issubset(df.columns):
        st.warning(
            "TSBC table is missing required columns ('min_mm2', 'max_mm2', 'codigo_retorno')."
        )
        return "ER"

    for _, row in df.dropna(subset=["min_mm2", "max_mm2", "codigo_retorno"]).iterrows():
        if row["min_mm2"] <= float(cond_size) <= row["max_mm2"]:
            return str(row["codigo_retorno"]).strip()

    return "N/A"

def find_conductor_code_iec_400a(cond_type: Optional[str], cond_size: float, db: Dict[str, pd.DataFrame]) -> str:
    """Optional helper to fetch the IEC-specific conductor code (if available)."""
    table_candidates = [
        "opcoes_condutores_iec_400a_v1",
        "opcoes_condutores_iec_400a",
        "options_condutores_iec_400a_v1",
    ]
    table_name = next((name for name in table_candidates if name in db), table_candidates[0])
    if table_name not in db:
        return "NA"

    df = db[table_name].copy()
    if "secao_mm2" in df.columns:
        df["secao_mm2"] = pd.to_numeric(df["secao_mm2"], errors="coerce")

    candidates = df[df["secao_mm2"] == float(cond_size)] if "secao_mm2" in df.columns else df
    if cond_type and "tipo_condutor" in candidates.columns:
        candidates = candidates[candidates["tipo_condutor"] == cond_type]

    if candidates.empty:
        return "NA"

    code = candidates.iloc[0].get("codigo_retorno")
    if pd.isna(code):
        return "NA"
    return str(code).strip()

def _hifen_join(*parts) -> str:
    parts = [str(p).strip("-") for p in parts if p and str(p).upper() not in {"NA","N/A","ER","ERR"}]
    return "-".join(parts)

def _is_deadbreak(selected_product: pd.Series) -> bool:
    txt = (str(selected_product.get("padrao","")) + " " +
           str(selected_product.get("nome_exibicao","")) + " " +
           str(selected_product.get("range_tabela_tipo",""))).lower()
    return "deadbreak" in txt

# ----------------------------- UI: Separable Connectors -----------------------------
def render_separable_connector_configurator(db: Dict[str, pd.DataFrame]):
    section("1. Initial Connector Selection")
    df_base = db["produtos_base"].copy()

    col1, col2, col3 = st.columns(3)
    with col1:
        standards = sorted(df_base["padrao"].dropna().unique())
        standard = st.selectbox("Standard", standards)
    df_filtered = df_base[df_base["padrao"] == standard]

    with col2:
        voltages = sorted(df_filtered["classe_tensao"].dropna().unique())
        voltage = st.selectbox("Voltage Class (kV)", voltages)

    with col3:
        currents = sorted(df_filtered["classe_corrente"].dropna().unique())
        current = st.selectbox("Current Rating (A)", currents)

    # Deadbreak 600A at 15 kV should see 25 kV items (15/25-TB600)
    if "deadbreak" in standard.lower() and int(current) >= 600 and int(voltage) == 15:
        df_filtered = df_filtered[(df_filtered["classe_corrente"] == current) & (df_filtered["classe_tensao"].isin([15, 25]))]
    else:
        df_filtered = df_filtered[(df_filtered["classe_tensao"] == voltage) & (df_filtered["classe_corrente"] == current)]

    section("2. Product Selection")
    if df_filtered.empty:
        st.warning("No products found for the selected initial combination.")
        return

    product_options = df_filtered["nome_exibicao"].dropna().unique()
    product_name = st.selectbox("Product Family", product_options)
    if not product_name: return

    selected_product_series = df_filtered[df_filtered["nome_exibicao"] == product_name]
    if selected_product_series.empty: return
    selected_product = selected_product_series.iloc[0]

    section("3. Product Configuration")
    col_config, col_img = st.columns([2, 1])

    with col_img:
        image_filename = selected_product.get("imagem_arquivo")
        if image_filename and isinstance(image_filename, str):
            image_path = IMAGES_DIR / image_filename
            if image_path.exists(): st.image(str(image_path), caption=product_name)
            else: st.warning(f"Image '{image_filename}' not found.")
        else:
            st.info("No image registered.")

    with col_config:
        base_code_raw = str(selected_product.get("codigo_base", "")).strip()
        logic_id  = selected_product.get("id_logica", "")

        v_int = int(float(voltage)) if pd.notna(voltage) else 0
        i_int = int(float(current)) if pd.notna(current) else 0
        d_iso = st.number_input("Cable insulation diameter (mm)", min_value=0.0, step=0.1, value=25.0)

        # If entering via 15 kV for TB600, use 15/25-TB600 in the Part Number
        if ("deadbreak" in standard.lower() and i_int >= 600 and "t-body" in product_name.lower() and v_int in (15, 25)):
            base_code = "15/25-TB600"
        else:
            base_code = base_code_raw

        df_cond_200 = db.get("opcoes_condutores_v1")
        df_cond_600 = db.get("opcoes_condutores_600a_v1")

        # ----------------- ELBOW 200A (Loadbreak & Deadbreak) -----------------
        if logic_id in {"LOGICA_COTOVELO_200A","LOGICA_DEADBREAK_ELBOW_200A","LOGICA_ELBOW_200A"}:
            if df_cond_200 is None:
                st.error("Table 'opcoes_condutores_v1.csv' not found in /data.")
                return

            tipos = sorted(df_cond_200["tipo_condutor"].dropna().unique())
            tipo_cond = st.selectbox("Conductor Type", tipos)
            tamanhos_series = df_cond_200[df_cond_200["tipo_condutor"] == tipo_cond]["secao_mm2"]
            tamanhos = sorted(tamanhos_series.dropna().astype(int).unique())

            if tamanhos:
                secao = st.selectbox("Conductor Cross Section (mm²)", tamanhos)
            else:
                st.warning(
                    "No conductor cross-sections found for the selected type. "
                    "Please enter the value manually."
                )
                secao = int(
                    st.number_input(
                        "Conductor Cross Section (mm²)",
                        min_value=1,
                        step=1,
                        value=95,
                        key="manual_cross_section_200a",
                    )
                )

            # Reactive elbow options
            add_test_point = st.checkbox("Capacitive Test Point (W = T)", value=False)
            connector_material = st.radio(
                "Connector Type",
                ["None", "Copper (Z = C)", "Bi-metal (Z = B)"],
                horizontal=True
            )

            # --- Reactive Part Number ---
            table_base = f"opcoes_range_cabo_{v_int}kv_deadbreak" if _is_deadbreak(selected_product) else None
            range_code = find_cable_range_code(d_iso, v_int, i_int, db, table_basename=table_base)
            cond_code  = find_conductor_code_200a(tipo_cond, int(secao), db)

            w_code = "T" if add_test_point else ""
            if connector_material.startswith("Tinned Copper"): z_code = "C"
            elif connector_material.startswith("Bi-metal"): z_code = "B"
            else: z_code = ""

            part_number = _hifen_join(base_code, w_code, range_code, cond_code, z_code)
            chip_result("Suggested Code", part_number)

            if range_code in {"N/A","ERR"}:
                st.warning("Could not determine the **cable range** for the specified diameter.")
            if cond_code in {"NA","ER"}:
                st.warning("Could not determine the **conductor code** with the chosen parameters.")

        # ----------------- T-Body 600A -----------------
        elif logic_id == "LOGICA_CORPO_T_600A":
            if df_cond_600 is None:
                st.error("Table 'opcoes_condutores_600a_v1.csv' not found in /data.")
                return
            tipos = sorted(df_cond_600["tipo_condutor"].dropna().unique())
            tipo_cond = st.selectbox("Conductor Type", tipos)
            tamanhos_series = df_cond_600[df_cond_600["tipo_condutor"] == tipo_cond]["secao_mm2"]
            tamanhos = sorted(tamanhos_series.dropna().astype(int).unique())

            if tamanhos:
                secao = st.selectbox("Conductor Cross Section (mm²)", tamanhos)
            else:
                st.warning(
                    "No conductor cross-sections found for the selected type. "
                    "Please enter the value manually."
                )
                secao = int(
                    st.number_input(
                        "Conductor Cross Section (mm²)",
                        min_value=1,
                        step=1,
                        value=185,
                        key="manual_cross_section_600a",
                    )
                )

            # Reactive options
            add_test_point = st.checkbox("Capacitive Test Point (W = T)", value=False)
            connector_type = st.radio("Connector Type", ["Compression", "Shear-Bolt"], horizontal=True)

            # --- Reactive Part Number ---
            range_code = find_cable_range_code(d_iso, v_int, i_int, db)
            w_code = "T" if add_test_point else ""

            if connector_type == "Compression":
                lug_code = find_compression_lug_600a(tipo_cond, int(secao), db)
                part_number = _hifen_join(base_code, w_code, range_code, lug_code)
                chip_result("Suggested Code", part_number)
            else:
                sb_table = "opcoes_shear_bolt_tb15_25" if v_int in {15, 25} else "opcoes_shear_bolt_tb35"
                sb_code = find_shear_bolt_lug(float(secao), db, table_name=sb_table)
                part_number = _hifen_join(base_code, w_code, range_code, sb_code)
                chip_result("Suggested Code", part_number)
                if sb_code in {"N/A","ER"}:
                    st.warning("Could not determine the **shear-bolt code** for the chosen cross-section.")

            if range_code in {"N/A","ERR"}:
                st.warning("Could not determine the **cable range** for the specified diameter.")

        elif logic_id == "LOGICA_TBODY_IEC_400A":
            df_cond_iec = (
                db.get("opcoes_condutores_iec_400a_v1")
                or db.get("opcoes_condutores_iec_400a")
                or db.get("options_condutores_iec_400a_v1")
            )

            secao: float
            tipo_cond: Optional[str]

            DEFAULT_IEC_SIZES = [25, 35, 50, 70, 95, 120, 150, 185, 240, 300, 400]
            size_options: list[float] = []

            if df_cond_iec is not None and not df_cond_iec.empty:
                df_cond_iec = df_cond_iec.copy()
                if "secao_mm2" in df_cond_iec.columns:
                    df_cond_iec["secao_mm2"] = pd.to_numeric(df_cond_iec["secao_mm2"], errors="coerce")
                    df_cond_iec = df_cond_iec.dropna(subset=["secao_mm2"])

                if "tipo_condutor" in df_cond_iec.columns:
                    df_cond_iec["tipo_condutor"] = df_cond_iec["tipo_condutor"].astype(str)
                    cond_types = sorted(df_cond_iec["tipo_condutor"].dropna().unique())
                else:
                    cond_types = []

                if cond_types:
                    tipo_cond = st.selectbox("Conductor Type", cond_types)
                    filtered = df_cond_iec[df_cond_iec["tipo_condutor"] == tipo_cond]
                else:
                    tipo_cond = None
                    filtered = df_cond_iec

                if "secao_mm2" in filtered.columns:
                    size_options = sorted(filtered["secao_mm2"].dropna().astype(float).unique())
            else:
                tipo_cond = None

            if not size_options:
                st.warning(
                    "No IEC conductor catalog sizes found. Showing a default list of cross-sections."
                )
                size_options = DEFAULT_IEC_SIZES

            def _format_mm2(value: float) -> str:
                return (
                    f"{int(value)}"
                    if float(value).is_integer()
                    else f"{value:.1f}".rstrip("0").rstrip(".")
                )

            secao = float(
                st.selectbox(
                    "Conductor Cross Section (mm²)",
                    options=size_options,
                    format_func=_format_mm2,
                )
            )

            material_cols = st.columns(2)
            selected_materials: list[tuple[str, str]] = []
            with material_cols[0]:
                if st.checkbox("B – Bi-metal (Al & Cu)", value=True, key="iec_mat_b"):
                    selected_materials.append(("B", "Bi-metal (Al & Cu)"))
            with material_cols[1]:
                if st.checkbox("C – Copper", value=False, key="iec_mat_c"):
                    selected_materials.append(("C", "Copper"))

            range_code = find_cable_range_code(
                d_iso,
                v_int,
                i_int,
                db,
                table_basename="opcoes_range_cabo_iec_36kv_400a",
                cross_section_mm2=secao,
            )
            tsbc_code = find_tsbc_lug_iec_36kv_400a(float(secao), db)
            conductor_code = find_conductor_code_iec_400a(tipo_cond, float(secao), db)

            def _materialize_tsbc(base_code: str, material_code: str) -> str:
                if not base_code or base_code.upper() in {"NA", "N/A", "ER", "ERR"}:
                    return base_code
                normalized = str(base_code).strip()
                if normalized.upper().startswith("TSBC"):
                    return normalized.replace("TSBC", f"TSBC-{material_code}", 1)
                return f"{material_code}-{normalized}"

            if not selected_materials:
                st.info("Select at least one lug material (B or C) to build the part number.")
            else:
                for material_code, material_label in selected_materials:
                    tsbc_final = _materialize_tsbc(tsbc_code, material_code)
                    part_number = _hifen_join(base_code, range_code, conductor_code, tsbc_final)
                    chip_result(f"Suggested Code ({material_label})", part_number)

            if range_code in {"N/A", "ERR"}:
                st.warning("Could not determine the **cable range** for the specified diameter.")
            if tsbc_code in {"N/A", "ER", "ERR"}:
                st.warning("Could not determine the **TSBC lug** for the selected cross-section.")
            if conductor_code in {"NA", "ER"}:
                st.info("No IEC conductor catalog code was matched. It will be omitted from the part number.")

        else:
            st.warning(
                f"Logic '{logic_id}' is not yet implemented. "
                "Use `LOGICA_ELBOW_200A` (or `LOGICA_COTOVELO_200A`/`LOGICA_DEADBREAK_ELBOW_200A`) or `LOGICA_CORPO_T_600A`."
            )

# ----------------------------- UI: Terminations -----------------------------
def termination_tol(tensao_term: str) -> float:
    return 2.0 if "15 kV" in tensao_term else 3.0

def suggest_termination_connector(s_mm2: int, kind: str, db: Dict[str, pd.DataFrame], material: Optional[str] = None) -> pd.DataFrame:
    df_conn = db["connector_selection_table"].copy()
    df_conn.columns = df_conn.columns.str.strip()
    need = ["Type","Conductor Min (mm2)","Conductor Max (mm2)"]
    missing = [c for c in need if c not in df_conn.columns]
    if missing:
        st.error(f"connector_selection_table.csv is missing columns: {missing}. Columns present: {list(df_conn.columns)}")
        return pd.DataFrame()
    df_conn["Type"] = df_conn["Type"].astype(str).str.lower()
    if "Material" in df_conn.columns: df_conn["Material"] = df_conn["Material"].astype(str).str.lower()
    df_conn["Conductor Min (mm2)"] = pd.to_numeric(df_conn["Conductor Min (mm2)"], errors="coerce")
    df_conn["Conductor Max (mm2)"] = pd.to_numeric(df_conn["Conductor Max (mm2)"], errors="coerce")
    filtered = df_conn[df_conn["Type"] == kind.lower()]
    if kind.lower() == "compression" and material:
        filtered = filtered[filtered["Material"] == str(material).lower()]
    matches = filtered[(filtered["Conductor Min (mm2)"] <= s_mm2) & (filtered["Conductor Max (mm2)"] >= s_mm2)].copy()
    if not matches.empty:
        matches["_span"] = matches["Conductor Max (mm2)"] - matches["Conductor Min (mm2)"]
        matches = matches.sort_values(by=["_span","Conductor Min (mm2)"]).drop(columns=["_span"], errors="ignore")
    return matches

def render_termination_selector(db: Dict[str, pd.DataFrame]):
    st.session_state.setdefault("term_searched", False)
    st.session_state.setdefault("term_query_signature", "")

    section("1. Cable and Application Selection")
    df_cable = db["bitola_to_od"]; CABLE_VOLTAGE_COL = "Cable Voltage"
    if CABLE_VOLTAGE_COL not in df_cable.columns:
        st.error(f"Column '{CABLE_VOLTAGE_COL}' not found in bitola_to_od.csv."); return
    TENS_MAP = {"8.7/15 kV":"15 kV","12/20 kV":"25 kV","15/25 kV":"25 kV","20/35 kV":"35 kV"}
    def _order_kv(t: str) -> float:
        m = re.match(r"([\d.]+)", t); return float(m.group(1)) if m else 1e9
    CABLE_VOLTAGES = sorted(df_cable[CABLE_VOLTAGE_COL].unique(), key=_order_kv)

    env_choice = st.radio("Termination Application:", ("Outdoor","Indoor"), horizontal=True, key="env_term")
    know_iso   = st.radio("Do you know the cable insulation diameter?", ("No, estimate by size","Yes, enter value"), key="know_iso")
    cabo_tensao = st.selectbox("Cable voltage class:", CABLE_VOLTAGES, key="volt_term")
    tensao_term = TENS_MAP.get(cabo_tensao, ""); tolerance = termination_tol(tensao_term)

    d_iso, s_mm2 = 0.0, 0.0
    if know_iso.startswith("Yes"):
        d_iso = st.number_input("Insulation diameter (mm)", min_value=0.0, step=0.1, key="dia_term")
        s_mm2 = st.selectbox("Nominal cross-section (mm²) to select lug:", sorted(df_cable["S_mm2"].astype(float).unique()), key="s_mm2_term_real")
        st.info(f"Provided insulation diameter: **{d_iso:.1f} mm**")
    else:
        filtro = df_cable[df_cable[CABLE_VOLTAGE_COL] == cabo_tensao]
        bitolas = sorted(filtro["S_mm2"].astype(float).unique())
        s_mm2 = st.selectbox("Nominal cross-section (mm²):", bitolas, key="s_mm2_term_est")
        linha = filtro[filtro["S_mm2"].astype(float) == float(s_mm2)]
        if not linha.empty:
            d_iso = float(linha.iloc[0]["OD_iso_mm"])
            st.info(f"ESTIMATED insulation diameter: **{d_iso:.1f} mm ± {tolerance} mm**")
        else:
            st.warning("Could not estimate the diameter for the selected size."); return

    signature = f"{env_choice}|{cabo_tensao}|{know_iso}|{s_mm2}|{d_iso:.3f}"
    if signature != st.session_state.get("term_query_signature",""):
        st.session_state["term_query_signature"] = signature
        st.session_state["term_searched"] = False

    col_a, col_b = st.columns([1,1])
    with col_a:
        if st.button("Search for Termination", key="btn_buscar"): st.session_state["term_searched"] = True
    with col_b:
        if st.button("Change parameters / Clear results", key="btn_reset"): st.session_state["term_searched"] = False

    if st.session_state["term_searched"]:
        section("2. Search Results")
        df_term = db["csto_selection_table"] if env_choice.startswith("Outdoor") else db["csti_selection_table"]
        family = "CSTO" if env_choice.startswith("Outdoor") else "CSTI"
        matches = df_term[(df_term["Voltage Class"] == tensao_term) &
                          (df_term["OD Min (mm)"] <= d_iso + tolerance) &
                          (df_term["OD Max (mm)"] >= d_iso - tolerance)]
        if matches.empty:
            st.error(f"No {family} termination found for ~{d_iso:.1f} mm."); return
        chip_result("Compatible Terminations", str(len(matches)))
        st.table(matches[["Part Number","OD Min (mm)","OD Max (mm)"]])

        section("3. Suggested Terminals (Lugs)")
        df_conn_table = db["connector_selection_table"].copy()
        if "Type" in df_conn_table.columns:
            mask_comp = df_conn_table["Type"].astype(str).str.lower() == "compression"
            LUG_MATERIALS = sorted(df_conn_table.loc[mask_comp,"Material"].dropna().astype(str).unique())
        else:
            LUG_MATERIALS = sorted(df_conn_table.get("Material", pd.Series([], dtype=str)).dropna().astype(str).unique())

        conn_ui = st.selectbox("Terminal Type:", ["Compression","Shear-Bolt"], key="lug_type_term")
        kind = "compression" if conn_ui == "Compression" else "shear-bolt"
        mat  = st.selectbox("Terminal Material:", LUG_MATERIALS, key="lug_mat_term") if kind=="compression" else None

        conn_df = suggest_termination_connector(int(float(s_mm2)), kind, db, mat)
        if conn_df.empty: st.error("No terminal/lug found for the selected cross-section.")
        else:
            st.info("Suggested terminals (closest range first):")
            st.table(conn_df)

# ----------------------------- router -----------------------------
try:
    db = load_database()
except Exception as e:
    st.error(f"Critical failure while loading data files. Please check the 'data' folder. Error: {e}")
    st.stop()

section("Select Product Line")
product_line = st.selectbox("**Select Product Line:**", ["Separable Connectors","Terminations"])
if product_line == "Separable Connectors":
    render_separable_connector_configurator(db)
else:
    render_termination_selector(db)