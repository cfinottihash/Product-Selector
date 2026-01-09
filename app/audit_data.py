import pandas as pd
from pathlib import Path
import sys

# Ajuste para garantir que o Python veja a pasta atual
sys.path.append(".")

def _norm_voltage(v_str):
    if "15" in v_str: return "15 kV"
    if "25" in v_str or "24" in v_str or "20" in v_str: return "25 kV"
    if "35" in v_str: return "35 kV"
    return v_str

def run_audit():
    print("--- GERANDO LISTA DE CABOS PROBLEMÁTICOS ---")
    
    try:
        df_cabos = pd.read_csv("data/bitola_to_od.csv").rename(columns=lambda x: x.strip())
        df_terms = pd.read_csv("data/csto_selection_table.csv").rename(columns=lambda x: x.strip())
    except Exception as e:
        print(f"ERRO: {e}")
        return

    lista_negra = [] 
    grupos = df_cabos.groupby(['Cable Voltage', 'S_mm2'])

    for (voltagem, bitola), grupo_df in grupos:
        od_med = grupo_df['OD_iso_mm'].median()
        v_norm = _norm_voltage(voltagem)

        # Simula a escolha do App
        pecas = df_terms[
            (df_terms['Voltage Class'] == v_norm) &
            (df_terms['OD Min (mm)'] <= od_med) &
            (df_terms['OD Max (mm)'] >= od_med)
        ]

        if pecas.empty:
            continue # Se não tem peça, não adiciona ao alerta específico (é outro tipo de erro)

        # Pega a peça escolhida
        pecas = pecas.copy()
        pecas['_span'] = pecas['OD Max (mm)'] - pecas['OD Min (mm)']
        peca_escolhida = pecas.sort_values('_span').iloc[0]
        
        t_min = peca_escolhida['OD Min (mm)']
        t_max = peca_escolhida['OD Max (mm)']

        # Verifica quem falha
        for _, row in grupo_df.iterrows():
            od_real = row['OD_iso_mm']
            if not (t_min <= od_real <= t_max):
                lista_negra.append({
                    "Cable Voltage": voltagem, # Manter nome exato da coluna original
                    "S_mm2": bitola,           # Manter nome exato
                    "Brand": row.get('Brand', 'Unknown'),
                    "Cable": row.get('Cable', 'Unknown'),
                    "Reason": "Too Thin" if od_real < t_min else "Too Thick"
                })

    # SALVAR O ARQUIVO CSV
    file_path = Path("data/problematic_cables.csv")
    if lista_negra:
        df_out = pd.DataFrame(lista_negra)
        df_out.to_csv(file_path, index=False)
        print(f"✅ ARQUIVO GERADO: {file_path} com {len(df_out)} alertas.")
        print(df_out.head())
    else:
        # Se não houver problemas, cria um arquivo vazio com cabeçalho para não quebrar o app
        pd.DataFrame(columns=["Cable Voltage", "S_mm2", "Brand", "Cable", "Reason"]).to_csv(file_path, index=False)
        print("✅ NENHUM PROBLEMA ENCONTRADO. Arquivo vazio gerado.")

if __name__ == "__main__":
    run_audit()