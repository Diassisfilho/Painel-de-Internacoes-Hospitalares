import streamlit as st
import pandas as pd
import plotly.express as px
import os

DIR_BASE = os.path.join(os.path.dirname(__file__), '..')
CAMINHO_DADOS = os.path.join(DIR_BASE, 'dados', 'internacoes_ocara.csv')
CAMINHO_CID = os.path.join(DIR_BASE, 'dados', 'cid10_subcategorias.csv')
CAMINHO_BRASAO = os.path.join(DIR_BASE, 'assets', 'brasao-ocara.png')

MAPA_SEXO = {1: 'Masculino', 3: 'Feminino'}

# Definir favicon como brasão se existir, senão emoji padrão
PAGE_ICON = CAMINHO_BRASAO if os.path.exists(CAMINHO_BRASAO) else "🏥"

st.set_page_config(
    page_title="Painel de Saúde - Ocara/CE", 
    page_icon=PAGE_ICON, 
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_data
def carregar_cid10():
    if not os.path.exists(CAMINHO_CID):
        return {}
    cid = pd.read_csv(CAMINHO_CID, sep=';', encoding='latin-1', usecols=['SUBCAT', 'DESCRICAO'])
    return dict(zip(cid['SUBCAT'], cid['DESCRICAO']))


@st.cache_data
def carregar_dados():
    if not os.path.exists(CAMINHO_DADOS):
        return pd.DataFrame()

    df = pd.read_csv(CAMINHO_DADOS)
    
    numeric_cols = ['ANO_CMPT', 'MES_CMPT', 'SEXO', 'IDADE', 'DIAS_PERM', 'MORTE', 'VAL_TOT']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna(subset=['ANO_CMPT', 'MES_CMPT', 'SEXO'])
    
    df['SEXO_LABEL'] = df['SEXO'].map(MAPA_SEXO).fillna('Outro')
    df['PERIODO'] = df['ANO_CMPT'].astype(int).astype(str) + '-' + df['MES_CMPT'].astype(int).astype(str).str.zfill(2)

    mapa_cid = carregar_cid10()
    df['DIAGNOSTICO'] = df['DIAG_PRINC'].map(mapa_cid).fillna(df['DIAG_PRINC'])

    return df


df_completo = carregar_dados()

if df_completo.empty:
    st.warning("Nenhum dado encontrado. Execute o script de extração primeiro.")
    st.code("uv run python src/extrator_datasus.py")
    st.stop()

periodos_disponiveis = sorted(df_completo['PERIODO'].unique())

with st.sidebar:
    # Brasão no topo da sidebar
    if os.path.exists(CAMINHO_BRASAO):
        st.image(CAMINHO_BRASAO, width=120)
        st.caption("Município de Ocara - CE")
        st.divider()
    st.header("🔍 Filtros")
    st.caption("Use os filtros abaixo para refinar os dados exibidos no dashboard")
    
    # Filtro de período
    periodo_inicio, periodo_fim = st.select_slider(
        "Período",
        options=periodos_disponiveis,
        value=(periodos_disponiveis[0], periodos_disponiveis[-1]),
    )
    
    st.divider()
    
    # Filtro de sexo
    sexos_disponiveis = ['Todos'] + sorted(df_completo['SEXO_LABEL'].unique().tolist())
    sexo_selecionado = st.selectbox(
        "Sexo",
        options=sexos_disponiveis,
        index=0
    )
    
    # Filtro de faixa etária
    idade_min = int(df_completo['IDADE'].min())
    idade_max = int(df_completo['IDADE'].max())
    faixa_etaria = st.slider(
        "Faixa Etária",
        min_value=idade_min,
        max_value=idade_max,
        value=(idade_min, idade_max)
    )
    
    # Filtro de diagnóstico
    diagnosticos_disponiveis = ['Todos'] + sorted(df_completo['DIAGNOSTICO'].unique().tolist())
    diagnostico_selecionado = st.multiselect(
        "Diagnósticos",
        options=diagnosticos_disponiveis,
        default=['Todos']
    )

# Aplicar filtros
df = df_completo[
    (df_completo['PERIODO'] >= periodo_inicio) &
    (df_completo['PERIODO'] <= periodo_fim)
]

# Filtro de sexo
if sexo_selecionado != 'Todos':
    df = df[df['SEXO_LABEL'] == sexo_selecionado]

# Filtro de faixa etária
df = df[(df['IDADE'] >= faixa_etaria[0]) & (df['IDADE'] <= faixa_etaria[1])]

# Filtro de diagnóstico
if 'Todos' not in diagnostico_selecionado and len(diagnostico_selecionado) > 0:
    df = df[df['DIAGNOSTICO'].isin(diagnostico_selecionado)]

# Mostrar resumo dos filtros aplicados
with st.sidebar:
    st.divider()
    total_completo = len(df_completo)
    total_filtrado = len(df)
    percentual = (total_filtrado / total_completo * 100) if total_completo > 0 else 0
    
    st.metric(
        "Registros Filtrados",
        f"{total_filtrado:,}",
        f"{percentual:.1f}% do total"
    )
    
    if total_filtrado < total_completo:
        st.caption(f"Total de registros: {total_completo:,}")
    
    # Verificar se há dados após filtros
    if df.empty:
        st.warning("⚠️ Nenhum registro encontrado com os filtros aplicados")

col_logo, col_titulo = st.columns([1, 8], gap="small", vertical_alignment="center")
with col_logo:
    if os.path.exists(CAMINHO_BRASAO):
        st.image(CAMINHO_BRASAO, width=110)
with col_titulo:
    st.title("Painel de Internações Hospitalares - Ocara/CE")
    st.caption("Fonte: DATASUS/SIH - AIH Reduzida")

# Pequeno espaçamento entre cabeçalho (brasão+título) e informações
st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

# Estilo destacado para o expander "Sobre"
st.markdown("""
<style>
div[data-testid="stExpander"] details {
    background-color: #e8f4f8;
    border: 2px solid #1f77b4;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(31, 119, 180, 0.15);
}
div[data-testid="stExpander"] details summary {
    font-weight: 700;
    font-size: 17px;
    color: #1f77b4 !important;
    padding: 6px 0;
}
div[data-testid="stExpander"] details summary:hover {
    color: #0d4a7a !important;
}
div[data-testid="stExpander"] details summary span {
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# Seção introdutória (recolhida por padrão)
with st.expander("📊 Sobre este Dashboard  —  clique para expandir", expanded=False):
    st.markdown("""
<div style="background-color: #e8f4f8; padding: 20px; border-radius: 10px; border-left: 5px solid #1f77b4; margin-top: 4px; margin-bottom: 5px;">
    <p style="font-size: 16px; line-height: 1.6; margin-bottom: 10px; color: #1a1a1a;">
        Este painel interativo apresenta <strong>dados oficiais de internações hospitalares</strong> do município de 
        <strong>Ocara, Ceará</strong>, extraídos do sistema DATASUS (Departamento de Informática do Sistema Único de Saúde).
    </p>
    <p style="font-size: 16px; line-height: 1.6; margin-bottom: 10px; color: #1a1a1a;">
        <strong>🎯 Objetivo:</strong> Fornecer uma visão clara e acessível dos indicadores de saúde pública, 
        permitindo análise de tendências, diagnósticos mais frequentes, perfil demográfico dos pacientes e evolução temporal das internações.
    </p>
    <p style="font-size: 16px; line-height: 1.6; margin-bottom: 0; color: #1a1a1a;">
        <strong>🔍 Como usar:</strong> Utilize os <strong>filtros na barra lateral</strong> (à esquerda) para refinar os dados 
        por período, sexo, faixa etária ou diagnóstico específico. Os gráficos e indicadores serão atualizados automaticamente.
    </p>
    <p style="font-size: 14px; line-height: 1.6; margin-bottom: 0; color: #333333; border-top: 1px solid #b0d4e3; padding-top: 12px; margin-top: 12px; font-style: italic;">
        <strong>Realização:</strong> Este dashboard foi desenvolvido pelo <strong>Grupo de Trabalho 13 (GT13) de Ocara</strong>, 
        no âmbito do Programa de Educação pelo Trabalho para a Saúde <strong>(PET-Saúde) – Informação e Saúde Digital</strong>, 
        da Universidade da Integração Internacional da Lusofonia Afro-Brasileira <strong>(UNILAB)</strong>, em parceria entre a 
        <strong>Secretaria de Informação e Saúde Digital (SEIDIGI)</strong> e a 
        <strong>Secretaria de Gestão do Trabalho e da Educação na Saúde (SGTES)</strong>, do Ministério da Saúde.
    </p>
    <p style="font-size: 14px; line-height: 1.6; margin: 12px 0 0 0; color: #333333;">
        <strong>📷 Acompanhe:</strong> <a href="https://www.instagram.com/petsaudedigital.unilab" target="_blank" style="color: #1f77b4; text-decoration: none; font-weight: 600;">@petsaudedigital.unilab</a> no Instagram
    </p>
</div>
""", unsafe_allow_html=True)

st.divider()

# Verificar se há dados após filtros
if df.empty:
    st.warning("⚠️ Nenhum registro encontrado com os filtros aplicados. Ajuste os filtros na barra lateral.")
    st.stop()

total = len(df)
obitos = int(df['MORTE'].sum())
dias_medio = round(df['DIAS_PERM'].mean(), 1) if not df.empty else 0
valor_total = df['VAL_TOT'].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de Internações", total)
col2.metric("Óbitos", obitos)
col3.metric("Permanência Média (dias)", dias_medio)
col4.metric("Valor Total (R$)", f"{valor_total:,.2f}")

st.divider()

col_esq, col_dir = st.columns(2)

with col_esq:
    contagem_diag = (
        df['DIAGNOSTICO']
        .value_counts()
        .head(10)
        .reset_index()
    )
    contagem_diag.columns = ['Diagnóstico', 'Quantidade']

    fig_diag = px.bar(
        contagem_diag, x='Quantidade', y='Diagnóstico',
        title='Diagnósticos Mais Frequentes',
        color_discrete_sequence=['#ff7f0e'],
        orientation='h',
    )
    fig_diag.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_diag, use_container_width=True)

with col_dir:
    contagem_sexo = df['SEXO_LABEL'].value_counts().reset_index()
    contagem_sexo.columns = ['Sexo', 'Quantidade']

    fig_sexo = px.pie(
        contagem_sexo, names='Sexo', values='Quantidade',
        title='Internações por Sexo',
    )
    st.plotly_chart(fig_sexo, use_container_width=True)

col_esq2, col_dir2 = st.columns(2)

with col_esq2:
    fig_idade = px.histogram(
        df, x='IDADE', nbins=20,
        title='Distribuição por Faixa Etária',
        labels={'IDADE': 'Idade', 'count': 'Quantidade'},
    )
    fig_idade.update_traces(marker=dict(line=dict(color='black', width=1)))
    st.plotly_chart(fig_idade, use_container_width=True)

with col_dir2:
    fig_perm = px.histogram(
        df, x='DIAS_PERM', nbins=20,
        title='Distribuição de Dias de Permanência',
        labels={'DIAS_PERM': 'Dias', 'count': 'Quantidade'},
    )
    fig_perm.update_traces(marker=dict(line=dict(color='black', width=1)))
    st.plotly_chart(fig_perm, use_container_width=True)

# Seção de Análises Avançadas
st.divider()
st.subheader("📊 Análises Avançadas")

# Criar faixas etárias
df['FAIXA_ETARIA'] = pd.cut(df['IDADE'], 
                              bins=[0, 1, 12, 18, 40, 60, 100], 
                              labels=['Bebês (0-1)', 'Crianças (2-12)', 'Adolescentes (13-18)', 
                                      'Adultos (19-40)', 'Meia-idade (41-60)', 'Idosos (60+)'])

# 1. Análise por Faixa Etária Detalhada
st.subheader("👥 Análise por Faixa Etária")
faixa_analise = df.groupby('FAIXA_ETARIA', observed=True).agg({
    'IDADE': 'count',
    'VAL_TOT': 'mean'
}).reset_index()
faixa_analise.columns = ['Faixa Etária', 'Internações', 'Custo Médio']
faixa_analise = faixa_analise.sort_values('Faixa Etária')

col_faixa1, col_faixa2 = st.columns(2)

with col_faixa1:
    fig_faixa_qtd = px.bar(
        faixa_analise, x='Faixa Etária', y='Internações',
        title='Internações por Faixa Etária',
        color='Internações',
        color_continuous_scale='Blues'
    )
    fig_faixa_qtd.update_traces(marker=dict(line=dict(color='#000000', width=1.5)))
    st.plotly_chart(fig_faixa_qtd, use_container_width=True)

with col_faixa2:
    fig_faixa_custo = px.bar(
        faixa_analise, x='Faixa Etária', y='Custo Médio',
        title='Custo Médio por Faixa Etária (R$)',
        color='Custo Médio',
        color_continuous_scale='Oranges'
    )
    fig_faixa_custo.update_traces(marker=dict(line=dict(color='#000000', width=1.5)))
    fig_faixa_custo.update_yaxes(tickformat=',.0f')
    st.plotly_chart(fig_faixa_custo, use_container_width=True)

# 2. Taxa de Mortalidade por Faixa Etária
st.subheader("💔 Taxa de Mortalidade por Faixa Etária")
morte_faixa = df.groupby('FAIXA_ETARIA', observed=True).agg({
    'MORTE': 'sum',
    'IDADE': 'count'
}).reset_index()
morte_faixa.columns = ['Faixa Etária', 'Óbitos', 'Internações']
morte_faixa['Taxa (%)'] = (morte_faixa['Óbitos'] / morte_faixa['Internações'] * 100).round(2)
morte_faixa['Sobreviventes'] = morte_faixa['Internações'] - morte_faixa['Óbitos']
morte_faixa = morte_faixa.sort_values('Faixa Etária')

# Criar gráfico de barras empilhadas
fig_mortalidade = px.bar(
    morte_faixa, x='Faixa Etária', y=['Sobreviventes', 'Óbitos'],
    title='Internações e Taxa de Mortalidade por Faixa Etária',
    labels={'value': 'Quantidade', 'variable': 'Status'},
    color_discrete_map={'Sobreviventes': '#90EE90', 'Óbitos': '#FF6B6B'},
    text_auto=False
)

# Adicionar texto da porcentagem dentro das barras de óbitos
for i, row in morte_faixa.iterrows():
    if row['Óbitos'] > 0:
        fig_mortalidade.add_annotation(
            x=row['Faixa Etária'],
            y=row['Sobreviventes'] + row['Óbitos']/2,
            text=f"{row['Taxa (%)']}%",
            showarrow=False,
            font=dict(size=12, color='white', family='Arial Black'),
            bgcolor='rgba(0,0,0,0.6)',
            borderpad=4
        )

fig_mortalidade.update_traces(marker=dict(line=dict(color='#000000', width=1)))
fig_mortalidade.update_layout(barmode='stack', showlegend=True)
st.plotly_chart(fig_mortalidade, use_container_width=True)

# 3. Composição do Valor das Internações
st.subheader("💰 Composição do Valor das Internações")
componentes_valor = pd.DataFrame({
    'Componente': ['Serviços Hospitalares', 'Serviços Profissionais', 'UTI'],
    'Valor': [df['VAL_SH'].sum(), df['VAL_SP'].sum(), df['VAL_UTI'].sum()]
})
componentes_valor = componentes_valor[componentes_valor['Valor'] > 0]

fig_composicao = px.pie(
    componentes_valor, names='Componente', values='Valor',
    title='Distribuição dos Custos por Componente',
    hole=0.4
)
fig_composicao.update_traces(textposition='inside', textinfo='percent+label')
st.plotly_chart(fig_composicao, use_container_width=True)

if df['PERIODO'].nunique() > 1:
    # Série temporal por sexo
    st.subheader("📊 Internações por Sexo ao Longo do Tempo")
    serie_sexo = df.groupby(['PERIODO', 'SEXO_LABEL']).size().reset_index(name='Internações')
    serie_sexo = serie_sexo.sort_values('PERIODO')
    
    fig_sexo_tempo = px.line(
        serie_sexo, x='PERIODO', y='Internações', color='SEXO_LABEL',
        title='Comparação Temporal por Sexo',
        markers=True,
    )
    fig_sexo_tempo.update_traces(line_width=3)
    st.plotly_chart(fig_sexo_tempo, use_container_width=True)
    
    # Top diagnósticos ao longo do tempo
    st.subheader("🏥 Top 5 Diagnósticos ao Longo do Tempo")
    top_diag = df['DIAGNOSTICO'].value_counts().head(5).index.tolist()
    df_top_diag = df[df['DIAGNOSTICO'].isin(top_diag)]
    serie_diag = df_top_diag.groupby(['PERIODO', 'DIAGNOSTICO']).size().reset_index(name='Internações')
    serie_diag = serie_diag.sort_values('PERIODO')
    
    fig_diag_tempo = px.line(
        serie_diag, x='PERIODO', y='Internações', color='DIAGNOSTICO',
        title='Evolução dos 5 Diagnósticos Mais Frequentes',
        markers=True,
    )
    fig_diag_tempo.update_traces(line_width=2)
    st.plotly_chart(fig_diag_tempo, use_container_width=True)

with st.expander("Ver dados tabulares"):
    colunas_exibir = ['ANO_CMPT', 'MES_CMPT', 'DIAGNOSTICO', 'SEXO_LABEL', 'IDADE', 'DIAS_PERM', 'VAL_TOT', 'MORTE']
    st.dataframe(df[colunas_exibir], use_container_width=True)

# Footer com realização e licença
st.divider()
st.markdown("""
<div style="text-align: center; padding: 16px 20px; background-color: #e8f4f8; border-radius: 8px; color: #1a1a1a; font-size: 13px; line-height: 1.6; margin-top: 10px;">
    <p style="margin-bottom: 8px; color: #1a1a1a; font-style: italic;">
        <strong>Realização:</strong> Desenvolvido pelo <strong>Grupo de Trabalho 13 (GT13) de Ocara</strong> no âmbito do 
        Programa de Educação pelo Trabalho para a Saúde <strong>(PET-Saúde) – Informação e Saúde Digital</strong> da 
        <strong>Universidade da Integração Internacional da Lusofonia Afro-Brasileira (UNILAB)</strong>, em parceria entre a 
        <strong>Secretaria de Informação e Saúde Digital (SEIDIGI)</strong> e a 
        <strong>Secretaria de Gestão do Trabalho e da Educação na Saúde (SGTES)</strong> do Ministério da Saúde.
    </p>
    <p style="margin-bottom: 0; color: #1a1a1a;">
        © 2026 GT13 de Ocara — PET-Saúde Digital / UNILAB &nbsp;|&nbsp; Licenciado sob a 
        <a href="https://opensource.org/licenses/MIT" target="_blank" style="color: #1f77b4; text-decoration: none;">Licença MIT</a> 
        &nbsp;|&nbsp; <a href="https://github.com/petsaudedigital-unilab/dashboard-saude-ocara-ce" target="_blank" style="color: #1f77b4; text-decoration: none;">Código no GitHub</a>
    </p>
</div>
""", unsafe_allow_html=True)
