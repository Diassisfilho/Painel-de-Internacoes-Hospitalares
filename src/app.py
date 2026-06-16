import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Painel de Saúde - Ocara/CE", page_icon="🏥", layout="wide")

@st.cache_data
def carregar_dados():
    dados_simulados = {
        'Mês': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
        'Casos de Dengue': [12, 25, 45, 80, 50, 20],
        'Internações': [40, 42, 38, 55, 48, 41],
        'Consultas UBS': [1200, 1150, 1300, 1250, 1400, 1350]
    }
    return pd.DataFrame(dados_simulados)

df = carregar_dados()

st.title("Painel de Dados de Saúde - Ocara, Ceará")
st.markdown("Visualização de indicadores públicos do município.")
st.divider()

st.subheader("Indicadores Recentes (Junho)")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Casos de Dengue", value="20", delta="-30 (relação a Maio)")
with col2:
    st.metric(label="Internações", value="41", delta="-7")
with col3:
    st.metric(label="Consultas UBS", value="1.350", delta="-50")

st.divider()

st.subheader("Evolução Histórica")
grafico_col1, grafico_col2 = st.columns(2)

with grafico_col1:
    fig_dengue = px.line(df, x='Mês', y='Casos de Dengue', 
                         title='Evolução de Casos de Dengue', markers=True)
    st.plotly_chart(fig_dengue, use_container_width=True)

with grafico_col2:
    fig_internacoes = px.bar(df, x='Mês', y='Internações', 
                             title='Internações Hospitalares por Mês',
                             color_discrete_sequence=['#ff7f0e'])
    st.plotly_chart(fig_internacoes, use_container_width=True)

with st.expander("Ver dados tabulares completos"):
    st.dataframe(df, use_container_width=True)
