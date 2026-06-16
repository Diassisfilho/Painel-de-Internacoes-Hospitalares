"""
Atualiza base com dados de 2023-2025 (3 anos) - equilíbrio entre série temporal rica e leveza.
Estimativa: ~1000-1500 linhas, <2MB, carregamento <1s.
"""
from pysus import sih
import pyarrow.parquet as pq
import pandas as pd
import os

os.makedirs('dados', exist_ok=True)
caminho = 'dados/internacoes_ocara.csv'
caminho_backup = 'dados/internacoes_ocara_backup_2025.csv'

# Backup atual se existir
if os.path.exists(caminho):
    df_existente = pd.read_csv(caminho, low_memory=False)
    df_existente.to_csv(caminho_backup, index=False)
    print(f"Backup: {len(df_existente)} registros de 2025 preservados em {caminho_backup}")
    # Usar N_AIH para deduplicação
    existentes_n_aih = set(df_existente['N_AIH'].astype(str)) if 'N_AIH' in df_existente.columns else set()
    print(f"N_AIH existentes: {len(existentes_n_aih)}")
else:
    df_existente = pd.DataFrame()
    existentes_n_aih = set()

# Intervalo balanceado: 2023-2025 (3 anos, 36 meses)
# Pesagem: cada ano tem ~200-700 registros para Ocara (município pequeno)
# Total estimado: 800-1500 linhas, ideal para dashboard
anos_meses = []
for ano in [2023, 2024, 2025]:
    for mes in range(1, 13):
        anos_meses.append((ano, mes))

print(f"Buscando {len(anos_meses)} competências (2023-2025)...")

total_novo = 0
novos_dfs = []
# Para deduplicação em memória
vistos = set(existentes_n_aih)

for ano, mes in anos_meses:
    print(f'Baixando {mes:02d}/{ano}...', flush=True)
    try:
        paths = sih(state='CE', year=ano, month=mes)
        if not paths:
            print('  -> sem dados', flush=True)
            continue
        for p in paths:
            try:
                schema = pq.read_schema(p)
                if 'MUNIC_RES' not in schema.names:
                    continue
                # Tenta filtro string e numérico
                table = pq.read_table(p, filters=[('MUNIC_RES', '==', '230930')])
                if table.num_rows == 0:
                    table = pq.read_table(p, filters=[('MUNIC_RES', '==', 230930)])
                if table.num_rows == 0:
                    continue
                df_ocara = table.to_pandas()
                del table
                if df_ocara.empty:
                    del df_ocara
                    continue
                # Deduplica por N_AIH antes de acumular
                if 'N_AIH' in df_ocara.columns:
                    mask_novo = ~df_ocara['N_AIH'].astype(str).isin(vistos)
                    df_ocara = df_ocara[mask_novo]
                    if df_ocara.empty:
                        print(f'  -> {os.path.basename(p)}: 0 novos (já existentes)', flush=True)
                        continue
                    vistos.update(df_ocara['N_AIH'].astype(str).tolist())
                
                novos_dfs.append(df_ocara)
                n = len(df_ocara)
                total_novo += n
                print(f'  -> {n} novos registros de Ocara', flush=True)
                del df_ocara
            except Exception as e:
                print(f'  -> erro leitura {os.path.basename(p)}: {e}', flush=True)
                continue
    except Exception as e:
        print(f'  -> erro {ano}-{mes:02d}: {e}', flush=True)
        continue

print(f"\nTotal novos coletados: {total_novo}")

if novos_dfs:
    df_novos = pd.concat(novos_dfs, ignore_index=True)
    print(f"Concatenados: {len(df_novos)} novos")
    # Merge com existente e deduplica final
    if not df_existente.empty:
        df_final = pd.concat([df_existente, df_novos], ignore_index=True)
        # Deduplica por N_AIH
        if 'N_AIH' in df_final.columns:
            antes = len(df_final)
            df_final = df_final.drop_duplicates(subset=['N_AIH'], keep='first')
            print(f"Deduplicação: {antes} -> {len(df_final)} (removidos {antes-len(df_final)})")
    else:
        df_final = df_novos
    
    # Ordena por ano/mês para série temporal consistente
    if 'ANO_CMPT' in df_final.columns and 'MES_CMPT' in df_final.columns:
        df_final = df_final.sort_values(['ANO_CMPT', 'MES_CMPT'])
    
    df_final.to_csv(caminho, index=False)
    print(f"\nBase atualizada! Total: {len(df_final)} registros")
    print(f"Períodos: {sorted(df_final['ANO_CMPT'].astype(str) + '-' + df_final['MES_CMPT'].astype(str).str.zfill(2).astype(str).tolist())[:5]} ... {sorted(df_final['ANO_CMPT'].astype(str) + '-' + df_final['MES_CMPT'].astype(str).str.zfill(2).astype(str).tolist())[-5:]}")
    print(f"Anos: {sorted(df_final['ANO_CMPT'].unique())}")
    print(f"Tamanho: {os.path.getsize(caminho)/1024:.1f} KB, Memória: {df_final.memory_usage(deep=True).sum()/1024/1024:.2f} MB")
    print(f"Distribuição por ano:\n{df_final['ANO_CMPT'].value_counts().sort_index()}")
else:
    print("Nenhum dado novo encontrado. Base mantida.")
    if not df_existente.empty:
        print(f"Base atual: {len(df_existente)} registros")
