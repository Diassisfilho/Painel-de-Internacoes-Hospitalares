import pandas as pd
from pysus import sih, list_files
from datetime import datetime, timezone
import json
import os
import pyarrow.parquet as pq

def obter_ultimo_mes_disponivel(estado='CE'):
    """Consulta o catálogo do PySUS e retorna o ano e mês mais recente
    disponível para AIH Reduzida (RD) do estado informado."""
    catalogo = list_files('sih', state=estado)

    if catalogo is None or catalogo.empty or 'name' not in catalogo.columns:
        return None, None

    # Filtrar apenas arquivos de AIH Reduzida (nome começa com RD)
    try:
        rd = catalogo[catalogo['name'].astype(str).str.startswith('RD')]
    except Exception:
        return None, None

    if rd.empty:
        return None, None

    rd_ordenado = rd.sort_values(['year', 'month'], ascending=False)
    mais_recente = rd_ordenado.iloc[0]
    return int(mais_recente['year']), int(mais_recente['month'])


def _escrever_log(status, mensagem, ano=None, mes=None, total_registros=None, periodo_mais_recente=None):
    """Escreve log JSON verificado pelo dashboard em dados/ultima_atualizacao.json"""
    try:
        from zoneinfo import ZoneInfo
        tz_brasil = ZoneInfo("America/Fortaleza")
        agora_utc = datetime.now(timezone.utc)
        agora_brasil = agora_utc.astimezone(tz_brasil)
    except Exception:
        agora_utc = datetime.now(timezone.utc)
        agora_brasil = agora_utc
        tz_brasil = None

    # Tenta obter total atual se não informado
    if total_registros is None:
        try:
            caminho = 'dados/internacoes_ocara.csv'
            if os.path.exists(caminho):
                df_tmp = pd.read_csv(caminho, usecols=['ANO_CMPT', 'MES_CMPT'])
                total_registros = len(df_tmp)
                if periodo_mais_recente is None and not df_tmp.empty:
                    df_tmp['ANO_CMPT'] = pd.to_numeric(df_tmp['ANO_CMPT'], errors='coerce')
                    df_tmp['MES_CMPT'] = pd.to_numeric(df_tmp['MES_CMPT'], errors='coerce')
                    df_tmp = df_tmp.dropna(subset=['ANO_CMPT', 'MES_CMPT'])
                    if not df_tmp.empty:
                        df_tmp = df_tmp.sort_values(['ANO_CMPT', 'MES_CMPT'])
                        ult = df_tmp.iloc[-1]
                        periodo_mais_recente = f"{int(ult['ANO_CMPT']):04d}-{int(ult['MES_CMPT']):02d}"
            else:
                total_registros = 0
        except Exception:
            total_registros = total_registros or 0

    log = {
        "data_ultima_atualizacao_utc": agora_utc.isoformat().replace("+00:00", "Z"),
        "data_ultima_atualizacao_brasil": agora_brasil.strftime("%d/%m/%Y %H:%M:%S %Z") if tz_brasil else agora_brasil.isoformat(),
        "timestamp_unix": int(agora_utc.timestamp()),
        "status": status,
        "mensagem": mensagem,
        "ano_solicitado": ano,
        "mes_solicitado": mes,
        "periodo_mais_recente": periodo_mais_recente,
        "total_registros": total_registros,
        "origem": "DATASUS/SIH via PySUS",
        "workflow": "github-actions",
        "frequencia": "2x por mês (dias 1 e 15 às 03:00 UTC)"
    }

    os.makedirs('dados', exist_ok=True)
    caminho_log = 'dados/ultima_atualizacao.json'
    with open(caminho_log, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print(f"Log salvo em {caminho_log}: {status} - {mensagem}")
    return log


def _obter_ultimo_periodo_local():
    """Retorna (ano, mes) do último período presente no CSV local, ou (None, None) se vazio."""
    caminho = 'dados/internacoes_ocara.csv'
    if not os.path.exists(caminho):
        return None, None
    try:
        df = pd.read_csv(caminho, usecols=['ANO_CMPT', 'MES_CMPT'])
        if df.empty:
            return None, None
        df['ANO_CMPT'] = pd.to_numeric(df['ANO_CMPT'], errors='coerce')
        df['MES_CMPT'] = pd.to_numeric(df['MES_CMPT'], errors='coerce')
        df = df.dropna(subset=['ANO_CMPT', 'MES_CMPT'])
        if df.empty:
            return None, None
        df = df.sort_values(['ANO_CMPT', 'MES_CMPT'])
        ult = df.iloc[-1]
        return int(ult['ANO_CMPT']), int(ult['MES_CMPT'])
    except Exception:
        return None, None


def _gerar_periodos(a_ano, a_mes, b_ano, b_mes):
    """Gera lista de (ano, mes) de a_ano/a_mes inclusive até b_ano/b_mes inclusive."""
    periodos = []
    ano, mes = a_ano, a_mes
    while (ano < b_ano) or (ano == b_ano and mes <= b_mes):
        periodos.append((ano, mes))
        mes += 1
        if mes > 12:
            mes = 1
            ano += 1
    return periodos


def _fetch_ocara_por_mes(ano, mes, estado='CE'):
    """Busca eficiente via parquet filtrado para um único mês, retorna df_ocara ou DataFrame vazio."""
    try:
        paths = sih(state=estado, year=ano, month=mes)
        if not paths:
            return pd.DataFrame()
        dfs = []
        for p in paths:
            try:
                schema = pq.read_schema(p)
                if 'MUNIC_RES' not in schema.names:
                    continue
                table = pq.read_table(p, filters=[('MUNIC_RES', '==', '230930')])
                if table.num_rows == 0:
                    table = pq.read_table(p, filters=[('MUNIC_RES', '==', 230930)])
                if table.num_rows == 0:
                    continue
                df = table.to_pandas()
                if not df.empty:
                    dfs.append(df)
            except Exception:
                continue
        if dfs:
            return pd.concat(dfs, ignore_index=True)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def atualizar_dados_incremental(estado='CE'):
    """
    Atualização incremental robusta: busca TODOS os meses desde o último período local
    até o mês atual (ou até o último disponível no catálogo), garantindo que mesmo se
    o servidor ficar offline até 2030, ao voltar buscará todas as atualizações perdidas.
    """
    # Descobre último período local
    ult_ano, ult_mes = _obter_ultimo_periodo_local()
    if ult_ano is None:
        print("Base local vazia ou inexistente, buscando desde 2023-01...")
        ult_ano, ult_mes = 2022, 12  # começará em 2023-01

    # Próximo mês após o último
    prox_ano, prox_mes = ult_ano, ult_mes + 1
    if prox_mes > 12:
        prox_mes = 1
        prox_ano += 1

    agora = datetime.now(timezone.utc)
    # Tenta usar catálogo para limitar ao último disponível, senão usa data atual
    try:
        cat_ano, cat_mes = obter_ultimo_mes_disponivel(estado)
        if cat_ano is not None:
            fim_ano, fim_mes = cat_ano, cat_mes
        else:
            fim_ano, fim_mes = agora.year, agora.month
    except Exception:
        fim_ano, fim_mes = agora.year, agora.month

    # Se próximo já é futuro, nada a fazer
    if (prox_ano > fim_ano) or (prox_ano == fim_ano and prox_mes > fim_mes):
        print(f"Base já atualizada até {ult_ano:04d}-{ult_mes:02d}, último disponível {fim_ano:04d}-{fim_mes:02d}. Nada a buscar.")
        _escrever_log("sem_dados", f"Base já atualizada até {ult_ano:04d}-{ult_mes:02d}", fim_ano, fim_mes)
        return

    periodos = _gerar_periodos(prox_ano, prox_mes, fim_ano, fim_mes)
    print(f"Atualização incremental: {len(periodos)} competências de {prox_ano:04d}-{prox_mes:02d} até {fim_ano:04d}-{fim_mes:02d} (último local {ult_ano:04d}-{ult_mes:02d})")

    caminho_arquivo = 'dados/internacoes_ocara.csv'
    os.makedirs('dados', exist_ok=True)

    total_novos = 0
    # Carrega existentes para dedup por N_AIH
    if os.path.exists(caminho_arquivo):
        try:
            df_existente = pd.read_csv(caminho_arquivo, low_memory=False)
            vistos = set(df_existente['N_AIH'].astype(str)) if 'N_AIH' in df_existente.columns else set()
        except Exception:
            df_existente = pd.DataFrame()
            vistos = set()
    else:
        df_existente = pd.DataFrame()
        vistos = set()

    novos_acumulados = []
    for ano, mes in periodos:
        print(f"Baixando {mes:02d}/{ano}...", flush=True)
        df_ocara = _fetch_ocara_por_mes(ano, mes, estado)
        if df_ocara.empty:
            print(f"  -> sem dados para {ano:04d}-{mes:02d}", flush=True)
            continue
        # Dedup por N_AIH
        if 'N_AIH' in df_ocara.columns:
            mask_novo = ~df_ocara['N_AIH'].astype(str).isin(vistos)
            df_ocara = df_ocara[mask_novo]
            if df_ocara.empty:
                print(f"  -> 0 novos (já existentes)", flush=True)
                continue
            vistos.update(df_ocara['N_AIH'].astype(str).tolist())
        novos_acumulados.append(df_ocara)
        print(f"  -> {len(df_ocara)} novos registros", flush=True)
        total_novos += len(df_ocara)

    if not novos_acumulados:
        print("Nenhum dado novo encontrado no intervalo.")
        _escrever_log("sem_dados", f"Nenhum dado novo de {prox_ano:04d}-{prox_mes:02d} até {fim_ano:04d}-{fim_mes:02d}", fim_ano, fim_mes, len(df_existente) if not df_existente.empty else 0)
        return

    df_novos = pd.concat(novos_acumulados, ignore_index=True)
    if not df_existente.empty:
        df_final = pd.concat([df_existente, df_novos], ignore_index=True)
        # Dedup final por N_AIH
        if 'N_AIH' in df_final.columns:
            antes = len(df_final)
            df_final = df_final.drop_duplicates(subset=['N_AIH'], keep='first')
            print(f"Deduplicação final: {antes} -> {len(df_final)}")
    else:
        df_final = df_novos

    # Ordena por período
    try:
        df_final['ANO_CMPT'] = pd.to_numeric(df_final['ANO_CMPT'], errors='coerce')
        df_final['MES_CMPT'] = pd.to_numeric(df_final['MES_CMPT'], errors='coerce')
        df_final = df_final.sort_values(['ANO_CMPT', 'MES_CMPT'])
    except Exception:
        pass

    df_final.to_csv(caminho_arquivo, index=False)
    print(f"Base atualizada incrementalmente! Total: {len(df_final)} registros (+{total_novos} novos)")

    try:
        periodo_recente = f"{int(df_final['ANO_CMPT'].max()):04d}-{int(df_final[df_final['ANO_CMPT']==df_final['ANO_CMPT'].max()]['MES_CMPT'].max()):02d}" if not df_final.empty else None
    except Exception:
        periodo_recente = None
    _escrever_log("sucesso", f"Incremental {prox_ano:04d}-{prox_mes:02d} até {fim_ano:04d}-{fim_mes:02d}: +{total_novos} novos, total {len(df_final)}", fim_ano, fim_mes, len(df_final), periodo_recente)


def atualizar_dados_internacoes(estado='CE', ano=None, mes=None):
    # Modo padrão (sem ano/mes): busca incremental desde último período local até último disponível
    # Garante que se o servidor ficar offline até 2030, ao voltar buscará todas as competências perdidas
    if ano is None and mes is None:
        return atualizar_dados_incremental(estado)

    # Se apenas um dos dois foi passado, completa com o último disponível no catálogo
    if ano is None or mes is None:
        ano2, mes2 = obter_ultimo_mes_disponivel(estado)
        if ano2 is None:
            print("Nenhum dado de AIH Reduzida disponível no catálogo.")
            _escrever_log("sem_dados", "Nenhum dado de AIH Reduzida disponível no catálogo.", ano, mes)
            return
        ano = ano if ano is not None else ano2
        mes = mes if mes is not None else mes2

    # Ambos informados: modo legado mês único (mantido para compatibilidade)
    print(f"Baixando dados do SIH para {estado} - {mes:02d}/{ano}... (modo mês único)")

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
            # Log de sucesso
            try:
                periodo_recente = f"{int(df_final['ANO_CMPT'].max()):04d}-{int(df_final[df_final['ANO_CMPT']==df_final['ANO_CMPT'].max()]['MES_CMPT'].max()):02d}" if not df_final.empty else None
            except Exception:
                periodo_recente = None
            _escrever_log("sucesso", f"Dados atualizados para {mes:02d}/{ano} - {len(df_ocara)} novos, total {len(df_final)}", ano, mes, len(df_final), periodo_recente)
        else:
            print("Nenhum dado retornado para o período solicitado.")
            _escrever_log("sem_dados", f"Nenhum dado retornado para {mes:02d}/{ano}", ano, mes)

    except Exception as e:
        print(f"Erro na extração: {e}")
        try:
            _escrever_log("erro", f"Erro na extração {mes:02d}/{ano if ano else '?'}: {e}", ano, mes)
        except Exception:
            pass
        raise


if __name__ == "__main__":
    atualizar_dados_internacoes(estado='CE')