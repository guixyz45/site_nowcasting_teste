import streamlit as st
import leafmap.foliumap as leafmap
import requests
import pandas as pd
import io
import numpy as np
from datetime import datetime, timedelta

# Login e senha do CEMADEN (previamente fornecidos)
login = 'd2020028915@unifei.edu.br'
senha = 'gLs24@ImgBr!'

# Recuperação do token
def get_token():
    token_url = 'http://sgaa.cemaden.gov.br/SGAA/rest/controle-token/tokens'
    login_payload = {'email': login, 'password': senha}
    response = requests.post(token_url, json=login_payload)
    content = response.json()
    return content['token']

# Função para solicitar dados de precipitação ao CEMADEN
def request_data(inicio, fim, uf, municipio, sws_url="http://sws.cemaden.gov.br/PED/rest/pcds/dados_rede"):
    token = get_token()  # Recupera o token
    date = datetime.strptime(inicio, "%Y%m%d%H%M")
    fim = datetime.strptime(fim, "%Y%m%d%H%M")
    combined_df = None

    while date <= fim:
        start_date = date.strftime("%Y%m%d%H%M")
        end_date = (date + timedelta(days=1)).strftime("%Y%m%d%H%M")
        params = dict(sensor=10, uf=uf, municipio=municipio, inicio=start_date, fim=end_date, formato="json")
        r = requests.get(sws_url, params=params, headers={'token': token})
        data = io.StringIO(r.text)

        try:
            df = pd.read_csv(data, sep=';', skiprows=1, encoding="ISO-8859-1")
            df = df.drop(columns=['sensor', 'qualificacao', 'offset'])
            df['datahora'] = pd.to_datetime(df['datahora'])
        except Exception as e:
            print(f"Erro: {e}")
            continue

        pivot_df = df.pivot(index='datahora', columns='cod.estacao', values='valor')
        stations_info = df[['cod.estacao', 'nome', 'municipio', 'latitude', 'longitude']].drop_duplicates().set_index('cod.estacao')

        if combined_df is None:
            combined_df = pd.concat([stations_info.T, pivot_df], axis=0)
        else:
            pivot_df = pivot_df.reindex(columns=combined_df.columns, fill_value=np.nan)
            combined_df = pd.concat([combined_df, pivot_df], axis=0)

        date += timedelta(days=1)

    return combined_df

# Função para visualizar dados de precipitação no mapa
def visualize_data_on_map(df):
    station_info = df.iloc[0:5].T.dropna(how='all')
    m = leafmap.Map(center=[-21.1, -45.0], zoom=7)
    for index, row in station_info.iterrows():
        m.add_marker(location=[row['latitude'], row['longitude']], popup=f"{row['nome']} ({row['municipio']})")
    return m

# Configuração da interface do usuário com Streamlit
st.title("Dashboard de Precipitação - Sul de Minas Gerais")

# Seleção do intervalo de datas
inicio = st.text_input("Data de início (formato: YYYYMMDDHHMM)", "202410180000")
fim = st.text_input("Data de fim (formato: YYYYMMDDHHMM)", "202410202300")

# Seleção do município
uf = "MG"  # Estado de Minas Gerais
municipio = st.text_input("Município", "Varginha")

# Botão para solicitar dados
if st.button("Consultar dados"):
    with st.spinner("Solicitando dados do CEMADEN..."):
        df = request_data(inicio, fim, uf, municipio)

    st.success("Dados carregados com sucesso!")

    # Exibe os dados em um mapa
    st.subheader("Mapa de Precipitação")
    m = visualize_data_on_map(df)
    st.write(m.to_streamlit(width=700, height=500))

    # Exibe dados de precipitação em formato de tabela
    st.subheader("Dados de Precipitação")
    st.dataframe(df.iloc[5:])

    # Exibe gráficos de precipitação por estação
    st.subheader("Gráficos de Precipitação por Estação")
    for station in df.columns[5:]:
        st.line_chart(df[station].dropna(), width=0, height=0, use_container_width=True)
