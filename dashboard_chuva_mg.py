import streamlit as st
import pandas as pd
import geopandas as gpd
import leafmap.foliumap as leafmap

# URLs e caminhos de arquivos
shp_mg_url = 'https://github.com/giuliano-macedo/geodata-br-states/raw/main/geojson/br_states/br_mg.json'
csv_file_path = 'caminho/para/seu/arquivo/lista_das_estacoes_CEMADEN_13maio2024.csv'

# Carregar os dados do shapefile de Minas Gerais
mg_gdf = gpd.read_file(shp_mg_url)

# Carregar os dados das estações
df = pd.read_csv(csv_file_path)
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['Longitude'], df['Latitude']))

# Realizar o filtro espacial: apenas estações dentro de Minas Gerais
gdf_mg = gpd.sjoin(gdf, mg_gdf, predicate='within')

# Função principal do dashboard
def main():
    st.title("Dashboard de Chuva - Minas Gerais")
    
    # Exibir o DataFrame filtrado
    st.subheader("Dados de Estações Pluviométricas em Minas Gerais")
    st.write(gdf_mg[['Código', 'Nome', 'Latitude', 'Longitude']])

    # Mapa interativo usando Leafmap
    st.subheader("Mapa de Estações Pluviométricas em Minas Gerais")
    m = leafmap.Map(center=[-18.5122, -44.5550], zoom=6)

    for i, row in gdf_mg.iterrows():
        m.add_marker(location=[row['Latitude'], row['Longitude']], popup=f"{row['Nome']} (Código: {row['Código']})")

    m.to_streamlit()

if __name__ == "__main__":
    main()
