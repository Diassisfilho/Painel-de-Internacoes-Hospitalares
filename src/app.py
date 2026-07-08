import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Painel de Saúde - Ocara/CE", page_icon="🏥", layout="wide")

DIR_BASE = os.path.join(os.path.dirname(__file__), '..')
CAMINHO_DADOS = os.path.join(DIR_BASE, 'dados', 'internacoes_ocara.csv')
CAMINHO_CID = os.path.join(DIR_BASE, 'dados', 'cid10_subcategorias.csv')

MAPA_SEXO = {1: 'Masculino', 3: 'Feminino'}


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
    st.header("Filtros")
    periodo_inicio, periodo_fim = st.select_slider(
        "Período",
        options=periodos_disponiveis,
        value=(periodos_disponiveis[0], periodos_disponiveis[-1]),
    )

df = df_completo[
    (df_completo['PERIODO'] >= periodo_inicio) &
    (df_completo['PERIODO'] <= periodo_fim)
]

st.title("Painel de Internações Hospitalares - Ocara/CE")
st.caption("Fonte: DATASUS/SIH - AIH Reduzida")
st.divider()

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
    st.plotly_chart(fig_idade, use_container_width=True)

with col_dir2:
    fig_perm = px.histogram(
        df, x='DIAS_PERM', nbins=20,
        title='Distribuição de Dias de Permanência',
        labels={'DIAS_PERM': 'Dias', 'count': 'Quantidade'},
    )
    st.plotly_chart(fig_perm, use_container_width=True)

if df['PERIODO'].nunique() > 1:
    por_mes = df.groupby('PERIODO').size().reset_index(name='Internações')
    por_mes = por_mes.sort_values('PERIODO')

    fig_serie = px.line(
        por_mes, x='PERIODO', y='Internações',
        title='Evolução Mensal de Internações',
        markers=True,
    )
    st.plotly_chart(fig_serie, use_container_width=True)

with st.expander("Ver dados tabulares"):
    colunas_exibir = ['ANO_CMPT', 'MES_CMPT', 'DIAGNOSTICO', 'SEXO_LABEL', 'IDADE', 'DIAS_PERM', 'VAL_TOT', 'MORTE']
    st.dataframe(df[colunas_exibir], use_container_width=True)
