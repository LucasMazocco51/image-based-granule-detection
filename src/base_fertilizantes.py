import os

import pandas as pd
import math
import pickle

pd.set_option('display.max_rows', 100)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
pd.set_option('display.float_format', '{:.4f}'.format)

# Inicialmente, apenas para a Ureia Heringer
configuracao_fertilizantes = {
    "Ureia": {
        "Fator de empacotamento": 0.64,  # 64%
        "Densidade": 740.0,  # kg/m3
        "Densidade real ureia cristalina": 1335.0,  # kg/m3
        "Diâmetros do fertilizante (mm)": [2.00, 2.50, 3.00, 3.50, 4.00, 4.50, 5.00]
    },
    "Sulfato de Amônia": {
        "Fator de empacotamento": 0.62,
        "Densidade": 950.0,
        "Densidade real ureia cristalina": 1770.0,
        "Diâmetros do fertilizante (mm)": [1.80, 2.20, 2.80, 3.20]
    }
}

# Função de cálculo das propriedades do fertilizante
def calcular_propriedades_fertilizante(nome_fertilizante: str, configuracao: dict) -> pd.DataFrame:
    if nome_fertilizante not in configuracao:
        raise ValueError(f"Fertilizante '{nome_fertilizante}' não encontrado na configuração.")

    params                    = configuracao[nome_fertilizante]
    fator_empacotamento       = params["Fator de empacotamento"]
    densidade                 = params["Densidade"]
    densidade_real_cristalina = params["Densidade real ureia cristalina"]
    diametros                 = params["Diâmetros do fertilizante (mm)"]

    # Listas para armazenar os resultados temporariamente
    volumes_mm3                    = []
    qtd_esferas_por_m3             = []
    massa_por_diam_qtde_esferas    = []
    massa_por_diam_dens_cristalina = []

    for diametro in diametros:
        # Volume mm3 = (4/3)*PI()*((Diametro do fertilizante/2)^3)
        volume_mm3 = (4/3) * math.pi * ((diametro / 2)**3)
        volumes_mm3.append(volume_mm3)

        # Quantidade de esferas por m3 = ROUND(((1*10^9)*Fator de empacotamento)/Volume mm3;0)
        qtd_esferas = round(((1 * (10**9)) * fator_empacotamento) / volume_mm3, 0)
        qtd_esferas_por_m3.append(qtd_esferas)

        # Massa por diâmetro (mg) Qtde de esferas / 1m3 = (Densidade/Quantidade de esferas por m3)*10^6
        if qtd_esferas > 0:
            massa_qtde_esferas = (densidade / qtd_esferas) * (10**6)
        else:
            massa_qtde_esferas = 0.0
        massa_por_diam_qtde_esferas.append(massa_qtde_esferas)

        # Massa por diâmetro (mg) Densidade ureia cristalina = Densidade real ureia cristalina/1000*Volume mm³
        massa_dens_cristalina = (densidade_real_cristalina * (10**-3)) * volume_mm3
        massa_por_diam_dens_cristalina.append(massa_dens_cristalina)

    # Cria o DataFrame
    df_resultado = pd.DataFrame({
        "Fertilizante": nome_fertilizante,
        "Diâmetro do fertilizante (mm)": diametros,
        "Volume (mm3)": volumes_mm3,
        "Quantidade de esferas por m3": qtd_esferas_por_m3,
        "Massa por diâmetro (mg) Qtde de esferas / 1m3": massa_por_diam_qtde_esferas,
        "Massa por diâmetro (mg) Densidade ureia cristalina": massa_por_diam_dens_cristalina
    })

    return df_resultado

def main(src = None):
    # Cria o dataframe de parâmetros do fertilizante
    # Lista para armazenar os DataFrames de cada fertilizante
    lista_de_dfs_por_fertilizante = []

    # Itera sobre cada fertilizante no dicionário de configuração
    for nome_fertilizante_atual in configuracao_fertilizantes.keys():
        df_temp = calcular_propriedades_fertilizante(nome_fertilizante_atual, configuracao_fertilizantes)
        lista_de_dfs_por_fertilizante.append(df_temp)

    # Concatena todos os DataFrames em um único DataFrame consolidado
    if lista_de_dfs_por_fertilizante:
        df_todos_fertilizantes = pd.concat(lista_de_dfs_por_fertilizante)
        df_todos_fertilizantes.set_index(["Fertilizante", "Diâmetro do fertilizante (mm)"], inplace=True)
        df_todos_fertilizantes.sort_index(inplace=True)
    else:
        df_todos_fertilizantes = pd.DataFrame()

    print("\nDataFrame Consolidado de Propriedades dos Fertilizantes (calculado dinamicamente):")
    print(df_todos_fertilizantes)

    # Salva o DataFrame em um arquivo pickle
    if src is None:
        caminhiArq_pickle = os.path.join(os.getcwd())
    else:
        caminhiArq_pickle = os.path.join(os.getcwd(), lib)

    arquivo_pickle    = "fertilizantes_data.pkl"

    try:
        df_todos_fertilizantes.to_pickle(os.path.join(caminhiArq_pickle, arquivo_pickle))
        print(f"\nDataFrame salvo com sucesso em..: {caminhiArq_pickle}")
        print(f"Nome do arquivo pickle..........: {arquivo_pickle}\n")
    except Exception as e:
        print(f"\nErro ao salvar o DataFrame em pickle: {e}")

    return df_todos_fertilizantes


if __name__ == "__main__":
    main()
