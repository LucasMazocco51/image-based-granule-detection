import os
import sys
import cv2
import pillow_heif
import logging

import tkinter as tk
import numpy   as np

from PIL       import Image, ImageTk
from tkinter   import filedialog

from src.log_config import configurar_logger

logger = configurar_logger(__name__) # usa WARNING como default
# logger = configurar_logger(__name__, nivel_console=logging.INFO)
# logger = configurar_logger(__name__, nivel_console=logging.ERROR)


class Arquivo:

    """
    Classe para leitura de imagens. Retorna a matriz de pixels e informações
    relacionadas ao arquivo e seu local de armazenamento.
    """

    def __init__(self,
                 detalhe: str       = None,
                 final_arquivo: str = None,
                 caminhoArq: str    = None):

        self.detalhe        = detalhe
        self.final_arquivo  = final_arquivo
        self.caminhoArq     = caminhoArq
        self.caminho        = None
        self.nomeArq        = None
        self.nomeArqB       = None
        self.nomeExt        = None
        self.imagem         = None
        self.miniaturaImg   = None
        self.imgLargura     = None
        self.imgAltura      = None
        self.arquivosDir    = None

        # Executa automaticamente se os dois parâmetros forem fornecidos
        if self.detalhe and self.final_arquivo:
            logger.info(
                f"Inicialização com parâmetros: '{self.detalhe}', '{self.final_arquivo}', '{self.caminhoArq}'")
            self.selecionar_arquivo(self.detalhe)
            self.obter_arquivos_com_string(self.final_arquivo)

        elif self.detalhe or self.final_arquivo:
            logger.warning("Parâmetro incompleto fornecido. Esperado 'detalhe' e 'final_arquivo'.")
            print("\n\033[93mAviso: Para execução automática, forneça os dois parâmetros: 'detalhe' e 'final_arquivo'.\033[0m")
            print("Ou inicie um objeto da classe, e.g.: arquivoObj = Arquivo() e depois")
            print("chame o método específico, e.g.: arquivoObj.selecionar_arquivo('IMAGEM ORIGINAL').")


    # Função auxiliar
    def _dimensoes(self):
        self.imgLargura = self.imagem.shape[1]
        self.imgAltura  = self.imagem.shape[0]


    # Função para criar uma miniatura da imagem para ser utilizada no Tkinter
    def gerar_miniatura(self, img=None, max_dim=250):
        try:
            # Usa imagem passada ou a da instância
            if img is not None:
                self.imagem = img
                self._dimensoes()
            elif self.imagem is None:
                logger.error("Nenhuma imagem carregada para gerar miniatura.")
                raise ValueError("Nenhuma imagem carregada para gerar miniatura.")

            # Define a maior dimensão (largura ou altura) para 150 pixels
            if self.imgLargura >= self.imgAltura:
                escala = max_dim / self.imgLargura
            else:
                escala = max_dim / self.imgAltura

            nova_largura = int(self.imgLargura * escala)
            nova_altura = int(self.imgAltura * escala)

            # Converte imagem para RGB apenas se tiver 3 canais
            if len(self.imagem.shape) == 3 and self.imagem.shape[2] == 3:
                imagem_rgb = cv2.cvtColor(self.imagem, cv2.COLOR_BGR2RGB)
                imagem_pil = Image.fromarray(imagem_rgb)
            else:
                imagem_pil = Image.fromarray(self.imagem)

            imagem_pil = imagem_pil.resize((nova_largura, nova_altura), Image.LANCZOS)
            # imagem_pil.show()

            logger.info("Miniatura PIL gerada com sucesso (%dx%d px).", nova_largura, nova_altura)

            # # Redimensiona mantendo proporção com a maior dimensão = max_dim
            # miniatura = cv2.resize(self.imagem, (nova_largura, nova_altura), interpolation=cv2.INTER_AREA)
            return imagem_pil

        except Exception as e:
            logger.error("Erro ao gerar miniatura: %s", e)
            return None


    # Função para obter os dados básicos do arquivo
    def atributosArq(self, camArq = None):

        if camArq is not None:
            self.caminho = camArq

        # Obtém o caminho e o nome do arquivo separadamente
        self.caminho = os.path.dirname(self.caminhoArq)
        self.nomeArq = os.path.basename(self.caminhoArq)
        self.nomeArqB, self.nomeExt = os.path.splitext(self.nomeArq)
        self.nomeExt = self.nomeExt.lower()

        logger.info("Arquivo selecionado: %s", self.nomeArq)


    # Função para selecionar o arquivo ou multiplos arquivos
    def selecionar_arquivo(self, detalhe: str):

        self.detalhe = detalhe
        logger.info("Solicitando seleção de arquivo(s): %s", detalhe)

        # Define os tipos de arquivo permitidos
        tipos_arquivos = [('Imagens', ('*.png', '*.jpg', '*.jpeg', '*.heic', '*.heif'))]

        # Abre o seletor de arquivos no diretório especificado com o filtro
        self.caminhoArq = filedialog.askopenfilename(title      = "Selecione o arquivo " + self.detalhe,
                                                     initialdir = os.getcwd(),
                                                     filetypes  = tipos_arquivos)

        # Avisa o usuário se o seletor de arquivos for cancelado
        if not self.caminhoArq:
            logger.error("Nenhum arquivo foi selecionado.")
            raise FileNotFoundError("Nenhum arquivo foi selecionado.")

        self.atributosArq()


    # Função para carregar (ler) a imagem usando OpenCV
    def carregar_imagem(self, caminho = None):
        logger.info("Carregando imagem: %s", self.nomeArq)
        # Usa imagem passada ou a da instância
        if caminho is not None:
            self.caminhoArq = caminho
            # print(f"Passou aqui {caminho}")
            self.atributosArq()

        # Outros formatos suportados nativamente pelo OpenCV podem ser adicionados
        if self.nomeExt in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
            self.imagem = cv2.imread(self.caminhoArq)
            self._dimensoes()

            # Cria a miniatura da imagem
            self.miniaturaImg = self.gerar_miniatura()

        elif self.nomeExt in ['.heic', '.heif']:
            try:
                pillow_heif.register_heif_opener()
                pil_imagem = Image.open(self.caminhoArq)
                self.imagem = cv2.cvtColor(np.array(pil_imagem), cv2.COLOR_RGB2BGR)
                self._dimensoes()

                # Cria a miniatura da imagem
                self.miniaturaImg = self.gerar_miniatura()

                # print(f"\nImagem HEIC convertida com sucesso de {self.nomeArq}")
                logger.info("Imagem HEIC convertida com sucesso: %s", self.nomeArq)
            except ImportError:
                # print("\n\033[91mErro: As bibliotecas 'Pillow' e 'pillow-heif' não estão instaladas para ler arquivos HEIC.\033[0m")
                logger.critical("Bibliotecas necessárias para HEIC não estão instaladas.")
                sys.exit()
            except Exception as e:
                # print(f"\n\033[91mErro ao carregar imagem HEIC: {e}\033[0m")
                logger.error("Erro ao carregar imagem HEIC: %s", e)
                sys.exit(0)

        else:
            logger.error("Formato de arquivo não suportado: %s", self.nomeExt)
            raise ValueError(f"\nFormato de arquivo '{self.nomeExt}' não suportado.")

        if self.imagem is None:
            logger.error("Falha ao carregar imagem: %s", self.caminhoArq)
            raise IOError(f"\nNão foi possível carregar a imagem de {self.caminho}. \nVerifique o arquivo.")

        logger.info("Imagem carregada: %dx%d px", self.imgLargura, self.imgAltura)


    # Função para listar os arquivos de um diretório dada uma string
    def obter_arquivos_com_string(self, final_arquivo: str):
        self.final_arquivo = final_arquivo
        logger.info("Buscando arquivos com sufixo '%s' no diretório %s", final_arquivo, self.caminho)

        if not os.path.isdir(self.caminho):
            logger.error("Diretório inválido: %s", self.caminho)
            raise NotADirectoryError(f"O diretório '{self.caminho}' não existe ou não é válido.")

        # Garante que lista será atualizada
        self.arquivosDir = []

        for nome_arquivo in os.listdir(self.caminho):
            if nome_arquivo.endswith(self.final_arquivo):
                caminho_completo = os.path.join(self.caminho, nome_arquivo)
                self.arquivosDir.append(caminho_completo)

        logger.info("Arquivos encontrados com final '%s': %d", final_arquivo, len(self.arquivosDir))


