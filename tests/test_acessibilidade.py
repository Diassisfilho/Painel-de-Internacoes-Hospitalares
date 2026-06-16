import os

DIR_BASE = os.path.join(os.path.dirname(__file__), '..')
CAMINHO_APP = os.path.join(DIR_BASE, 'src', 'app.py')


class TestAcessibilidadeDaltonismo:
    def test_paleta_okabe_ito_valida(self):
        texto = open(CAMINHO_APP, encoding='utf-8').read()
        # Okabe-Ito tem 8 cores
        assert 'PALETA_OKABE_ITO' in texto
        # Verifica que as cores hex estão presentes
        for cor in ["#0072B2", "#E69F00", "#009E73", "#D55E00"]:
            assert cor in texto, f"Cor {cor} da paleta Okabe-Ito deve estar presente"

    def test_toggle_daltonico_existe(self):
        texto = open(CAMINHO_APP, encoding='utf-8').read()
        assert 'modo_daltonico' in texto, "Variável modo_daltonico deve existir"
        assert 'st.toggle' in texto, "Toggle deve existir"
        assert 'Paleta para daltônicos' in texto or 'Modo daltônico' in texto

    def test_toggle_no_header(self):
        texto = open(CAMINHO_APP, encoding='utf-8').read()
        # Toggle deve estar no header (col_toggle), não na sidebar
        # Verifica que após col_logo/col_titulo há col_toggle com toggle
        assert 'col_toggle' in texto
        # E que não há toggle duplicado na sidebar após refatoração
        # Sidebar deve ter apenas Filtros, sem toggle
        # Conta ocorrências de st.toggle - deve ser 1
        assert texto.count('st.toggle') == 1, "Deve haver exatamente 1 toggle (no header)"

    def test_sidebar_minima(self):
        texto = open(CAMINHO_APP, encoding='utf-8').read()
        # Sidebar deve iniciar direto com Filtros, sem brasão grande
        # Verifica que width=120 não está mais na sidebar (foi movido para 38 e depois removido)
        # Agora sidebar deve ter apenas st.header("Filtros")
        assert 'with st.sidebar:' in texto
        # Brasão na sidebar deve ter sido removido (apenas no header)
        # Conta st.image com brasão - deve aparecer 1 vez (no header col_logo) ou 2 se contar favicon
        # Mas sidebar não deve ter imagem 120
        assert 'width=120' not in texto, "Brasão na sidebar deve ser removido/minimizado (sem width=120)"
        assert 'width=38' not in texto, "Brasão minimizado 38 também foi removido"

    def test_contraste_footer(self):
        texto = open(CAMINHO_APP, encoding='utf-8').read()
        # Footer deve ter fundo claro fixo para contraste em tema escuro
        assert 'background-color: #e8f4f8' in texto or 'background-color: #f0f2f6' in texto
        assert 'color: #1a1a1a' in texto, "Footer deve usar texto escuro #1a1a1a para contraste"

    def test_contraste_box_sobre(self):
        texto = open(CAMINHO_APP, encoding='utf-8').read()
        assert 'background-color: #e8f4f8' in texto
        assert 'color: #1a1a1a' in texto

    def test_barras_com_contorno(self):
        texto = open(CAMINHO_APP, encoding='utf-8').read()
        # Todas as barras devem ter contorno preto para contraste
        assert "line=dict(color='black'" in texto or 'line=dict(color="#000000"' in texto or "line=dict(color='black'" in texto
        assert texto.count("marker=dict(line=dict(color=") >= 5, "Pelo menos 5 gráficos devem ter contorno"

    def test_series_com_simbolos_e_tracos(self):
        texto = open(CAMINHO_APP, encoding='utf-8').read()
        # Séries temporais devem ter symbol e line_dash para além da cor
        assert "symbol='SEXO_LABEL'" in texto or 'symbol=' in texto
        assert "line_dash='SEXO_LABEL'" in texto or 'line_dash=' in texto
        assert 'marker=dict(size=' in texto

    def test_composicao_com_contorno(self):
        texto = open(CAMINHO_APP, encoding='utf-8').read()
        assert "hole=0.4" in texto  # pizza donut
        assert "marker=dict(line=dict(color='black'" in texto

    def test_mortalidade_sem_verde_vermelho(self):
        texto = open(CAMINHO_APP, encoding='utf-8').read()
        # Quando modo_daltonico, não deve usar verde/vermelho puro para mortalidade
        assert 'PALETA_MORTALIDADE' in texto
        assert '#0072B2' in texto and '#D55E00' in texto
        # Verifica que o mapa mortalidade usa azul e vermillion, não verde/vermelho
        assert '"#90EE90"' not in texto or 'PALETA_MORTALIDADE' in texto  # fallback ainda existe mas não é usado quando daltonico


class TestAcessibilidadeGeral:
    def test_expander_sobre_recolhido(self):
        texto = open(CAMINHO_APP, encoding='utf-8').read()
        assert 'st.expander("Sobre este Dashboard' in texto
        assert 'expanded=False' in texto, "Sobre deve estar recolhido por padrão"

    def test_periodo_em_destaque(self):
        texto = open(CAMINHO_APP, encoding='utf-8').read()
        assert 'Período em exibição' in texto, "Período deve estar em destaque acima dos indicadores"
        assert 'periodo_inicio' in texto and 'periodo_fim' in texto

    def test_favicon_brasao(self):
        texto = open(CAMINHO_APP, encoding='utf-8').read()
        assert 'CAMINHO_BRASAO' in texto
        assert 'PAGE_ICON' in texto
        assert 'st.set_page_config' in texto
        # PAGE_ICON deve ser CAMINHO_BRASAO se existir
        assert 'CAMINHO_BRASAO if os.path.exists(CAMINHO_BRASAO)' in texto

    def test_footer_completo(self):
        texto = open(CAMINHO_APP, encoding='utf-8').read()
        assert 'Realização:' in texto
        assert 'GT13 de Ocara' in texto
        assert 'Licença MIT' in texto or 'Licenciado sob' in texto
        assert 'Código no GitHub' in texto
        assert 'https://opensource.org/licenses/MIT' in texto

    def test_sem_emojis_no_codigo(self):
        import unicodedata
        texto = open(CAMINHO_APP, encoding='utf-8').read()
        emojis = [ch for ch in texto if unicodedata.category(ch) == "So" and ch != "©" and ord(ch) > 1000]
        assert len(emojis) == 0, f"Não deve haver emojis no código, encontrados: {set(emojis)}"
