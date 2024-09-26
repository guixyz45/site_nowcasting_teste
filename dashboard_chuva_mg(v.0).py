import streamlit as st
import pandas as pd
import geopandas as gpd
import requests
from datetime import datetime, timedelta
import leafmap.foliumap as leafmap

# URLs e caminhos de arquivos
shp_mg_url = 'https://github.com/giuliano-macedo/geodata-br-states/raw/main/geojson/br_states/br_mg.json'
csv_file_path = 'input;/lista_das_estacoes_CEMADEN_13maio2024.csv'

# Login e senha do CEMADEN (previamente fornecidos)
login = 'd2020028915@unifei.edu.br'
senha = 'gLs24@ImgBR!'

# Carregar os dados do shapefile de Minas Gerais
mg_gdf = gpd.read_file(shp_mg_url)

# Carregar os dados das estações
df = pd.read_csv(csv_file_path)
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['Longitude'], df['Latitude']))

# Realizar o filtro espacial: apenas estações dentro de Minas Gerais
gdf_mg = gpd.sjoin(gdf, mg_gdf, predicate='within')

# Função principal do dashboard
def main():
    # Pega a data de hoje
    hoje = datetime.now()
    
    # Definir a data inicial como o primeiro dia do mês atual
    data_inicial = hoje.replace(day=1)
    
    # Definir a data final como a data de hoje
    data_final = hoje
    
    # Defina o layout da página como largo
    st.set_page_config(layout="wide")

    # CSS customizado para tornar o mapa tela cheia
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

    # Adiciona o shapefile de Minas Gerais ao mapa
    m.add_gdf(
        mg_gdf, 
        layer_name="Minas Gerais", 
        style={"color": "black", "weight": 1, "fillOpacity": 0, "interactive": False},
        info_mode=None
    )

    # Sidebar para seleção de estação e datas
    st.sidebar.header("Filtros de Seleção")

    # Opções de seleção: Nome ou Código
    modo_selecao = st.sidebar.radio("Selecionar Estação por:", ('Nome'))

    if modo_selecao == 'Nome':
        estacao_selecionada = st.sidebar.selectbox("Selecione a Estação", gdf_mg['Nome'].unique())
        codigo_estacao = gdf_mg[gdf_mg['Nome'] == estacao_selecionada]['Código'].values[0]

    # Recupera as coordenadas da estação selecionada
    latitude_estacao = gdf_mg[gdf_mg['Nome'] == estacao_selecionada]['Latitude'].values[0]
    longitude_estacao = gdf_mg[gdf_mg['Nome'] == estacao_selecionada]['Longitude'].values[0]

    sigla_estado = 'MG'

    # Escolha entre busca diária ou mensal
    tipo_busca = st.sidebar.radio("Tipo de Busca:", ('Diária', 'Mensal'))

    if tipo_busca == 'Diária':
        # Seleção de datas para busca diária
        data_inicial = st.sidebar.date_input("Data Inicial", value=data_inicial)
        data_final = st.sidebar.date_input("Data Final", value=data_final)
    else:
        # Seleção de mês para busca mensal
        ano_selecionado = st.sidebar.selectbox("Selecione o Ano", range(2020, datetime.now().year + 1))
        mes_selecionado = st.sidebar.selectbox("Selecione o Mês", range(1, 13))

        # Definindo a data inicial e final com base no mês e ano selecionados
        data_inicial = datetime(ano_selecionado, mes_selecionado, 1)
        data_final = datetime(ano_selecionado, mes_selecionado + 1, 1) - timedelta(days=1) if mes_selecionado != 12 else datetime(ano_selecionado, 12, 31)

    if st.sidebar.button("Baixar Dados"):
        # Converter datas para o formato necessário
        data_inicial_str = data_inicial.strftime('%Y%m%d')
        data_final_str = data_final.strftime('%Y%m%d')
        
        # Exibir os dados da estação (mock)
        st.subheader(f"Dados da Estação: {estacao_selecionada} (Código: {codigo_estacao})")
        st.write("Dados simulados aqui...")

    # Adiciona marcadores ao mapa com popups estilizados
    for i, row in gdf_mg.iterrows():
        estacao_nome = row['Nome']
        codigo_estacao = row['Código']

        # Conteúdo estilizado do popup
        popup_content = f"""
        <div style="font-family: Arial; border-radius: 10px; padding: 10px; background-color: #f9f9f9; box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1);">
            <h4 style="margin-bottom: 5px; color: #2b6cb0;">{estacao_nome}</h4>
            <p style="margin: 0;"><strong>Código:</strong> {codigo_estacao}</p>
            <p style="margin: 0;"><strong>Latitude:</strong> {row['Latitude']}</p>
            <p style="margin: 0;"><strong>Longitude:</strong> {row['Longitude']}</p>
        </div>
        """
        # Adiciona o marcador com popup estilizado
        m.add_marker(location=[row['Latitude'], row['Longitude']], popup=popup_content)

    # Exibe o mapa no Streamlit
    m.to_streamlit()

if __name__ == "__main__":
    main()
