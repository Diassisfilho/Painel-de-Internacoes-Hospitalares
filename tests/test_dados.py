import os
import pandas as pd
import pytest

DIR_BASE = os.path.join(os.path.dirname(__file__), '..')
CAMINHO_DADOS = os.path.join(DIR_BASE, 'dados', 'internacoes_ocara.csv')
CAMINHO_CID = os.path.join(DIR_BASE, 'dados', 'cid10_subcategorias.csv')
CAMINHO_BRASAO = os.path.join(DIR_BASE, 'assets', 'brasao-ocara.png')


class TestArquivosBase:
    def test_csv_existe(self):
        assert os.path.exists(CAMINHO_DADOS), "dados/internacoes_ocara.csv deve existir"

    def test_csv_nao_vazio(self):
        df = pd.read_csv(CAMINHO_DADOS, low_memory=False)
        assert len(df) > 0, "CSV não deve estar vazio"
        assert len(df) >= 500, "Base deve ter pelo menos 500 registros após expansão 2023-2025"

    def test_csv_nao_pesado(self):
        # Regra: não pesar no servidor - <5MB e <5000 linhas
        tamanho_kb = os.path.getsize(CAMINHO_DADOS) / 1024
        assert tamanho_kb < 2048, f"CSV deve ser <2MB, atual {tamanho_kb:.1f}KB"
        df = pd.read_csv(CAMINHO_DADOS, low_memory=False)
        assert len(df) < 5000, f"Base deve ter <5000 linhas, atual {len(df)}"
        mem_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
        assert mem_mb < 5, f"Memória deve ser <5MB, atual {mem_mb:.2f}MB"

    def test_colunas_essenciais(self):
        df = pd.read_csv(CAMINHO_DADOS, low_memory=False)
        essenciais = ['ANO_CMPT', 'MES_CMPT', 'SEXO', 'IDADE', 'DIAS_PERM', 'MORTE', 'VAL_TOT', 'DIAG_PRINC', 'N_AIH']
        for col in essenciais:
            assert col in df.columns, f"Coluna essencial {col} ausente"

    def test_sem_n_aih_duplicado(self):
        df = pd.read_csv(CAMINHO_DADOS, low_memory=False)
        assert df['N_AIH'].nunique() == len(df), "N_AIH deve ser único (deduplicação)"

    def test_anos_cobertos(self):
        df = pd.read_csv(CAMINHO_DADOS, low_memory=False)
        anos = sorted(pd.to_numeric(df['ANO_CMPT'], errors='coerce').dropna().unique().astype(int).tolist())
        assert 2023 in anos or 2024 in anos, "Base deve conter anos anteriores (2023/2024) para série temporal"
        assert 2025 in anos, "Base deve conter 2025"

    def test_periodos_multiplos(self):
        df = pd.read_csv(CAMINHO_DADOS, low_memory=False)
        for c in ['ANO_CMPT', 'MES_CMPT']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        df = df.dropna(subset=['ANO_CMPT', 'MES_CMPT'])
        df['PERIODO'] = df['ANO_CMPT'].astype(int).astype(str) + '-' + df['MES_CMPT'].astype(int).astype(str).str.zfill(2)
        assert df['PERIODO'].nunique() >= 5, "Deve haver >=5 períodos distintos para análise temporal"

    def test_cid_existe(self):
        assert os.path.exists(CAMINHO_CID), "cid10_subcategorias.csv deve existir"

    def test_brasao_existe(self):
        assert os.path.exists(CAMINHO_BRASAO), "assets/brasao-ocara.png deve existir"
        assert os.path.getsize(CAMINHO_BRASAO) > 0, "Brasão não deve estar vazio"

    def test_license_existe(self):
        caminho_license = os.path.join(DIR_BASE, 'LICENSE')
        assert os.path.exists(caminho_license), "LICENSE deve existir"
        texto = open(caminho_license, encoding='utf-8').read()
        assert 'MIT License' in texto, "LICENSE deve conter MIT License"
        assert '2026' in texto, "LICENSE deve conter ano 2026"


class TestCarregamentoDados:
    def test_carregar_dados_transformacao(self, df_pequeno):
        # Simula lógica de src/app.py: carregar_dados
        df = df_pequeno.copy()
        for col in ['ANO_CMPT', 'MES_CMPT', 'SEXO', 'IDADE', 'DIAS_PERM', 'MORTE', 'VAL_TOT']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['ANO_CMPT', 'MES_CMPT', 'SEXO'])
        MAPA_SEXO = {1: 'Masculino', 3: 'Feminino'}
        df['SEXO_LABEL'] = df['SEXO'].map(MAPA_SEXO).fillna('Outro')
        df['PERIODO'] = df['ANO_CMPT'].astype(int).astype(str) + '-' + df['MES_CMPT'].astype(int).astype(str).str.zfill(2)
        assert 'SEXO_LABEL' in df.columns
        assert 'PERIODO' in df.columns
        assert set(df['SEXO_LABEL'].unique()) <= {'Masculino', 'Feminino', 'Outro'}
        assert all('-' in p for p in df['PERIODO'])

    def test_carregar_dados_real(self, df_real):
        # Testa com dados reais - não deve falhar
        df = df_real.copy()
        for col in ['ANO_CMPT', 'MES_CMPT', 'SEXO', 'IDADE', 'DIAS_PERM', 'MORTE', 'VAL_TOT']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['ANO_CMPT', 'MES_CMPT', 'SEXO'])
        assert len(df) > 0
        # Verifica que após limpeza ainda há dados
        assert len(df) == 1730 or len(df) > 1000

    def test_periodo_formato(self, df_pequeno):
        df = df_pequeno.copy()
        df['PERIODO'] = df['ANO_CMPT'].astype(str) + '-' + df['MES_CMPT'].astype(str).str.zfill(2)
        for p in df['PERIODO']:
            assert len(p) == 7, f"Período deve ter formato YYYY-MM, recebido {p}"
            ano, mes = p.split('-')
            assert ano.isdigit() and len(ano) == 4
            assert mes.isdigit() and 1 <= int(mes) <= 12
