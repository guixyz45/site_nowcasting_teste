import streamlit as st
import pandas as pd
import geopandas as gpd
import requests
import leafmap.foliumap as leafmap

# URLs e caminhos de arquivos
shp_mg_url = 'https://github.com/giuliano-macedo/geodata-br-states/raw/main/geojson/br_states/br_mg.json'
csv_file_path = 'input;/lista_das_estacoes_CEMADEN_13maio2024.csv'

# Login e senha do CEMADEN (previamente fornecidos)
login = 'd2020028915@unifei.edu.br'
senha = 'gLs24@ImgBr!'

# Carregar os dados do shapefile de Minas Gerais
mg_gdf = gpd.read_file(shp_mg_url)

# Carregar os dados das estações
df = pd.read_csv(csv_file_path)
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['Longitude'], df['Latitude']))

# Realizar o filtro espacial: apenas estações dentro de Minas Gerais
gdf_mg = gpd.sjoin(gdf, mg_gdf, predicate='within')

# Função para baixar os dados da estação
def baixar_dados_estacao(codigo_estacao, sigla_estado, data_inicial, data_final, login, senha):
    # Recuperação do token
    token_url = 'http://sgaa.cemaden.gov.br/SGAA/rest/controle-token/tokens'
    login_payload = {'email': login, 'password': senha}
    response = requests.post(token_url, json=login_payload)
    content = response.json()
    token = content['token']

    # Lista para armazenar os dados
    dfs = []

    # Loop para baixar os dados mês a mês
    for ano_mes_dia in pd.date_range(data_inicial, data_final, freq='1M'):
        ano_mes = ano_mes_dia.strftime('%Y%m')
        sws_url = 'http://sws.cemaden.gov.br/PED/rest/pcds/df_pcd'
        params = dict(rede=11, uf=sigla_estado, inicio=ano_mes, fim=ano_mes, codigo=codigo_estacao)
        r = requests.get(sws_url, params=params, headers={'token': token})
        
        # Se há dados, adiciona ao DataFrame
        if r.text:
            df_mes = pd.read_csv(pd.compat.StringIO(r.text))
            dfs.append(df_mes)

    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        return pd.DataFrame()

# Função principal do dashboard
def main():
    st.title("Dashboard de Chuva - Minas Gerais")

    # Inputs do usuário
    estacao_selecionada = st.selectbox("Selecione a Estação", gdf_mg['Nome'].unique())
    codigo_estacao = gdf_mg[gdf_mg['Nome'] == estacao_selecionada]['Código'].values[0]
    sigla_estado = 'MG'

    # Seleção de datas
    data_inicial = st.date_input("Data Inicial", value=pd.to_datetime('2023-01-01'))
    data_final = st.date_input("Data Final", value=pd.to_datetime('2023-12-31'))

    if st.button("Baixar Dados"):
        # Converter datas para o formato necessário
        anoi, mesi, diai = data_inicial.year, data_inicial.month, data_inicial.day
        anof, mesf, diaf = data_final.year, data_final.month, data_final.day
        diaf = str(calendar.monthrange(anof, mesf)[1])  # Último dia do mês final

        data_inicial_str = f'{anoi:04d}{mesi:02d}{diai:02d}'
        data_final_str = f'{anof:04d}{mesf:02d}{diaf:02d}'

        # Baixar os dados da estação
        dados_estacao = baixar_dados_estacao(codigo_estacao, sigla_estado, data_inicial_str, data_final_str, login, senha)
        
        if not dados_estacao.empty:
            st.subheader(f"Dados da Estação: {estacao_selecionada}")
            st.write(dados_estacao)
        else:
            st.warning("Nenhum dado encontrado para o período selecionado.")

    # Mapa interativo usando Leafmap
    st.subheader("Mapa de Estações Pluviométricas em Minas Gerais")
    m = leafmap.Map(center=[-18.5122, -44.5550], zoom=6)

    for i, row in gdf_mg.iterrows():
        m.add_marker(location=[row['Latitude'], row['Longitude']], popup=f"{row['Nome']} (Código: {row['Código']})")

    m.to_streamlit()

if __name__ == "__main__":
    main()
