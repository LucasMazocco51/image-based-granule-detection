import os
import sys
import cv2
import csv
import logging

from src.classe_arquivo import Arquivo
from src.log_config import configurar_logger

logger = configurar_logger(__name__) # usa WARNING como default
# logger = configurar_logger(__name__, nivel_console=logging.INFO)
# logger = configurar_logger(__name__, nivel_console=logging.ERROR)

class Reconhecedor4Pontos:

    """
    Classe para capturar manualmente uma área formada por quatro pontos selecionados pelo usuário.

    No caso específico da Marispan, o objeto é um retângulo de lado 1m x 1m. Esta classe permite
    selecionar os vértices manualmente em substituição ao reconhecimento automático por transformadas.
    """

    def __init__(self, arquivoObj: Arquivo):
        # Inicializa o objeto com a imagem fornecida e define o caminho padrão do CSV que será gerado.
        self.arquivoObj       = arquivoObj
        self.pontos           = []  # Lista de pontos (x, y) capturados pelo usuário
        self.dimensoes_imagem = (self.arquivoObj.imgLargura, self.arquivoObj.imgAltura)
        self.caminho_csv      = os.path.join(arquivoObj.caminho, f"{arquivoObj.nomeArqB}_pontos_capturados.csv")


    # Função para capturar quatro pontos manualmente via interface gráfica do OpenCV.
    # Se o CSV já existir, a função evita sobrescrever os dados e cancela a captura.
    def capturar_com_mouse(self):

        if os.path.exists(self.caminho_csv):
            logger.warning("Arquivo de pontos já existe em: %s", os.path.dirname(self.caminho_csv))
            logger.warning("Nome do arquivo...............: %s", os.path.basename(self.caminho_csv))
            logger.info("Captura cancelada para evitar sobrescrever o CSV existente.")
            self.carregar_de_csv()
            return []

        if self.arquivoObj.imagem is None:
            logger.error("Imagem não foi definida para captura de pontos.")
            raise ValueError("Imagem não foi definida para captura de pontos.")

        # Cópia da imagem para exibição sem alterar a original
        imagem_display = self.arquivoObj.imagem.copy()
        self.pontos = []

        logger.info("Capture manualmente os 4 pontos com o mouse na seguinte ordem:")
        logger.info("P1) Superior esquerdo")
        logger.info("P2) Superior direito")
        logger.info("P3) Inferior esquerdo")
        logger.info("P4) Inferior direito")

        # Configuração da janela de exibição
        nomeJanela = "IMAGEM PARA CAPTURA DOS PONTOS MANUALMENTE - Clique em 4 pontos"
        cv2.namedWindow(nomeJanela, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(nomeJanela, 800, 600)

        # Callback para capturar cliques do mouse
        def _mouse_callback(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN and len(self.pontos) < 4:
                self.pontos.append((x, y))
                logger.info("Ponto capturado: (%d, %d)", x, y)
                raio = max(5, int(min(imagem_display.shape[:2]) * 0.01))
                cv2.circle(imagem_display, (x, y), raio, (0, 0, 255), -1)
                cv2.imshow(nomeJanela, imagem_display)

                # Fecha automaticamente ao atingir 4 pontos
                if len(self.pontos) == 4:
                    cv2.destroyAllWindows()

        # Exibição da imagem e captura dos eventos de clique
        cv2.imshow(nomeJanela, imagem_display)
        cv2.setMouseCallback(nomeJanela, _mouse_callback)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        self.salvar_para_csv()

        if len(self.pontos) != 4:
            logger.warning("Foram capturados menos de 4 pontos.")
        return None


    # Função para salvar os pontos capturados no arquivo CSV.
    # A primeira linha contém as dimensões da imagem; as demais, os pontos (x, y).
    def salvar_para_csv(self):

        if not self.caminho_csv:
            logger.error("Caminho para CSV não definido.")
            raise ValueError("Caminho para CSV não definido.")

        if not self.pontos or len(self.pontos) != 4:
            logger.error("São necessários exatamente 4 pontos para salvar.")
            raise ValueError("São necessários exatamente 4 pontos para salvar.")

        with open(self.caminho_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(self.dimensoes_imagem)
            writer.writerows(self.pontos)

        logger.info("Pontos salvos em...: %s", os.path.dirname(self.caminho_csv))
        logger.info("Nome do arquivo....: %s", os.path.basename(self.caminho_csv))


    # Função para carregar pontos e dimensões da imagem a partir do CSV.
    def carregar_de_csv(self):

        if not self.caminho_csv or not os.path.exists(self.caminho_csv):
            logger.error("Arquivo CSV não encontrado: %s", {self.caminho_csv})
            raise FileNotFoundError(f"Arquivo CSV não encontrado: {self.caminho_csv}")

        with open(self.caminho_csv, 'r') as f:
            reader        = csv.reader(f)
            dimensoes_str = next(reader)
            self.dimensoes_imagem = tuple(map(int, dimensoes_str))
            self.pontos = [tuple(map(int, row)) for row in reader]

        if len(self.pontos) != 4:
            logger.error("Arquivo CSV não contém exatamente 4 pontos.")
            raise ValueError("Arquivo CSV não contém exatamente 4 pontos.")

        logger.info("Pontos carregados de %s: %s", os.path.basename(self.caminho_csv), self.pontos)


'==================================== Início para execução isolada do módulo =========================================='

if __name__ == "__main__":
    print("\nTeste da classe Reconhecedor4Pontos")

    tipoImagem = "IMAGEM ORIGINAL"

    try:
        # Seleciona e carrega a imagem
        arquivoObj = Arquivo()
        arquivoObj.selecionar_arquivo(tipoImagem)
        arquivoObj.carregar_imagem()

        # Instancia a classe reconhecedora
        reconhecedor = Reconhecedor4Pontos(arquivoObj)

        # Inicia a captura dos pontos
        reconhecedor.capturar_com_mouse()

        # Se pontos foram capturados corretamente, salva e testa carregamento
        if len(reconhecedor.pontos) == 4:
            print("\n[INFO] Carregando pontos salvos para verificar...")
            reconhecedorTeste = Reconhecedor4Pontos(arquivoObj)
            reconhecedorTeste.carregar_de_csv()
            print(f"\033[92m[CHECK] Pontos carregados com sucesso:\033[0m {reconhecedorTeste.pontos}")

        # Caso o CSV já existisse, não faz nada
        elif len(reconhecedor.pontos) == 0 and os.path.exists(reconhecedor.caminho_csv):
            print("\033[93m[INFO] Captura não realizada pois o arquivo CSV já existia. Nenhuma ação foi feita.\033[0m")

        # Captura incompleta
        else:
            print("\033[91m[ERRO] Não foram capturados 4 pontos. Operação cancelada.\033[0m")

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
