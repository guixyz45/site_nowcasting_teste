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

import streamlit as st
import leafmap.foliumap as leafmap
import requests
import pandas as pd
import geopandas as gpd
import io
import numpy as np
from datetime import datetime, timedelta

# URLs e caminhos de arquivos
mg_shp_url = 'https://github.com/giuliano-macedo/geodata-br-states/raw/main/geojson/br_states/br_mg.json'
csv_file_path = 'input/lista_das_estacoes_CEMADEN_13maio2024.csv'

# Função para carregar os dados de Minas Gerais e das estações
@st.cache_data
def load_data():
    # Carregar o shapefile de Minas Gerais
    mg_gdf = gpd.read_file(mg_shp_url)
    # Carregar os dados das estações
    df = pd.read_csv(csv_file_path)
    # Convertendo o DataFrame para GeoDataFrame usando longitude e latitude
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['Longitude'], df['Latitude']))
    # Filtrar as estações que estão dentro de Minas Gerais
    gdf_mg = gpd.sjoin(gdf, mg_gdf, predicate='within')
    return mg_gdf, gdf_mg

# Função para gerar o mapa interativo
def create_map(mg_gdf, gdf_mg):
    # Cria um mapa focado em Minas Gerais
    m = leafmap.Map(center=[-19.2, -44.2], zoom=6)
    # Adiciona o shapefile de Minas Gerais ao mapa
    m.add_gdf(mg_gdf, layer_name="Minas Gerais", style={'fillColor': '#0000ff', 'color': '#0000ff'})
    # Adiciona as estações ao mapa
    for idx, row in gdf_mg.iterrows():
        popup = f"Estação: {row['Nome']}<br>Município: {row['Municipio']}"
        m.add_marker(location=[row.geometry.y, row.geometry.x], popup=popup)
    return m

# Carregar dados
mg_gdf, gdf_mg = load_data()

# Configuração da interface com Streamlit
st.title("Dashboard de Precipitação - Sul de Minas Gerais")

# Exibir mapa interativo com estações de monitoramento
st.subheader("Mapa Interativo das Estações de Monitoramento em Minas Gerais")
m = create_map(mg_gdf, gdf_mg)
st.write(m.to_streamlit(width=700, height=500))

