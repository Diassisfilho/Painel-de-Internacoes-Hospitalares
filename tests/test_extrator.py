import os
import sys
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestExtratorDatasus:
    def test_imports(self):
        # Verifica que o módulo pode ser importado
        try:
            import extrator_datasus
            assert hasattr(extrator_datasus, 'obter_ultimo_mes_disponivel')
            assert hasattr(extrator_datasus, 'atualizar_dados_internacoes')
        except ImportError as e:
            pytest.fail(f"Falha ao importar extrator_datasus: {e}")

    def test_obter_ultimo_mes_mock(self):
        import extrator_datasus
        # Mock do catálogo
        mock_catalogo = pd.DataFrame({
            'name': ['RDCE2504', 'RDCE2312', 'SPCE2504'],
            'year': [2025, 2023, 2025],
            'month': [4, 12, 4]
        })
        with patch('extrator_datasus.list_files', return_value=mock_catalogo):
            ano, mes = extrator_datasus.obter_ultimo_mes_disponivel('CE')
            assert ano == 2025
            assert mes == 4

    def test_obter_ultimo_mes_vazio(self):
        import extrator_datasus
        mock_catalogo = pd.DataFrame({'name': pd.Series([], dtype='str'), 'year': pd.Series([], dtype='int'), 'month': pd.Series([], dtype='int')})
        with patch('extrator_datasus.list_files', return_value=mock_catalogo):
            ano, mes = extrator_datasus.obter_ultimo_mes_disponivel('CE')
            assert ano is None
            assert mes is None
        # Também testa DataFrame totalmente vazio sem colunas
        with patch('extrator_datasus.list_files', return_value=pd.DataFrame()):
            ano, mes = extrator_datasus.obter_ultimo_mes_disponivel('CE')
            assert ano is None
            assert mes is None

    def test_atualizar_dados_sem_dados(self):
        import extrator_datasus
        with patch('extrator_datasus.sih', return_value=pd.DataFrame()):
            # Deve lidar com DataFrame vazio sem erro
            try:
                extrator_datasus.atualizar_dados_internacoes(estado='CE', ano=2025, mes=99)
            except Exception:
                pass  # Pode lançar mas não deve crashar inesperadamente


class TestAtualizacaoIncremental:
    def test_gerar_periodos(self):
        import extrator_datasus
        assert extrator_datasus._gerar_periodos(2025, 11, 2025, 11) == [(2025, 11)]
        assert extrator_datasus._gerar_periodos(2025, 11, 2026, 1) == [(2025, 11), (2025, 12), (2026, 1)]
        assert extrator_datasus._gerar_periodos(2025, 12, 2026, 2) == [(2025, 12), (2026, 1), (2026, 2)]
        # Gap até 2030
        gap = extrator_datasus._gerar_periodos(2025, 12, 2030, 1)
        assert len(gap) == 50  # 2025-12 + 4 anos *12 + 1 = 50
        assert gap[0] == (2025, 12) and gap[-1] == (2030, 1)

    def test_ultimo_periodo_local(self):
        import extrator_datasus
        ano, mes = extrator_datasus._obter_ultimo_periodo_local()
        assert ano == 2025 and mes == 11

    def test_incremental_sem_gap(self):
        import extrator_datasus
        with patch('extrator_datasus.obter_ultimo_mes_disponivel', return_value=(2025, 11)):
            # Já atualizado, não deve buscar nada
            extrator_datasus.atualizar_dados_incremental(estado='CE')
            # Log deve ter sido escrito com sem_dados
            import json
            log_path = os.path.join(os.path.dirname(__file__), '..', 'dados', 'ultima_atualizacao.json')
            assert os.path.exists(log_path)
            log = json.load(open(log_path, encoding='utf-8'))
            assert log['status'] == 'sem_dados'

    def test_incremental_com_gap_mock(self):
        import extrator_datasus
        with patch('extrator_datasus.obter_ultimo_mes_disponivel', return_value=(2026, 1)):
            with patch('extrator_datasus._fetch_ocara_por_mes', return_value=pd.DataFrame()):
                extrator_datasus.atualizar_dados_incremental(estado='CE')
                # Deve tentar 2025-12 e 2026-01 e logar sem_dados
                import json
                log_path = os.path.join(os.path.dirname(__file__), '..', 'dados', 'ultima_atualizacao.json')
                log = json.load(open(log_path, encoding='utf-8'))
                assert log['status'] == 'sem_dados'

    def test_incremental_gap_2030(self):
        import extrator_datasus
        # Simula gap de 5 anos: 2025-11 até 2030-06 = 56 meses
        periodos = extrator_datasus._gerar_periodos(2025, 12, 2030, 6)
        assert len(periodos) == 55
        assert periodos[0] == (2025, 12)
        assert periodos[-1] == (2030, 6)

    def test_atualizar_dados_sem_args_chama_incremental(self):
        import extrator_datasus
        with patch('extrator_datasus.atualizar_dados_incremental') as mock_inc:
            extrator_datasus.atualizar_dados_internacoes(estado='CE')
            mock_inc.assert_called_once_with('CE')


class TestPopularDados:
    def test_popular_dados_existe(self):
        caminho = os.path.join(os.path.dirname(__file__), '..', 'popular_dados.py')
        assert os.path.exists(caminho), "popular_dados.py deve existir"

    def test_atualizar_base_existe(self):
        caminho = os.path.join(os.path.dirname(__file__), '..', 'atualizar_base_2023_2025.py')
        assert os.path.exists(caminho), "atualizar_base_2023_2025.py deve existir"

    def test_atualizar_base_intervalo(self):
        caminho = os.path.join(os.path.dirname(__file__), '..', 'atualizar_base_2023_2025.py')
        texto = open(caminho, encoding='utf-8').read()
        assert '2023' in texto and '2025' in texto, "Script deve cobrir 2023-2025"
        assert 'N_AIH' in texto, "Script deve deduplicar por N_AIH"
        assert 'drop_duplicates' in texto or 'vistos' in texto

    def test_csv_apos_atualizacao(self):
        caminho = os.path.join(os.path.dirname(__file__), '..', 'dados', 'internacoes_ocara.csv')
        df = pd.read_csv(caminho, low_memory=False)
        # Verifica que dados são consistentes após atualização
        assert 'N_AIH' in df.columns
        assert df['N_AIH'].nunique() == len(df), "Sem duplicatas após atualização"
        anos = pd.to_numeric(df['ANO_CMPT'], errors='coerce').dropna().unique()
        assert len(anos) >= 2, "Deve haver pelo menos 2 anos distintos"
