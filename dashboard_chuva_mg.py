import streamlit as st
import pandas as pd
import leafmap.foliumap as leafmap

# Carregar os dados de chuva (substitua o caminho pelo seu arquivo de dados)
@st.cache
def load_data():
    # Exemplo de dados fictícios, você deve carregar seus próprios dados
    data = pd.DataFrame({
        'Municipio': ['Belo Horizonte', 'Uberlândia', 'Juiz de Fora', 'Montes Claros', 'Governador Valadares'],
        'Latitude': [-19.9245, -18.9128, -21.7596, -16.7282, -18.8500],
        'Longitude': [-43.9352, -48.2754, -43.3390, -43.8616, -41.9450],
        'Precipitacao': [100, 150, 120, 90, 200]  # em mm
    })
    return data

# Função principal
def main():
    st.title("Dashboard de Chuva - Minas Gerais")
    
    # Carregar os dados
    data = load_data()

    # Exibir o DataFrame
    st.subheader("Dados de Precipitação")
    st.write(data)

    # Mapa interativo usando Leafmap
    st.subheader("Mapa de Precipitação")
    m = leafmap.Map(center=[-18.5122, -44.5550], zoom=6)

    for i, row in data.iterrows():
        m.add_marker(location=[row['Latitude'], row['Longitude']], popup=f"{row['Municipio']}: {row['Precipitacao']} mm")

    m.to_streamlit()

    # Gráfico de precipitação
    st.subheader("Gráfico de Precipitação por Município")
    st.bar_chart(data.set_index('Municipio')['Precipitacao'])

if __name__ == "__main__":
    main()
