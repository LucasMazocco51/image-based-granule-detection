import os
import sys
import cv2
import math
import logging

import numpy as np


from src.classe_arquivo import Arquivo
from src.log_config import configurar_logger

logger = configurar_logger(__name__) # usa WARNING como default
# logger = configurar_logger(__name__, nivel_console=logging.INFO)
# logger = configurar_logger(__name__, nivel_console=logging.ERROR)


class Detecta:

    """
    Classe para detectar a área formada por objeto que contenha quatro vértices.
    No caso específico da Marispan, o objeto é um retângulo de lado 1m x 1m.

    Infomrmações a respeito da transformada de Hough: https://tinyurl.com/yxupz5jc
    """

    def __init__(self, arquivoObj: Arquivo, threshold=300, kernel=(5, 5), salva_imagem=False, plot=False):
        self.arquivoObj   = arquivoObj
        self.threshold    = threshold  # Limite de detecção da HoughLines
        self.kernel       = kernel     # Kernel morfológico (para limpeza da imagem)
        self.salva_imagem = salva_imagem
        self.plot         = plot

        self.vertices     = None       # Vértices detectados (serão preenchidos após execução)
        self.imagem       = None       # Imagem com as marcações

        # Centro da imagem (usado para ajudar na organização dos vértices)
        self.centro_x = self.arquivoObj.imgLargura // 2
        self.centro_y = self.arquivoObj.imgAltura // 2
        self.centro   = (self.centro_x, self.centro_y)


    # Calcula ponto de interseção entre duas retas representadas em coordenadas polares
    def _intersecao_linhas(self, rho1, theta1, rho2, theta2):
        A = np.array([
            [np.cos(theta1), np.sin(theta1)],
            [np.cos(theta2), np.sin(theta2)]
        ])
        b = np.array([[rho1], [rho2]])
        try:
            ponto = np.linalg.solve(A, b)
            return int(ponto[0][0]), int(ponto[1][0])
        except np.linalg.LinAlgError:
            return None  # Se forem paralelas, não há interseção


    # Retorna o ponto mais próximo do centro da imagem
    def _mais_proximo_centro(self, lista_pontos):
        return min(lista_pontos, key=lambda p: (p[0] - self.centro_x) ** 2 + (p[1] - self.centro_y) ** 2)


    # Função principal que detecta a área delimitada por quatro vértices
    def detectaArea4V(self):
        nomeImgTratada = f"{self.arquivoObj.nomeArqB}_reconhecimento_linhas.jpg"
        self.imagem = self.arquivoObj.imagem.copy()

        # === Pré-processamento da imagem ===
        cinza           = cv2.cvtColor(self.arquivoObj.imagem, cv2.COLOR_BGR2GRAY)
        cinza_contraste = cv2.convertScaleAbs(cinza, alpha=1, beta=3)  # Aumenta contraste leve
        cinza_borrado   = cv2.GaussianBlur(cinza_contraste, (5, 5), 0)  # Reduz ruído

        # Binarização adaptativa com inversão (realça bordas brancas)
        mascara = cv2.adaptiveThreshold(cinza_borrado, 255,
                                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                        cv2.THRESH_BINARY_INV,
                                        21, 2)

        # Operações morfológicas para fechar buracos e remover ruído
        kernel_np       = np.ones(self.kernel, np.uint8)
        mascara_fechada = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel_np, iterations=2)
        mascara_limpa   = cv2.morphologyEx(mascara_fechada, cv2.MORPH_OPEN, kernel_np, iterations=1)

        # Detecção de bordas com Canny
        cannyEdge = cv2.Canny(mascara_limpa, 50, 180)

        # === Parâmetros da HoughLines ===
        distResol      = 1              # Resolução de distância
        angleResol     = np.pi / 180    # Resolução angular
        horizontal_tol = np.deg2rad(20) # Tolerância para linhas horizontais
        vertical_tol   = np.deg2rad(20) # Tolerância para linhas verticais

        # Tenta detectar as linhas com thresholds decrescentes
        for current_threshold in range(self.threshold, 0, -50):
            lines = cv2.HoughLines(cannyEdge, distResol, angleResol, current_threshold)

            horizontais_sup = []
            horizontais_inf = []
            verticais_esq   = []
            verticais_dir   = []

            if lines is not None:
                for curline in lines:
                    rho, theta = curline[0]
                    x = int(rho * np.cos(theta))
                    y = int(rho * np.sin(theta))

                    # Classificação das linhas de acordo com sua orientação e posição na imagem
                    if abs(theta - np.pi / 2) < horizontal_tol:
                        if y < self.centro_y:
                            horizontais_sup.append((rho, theta))
                        else:
                            horizontais_inf.append((rho, theta))
                    elif abs(theta) < vertical_tol or abs(theta - np.pi) < vertical_tol:
                        if x < self.centro_x:
                            verticais_esq.append((rho, theta))
                        else:
                            verticais_dir.append((rho, theta))

            # Calcula interseções entre pares de linhas de diferentes orientações
            sup_esq_pts = [self._intersecao_linhas(h[0], h[1], v[0], v[1])
                           for h in horizontais_sup for v in verticais_esq]
            sup_dir_pts = [self._intersecao_linhas(h[0], h[1], v[0], v[1])
                           for h in horizontais_sup for v in verticais_dir]
            inf_esq_pts = [self._intersecao_linhas(h[0], h[1], v[0], v[1])
                           for h in horizontais_inf for v in verticais_esq]
            inf_dir_pts = [self._intersecao_linhas(h[0], h[1], v[0], v[1])
                           for h in horizontais_inf for v in verticais_dir]

            # Remove interseções inválidas
            sup_esq_pts = [p for p in sup_esq_pts if p is not None]
            sup_dir_pts = [p for p in sup_dir_pts if p is not None]
            inf_esq_pts = [p for p in inf_esq_pts if p is not None]
            inf_dir_pts = [p for p in inf_dir_pts if p is not None]

            # Se ao menos um ponto de cada canto foi identificado, consideramos uma detecção válida
            if all([sup_esq_pts, sup_dir_pts, inf_esq_pts, inf_dir_pts]):
                # Seleciona o ponto mais próximo do centro para cada canto
                sup_esq = self._mais_proximo_centro(sup_esq_pts)
                sup_dir = self._mais_proximo_centro(sup_dir_pts)
                inf_esq = self._mais_proximo_centro(inf_esq_pts)
                inf_dir = self._mais_proximo_centro(inf_dir_pts)

                # Desenha o retângulo detectado sobre a imagem
                espessura = 20
                cor_linha = (0, 255, 0)

                cv2.line(self.imagem, sup_esq, sup_dir, cor_linha, espessura)
                cv2.line(self.imagem, inf_esq, inf_dir, cor_linha, espessura)
                cv2.line(self.imagem, sup_esq, inf_esq, cor_linha, espessura)
                cv2.line(self.imagem, sup_dir, inf_dir, cor_linha, espessura)

                # Adiciona sobreposição (polígono preenchido semi-transparente)
                overlay = self.arquivoObj.imagem.copy()
                pontos  = np.array([sup_esq, sup_dir, inf_dir, inf_esq], dtype=np.int32)
                cv2.fillPoly(overlay, [pontos], color=(255, 0, 0))
                alpha = 0.3
                cv2.addWeighted(overlay, alpha, self.imagem, 1 - alpha, 0, self.imagem)

                # Salva imagem com marcações, se solicitado
                if self.salva_imagem:
                    cv2.imwrite(os.path.join(self.arquivoObj.caminho, nomeImgTratada), self.imagem)
                    # print(f"\nImagem com reconhecimento salva em..: {self.arquivoObj.caminho}")
                    # print(f"Nome do arquivo.....................: {nomeImgTratada}")
                    logger.info("Imagem com reconhecimento salva em..: %s", self.arquivoObj.caminho)
                    logger.info("Nome do arquivo.....................: %s", nomeImgTratada)

                # Exibe imagem com marcações, se solicitado
                if self.plot:
                    nomeJanela = 'ÁREA SELECIONADA - Clique em qualquer tecla para fechar'
                    cv2.namedWindow(nomeJanela, cv2.WINDOW_NORMAL)
                    cv2.resizeWindow(nomeJanela, 800, 600)
                    cv2.imshow(nomeJanela, self.imagem)
                    cv2.waitKey(0)
                    cv2.destroyAllWindows()

                # Armazena os vértices encontrados
                pontos = np.array([sup_esq, sup_dir, inf_esq, inf_dir], dtype=np.int32)
                self.vertices = [tuple(p) for p in pontos]

                # print(f"\nVértices encontrados em {self.arquivoObj.nomeArq} com threshold = {current_threshold}")
                logger.info("Vértices encontrados em %s com threshold = %d", self.arquivoObj.nomeArq, current_threshold)
                return None

        # print(f"[ERRO] Não foi possível encontrar todos os vértices em {self.arquivoObj.nomeArq}")
        logger.error("Não foi possível encontrar todos os vértices em %s", self.arquivoObj.nomeArq)
        return None, None


'==================================== Início para execução isolada do módulo =========================================='

if __name__ == "__main__":
    print("\nTeste da classe Detecta")

    tipoImagem   = "IMAGEM ORIGINAL"

    try:
        arquivoObj = Arquivo()
        arquivoObj.selecionar_arquivo(tipoImagem)
        arquivoObj.carregar_imagem()

        detector = Detecta(arquivoObj,
                           threshold    = 300,
                           kernel       = (5, 5),
                           salva_imagem = True,
                           plot         = True)

        # Retorno esperado --> detector.vertices (tupla dos vertices do retângulo)
        detector.detectaArea4V()

        if detector.imagem is not None:
            print("\nImagem processada retornada com sucesso!")

        else:
            print("\nO processamento da imagem não pôde ser concluído.")

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
