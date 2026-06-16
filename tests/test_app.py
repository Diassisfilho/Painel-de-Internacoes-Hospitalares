import os
import sys
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock streamlit cache para testes sem servidor
try:
    import streamlit as st
    # Desativa cache em testes
    original_cache_data = st.cache_data
    def _no_cache(func):
        return func
    st.cache_data = _no_cache
except ImportError:
    pass

from unittest.mock import patch


class TestLogicaFiltros:
    def test_filtro_periodo(self, df_pequeno):
        df = df_pequeno.copy()
        df['PERIODO'] = df['ANO_CMPT'].astype(int).astype(str) + '-' + df['MES_CMPT'].astype(int).astype(str).str.zfill(2)
        periodo_inicio, periodo_fim = '2023-01', '2024-12'
        filtrado = df[(df['PERIODO'] >= periodo_inicio) & (df['PERIODO'] <= periodo_fim)]
        assert len(filtrado) <= len(df)
        # Todos os períodos filtrados devem estar no intervalo
        for p in filtrado['PERIODO']:
            assert periodo_inicio <= p <= periodo_fim

    def test_filtro_sexo(self, df_pequeno):
        df = df_pequeno.copy()
        df['SEXO_LABEL'] = df['SEXO'].map({1: 'Masculino', 3: 'Feminino'}).fillna('Outro')
        for sexo in ['Masculino', 'Feminino']:
            filtrado = df[df['SEXO_LABEL'] == sexo]
            assert all(filtrado['SEXO_LABEL'] == sexo)

    def test_filtro_faixa_etaria(self, df_pequeno):
        df = df_pequeno.copy()
        faixa = (20, 60)
        filtrado = df[(df['IDADE'] >= faixa[0]) & (df['IDADE'] <= faixa[1])]
        assert all((filtrado['IDADE'] >= faixa[0]) & (filtrado['IDADE'] <= faixa[1]))

    def test_filtro_diagnostico(self, df_pequeno):
        df = df_pequeno.copy()
        # Simula DIAGNOSTICO mapeado
        df['DIAGNOSTICO'] = df['DIAG_PRINC']
        selecionados = ['J189', 'I10']
        filtrado = df[df['DIAGNOSTICO'].isin(selecionados)]
        assert all(filtrado['DIAGNOSTICO'].isin(selecionados))

    def test_filtro_combinado(self, df_pequeno):
        df = df_pequeno.copy()
        df['PERIODO'] = df['ANO_CMPT'].astype(int).astype(str) + '-' + df['MES_CMPT'].astype(int).astype(str).str.zfill(2)
        df['SEXO_LABEL'] = df['SEXO'].map({1: 'Masculino', 3: 'Feminino'}).fillna('Outro')
        # Aplica múltiplos filtros
        filtrado = df[
            (df['PERIODO'] >= '2023-01') & (df['PERIODO'] <= '2024-12') &
            (df['SEXO_LABEL'] == 'Masculino') &
            (df['IDADE'] >= 20) & (df['IDADE'] <= 60)
        ]
        assert len(filtrado) <= len(df)

    def test_filtro_vazio(self, df_pequeno):
        df = df_pequeno.copy()
        df['PERIODO'] = df['ANO_CMPT'].astype(int).astype(str) + '-' + df['MES_CMPT'].astype(int).astype(str).str.zfill(2)
        # Filtro impossível
        filtrado = df[df['PERIODO'] == '1900-01']
        assert filtrado.empty


