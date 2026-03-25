import os
import sys
import cv2
import logging

import numpy             as np
import matplotlib.pyplot as plt


from src.classe_arquivo import Arquivo
from src.log_config import configurar_logger

# logger = configurar_logger(__name__) # usa WARNING como default
logger = configurar_logger(__name__, nivel_console=logging.INFO)
# logger = configurar_logger(__name__, nivel_console=logging.ERROR)

class ReconhecedorGraos:

    """
    Classe para processar imagem ajustada (recortada e corrigida) e realizar
    detecção de partículas com base na máscara HSV e no tamanho mínimo esperado.
    """

    def __init__(self, arquivoObj: Arquivo,
                 imagem       = None,
                 diametro_mm  = 2.0,
                 tolerancia   = 0.8,
                 lower_color  = 0,
                 upper_color  = 80,
                 plot         = True):

        # Objeto com informações do caminho da imagem
        self.arquivoObj     = arquivoObj

        if imagem is None:
            logger.error("A imagem ajustada fornecida está vazia ou inválida.")
            raise ValueError("A imagem ajustada fornecida está vazia ou inválida.")

        elif np.mean(imagem[:, :, 0]) > np.mean(imagem[:, :, 2]):
            logger.info("Convertendo imagem de RGB para BGR.")
            self.imagem_original = cv2.cvtColor(imagem, cv2.COLOR_RGB2BGR)

        else:
            # Imagem ajustada (vinda do módulo Ajustador)
            self.imagem_original = imagem

        # Redimensiona a imagem para 2200x2200 para padronizar escala
        self.imagem = cv2.resize(self.imagem_original, (2200, 2200), interpolation=cv2.INTER_AREA)

        # Faixa de cor para segmentação HSV
        self.lower_color     = lower_color
        self.upper_color     = upper_color

        # Diâmetro mínimo esperado da partícula (filtro) e tolerância
        self.diametro_padrao = diametro_mm
        self._atribui_filtro()
        self.tolerancia      = tolerancia

        # Visualização da imagem
        self.plot            = plot

        # Define a resolução da imagem como pixels por metro (ppm)
        self.pixels_por_metro = self.imagem.shape[0]

        # Calcula a área mínima em pixels com base no diâmetro e tolerância
        self.area_minima_px = self._calcular_area_minima_px()

        # Inicializa os resultados
        self.qtd_particulas = 0
        self.area_total_m2  = 0.0
        self.contornos      = []
        self.mascara        = None
        self.mascaraMini    = None


    # Função para definir o filtro em função do nome do arquivo (eventualmente pode ser um parâmetro do banco de dados)
    def _atribui_filtro(self):
        try:
            if "FC" in self.arquivoObj.nomeArqB:
                self.diametro_mm = 2.4
            elif "FP" in self.arquivoObj.nomeArqB:
                self.diametro_mm = 1.0
            elif "U" in self.arquivoObj.nomeArqB:
                self.diametro_mm = 1.5
            else:
                self.diametro_mm = self.diametro_padrao
                logger.warning("Tipo de fertilizante não identificado no nome do arquivo: %s, adotando o padrão %.2f", self.arquivoObj.nomeArqB, self.diametro_padrao)

        except Exception as e:
            logger.exception("Fertilizante não reconhecido na imagem: %s %s",  self.arquivoObj.nomeArqB, e)


    # Função para converter diâmetro de mm para pixels e calcular a área de um círculo
    def _calcular_area_minima_px(self):
        ppm           = self.pixels_por_metro
        pixels_por_mm = ppm / 1000
        raio_px       = (self.diametro_mm / 2) * pixels_por_mm
        area_px       = np.pi * (raio_px ** 2)

        return area_px * self.tolerancia


    # Função para ajustar contraste e brilho e converter para HSV, depois para escala de cinza
    def _converter_para_hsv(self):
        contraste = 1.5
        brilho    = 1

        imagem_ajustada = cv2.convertScaleAbs(self.imagem, alpha=contraste, beta=brilho)
        imagem_hsv      = cv2.cvtColor(imagem_ajustada, cv2.COLOR_BGR2HSV)
        imagem_cinza    = cv2.cvtColor(imagem_hsv, cv2.COLOR_BGR2GRAY)

        return imagem_cinza


    # Cria uma máscara binária com base nos valores HSV informados
    def _gerar_mascara(self, imagem_hsv):

        return cv2.inRange(imagem_hsv, self.lower_color, self.upper_color)


    # Função para reconhecer as partículas por meio de contornos
    def reconhecer_particulas(self):
        # Aplica limiarização para binarizar a máscara
        _, thresholded = cv2.threshold(self.mascara, 127, 255, cv2.THRESH_BINARY)

        # Encontra contornos externos
        contornos, _ = cv2.findContours(thresholded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        contornos_filtrados = []
        area_total          = 0.0

        # Filtra contornos com base na área mínima esperada
        for contorno in contornos:
            area_px = cv2.contourArea(contorno)
            if area_px >= self.area_minima_px:
                contornos_filtrados.append(contorno)
                # Converte a área da partícula para m²
                area_total += area_px * ((1 / self.pixels_por_metro) ** 2)

        # Armazena os resultados
        self.qtd_particulas = len(contornos_filtrados)
        self.area_total_m2  = area_total
        self.contornos      = contornos_filtrados


    # Função para exibir e savlar a imagem original e máscara em uma única figura
    def _plotar_resultados(self):
        img_rgb = cv2.cvtColor(self.imagem, cv2.COLOR_BGR2RGB)

        plt.figure(figsize=(20, 10))
        plt.subplot(1, 2, 1)
        plt.title("Imagem original ajustada")
        plt.imshow(img_rgb)
        plt.axis('off')

        plt.subplot(1, 2, 2)
        plt.title("Máscara binária por cor (HSV)")
        plt.imshow(self.mascara, cmap='gray')
        plt.axis('off')

        # Salva a figura com as imagens lado a lado
        if self.arquivoObj.nomeArqB.endswith("_com_retangulo"):
            img_nome = f'{self.arquivoObj.nomeArqB}_e_mascara.jpg'
        else:
            img_nome = f'{self.arquivoObj.nomeArqB}_com_retangulo_e_mascara.jpg'
        img_path = os.path.join(self.arquivoObj.caminho, img_nome)

        plt.savefig(img_path, dpi = 300)
        logger.info("Imagem com retângulo e máscara salva em...: %s", self.arquivoObj.caminho)
        logger.info("Nome do arquivo...........................: %s", img_nome)

        # Tenta maximizar a janela da figura
        try:
            mng = plt.get_current_fig_manager()
            mng.window.state('zoomed')  # TkAgg
        except Exception:
            try:
                mng.window.showMaximized()  # QtAgg, Qt5Agg
            except Exception:
                pass
        plt.show()


    # Função de execução da classe
    def processar(self):
        # Pipeline principal de processamento da imagem

        logger.info("ppm: %s", self.pixels_por_metro)
        logger.info("Área mínima (px) para partícula de %.2f mm: %.4f", self.diametro_mm, self.area_minima_px)


        imagem_hsv        = self._converter_para_hsv()
        self.mascara      = self._gerar_mascara(imagem_hsv)
        self.mascaraMini  = self.arquivoObj.gerar_miniatura(self.mascara)

        if self.mascara is None:
            logger.error("A máscara HSV não foi gerada corretamente.")
            raise ValueError("A máscara HSV não foi gerada corretamente.")

        self.reconhecer_particulas()

        if self.plot:
            self._plotar_resultados()

        # Retorna os resultados em dicionário para encapsular os resultados relevantes
        return {
            "quantidade": self.qtd_particulas,
            "area_m2": self.area_total_m2,
            "contornos": self.contornos,
            "imagem_original": self.imagem,
            "mascara": self.mascara,
            "mascara_miniatura": self.mascaraMini,
            "area_minima_pixels": self.area_minima_px,
            "pixels_por_metro": self.pixels_por_metro
        }


'==================================== Início para execução isolada do módulo =========================================='

if __name__ == "__main__":

    print("\nTeste da classe ReconhecedorGraos")

    tipoImagem = "IMAGEM AJUSTADA e RECORTADA ('_com_retangulo.jpg')"
    finalArq   = "_com_retangulo_e_mascara.jpg"

    try:
        # Etapas iniciais de seleção e verificação
        arquivoObj = Arquivo()
        arquivoObj.selecionar_arquivo(tipoImagem)
        arquivoObj.obter_arquivos_com_string(finalArq)

        print(f"\nVerificação dos arquivos processados no diretório: {len(arquivoObj.arquivosDir)} arquivos\n")
        for arq in arquivoObj.arquivosDir:
            print(os.path.basename(arq))
        print()

        if len(arquivoObj.arquivosDir) == 29:
            print(f"\nTodos os arquivos com final '{finalArq}' estão no diretório de imagens.")
            print("Nada a executar nesse módulo.")
            logger.critical("Encerrando a execução devido a erro crítico.\n")
            sys.exit(0)

        # Carrega a imagem ajustada
        arquivoObj.carregar_imagem()

        if arquivoObj.imagem is None:
            raise ValueError("Imagem não carregada corretamente ou está vazia.")

        # Exibe a imagem em uma janela
        nomeJanela = 'IMAGEM AJUSTADA e RECORTADA - Clique em qualquer tecla para fechar a janela'
        cv2.namedWindow(nomeJanela, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(nomeJanela, 800, 600)
        cv2.imshow(nomeJanela, arquivoObj.imagem)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        # Inicializa o processador e executa
        proc = ReconhecedorGraos(arquivoObj,
                                 arquivoObj.imagem,
                                 lower_color  = 0,
                                 upper_color  = 80,
                                 diametro_mm  = 1.5,
                                 tolerancia   = 0.8,
                                 plot         = True)

        resultados = proc.processar()

        # Exibe resultados do dicionário
        print('\033[93m\nProcessamento concluído!\033[0m\n')
        print(f'Qtd de partículas......: {resultados["quantidade"]}')
        print(f'Área total (m²)........: {resultados["area_m2"]:.6f}')

        resultados["mascara_miniatura"].show()

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
