import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Painel de Saude - Ocara/CE", page_icon="🏥", layout="wide")

CAMINHO_DADOS = os.path.join(os.path.dirname(__file__), '..', 'dados', 'internacoes_ocara.csv')

MAPA_SEXO = {1: 'Masculino', 3: 'Feminino'}

@st.cache_data
def carregar_dados():
    if not os.path.exists(CAMINHO_DADOS):
        return pd.DataFrame()

    df = pd.read_csv(CAMINHO_DADOS)
    df['SEXO_LABEL'] = df['SEXO'].map(MAPA_SEXO).fillna('Outro')
    df['PERIODO'] = df['ANO_CMPT'].astype(str) + '-' + df['MES_CMPT'].astype(str).str.zfill(2)
    return df


df = carregar_dados()

if df.empty:
    st.warning("Nenhum dado encontrado. Execute o script de extracao primeiro.")
    st.code("uv run python src/extrator_datasus.py")
    st.stop()

st.title("Painel de Internacoes Hospitalares - Ocara/CE")
st.caption("Fonte: DATASUS/SIH - AIH Reduzida")
st.divider()

total = len(df)
obitos = int(df['MORTE'].sum())
dias_medio = round(df['DIAS_PERM'].mean(), 1)
valor_total = df['VAL_TOT'].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de Internacoes", total)
col2.metric("Obitos", obitos)
col3.metric("Permanencia Media (dias)", dias_medio)
col4.metric("Valor Total (R$)", f"{valor_total:,.2f}")

st.divider()

col_esq, col_dir = st.columns(2)

with col_esq:
    contagem_diag = (
        df['DIAG_PRINC']
        .value_counts()
        .head(10)
        .reset_index()
    )
    contagem_diag.columns = ['CID-10', 'Quantidade']

    fig_diag = px.bar(
        contagem_diag, x='CID-10', y='Quantidade',
        title='Diagnosticos Mais Frequentes (CID-10)',
        color_discrete_sequence=['#ff7f0e'],
    )
    st.plotly_chart(fig_diag, use_container_width=True)

with col_dir:
    contagem_sexo = df['SEXO_LABEL'].value_counts().reset_index()
    contagem_sexo.columns = ['Sexo', 'Quantidade']

    fig_sexo = px.pie(
        contagem_sexo, names='Sexo', values='Quantidade',
        title='Internacoes por Sexo',
    )
    st.plotly_chart(fig_sexo, use_container_width=True)

col_esq2, col_dir2 = st.columns(2)

with col_esq2:
    fig_idade = px.histogram(
        df, x='IDADE', nbins=20,
        title='Distribuicao por Faixa Etaria',
        labels={'IDADE': 'Idade', 'count': 'Quantidade'},
    )
    st.plotly_chart(fig_idade, use_container_width=True)

with col_dir2:
    fig_perm = px.histogram(
        df, x='DIAS_PERM', nbins=20,
        title='Distribuicao de Dias de Permanencia',
        labels={'DIAS_PERM': 'Dias', 'count': 'Quantidade'},
    )
    st.plotly_chart(fig_perm, use_container_width=True)

if df['PERIODO'].nunique() > 1:
    por_mes = df.groupby('PERIODO').size().reset_index(name='Internacoes')
    por_mes = por_mes.sort_values('PERIODO')

    fig_serie = px.line(
        por_mes, x='PERIODO', y='Internacoes',
        title='Evolucao Mensal de Internacoes',
        markers=True,
    )
    st.plotly_chart(fig_serie, use_container_width=True)

with st.expander("Ver dados tabulares"):
    colunas_exibir = ['ANO_CMPT', 'MES_CMPT', 'DIAG_PRINC', 'SEXO_LABEL', 'IDADE', 'DIAS_PERM', 'VAL_TOT', 'MORTE']
    st.dataframe(df[colunas_exibir], use_container_width=True)
