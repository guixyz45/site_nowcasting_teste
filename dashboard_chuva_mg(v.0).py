import streamlit as st
import pandas as pd
import geopandas as gpd
import requests
from datetime import datetime, timedelta
import leafmap.foliumap as leafmap
import folium
from folium.plugins import MarkerCluster

# URLs e caminhos de arquivos
mg_shp_url = 'https://github.com/giuliano-macedo/geodata-br-states/raw/main/geojson/br_states/br_mg.json'
csv_file_path = 'input;/lista_das_estacoes_CEMADEN_13maio2024.csv'

# Login e senha do CEMADEN (previamente fornecidos)
login = 'd2020028915@unifei.edu.br'
senha = 'gLs24@ImgBr!'

# Carregar os dados do shapefile de Minas Gerais
mg_gdf = gpd.read_file(mg_shp_url)

# Carregar os dados das estações
df = pd.read_csv(csv_file_path)
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['Longitude'], df['Latitude']))

# Realizar o filtro espacial: apenas estações dentro de Minas Gerais
gdf_mg = gpd.sjoin(gdf, mg_gdf, predicate='within')

# Recuperação do token
token_url = 'http://sgaa.cemaden.gov.br/SGAA/rest/controle-token/tokens'
login_payload = {'email': login, 'password': senha}
response = requests.post(token_url, json=login_payload)
content = response.json()
token = content['token']

# Função para baixar os dados da estação e retornar a soma do último mês
def baixar_dados_estacao(codigo_estacao, sigla_estado, data_inicial, data_final, login, senha):
    dfs = []
    for ano_mes_dia in pd.date_range(data_inicial, data_final, freq='1M'):
        ano_mes = ano_mes_dia.strftime('%Y%m')
        sws_url = 'http://sws.cemaden.gov.br/PED/rest/pcds/df_pcd'
        params = dict(rede=11, uf=sigla_estado, inicio=ano_mes, fim=ano_mes, codigo=codigo_estacao)
        r = requests.get(sws_url, params=params, headers={'token': token})

        if r.text:
            df_mes = pd.read_csv(pd.compat.StringIO(r.text))
            dfs.append(df_mes)

        if dfs:
            dados_completos = pd.concat(dfs, ignore_index=True)
            dados_completos['datahora'] = pd.to_datetime(dados_completos['datahora'], format='%Y-%m-%d %H:%M:%S')
            ultimo_mes = dados_completos['datahora'].max().strftime('%Y-%m')
            dados_ultimo_mes = dados_completos[dados_completos['datahora'].dt.strftime('%Y-%m') == ultimo_mes]
            soma_ultimo_mes = dados_ultimo_mes['valor'].sum()
            return dados_completos, soma_ultimo_mes
        else:
            return pd.DataFrame(), 0

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

    # Adicionar marcadores das estações meteorológicas em Minas Gerais no estilo fornecido
    for i, row in gdf_mg.iterrows():
        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=8,  # Tamanho da bolinha
            color='purple',  # Cor da borda
            fill=True,
            fill_color='green',  # Cor de preenchimento
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

    tipo_busca = st.sidebar.radio("Tipo de Busca:", ('Diária', 'Mensal'))

    if tipo_busca == 'Diária':
        data_inicial = st.sidebar.date_input("Data Inicial", value=data_inicial)
        data_final = st.sidebar.date_input("Data Final", value=data_final)
    else:
        ano_selecionado = st.sidebar.selectbox("Selecione o Ano", range(2020, datetime.now().year + 1))
        mes_selecionado = st.sidebar.selectbox("Selecione o Mês", range(1, 13))

        data_inicial = datetime(ano_selecionado, mes_selecionado, 1)
        data_final = datetime(ano_selecionado, mes_selecionado + 1, 1) - timedelta(days=1) if mes_selecionado != 12 else datetime(ano_selecionado, 12, 31)

    if st.sidebar.button("Baixar Dados"):
        data_inicial_str = data_inicial.strftime('%Y%m%d')
        data_final_str = data_final.strftime('%Y%m%d')
        dados_estacao, soma_ultimo_mes = baixar_dados_estacao(codigo_estacao, sigla_estado, data_inicial, data_final, login, senha)

        if not dados_estacao.empty:
            st.subheader(f"Dados da Estação: {estacao_selecionada} (Código: {codigo_estacao})")
            st.write(dados_estacao)
        else:
            st.warning("Nenhum dado encontrado para o período selecionado.")

    m.to_streamlit()

if __name__ == "__main__":
    main()
