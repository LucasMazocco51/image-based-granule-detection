import os
import sys
import cv2
import logging

import numpy as np

from src.classe_arquivo import Arquivo
from src.log_config import configurar_logger

logger = configurar_logger(__name__) # usa WARNING como default
# logger = configurar_logger(__name__, nivel_console=logging.INFO)
# logger = configurar_logger(__name__, nivel_console=logging.ERROR)

class Ajustador:

    """
    Classe para ajustar (warp + crop, transformar + recortar) a imagem com base nos 4 vértices
    detectados ou capturados usando o objeto Arquivo para informações de caminho e imagem.
    """

    def __init__(self, arquivoObj: Arquivo, detectorOuReconhecedor, salva_imagem=False, plot=False):
        self.arquivoObj   = arquivoObj
        self.obj_pontos   = detectorOuReconhecedor
        self.salva_imagem = salva_imagem
        self.plot         = plot

        # Dimensões de referência
        self.ladoArea1m  = 100  # em cm para obter area de 1m2
        self.dimRef      = 100  # comprimento dos lados do esquadro em cm
        self.valorOffset = (self.ladoArea1m - self.dimRef) / 2

        self.pontos_com_offset       = None
        self.imagem_transformada_rgb = None
        self.imagem_recortada        = None

        # print(f'\033[91m\nComprimento de referência do quadrado: {self.dimRef} cm\n\033[0m')
        logger.info("Comprimento de referência do quadrado: %s cm", self.dimRef)

        # Obtem os pontos (vertices ou pontos) do objeto detectorOuReconhecedor
        if hasattr(self.obj_pontos, "vertices") and self.obj_pontos.vertices is not None:
            self.pontos = self.obj_pontos.vertices
        elif hasattr(self.obj_pontos, "pontos") and self.obj_pontos.pontos is not None:
            self.pontos = self.obj_pontos.pontos
        else:
            logger.error("O objeto fornecido não possui os pontos necessários.")
            raise ValueError("O objeto fornecido não possui os pontos necessários.")

        # Confirma que pontos são 4 tuplas
        if len(self.pontos) != 4:
            logger.error("São necessários exatamente 4 pontos para ajuste.")
            raise ValueError("São necessários exatamente 4 pontos para ajuste.")

        if self.arquivoObj.imagem is None:
            logger.error("Imagem não carregada no objeto Arquivo.")
            raise ValueError("Imagem não carregada no objeto Arquivo.")


    # Função para recortar a imagem após a transformação e em função dos pontos do reconhecedor
    def _recortar_por_pontos(self):
        x_coords = [p[0] for p in self.pontos_com_offset]
        y_coords = [p[1] for p in self.pontos_com_offset]

        # Encontra as coordenadas mínimas e máximas para o recorte
        # Garante que as coordenadas de corte fiquem dentro dos limites da imagem
        min_x = max(0, int(min(x_coords)))
        max_x = min(self.arquivoObj.imgLargura, int(max(x_coords)))
        min_y = max(0, int(min(y_coords)))
        max_y = min(self.arquivoObj.imgAltura, int(max(y_coords)))

        # Realiza o recorte da imagem usando fatiamento de array NumPy
        self.imagem_recortada = self.imagem_transformada_rgb[min_y:max_y, min_x:max_x]


    # Funçãp para salvar a imagem original ajustada
    def _salvar_imagem(self):
        if self.arquivoObj.caminhoArq is not None:
            caminho_imagem_recortada = os.path.join(self.arquivoObj.caminho, f"{self.arquivoObj.nomeArqB}_com_retangulo.jpg")

        cv2.imwrite(caminho_imagem_recortada, cv2.cvtColor(self.imagem_recortada, cv2.COLOR_RGB2BGR))

        logger.info("Imagem recortada salva em..: %s", self.arquivoObj.caminho)
        logger.info("Nome do arquivo............: %s", os.path.basename(caminho_imagem_recortada))


    # Função para apresentar o resultado do ajuste na tela
    def _mostrar_imagem(self):
        nomeJanela = 'IMAGEM RECORTADA - Clique em qualquer tecla para fechar'
        cv2.namedWindow(nomeJanela, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(nomeJanela, 800, 600)
        cv2.imshow(nomeJanela, cv2.cvtColor(self.imagem_recortada, cv2.COLOR_RGB2BGR))
        cv2.waitKey(0)
        cv2.destroyAllWindows()


    # Função para ajustar o posicionamento da imagem em função dos pontos
    def transformar_imagem(self):
        largura = int(np.linalg.norm(np.array(self.pontos[1]) - np.array(self.pontos[0])))
        altura  = int(np.linalg.norm(np.array(self.pontos[2]) - np.array(self.pontos[0])))

        # Calcula a maior dimensão para manter a proporção
        maior_dimensao = max(largura, altura)

        logger.info("Largura original..: %s pixels", self.arquivoObj.imgLargura)
        logger.info("Largura final.....: %s pixels", largura)
        logger.info("Altura original...: %s pixels", self.arquivoObj.imgAltura)
        logger.info("Altura final......: %s pixels", altura)

        # Cria a matrix de transformação e realiza o ajuste da imagem inteira

        # Pontos na imagem original
        origem = np.array(self.pontos, dtype='float32')

        destino = np.array([
            [(self.arquivoObj.imgLargura - maior_dimensao) / 2, (self.arquivoObj.imgAltura - maior_dimensao) / 2],
            [(self.arquivoObj.imgLargura + maior_dimensao) / 2, (self.arquivoObj.imgAltura - maior_dimensao) / 2],
            [(self.arquivoObj.imgLargura - maior_dimensao) / 2, (self.arquivoObj.imgAltura + maior_dimensao) / 2],
            [(self.arquivoObj.imgLargura + maior_dimensao) / 2, (self.arquivoObj.imgAltura + maior_dimensao) / 2]
        ], dtype='float32')

        # Calcula a matriz de transformação
        matriz_transformacao = cv2.getPerspectiveTransform(origem, destino)

        # Aplica a transformação
        imagem_transformada = cv2.warpPerspective(self.arquivoObj.imagem,
                                                  matriz_transformacao,
                                                  (self.arquivoObj.imgLargura, self.arquivoObj.imgAltura))
        self.imagem_transformada_rgb = cv2.cvtColor(imagem_transformada, cv2.COLOR_BGR2RGB)

        # Calcula a escala em pixels para xx cm com base na distância horizontal
        escala = maior_dimensao / self.dimRef

        # Calcula o offset em pixels
        offset_pixel = self.valorOffset * escala # dimRef cm em pixels

        # Desenha os pontos de destino com offset na imagem transformada
        self.pontos_com_offset = [
            (destino[0][0] - offset_pixel, destino[0][1] - offset_pixel),
            (destino[1][0] + offset_pixel, destino[1][1] - offset_pixel),
            (destino[2][0] - offset_pixel, destino[2][1] + offset_pixel),
            (destino[3][0] + offset_pixel, destino[3][1] + offset_pixel)
        ]

        # Verifica se os pontos estão dentro dos limites da imagem transformada
        fora_dos_limites = any(
            x < 0 or x > self.arquivoObj.imgLargura or y < 0 or y > self.arquivoObj.imgAltura
            for x, y in self.pontos_com_offset
        )

        if fora_dos_limites:
            logger.error("Erro: pontos com offset estão fora dos limites da imagem transformada.")
            logger.error("Medida de referência de %s cm é muito pequena para essa imagem.", self.dimRef)
            logger.critical("Encerrando a execução devido a erro crítico.\n")
            sys.exit()

        # Desenha os novos pontos
        for x, y in self.pontos_com_offset:
            cv2.circle(self.imagem_transformada_rgb, (int(x), int(y)), 5, (255, 0, 0), -1)

        # Desenha o retângulo usando os pontos com offset
        cv2.line(self.imagem_transformada_rgb,
                 (int(self.pontos_com_offset[0][0]), int(self.pontos_com_offset[0][1])),
                 (int(self.pontos_com_offset[1][0]), int(self.pontos_com_offset[1][1])),
                 (255, 0, 0), 5)
        cv2.line(self.imagem_transformada_rgb,
                 (int(self.pontos_com_offset[1][0]), int(self.pontos_com_offset[1][1])),
                 (int(self.pontos_com_offset[3][0]), int(self.pontos_com_offset[3][1])),
                 (255, 0, 0), 5)
        cv2.line(self.imagem_transformada_rgb,
                 (int(self.pontos_com_offset[3][0]), int(self.pontos_com_offset[3][1])),
                 (int(self.pontos_com_offset[2][0]), int(self.pontos_com_offset[2][1])),
                 (255, 0, 0), 5)
        cv2.line(self.imagem_transformada_rgb,
                 (int(self.pontos_com_offset[2][0]), int(self.pontos_com_offset[2][1])),
                 (int(self.pontos_com_offset[0][0]), int(self.pontos_com_offset[0][1])),
                 (255, 0, 0), 5)

        self._recortar_por_pontos()


    # Função de execução da classe
    def processar(self):
        self.transformar_imagem()

        if self.salva_imagem:
            self._salvar_imagem()
        if self.plot:
            self._mostrar_imagem()

        return


'==================================== Início para execução isolada do módulo =========================================='

if __name__ == "__main__":
    print("\nTeste da classe Ajustador")

    tipoImagem = "IMAGEM ORIGINAL"

    try:
        arquivoObj = Arquivo()
        arquivoObj.selecionar_arquivo(tipoImagem)
        arquivoObj.carregar_imagem()

        # Pergunta ao usuário qual técnica utilizar
        escolha = input("\nDeseja detectar retângulo automaticamente? (s/n): ").strip().lower()
        print()

        if escolha == 's':
            from detecta_hough_lines import Detecta
            detector = Detecta(arquivoObj, salva_imagem=False, plot=True)
            detector.detectaArea4V()
            obj_reconhecido = detector
        else:
            from detecta_4_pontos import Reconhecedor4Pontos
            reconhecedor = Reconhecedor4Pontos(arquivoObj)
            reconhecedor.capturar_com_mouse()
            obj_reconhecido = reconhecedor

        ajustador = Ajustador(arquivoObj, obj_reconhecido, salva_imagem=True, plot=True)
        ajustador.processar()

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
