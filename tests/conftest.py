import os
import sys
import pandas as pd
import pytest

# Garantir src no path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

DIR_BASE = os.path.join(os.path.dirname(__file__), '..')
CAMINHO_DADOS = os.path.join(DIR_BASE, 'dados', 'internacoes_ocara.csv')
CAMINHO_CID = os.path.join(DIR_BASE, 'dados', 'cid10_subcategorias.csv')
CAMINHO_BRASAO = os.path.join(DIR_BASE, 'assets', 'brasao-ocara.png')

@pytest.fixture
def caminho_dados():
    return CAMINHO_DADOS

@pytest.fixture
def caminho_cid():
    return CAMINHO_CID

@pytest.fixture
def caminho_brasao():
    return CAMINHO_BRASAO

@pytest.fixture
def df_real():
    if not os.path.exists(CAMINHO_DADOS):
        pytest.skip("dados/internacoes_ocara.csv não encontrado")
    df = pd.read_csv(CAMINHO_DADOS, low_memory=False)
    return df

@pytest.fixture
def df_pequeno():
    # DataFrame sintético mínimo para testes unitários sem depender do CSV real
    data = {
        'ANO_CMPT': [2023, 2023, 2024, 2024, 2025],
        'MES_CMPT': [1, 2, 5, 7, 4],
        'SEXO': [1, 3, 1, 3, 1],
        'IDADE': [10, 45, 70, 30, 55],
        'DIAS_PERM': [2, 5, 10, 3, 4],
        'MORTE': [0, 0, 1, 0, 0],
        'VAL_TOT': [500.0, 1200.5, 3000.0, 800.0, 1500.0],
        'VAL_SH': [300.0, 700.0, 2000.0, 500.0, 900.0],
        'VAL_SP': [100.0, 300.0, 500.0, 200.0, 400.0],
        'VAL_UTI': [0.0, 0.0, 500.0, 0.0, 0.0],
        'DIAG_PRINC': ['J189', 'I10', 'J189', 'A09', 'I10'],
        'N_AIH': ['0001','0002','0003','0004','0005'],
    }
    return pd.DataFrame(data)
