# Dashboard de Indicadores de Saúde Pública - Ocara/CE

Este projeto consiste em um painel interativo (dashboard) desenvolvido em **Streamlit** para visualização, monitoramento e análise de indicadores públicos de saúde do município de Ocara, Ceará. 

O sistema foi arquitetado para operar de forma autônoma, contando com um pipeline automatizado de Extração, Transformação e Carga (ETL) que busca dados diretamente das bases oficiais do Ministério da Saúde (**DATASUS**) sem a necessidade de intervenção humana.

---

## 🚀 Funcionalidades

- **Indicadores em Tempo Real (KPIs):** Visualização rápida de métricas críticas como casos de arboviroses (Dengue), internações hospitalares e consultas em Unidades Básicas de Saúde (UBS).
- **Gráficos Interativos:** Gráficos de linha e barras gerados via **Plotly**, permitindo análise temporal e exploração dinâmica dos dados históricos.
- **Extração Automatizada (ETL):** Script Python que consulta o catálogo do PySUS para detectar automaticamente o período mais recente disponível, baixa microdados de Autorizações de Internação Hospitalar (AIH Reduzida) e aplica filtros granulares por município.
- **Otimização de Performance:** Implementação de mecanismos de *caching* (`@st.cache_data`) no Streamlit para garantir carregamento sub-segundo da interface e evitar requisições redundantes de I/O.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.12+
- **Gerenciador de Pacotes/Ambiente:** [uv](https://docs.astral.sh/uv/) (substitui `pip` + `venv`)
- **Interface Web:** [Streamlit](https://streamlit.io/)
- **Manipulação de Dados:** [Pandas](https://pandas.pydata.org/)
- **Visualização Gráfica:** [Plotly Express](https://plotly.com/python/)
- **Ingestão de Dados:** [PySUS](https://github.com/AlertaDengue/PySUS) (Conexão e decodificação de arquivos `.dbc` do DATASUS)
- **Automação/Orquestração:** GitHub Actions (Pipeline CI/CD serverless com execução agendada)

---

## 📂 Estrutura do Repositório

```text
├── .github/
│   └── workflows/
│       └── atualiza_datasus.yml  # Pipeline de automação do GitHub Actions
├── dados/
│   └── internacoes_ocara.csv     # Base de dados local filtrada e atualizada
├── src/
│   ├── app.py                    # Aplicação principal do Streamlit
│   └── extrator_datasus.py       # Script de ETL (Download e filtragem via PySUS)
├── pyproject.toml                # Definição do projeto e dependências (uv)
├── uv.lock                      # Lockfile de dependências (gerado pelo uv)
└── .python-version               # Versão do Python fixada para o projeto
```

---

## ⚙️ Arquitetura de Automação (ETL)

O fluxo de dados foi projetado para evitar processos manuais de download no TabNet:

1. **Gatilho via GitHub Actions:** Um workflow agendado roda periodicamente (configurado para o dia 15 de cada mês às 03:00 AM UTC), eliminando a necessidade de crontab local.
2. **Detecção Automática:** O script consulta o catálogo do PySUS (`list_files`) para identificar o mês mais recente com dados de AIH Reduzida disponíveis, evitando falhas quando o DATASUS ainda não publicou o período mais recente.
3. **Coleta de Microdados:** O script `extrator_datasus.py` aciona a API do `PySUS` para baixar os arquivos consolidados do estado do Ceará (`CE`).
4. **Filtragem por Código IBGE:** O dataset é filtrado utilizando o código de identificação do município de Ocara (**230930**) na coluna de residência do paciente (`MUNIC_RES`).
5. **Persistência Incremental:** Os dados novos são mesclados com a base histórica (`dados/internacoes_ocara.csv`), removendo duplicatas.
6. **Atualização da Tela:** No modelo de nuvem (Streamlit Cloud), o pipeline faz o *push* automático para o repositório, disparando o *hot-reload* da aplicação.

---

## 🔧 Como Executar o Projeto

### 1. Pré-requisitos

Certifique-se de ter o **[uv](https://docs.astral.sh/uv/)** instalado:

```bash
# Instalar o uv (Linux/macOS)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Ou via pip (qualquer plataforma)
pip install uv
```

> **Nota:** O projeto requer Python **3.12 ou 3.13**. O `uv` irá baixar e gerenciar a versão correta automaticamente — não é necessário instalá-la manualmente.

### 2. Instalação das Dependências

Clone o repositório e instale todas as dependências com um único comando:

```bash
git clone <url-do-repositório>
cd dashboard-saude-ocara-ce

# Instalar dependências e criar ambiente virtual automaticamente
uv sync
```

### 3. Execução do Ingestor de Dados (Opcional para primeiro setup)

Para forçar a carga inicial de dados históricos do DATASUS:

```bash
uv run python src/extrator_datasus.py
```

### 4. Inicialização do Dashboard

Rode a aplicação Streamlit localmente:

```bash
uv run streamlit run src/app.py
```

O painel estará acessível no endereço padrão `http://localhost:8501`.

---

## Fontes de Dados Referenciadas

* **DATASUS (TabNet/SIHSUS):** Sistema de Informacoes Hospitalares do SUS. Microdados de AIH Reduzida acessados via [PySUS](https://github.com/AlertaDengue/PySUS).
* **IntegraSUS:** Portal de transparencia da Secretaria da Saude do Estado do Ceara (SESA).
* **Tabela CID-10 (Subcategorias):** Arquivo `CID-10-SUBCATEGORIAS.CSV` extraido do repositorio [CidDataSus](https://github.com/cleytonferrari/CidDataSus) (`CIDImport/Repositorio/Resources/CID-10-SUBCATEGORIAS.CSV`). Contem 12.451 subcategorias da Classificacao Internacional de Doencas em portugues, utilizado para converter codigos CID-10 em nomes de diagnostico no dashboard. Codificacao original ISO-8859-1, separador `;`.