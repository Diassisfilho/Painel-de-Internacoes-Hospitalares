from pysus import sih
import pyarrow.parquet as pq
import pandas as pd
import os

os.makedirs('dados', exist_ok=True)
caminho = 'dados/internacoes_ocara.csv'

meses = [
    (2025, 1), (2025, 2), (2025, 3), (2025, 4), (2025, 5), (2025, 6),
    (2025, 7), (2025, 8), (2025, 9), (2025, 10), (2025, 11), (2025, 12),
]

total = 0
header = True

for ano, mes in meses:
    print(f'Baixando {mes:02d}/{ano}...', flush=True)
    try:
        paths = sih(state='CE', year=ano, month=mes)
        if not paths:
            print('  -> sem dados', flush=True)
            continue
        for p in paths:
            schema = pq.read_schema(p)
            if 'MUNIC_RES' not in schema.names:
                print(f'  -> {os.path.basename(p)} sem MUNIC_RES, ignorado', flush=True)
                continue
            table = pq.read_table(p, filters=[('MUNIC_RES', '==', '230930')])
            if table.num_rows == 0:
                table2 = pq.read_table(p, filters=[('MUNIC_RES', '==', 230930)])
                if table2.num_rows > 0:
                    table = table2
            df_ocara = table.to_pandas()
            del table
            if df_ocara.empty:
                print(f'  -> 0 registros de Ocara', flush=True)
                del df_ocara
                continue
            df_ocara.to_csv(caminho, mode='a', index=False, header=header)
            header = False
            n = len(df_ocara)
            total += n
            print(f'  -> {n} registros de Ocara', flush=True)
            del df_ocara
    except Exception as e:
        print(f'  -> erro: {e}', flush=True)

print(f'Total salvo: {total} registros')