'==================================== Início para execução isolada do módulo =========================================='

if __name__ == "__main__":
    print("\nTeste da classe Arquivo")

    tipoArq    = "ORIGINAL"
    finalArq   = "_com_retangulo.jpg"

    try:
        arquivoObj = Arquivo(tipoArq, finalArq)
        arquivoObj.carregar_imagem()

        arquivoObj.obter_arquivos_com_string(finalArq)

        if len(arquivoObj.arquivosDir) == 29:
            print(f"\nTodos os arquivos com final '{finalArq}' estão no diretório de imagens.")
            print("Nada a executar nesse módulo.")


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


    print('\nArquivo selecionado:\n')
    print(f'Caminho completo.............: {arquivoObj.caminhoArq}')
    print(f'Nome do arquivo completo.....: {arquivoObj.nomeArq}')
    print(f'Caminho sem arquivo..........: {arquivoObj.caminho}')
    print(f'Nome do arquivo sem extensão.: {arquivoObj.nomeArqB}')
    print(f'Extensão do arquivo..........: {arquivoObj.nomeExt}\n')
    print(f'Largura desejada (original)..: {arquivoObj.imgLargura} pixels')
    print(f'Altura desejada (original)...: {arquivoObj.imgAltura} pixels\n')
    print(f'Arquivos com final "{finalArq}"...: {str(len(arquivoObj.arquivosDir))} arquivos\n')

    for arq in arquivoObj.arquivosDir:
        print(arq)

    if arquivoObj.imagem is not None:
        # Cria a janela com a flag WINDOW_NORMAL
        nomeJanela = 'IMAGEM ORIGINAL - Clique em qualquer tecla para fechar a janela'
        cv2.namedWindow(nomeJanela, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(nomeJanela, 800, 600)

        # Janela em tamanho maximizado
        # cv2.setWindowProperty(nomeJanela, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        # Mostra a imagem
        cv2.imshow(nomeJanela, arquivoObj.imagem)

        # Espera tecla e fecha
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    if arquivoObj.miniaturaImg is not None:
        # Cria a janela Tkinter
        root = tk.Tk()
        root.title("Miniatura no Tkinter")

        if arquivoObj.miniaturaImg is not None:
            # Converte a miniatura PIL para formato ImageTk DEPOIS da janela existir
            miniatura_tk = ImageTk.PhotoImage(arquivoObj.miniaturaImg)

            # Armazena a referência no root
            root.miniatura_ref = miniatura_tk

            # Cria um label com a imagem
            label_imagem = tk.Label(root, image=miniatura_tk)
            label_imagem.pack(padx=20, pady=20)

        else:
            label_erro = tk.Label(root, text="Miniatura não disponível", fg="red")
            label_erro.pack()

        root.mainloop()