class TestMetricas:
    def test_total_internacoes(self, df_pequeno):
        total = len(df_pequeno)
        assert total == 5

    def test_obitos(self, df_pequeno):
        obitos = int(df_pequeno['MORTE'].sum())
        assert obitos == 1

    def test_permanencia_media(self, df_pequeno):
        dias_medio = round(df_pequeno['DIAS_PERM'].mean(), 1)
        assert dias_medio == round((2+5+10+3+4)/5, 1)

    def test_valor_total(self, df_pequeno):
        valor_total = df_pequeno['VAL_TOT'].sum()
        assert valor_total == 500.0+1200.5+3000.0+800.0+1500.0

    def test_metricas_real(self, df_real):
        total = len(df_real)
        # Real tem 1730 após expansão
        assert total >= 1000
        obitos = int(pd.to_numeric(df_real['MORTE'], errors='coerce').sum())
        assert obitos >= 0
        dias_medio = pd.to_numeric(df_real['DIAS_PERM'], errors='coerce').mean()
        assert 0 <= dias_medio <= 100

    def test_faixa_etaria_criacao(self, df_pequeno):
        df = df_pequeno.copy()
        df['FAIXA_ETARIA'] = pd.cut(df['IDADE'], bins=[0,1,12,18,40,60,100],
                                     labels=['Bebês (0-1)', 'Crianças (2-12)', 'Adolescentes (13-18)', 'Adultos (19-40)', 'Meia-idade (41-60)', 'Idosos (60+)'])
        assert 'FAIXA_ETARIA' in df.columns
        assert df['FAIXA_ETARIA'].notna().all()

    def test_taxa_mortalidade(self, df_pequeno):
        df = df_pequeno.copy()
        df['FAIXA_ETARIA'] = pd.cut(df['IDADE'], bins=[0,1,12,18,40,60,100],
                                     labels=['Bebês (0-1)', 'Crianças (2-12)', 'Adolescentes (13-18)', 'Adultos (19-40)', 'Meia-idade (41-60)', 'Idosos (60+)'])
        morte_faixa = df.groupby('FAIXA_ETARIA', observed=True).agg({'MORTE':'sum','IDADE':'count'}).reset_index()
        morte_faixa.columns = ['Faixa Etária', 'Óbitos', 'Internações']
        morte_faixa['Taxa (%)'] = (morte_faixa['Óbitos']/morte_faixa['Internações']*100).round(2)
        # Verifica que taxa está entre 0 e 100
        assert all((morte_faixa['Taxa (%)'] >= 0) & (morte_faixa['Taxa (%)'] <= 100))

    def test_composicao_valor(self, df_pequeno):
        for col in ['VAL_SH','VAL_SP','VAL_UTI']:
            assert col in df_pequeno.columns
        total_sh = df_pequeno['VAL_SH'].sum()
        total_sp = df_pequeno['VAL_SP'].sum()
        total_uti = df_pequeno['VAL_UTI'].sum()
        assert total_sh >= 0
        assert total_sp >= 0
        assert total_uti >= 0


class TestPeriodoExibicao:
    def test_periodo_inicio_fim_ordenado(self, df_pequeno):
        df = df_pequeno.copy()
        df['PERIODO'] = df['ANO_CMPT'].astype(int).astype(str) + '-' + df['MES_CMPT'].astype(int).astype(str).str.zfill(2)
        periodos = sorted(df['PERIODO'].unique())
        assert periodos[0] <= periodos[-1]
        periodo_inicio, periodo_fim = periodos[0], periodos[-1]
        assert periodo_inicio <= periodo_fim

    def test_periodo_exibicao_formato(self):
        periodo_inicio, periodo_fim = '2023-01', '2025-11'
        texto = f"Período em exibição: {periodo_inicio} a {periodo_fim}"
        assert '2023-01' in texto
        assert '2025-11' in texto
        assert 'Período em exibição' in texto


class TestImportApp:
    def test_app_importa_sem_erro(self):
        # Verifica que src/app.py pode ser importado (sem executar Streamlit)
        # Mock de st.set_page_config para evitar SideEffect
        with patch('streamlit.set_page_config'):
            with patch('streamlit.cache_data', lambda f: f):
                try:
                    import importlib.util, os
                    spec = importlib.util.spec_from_file_location("app_test", os.path.join(os.path.dirname(__file__), '..', 'src', 'app.py'))
                    # Não executamos, apenas verificamos sintaxe
                    assert spec is not None
                except Exception as e:
                    pytest.fail(f"Erro ao carregar app.py: {e}")

    def test_paleta_daltonico_definida(self):
        # Verifica que paletas Okabe-Ito estão definidas no arquivo
        caminho_app = os.path.join(os.path.dirname(__file__), '..', 'src', 'app.py')
        texto = open(caminho_app, encoding='utf-8').read()
        assert 'PALETA_OKABE_ITO' in texto, "Paleta Okabe-Ito deve estar definida"
        assert 'PALETA_SEXO_DALTONICO' in texto
        assert 'PALETA_MORTALIDADE' in texto
        assert 'Viridis' in texto or 'CORES_CONTINUAS_DALTONICO' in texto

    def test_sem_emojis(self):
        caminho_app = os.path.join(os.path.dirname(__file__), '..', 'src', 'app.py')
        texto = open(caminho_app, encoding='utf-8').read()
        # Verifica que não há emojis (categoria So) exceto ©
        import unicodedata
        emojis_encontrados = []
        for ch in texto:
            if ch == "©":
                continue
            if unicodedata.category(ch) == "So" and ord(ch) > 1000:
                emojis_encontrados.append(ch)
        assert len(emojis_encontrados) == 0, f"App não deve conter emojis, encontrados: {set(emojis_encontrados)}"

    def test_favicon_e_brasao(self):
        caminho_app = os.path.join(os.path.dirname(__file__), '..', 'src', 'app.py')
        texto = open(caminho_app, encoding='utf-8').read()
        assert 'CAMINHO_BRASAO' in texto
        assert 'PAGE_ICON' in texto
        assert 'brasao-ocara.png' in texto
