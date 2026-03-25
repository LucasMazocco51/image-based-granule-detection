import os
import sys
import logging

from tkinter import filedialog
from tqdm    import tqdm

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.classe_arquivo import Arquivo
from src.detecta_hough_lines import Detecta
from src.ajuste_de_imagem_4P import Ajustador
from src.image_processing import ReconhecedorGraos
from src.log_config import configurar_logger

logger = configurar_logger(__name__) # usa WARNING como default
# logger = configurar_logger(__name__, nivel_console=logging.INFO)
# logger = configurar_logger(__name__, nivel_console=logging.ERROR)


class ComparadorParticulas:

    """
    Classe para comparar a quantidade de grão entre 2 a 6 imagens.
    Retorna a quantidade de grãos por imagem, o desvio padrão e a situação de cada
    imagem em relação a uma referência.
    """

    def __init__(self, desvio_permitido: float = 10.0):

        self.desvio_permitido = desvio_permitido
        self.miniaturas       = {}
        self.resultados       = []
        self.listaArquivos    = []
        self.listaObj         = {}
        logger.info("ComparadorParticulas inicializado com desvio permitido de %.2f%%", desvio_permitido)


    # Função para selecionar várias imagens via GUI (2 a 6 imagens)
    def selecionar_imagens(self):
        logger.info("Iniciando seleção de imagens para comparação")
        tipos_arquivos = [('Imagens', ('*.png', '*.jpg', '*.jpeg', '*.heic', '*.heif'))]

        # Abre o seletor de arquivos (multiplos) no diretório especificado com o filtro
        arquivos = filedialog.askopenfilenames(
            title      = f"Selecione de 2 a 6 arquivos para comparação de imagens.",
            initialdir = os.getcwd(),
            filetypes  = tipos_arquivos)

        self.listaArquivos = list(arquivos)

        self.criar_atributos()


    # Função para criar os atributos básicos dos arquivos
    def criar_atributos(self, listaGUI = None):

        if listaGUI:
            self.listaArquivos = listaGUI

        if not self.listaArquivos:
            logger.warning("Nenhum arquivo foi selecionado.")

        elif not (2 <= len(self.listaArquivos) <= 6):
            logger.error("Número de arquivos selecionados fora do intervalo permitido: %d", len(self.listaArquivos))
            raise ValueError("É necessário selecionar entre 2 e 6 arquivos.")
        logger.info("Selecionados %d arquivos para comparação.", len(self.listaArquivos))

        # Limpa dicionário anterior se houver
        self.listaObj.clear()

        # Obtem os atributos dos arquivos
        if self.listaArquivos:
            logger.info("%d imagens selecionadas.", len(self.listaArquivos))

            for idx, camArq in enumerate(self.listaArquivos):
                self.listaObj[idx] = Arquivo(caminhoArq = camArq)
                self.listaObj[idx].atributosArq()


    # Função para carregar as imagens (processamento pesado)
    def carregar_imagens_em_memoria(self, progress_callback=None):
        """
        Itera sobre os objetos de arquivo e carrega a imagem de cada um.
        Esta é uma operação de I/O e deve ser chamada em uma thread.
        """
        if not self.listaObj:
            logger.warning("Nenhum objeto de imagem para carregar.")
            return
        logger.info("Iniciando carregamento de %d imagens em memória...", len(self.listaObj))

        for i, obj in enumerate(self.listaObj.values()):
            obj.carregar_imagem()
            if progress_callback:
                # Passa a porcentam concluída para o GUI
                progress_callback((i + 1) / len(self.listaObj) * 100)
        logger.info("Carregamento de imagens concluído.")


    # Função para processar as imagens fornecidas, realizar a contagem de partículas e calcular desvios.
    def processar_imagens(self, progress_callback=None):
        """
        Itera sobre os objetos de arquivo e processa a imagem de cada um para reconhecer a qtde de partículas.
        Esta é uma operação de I/O e deve ser chamada em uma thread.
        """
        logger.info("Iniciando processamento de %d imagens.", len(self.listaObj))

        # Limpa a lista anterior se houver
        self.resultados.clear()
        quantidades  = []

        # Itera na lista de objetos para realizar a detecção do retângulo, ajuste de imagem e detecção das partículas.
        for i, obj in enumerate(
                tqdm(self.listaObj.values(), desc="Processando imagens", unit="img", ncols=80, colour="cyan",
                     leave=True)):

            # Detecta retângulo automaticamente
            logger.info("Iniciando detecção dos 4 vértices na imagem: %s", obj.nomeArq)
            detector = Detecta(obj, salva_imagem=False, plot=False)
            detector.detectaArea4V()

            if not detector.vertices:
                logger.error("Não foi possível detectar os 4 vértices na imagem: %s", obj.nomeArq)
                raise ValueError(f"Não foi possível detectar os 4 vértices em {obj.nomeArq}")

            # Ajusta a imagem (recorte e warping)
            logger.info("Ajustando imagem com recorte e warping: %s", obj.nomeArq)
            ajustador = Ajustador(obj, detector, salva_imagem=False, plot=False)
            ajustador.processar()

            # Reconhecimento das partículas
            logger.info("Iniciando reconhecimento de partículas na imagem ajustada: %s", obj.nomeArq)
            reconhecedor = ReconhecedorGraos(
                obj,
                ajustador.imagem_recortada,
                lower_color = 0,
                upper_color = 80,
                diametro_mm = 2.0,
                tolerancia  = 0.8,
                plot        = False
            )

            resultado    = reconhecedor.processar()
            qtd          = resultado.get("quantidade", 0)
            mascara      = resultado.get("mascara", 0)
            mascara_mini = resultado.get("mascara_miniatura", 0)

            logger.info("Imagem %s - Quantidade detectada: %d", obj.nomeArq, qtd)

            # Acumula quantidade de partículas para cálculo estatístico
            quantidades.append(qtd)

            self.resultados.append({
                "nome": obj.nomeArq,
                "quantidade": qtd,
                "mascara": mascara,
                "mascara_miniatura": mascara_mini
            })

            if progress_callback:
                # Atualizar a porcentagem de conclusão no GUI
                progress_callback((i + 1) / len(self.listaObj) * 100)

        # Cálculo do desvio padrão e situação
        media = np.mean(quantidades)
        logger.info("Quantidade média calculada: %.2f", media)

        for r in self.resultados:
            desvio_pct = abs(r["quantidade"] - media) / media * 100
            r["desvio_percentual"] = round(desvio_pct, 2)
            r["status"] = "OK" if desvio_pct <= self.desvio_permitido else "NOK"
            logger.info("Imagem %s: Desvio %.2f%% - Status: %s", r["nome"], r["desvio_percentual"], r["status"])

        media = np.mean(quantidades)
        logger.info("Quantidade média calculada: %.2f", media)


'==================================== Início para execução isolada do módulo =========================================='

# Execução isolada para testes
if __name__ == "__main__":

    # Inicia a classe
    comparador = ComparadorParticulas(desvio_permitido = 10.0)

    try:
        comparador.selecionar_imagens()
        comparador.carregar_imagens_em_memoria()
        comparador.processar_imagens()

        quantidades   = [r["quantidade"] for r in comparador.resultados]
        media         = np.mean(quantidades)
        desvio_padrao = np.std(quantidades)

        print("\033[93m\n\nResultado da comparação:\033[0m\n")
        print(f"Média das quantidades de grãos.....: {media:.2f}")
        print(f"Desvio padrão das quantidades......: {desvio_padrao:.2f}")
        print("-" * 80)

        # Calcula desvio percentual individual e classifica como OK/NOK
        for r in comparador.resultados:
            print(f"{r['nome']:<30}  "
                  f"Qtd: {r['quantidade']:<5}  "
                  f"Desvio: {r['desvio_percentual']:<6.2f}%  "
                  f"{'':<8}"  
                  f"Status: {r['status']}")
            # r['mascara_miniatura'].show()


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
