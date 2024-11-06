import streamlit as st
import pandas as pd
import geopandas as gpd
import requests
import io
import numpy as np
from datetime import datetime, timedelta
import leafmap.foliumap as leafmap
import folium
from folium.plugins import MarkerCluster
import plotly.express as px


# URLs e caminhos de arquivos
mg_shp_url = 'https://github.com/giuliano-macedo/geodata-br-states/raw/main/geojson/br_states/br_mg.json'
csv_file_path = 'input;/lista_das_estacoes_CEMADEN_13maio2024.csv'

# Login e senha do CEMADEN (previamente fornecidos)
login = 'd2020028915@unifei.edu.br'
senha = 'gLs24@ImgBR!'

# Recuperação do token
token_url = 'http://sgaa.cemaden.gov.br/SGAA/rest/controle-token/tokens'
login_payload = {'email': login, 'password': senha}
response = requests.post(token_url, json=login_payload)
content = response.json()
token = content['token']

# URL e parâmetros para a requisição inicial de dados de estações
sws_url = 'http://sws.cemaden.gov.br/PED/rest/pcds/df_pcd'
params = dict(rede=11, uf='MG')
r = requests.get(sws_url, params=params, headers={'token': token})

# Carregar os dados do shapefile de Minas Gerais
mg_gdf = gpd.read_file(mg_shp_url)

# Carregar os dados das estações
df = pd.read_csv(csv_file_path)
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['Longitude'], df['Latitude']))

# Realizar o filtro espacial: apenas estações dentro de Minas Gerais
gdf_mg = gpd.sjoin(gdf, mg_gdf, predicate='within')

# Função de solicitação de dados de precipitação
def request_data(inicio, fim, uf, municipio, sws_url="http://sws.cemaden.gov.br/PED/rest/pcds/dados_rede"):
    date = datetime.strptime(inicio, "%Y%m%d%H%M")  # Convert inicio to datetime object
    fim = datetime.strptime(fim, "%Y%m%d%H%M")    # Convert fim to datetime object
    combined_df = None

    while date <= fim:
        print(f"Requesting data from: {date}")
        start_date = date.strftime("%Y%m%d%H%M")
        end_date = (date + timedelta(days=1)).strftime("%Y%m%d%H%M")
        params = dict(sensor=10, uf=uf, municipio=municipio, inicio=start_date, fim=end_date, formato="json")

        r = requests.get(sws_url, params=params, headers={'token': token})

        # Use StringIO to create a file-like object from the response text
        data = io.StringIO(r.text)

        try:
            df = pd.read_csv(data, sep=';', skiprows=1, encoding="ISO-8859-1")
            df = df.drop(columns=['sensor', 'qualificacao', 'offset'])
            df['datahora'] = pd.to_datetime(df['datahora'])
        except Exception as e:
            print(f"Error occurred: {e}")
            print(df)
            continue

        # Step 1: Create the pivoted data
        pivot_df = df.pivot(index='datahora', columns='cod.estacao', values='valor')

        # Step 2: Extract the station info and set as columns
        stations_info = df[['cod.estacao', 'nome', 'municipio', 'latitude', 'longitude']].drop_duplicates().set_index(
            'cod.estacao')

        if combined_df is None:
            combined_df = pd.concat([stations_info.T, pivot_df], axis=0)
        else:
            pivot_df = pivot_df.reindex(columns=combined_df.columns, fill_value=np.nan)
            combined_df = pd.concat([combined_df, pivot_df], axis=0)

        date += timedelta(days=1)

    return combined_df


# Função principal do dashboard
def main():
    hoje = datetime.now()

    st.set_page_config(layout="wide")

    st.markdown(
        """
        <style>
            .main .block-container {
                padding: 0;
                margin: 0;
            }
            iframe {
                height: 100vh !important;
                width: 100vw !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Mapa interativo usando Leafmap
    m = leafmap.Map(center=[-18.5122, -44.5550], zoom=7, draw_control=False, measure_control=False, fullscreen_control=False, attribution_control=True)

    # Criar um cluster de marcadores para agrupar os marcadores no mapa
    marker_cluster = MarkerCluster().add_to(m)

    # Adicionar marcadores das estações meteorológicas em Minas Gerais no estilo fornecido
    for i, row in gdf_mg.iterrows():
        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=8,  # Tamanho da bolinha
            color='blue',  # Cor da borda
            fill=True,
            fill_color='white',  # Cor de preenchimento
            fill_opacity=0.6,
            popup=f"{row['Nome']} (Código: {row['Código']})"
        ).add_to(marker_cluster)

    # Sidebar para seleção de estação e datas
    st.sidebar.header("Filtros de Seleção")

    modo_selecao = st.sidebar.radio("Selecionar Estação por:", ('Nome'))

    if modo_selecao == 'Nome':
        estacao_selecionada = st.sidebar.selectbox("Selecione a Estação", gdf_mg['Nome'].unique())
        codigo_estacao = gdf_mg[gdf_mg['Nome'] == estacao_selecionada]['Código'].values[0]

    latitude_estacao = gdf_mg[gdf_mg['Nome'] == estacao_selecionada]['Latitude'].values[0]
    longitude_estacao = gdf_mg[gdf_mg['Nome'] == estacao_selecionada]['Longitude'].values[0]

    sigla_estado = 'MG'

    # Definir intervalo de tempo para os dados horários
    st.sidebar.subheader("Período de Dados Horários")
    dias_opcao = st.sidebar.selectbox("Selecione o intervalo", ["Hoje", "Últimos 3 dias"])

    if dias_opcao == "Hoje":
        data_inicial = hoje
    else:
        data_inicial = hoje - timedelta(days=3)
        
    data_inicial_str = data_inicial.strftime('%Y%m%d%H%M')
    data_final_str = hoje.strftime('%Y%m%d%H%M')

    if st.sidebar.button("Mostrar Gráfico"):
        dados_estacao = request_data(data_inicial_str, data_final_str, sigla_estado, estacao_selecionada)

        if not dados_estacao.empty:
            st.subheader(f"Gráfico de Precipitação Horária - Estação: {estacao_selecionada} (Código: {codigo_estacao})")

            # Preparar os dados para o gráfico
            dados_estacao['datahora'] = pd.to_datetime(dados_estacao['datahora'])
            fig = px.line(dados_estacao, x=dados_estacao['datahora'], y='valor', title='Precipitação Horária', labels={'valor': 'Precipitação (mm)'})

            st.plotly_chart(fig)
        else:
            st.warning("Nenhum dado encontrado para o período selecionado.")

    m.to_streamlit()

if __name__ == "__main__":
    main()
