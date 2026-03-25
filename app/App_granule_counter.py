import os
import pickle
import sys
import cv2
import logging

import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.classe_arquivo      import Arquivo
from src.ajuste_de_imagem_4P import Ajustador
from src.image_processing    import ReconhecedorGraos
from src.log_config          import configurar_logger

logger = configurar_logger(__name__) # usa WARNING como default
# logger = configurar_logger(__name__, nivel_console=logging.INFO)
# logger = configurar_logger(__name__, nivel_console=logging.ERROR)

pd.set_option('display.max_rows', 100)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
pd.set_option('display.float_format', '{:.4f}'.format)

caminho_arquivo_pickle = os.path.join(os.getcwd(), "src", "fertilizantes_data.pkl")


'============================= Parte opcional prevendo a construção do dataset de fertilizantes ======================='

try:
    df_carregado = pd.read_pickle(caminho_arquivo_pickle)
    logger.info("DataFrame carregado com sucesso:")
    logger.info("\n%s", df_carregado)
except FileNotFoundError:
    logger.warning("O arquivo '%s' não foi encontrado. Executando base_fertilizante.py", caminho_arquivo_pickle)
    import base_fertilizantes as baseFert
    df_carregado = baseFert.main("src")
except Exception as e:
    logger.error("Erro ao carregar o DataFrame do pickle: %s", e)


'==================================== Início para execução isolada do módulo =========================================='


tipoImagem = "ORIGINAL"

fert_procurado       = "Ureia"
diam_procurado       = 4.00
massa_fertilizante   = df_carregado.loc[(fert_procurado, diam_procurado), "Massa por diâmetro (mg) Densidade ureia cristalina"]
filtro_fertilizantes = {
    "FC": 2.4,
    "FP": 1.0,
    "U": 1.5
}


try:
    # Etapa inicial de seleção do arquivo
    arquivoObj = Arquivo()
    arquivoObj.selecionar_arquivo(tipoImagem)

    # Carrega a imagem ajustada
    arquivoObj.carregar_imagem()

    #
    print("\nEscolha uma das seguintes opções de fertilizantes:")
    logger.info("Escolha uma das seguintes opções de fertilizantes:")
    for chave in filtro_fertilizantes:
        print(f"- {chave}")

    while True:
        escolha_filtro = input("Sua escolha: ").upper()
        if escolha_filtro in filtro_fertilizantes:
            valor_filtro = float(filtro_fertilizantes[escolha_filtro])
            print(f"\nVocê escolheu '{escolha_filtro}' com o valor de filtro do grão em {valor_filtro} mm.")
            logger.info("Filtro escolhido: %s com valor %.2f mm", escolha_filtro, valor_filtro)
            break
        else:
            print("Opção inválida. Por favor, escolha uma das opções listadas.")
            logger.warning("Opção inválida: %s", escolha_filtro)

    if arquivoObj.imagem is None:
        logger.error("Imagem não carregada corretamente ou está vazia.")
        raise ValueError("Imagem não carregada corretamente ou está vazia.")

    # Pergunta ao usuário qual técnica utilizar
    while True:
        escolha = input("\nDeseja detectar retângulo automaticamente? (s/n): ").strip().lower()
        if escolha in ('s', 'n'):
            break
        print("Resposta inválida! Por favor, digite 's' para sim ou 'n' para não.")
        print()

    if escolha == 's':
        # Utiliza reconhecimento automático do retângulo.
        from detecta_hough_lines import Detecta

        logger.info("Detecção automática usando Hough lines selecionada.")

        detector = Detecta(arquivoObj,
                           threshold    = 300,
                           kernel       = (5, 5),
                           salva_imagem = False,
                           plot         = True)
        detector.detectaArea4V()
        obj_reconhecido = detector
    else:
        # Utiliza o reconhecimento manual do retângulo por meio de quatro cliques com o mouse.
        from detecta_4_pontos import Reconhecedor4Pontos

        logger.info("Detecção manual do usuário com cliques do mouse selecionada.")

        reconhecedor = Reconhecedor4Pontos(arquivoObj)
        reconhecedor.capturar_com_mouse()
        obj_reconhecido = reconhecedor


        # Faz o ajuste da imagem (planificação e recorte).
    ajustador = Ajustador(arquivoObj,
                          obj_reconhecido,
                          salva_imagem = False,
                          plot         = True)

    ajustador.processar()

    # Inicializa o reconhecedor de grãos (partículas).
    proc = ReconhecedorGraos(arquivoObj,
                             ajustador.imagem_recortada,
                             lower_color  = 0,
                             upper_color  = 80,
                             diametro_mm  = valor_filtro,
                             tolerancia   = 0.8,
                             plot         = False)

    # Dicionários de resultados do módulo "ajuste_de_imagem_4P.py":
    # "quantidade":         self.qtd_particulas,
    # "area_m2":            self.area_total_m2,
    # "contornos":          self.contornos,
    # "imagem_original":    self.imagem,
    # "mascara":            self.mascara,
    # "mascara_miniatura":  self.mascaraMini,
    # "area_minima_pixels": self.area_minima_px,
    # "pixels_por_metro":   self.pixels_por_metro
    resultados = proc.processar()

    # Exibe resultados
    print('\033[93m\nProcessamento concluído!\033[0m\n')
    print(f'Qtd de partículas......: {resultados["quantidade"]}')
    print(f'Mass de fertilizante...: {(resultados["quantidade"]*massa_fertilizante)/1000:.2f} g')
    print(f'Área total (m²)........: {resultados["area_m2"]:.6f}')
    logger.info("Processamento concluído!")
    logger.info("Qtd de partículas......: %s", resultados["quantidade"])
    logger.info("Massa de fertilizante..: %.2f g", (resultados["quantidade"] * massa_fertilizante) / 1000)
    logger.info("Área total (m²)........: %.6f", resultados["area_m2"])

    proc.mascaraMini.show()

# Tratamento de erros com mensagens específicas
except FileNotFoundError as e:
    logger.error("Arquivo não encontrado: %s", e)
    logger.critical("Encerrando a execução devido a erro crítico.\n")
    print(f"\n\033[91m[ERRO] Arquivo não encontrado:\033[0m {e}")
    sys.exit(0)

except ValueError as e:
    logger.error("Valor inválido: %s", e)
    logger.critical("Encerrando a execução devido a erro crítico.\n")
    print(f"\n\033[91mErro:\033[0m {e}")
    sys.exit(0)

except NotADirectoryError as e:
    logger.error("Falha de diretório: %s", e)
    logger.critical("Encerrando a execução devido a erro crítico.\n")
    print(f"\n\033[91m[ERRO] Falha de diretório:\033[0m {e}")
    sys.exit(0)

except IOError as e:
    logger.error("Erro de leitura de imagem: %s", e)
    logger.critical("Encerrando a execução devido a erro crítico.\n")
    print(f"\n\033[91m[ERRO] Falha na leitura da imagem:\033[0m {e}")
    sys.exit(0)

except Exception as e:
    logger.exception("Erro inesperado: %s", e)
    logger.critical("Encerrando a execução devido a erro crítico.\n")
    print(f"\n\033[91m[ERRO] Erro inesperado:\033[0m {e}")
    sys.exit(1)

logger.critical(f"Fim da execução com sucesso.\n")
