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
senha = 'gLs24@ImgBr!'

# Recuperação do token
token_url = 'http://sgaa.cemaden.gov.br/SGAA/rest/controle-token/tokens'
login_payload = {'email': login, 'password': senha}
response = requests.post(token_url, json=login_payload)
content = response.json()
token = content['token']

# Carregar os dados do shapefile de Minas Gerais
mg_gdf = gpd.read_file(mg_shp_url)

# Carregar os dados das estações
df = pd.read_csv(csv_file_path)
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['Longitude'], df['Latitude']))

# Filtrar apenas as estações dentro de Minas Gerais
gdf_mg = gpd.sjoin(gdf, mg_gdf, predicate='within')

# Lista das estações desejadas
codigo_estacao = ['314790701A', '310710901A', '312870901A', '315180001A', '316930701A',
                  '314780801A', '315250101A', '313240401A', '313360001A', '311410501A',
                  '316230201A', '313300601A']

# Filtrar as estações desejadas no GeoDataFrame
gdf_mg = gdf_mg[gdf_mg['Código'].isin(codigo_estacao)]

# Função de solicitação de dados de precipitação
def request_data(inicio, fim, uf, municipio, sws_url="http://sws.cemaden.gov.br/PED/rest/pcds/dados_rede"):
    date = datetime.strptime(inicio, "%Y%m%d%H%M")
    fim = datetime.strptime(fim, "%Y%m%d%H%M")
    combined_df = None

    while date <= fim:
        print(f"Requesting data from: {date}")
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
            print(f"Error occurred: {e}")
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


# Função principal do dashboard
def main():
    hoje = datetime.now()
    data_inicial = hoje.replace(day=1)
    data_final = hoje

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

    # Adicionar marcadores das estações meteorológicas selecionadas
    for i, row in gdf_mg.iterrows():
        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=8,
            color='blue',
            fill=True,
            fill_color='white',
            fill_opacity=0.6,
            popup=f"{row['Nome']} (Código: {row['Código']})"
        ).add_to(marker_cluster)

    # Sidebar para seleção de estação e datas
    st.sidebar.header("Filtros de Seleção")

    # Adicionar dropdown com a lista de estações filtradas
    estacao_selecionada = st.sidebar.selectbox("Selecione a Estação", gdf_mg['Nome'].unique())
    codigo_estacao_selecionada = gdf_mg[gdf_mg['Nome'] == estacao_selecionada]['Código'].values[0]

    sigla_estado = 'MG'

    tipo_busca = st.sidebar.radio("Tipo de Busca:", ('Diária', 'Mensal'))

    if tipo_busca == 'Diária':
        data_inicial = st.sidebar.date_input("Data Inicial", value=data_inicial)
        data_final = st.sidebar.date_input("Data Final", value=data_final)
    else:
        ano_selecionado = st.sidebar.selectbox("Selecione o Ano", range(2020, datetime.now().year + 1))
        mes_selecionado = st.sidebar.selectbox("Selecione o Mês", range(1, 13))
        data_inicial = datetime(ano_selecionado, mes_selecionado, 1)
        data_final = (datetime(ano_selecionado, mes_selecionado + 1, 1) - timedelta(days=1)) if mes_selecionado != 12 else datetime(ano_selecionado, 12, 31)

    if st.sidebar.button("Mostrar Gráfico"):
        data_inicial_str = data_inicial.strftime('%Y%m%d%H%M')
        data_final_str = data_final.strftime('%Y%m%d%H%M')
        dados_estacao = request_data(data_inicial_str, data_final_str, sigla_estado, estacao_selecionada)

        if not dados_estacao.empty:
            st.subheader(f"Gráfico de Precipitação - Estação: {estacao_selecionada} (Código: {codigo_estacao_selecionada})")

            dados_estacao['datahora'] = pd.to_datetime(dados_estacao['datahora'])
            if tipo_busca == 'Diária':
                dados_diarios = dados_estacao.resample('D', on='datahora').sum()
                fig = px.line(dados_diarios, x=dados_diarios.index, y='valor', title='Precipitação Diária', labels={'valor': 'Precipitação (mm)'})
            else:
                dados_mensais = dados_estacao.resample('M', on='datahora').sum()
                fig = px.bar(dados_mensais, x=dados_mensais.index, y='valor', title='Precipitação Mensal', labels={'valor': 'Precipitação (mm)'})

            st.plotly_chart(fig)
        else:
            st.warning("Nenhum dado encontrado para o período selecionado.")

    m.to_streamlit()

if __name__ == "__main__":
    main()
