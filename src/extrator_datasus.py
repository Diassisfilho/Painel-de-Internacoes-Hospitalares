import pandas as pd
from pysus import sih, list_files
from datetime import datetime
import os

def obter_ultimo_mes_disponivel(estado='CE'):
    """Consulta o catálogo do PySUS e retorna o ano e mês mais recente
    disponível para AIH Reduzida (RD) do estado informado."""
    catalogo = list_files('sih', state=estado)

    # Filtrar apenas arquivos de AIH Reduzida (nome começa com RD)
    rd = catalogo[catalogo['name'].str.startswith('RD')]

    if rd.empty:
        return None, None

    rd_ordenado = rd.sort_values(['year', 'month'], ascending=False)
    mais_recente = rd_ordenado.iloc[0]
    return int(mais_recente['year']), int(mais_recente['month'])


def atualizar_dados_internacoes(estado='CE', ano=None, mes=None):
    if ano is None or mes is None:
        ano, mes = obter_ultimo_mes_disponivel(estado)
        if ano is None:
            print("Nenhum dado de AIH Reduzida disponível no catálogo.")
            return

    print(f"Baixando dados do SIH para {estado} - {mes:02d}/{ano}...")

    try:
        df_ceara = sih(
            state=estado,
            year=ano,
            month=mes,
            as_dataframe=True,
        )

        if df_ceara is not None and not df_ceara.empty:
            print(f"Dados brutos do Ceará: {len(df_ceara)} registros")

            df_ocara = df_ceara[
                df_ceara['MUNIC_RES'].astype(str).str.startswith('230930')
            ]
            print(f"Registros filtrados para Ocara (230930): {len(df_ocara)}")

            caminho_arquivo = 'dados/internacoes_ocara.csv'
            os.makedirs('dados', exist_ok=True)

            if os.path.exists(caminho_arquivo):
                df_existente = pd.read_csv(caminho_arquivo)
                df_final = pd.concat([df_existente, df_ocara]).drop_duplicates()
            else:
                df_final = df_ocara

            df_final.to_csv(caminho_arquivo, index=False)
            print(f"Dados atualizados com sucesso! Total de registros: {len(df_final)}")
        else:
            print("Nenhum dado retornado para o período solicitado.")

    except Exception as e:
        print(f"Erro na extração: {e}")
        raise


if __name__ == "__main__":
    atualizar_dados_internacoes(estado='CE')