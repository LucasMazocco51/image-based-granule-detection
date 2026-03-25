import os
import sys
import logging
import threading

import tkinter as tk
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from tkinter             import messagebox
from tkinter             import ttk
from tkinterdnd2         import DND_FILES, TkinterDnD
from tkinter             import Toplevel

from PIL                 import ImageTk, Image

from App_comparator import ComparadorParticulas

from src.log_config          import configurar_logger


logger = configurar_logger(__name__) # usa WARNING como default
# logger = configurar_logger(__name__, nivel_console=logging.INFO)
# logger = configurar_logger(__name__, nivel_console=logging.ERROR)


class ComparadorGraosUI:

    """
    Classe para comparar a quantidade de grão entre 2 a 6 imagens.
    Retorna a quantidade de grãos por imagem, o desvio padrão e a situação de cada
    imagem em relação a uma referência.

    Interface gráfica com o usuário (GUI - Frontend)
    """

    def __init__(self, master):

        # Instancia o backend
        self.comparador = ComparadorParticulas()

        # Construtor principal do GUI
        self.master = master
        # Título da janela
        master.title("Comparador de Grãos")
        # Tamanho inicial da janela
        master.geometry("1400x760")
        # Cor de fundo EDAG dark gray
        master.configure(bg="#455561")

        # Título superior da interface
        titulo = tk.Label(master,
                          text = "Comparador de grãos - EDAG do Brasil",
                          font = ("Helvetica", 20, "bold"),
                          bg   = "#D71946",
                          fg   = "white")
        # Preenche horizontalmente com padding superior
        titulo.pack(pady=0, fill=tk.X)

        # Frame principal que divide a interface em esquerda e direita
        main_frame = tk.Frame(master, bg="#8699A8")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Define proporções das colunas da grid: esquerda (1), direita (3)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=3)
        main_frame.rowconfigure(0, weight=1)

        # Área esquerda (drag-and-drop e resultados finais)
        esquerda = tk.Frame(main_frame, bg="#8699A8")
        esquerda.grid(row=0, column=0, sticky="nsew", padx=10)

        # Cria os componentes da área esquerda
        self._criar_area_upload(esquerda)
        self._criar_area_resultados(esquerda)

        # Área direita (galeria de blocos de imagem)
        direita = tk.Frame(main_frame, bg="#8699A8")
        direita.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # Barra de status na parte inferior
        self.status_var = tk.StringVar()
        self.status_var.set("Pronto.")

        # Cria barra de status
        self._criar_barra_status()

        # Cria a galeria de blocos de imagem
        self._criar_galeria_imagens(direita)

        # Dimensões para visualização da imagem e máscara
        self.largura_max, self.altura_max = 900, 900

        # Monitora o fechamento da janela
        self.master.protocol("WM_DELETE_WINDOW", self._fechar_janela)


    # Função para selecionar imagens
    def _clicar_selecionar_imagens(self):
        try:
            self._limpar_area_resultados()
            self._atualizar_status("Selecionando as imagens...")
            self.comparador.selecionar_imagens()

            if not self.comparador.listaObj:
                logger.warning("Nenhuma imagem foi selecionada.")
                self._atualizar_status("Nenhuma imagem foi selecionada.", cor="yellow")
                return

            # Inicia o carregamento das imagens e visualização das miniaturas na galeria de blocos
            self._atualizar_blocos_com_imagem()

        except Exception as e:
            logger.error(f"Erro ao selecionar imagens: {e}")
            messagebox.showwarning("Aviso",
                                   f"Número de arquivos inválido via Selecionar imagem: {len(self.comparador.listaArquivos)}. {e}")
            self._atualizar_status(f"Erro ao selecionar imagens: {e}", cor="red")


    # Função para criar o arrastar-e-largar arquivos
    def _ao_arrastar_arquivos(self, event):
        try:
            self._limpar_area_resultados()
            self._atualizar_status("Selecionando as imagens...")

            arquivos         = self.master.tk.splitlist(event.data)
            caminhos_validos = [f for f in arquivos if f.lower().endswith(('.png', '.jpg', '.jpeg', '.heic', '.heif'))]

            if not (2 <= len(caminhos_validos) <= 6):
                logger.error("Número de arquivos inválido via DnD: %d", len(caminhos_validos))
                messagebox.showwarning("Aviso",
                                       f"Número de arquivos inválido via Drag-and-Drop: {len(caminhos_validos)}. Selecione de 2 a 6 arquivos de imagem.")
                self._atualizar_status("Selecione de 2 a 6 arquivos de imagem.", cor="red")
                return

            logger.info("Imagens recebidas via DnD: %s", caminhos_validos)

            # Cria os atributos básicos dos arquivos
            self.comparador.criar_atributos(caminhos_validos)

            # Inicia o carregamento das imagens e visualização das miniaturas na galeria de blocos
            self._atualizar_blocos_com_imagem()

        except Exception as e:
            logger.error(f"Erro ao selecionar imagens: {e}")
            self._atualizar_status(f"Erro ao selecionar imagens: {e}", cor="red")


    # Função para chamar a atualização dos blocos de miniaturas
    def _atualizar_blocos_com_imagem(self):
        try:
            self._mostrar_progresso()

            # Inicia thread para carregar as imagens
            thread = threading.Thread(target=self._carregar_blocos_em_thread, daemon=True)
            thread.start()
            self._atualizar_status(f"{len(self.comparador.listaObj)} imagens carregadas com sucesso.", cor="green")

        except Exception as e:
            logger.error(f"Erro ao carregar as imagens: {e}")
            self._atualizar_status(f"Erro ao carregar as imagens: {e}", cor="red")


    # Função para carregar as imagens em threading
    def _carregar_blocos_em_thread(self):
        try:
            self._atualizar_status("Carregando as imagens no backend...")

            def progress_callback(value):
                # logger.debug(f"Atualizando progresso: {value:.2f}%")
                # self.master.after(0, lambda: [self.progress.__setitem__("value", value), self.master.update(),
                #                               logger.debug(f"Valor da barra: {self.progress['value']}")])
                self.master.after(0, lambda: [self.progress.__setitem__("value", value)])

            self.comparador.carregar_imagens_em_memoria(progress_callback)
            self.master.after(0, self._atualizar_blocos_com_miniaturas_gui)

        except Exception as e:
            logger.error(f"Erro ao carregar miniaturas: {e}")
            self.master.after(0, lambda: [
                self._atualizar_status(f"Erro ao carregar imagens: {e}", cor="red"),
                self._ocultar_progresso()
            ])


    # Função para atualizar os blocos de imagens (miniaturas) no thread principal após carregamento.
    def _atualizar_blocos_com_miniaturas_gui(self):
        for i, obj in enumerate(self.comparador.listaObj.values()):
            bloco_info = self.blocos[i]
            bloco = bloco_info["frame"]
            top_frame = bloco_info["top_frame"]

            # Limpa os labels antigos do top_frame
            for widget in top_frame.winfo_children():
                if isinstance(widget, tk.Label):
                    widget.destroy()

            # Cria os labels atualizados no top_frame
            label_prefixo = tk.Label(top_frame,
                                     text=f"Imagem {i + 1}:",
                                     bg="#455561",
                                     fg="white",
                                     font=("Helvetica", 9, "bold"))
            label_prefixo.pack(side="left")

            label_nome = tk.Label(top_frame,
                                  text=obj.nomeArq,
                                  bg="#455561",
                                  fg="cyan",
                                  font=("Helvetica", 9, "bold"))
            label_nome.pack(side="left")

            # Adiciona a miniatura, se estiver disponível
            if obj.miniaturaImg:
                # Habilita o botão mostrar imagem
                # bloco_info["botao_imagem"].config(state="disable")
                miniatura_tk = ImageTk.PhotoImage(obj.miniaturaImg)
                img_label = tk.Label(bloco, image=miniatura_tk, bg="#455561")
                img_label.image = miniatura_tk  # mantém referência viva
                img_label.pack(pady=5)
                logger.debug("Miniatura exibida para: %s", obj.nomeArq)
            else:
                logger.warning("Miniatura não encontrada para: %s", obj.nomeArq)

        logger.info(f"Blocos de imagem atualizados com {len(self.comparador.listaObj)} imagens.")
        self._ocultar_progresso()
        self._atualizar_status(f"{len(self.comparador.listaObj)} imagens carregadas com sucesso.", cor="green")


    # Função para processar as imagens usando o backend
    def _clicar_processar_imagens(self):
        if not self.comparador.listaObj:
            logger.warning("Nenhuma imagem carregada para processamento.")
            messagebox.showwarning("Aviso", "Nenhuma imagem carregada para processamento.")
            self._atualizar_status("Nenhuma imagem carregada para processamento.", cor="yellow")
            return

        # Mostra barra de progresso
        self._mostrar_progresso()

        # Inicia thread
        thread = threading.Thread(target=self._processar_em_thread, daemon=True)
        thread.start()


    # Função para processar as imagens em thread
    def _processar_em_thread(self):
        try:
            self._atualizar_status("Processando as imagens no backend...")

            def progress_callback(value):
                # logger.debug(f"Atualizando progresso: {value:.2f}%")
                # self.master.after(0, lambda: [self.progress.__setitem__("value", value), self.master.update(),
                #                               logger.debug(f"Valor da barra: {self.progress['value']}")])
                self.master.after(0, lambda: [self.progress.__setitem__("value", value)])

            # Processa as imagens no backend
            self.comparador.processar_imagens(progress_callback)

            if not self.comparador.resultados:
                logger.error("Nenhuma imagem pôde ser processada.")
                self.master.after(0, lambda: [
                    messagebox.showinfo("Resultado", "Nenhuma imagem pôde ser processada."),
                    self._atualizar_status("Nenhuma imagem pôde ser processada", cor="red"),
                    self._ocultar_progresso()
                ])
                return

            self.master.after(0, self._finalizar_processamento)

        except Exception as e:
            logger.exception("Erro ao processar imagens: %s", e)
            self.master.after(0, lambda: [
                messagebox.showerror("Erro", f"Erro ao processar imagens:\n{e}"),
                self._atualizar_status("Erro ao processar imagens.", cor="red"),
                self._ocultar_progresso()
            ])


    # Função para finalizar o processamento das imagens em thread
    def _finalizar_processamento(self):
        self._atualizar_area_resultados()
        self._atualizar_blocos_resultados()
        self._ocultar_progresso()


    # Função para atualizar o bloco de resultados
    def _atualizar_blocos_resultados(self):
        if not self.comparador.resultados:
            return

        for i, r in enumerate(self.comparador.resultados):
            if i >= len(self.blocos):
                break

            bloco_info = self.blocos[i]
            qtd    = r.get("quantidade", "--")
            std    = r.get("desvio_percentual", "-- %")
            status = r.get("status", "--")

            # Habilita o botão mostrar mascara
            if r["quantidade"] > 0:
                bloco_info["botao_mascara"].config(state="normal")
                bloco_info["botao_imagem"].config(state="normal")

            else:
                bloco_info["botao_mascara"].config(state="disabled")
                bloco_info["botao_imagem"].config(state="disabled")


            # Cor do texto de status
            if status == "OK":
                cor_borda = "#00FF99"
            elif status == "NOK":
                cor_borda = "#FF3B3F"
            else:
                cor_borda = "#A9A9A9"

            # Atualiza texto e cor
            bloco_info["qtd_label"].config(text=f"Qtde de grãos: {qtd} ({std} %)")
            bloco_info["status_label"].config(text=f"Status: {status}")

            # Destaca a borda do frame visualmente
            bloco_info["frame"].config(highlightthickness=5, highlightbackground=cor_borda)


    # Função para atualizar a área de resultados com os valores do processamento das imagens
    def _atualizar_area_resultados(self):
        if not self.comparador.resultados:
            logger.warning("Tentativa de atualizar área de resultados sem dados.")
            return

        # Extrai os valores de quantidade para calcular média e desvio
        quantidades = [r["quantidade"] for r in self.comparador.resultados]
        media       = sum(quantidades) / len(quantidades)

        if len(quantidades) > 1:
            variancia = sum((q - media) ** 2 for q in quantidades) / len(quantidades)
            desvio    = variancia ** 0.5
        else:
            desvio = 0.0

        # Atualiza os primeiros dois labels
        self.labels_resultados[0].config(text=f"Média: {media:.1f}")
        self.labels_resultados[1].config(text=f"Desvio padrão: {desvio:.1f}")

        # Atualiza os próximos labels (máximo 6 imagens)
        for i, r in enumerate(self.comparador.resultados):
            texto = f"Imagem {i + 1} - Desvio: {r['desvio_percentual']}% - Status: {r['status']}"
            self.labels_resultados[i + 2].config(text=texto)

        # Se sobrar labels além do número de imagens, limpa os textos restantes
        for j in range(len(self.comparador.resultados), 6):
            self.labels_resultados[j + 2].config(text="Imagem -- - Desvio: -- % - Status: --")

        self._atualizar_status(f"{len(self.comparador.resultados)} imagens processadas com sucesso.", cor="green")


    # Função para limpar a área de resultados
    def _limpar_area_resultados(self):
        # Textos padrão
        textos_padrao = [
            "Média: --",
            "Desvio padrão: --",
            "Imagem 1 - Desvio: -- % - Status: --",
            "Imagem 2 - Desvio: -- % - Status: --",
            "Imagem 3 - Desvio: -- % - Status: --",
            "Imagem 4 - Desvio: -- % - Status: --",
            "Imagem 5 - Desvio: -- % - Status: --",
            "Imagem 6 - Desvio: -- % - Status: --"
        ]

        for lbl, texto in zip(self.labels_resultados, textos_padrao):
            lbl.config(text=texto)

        # Limpa os blocos visuais (imagem, quantidade, status)
        for bloco_info in self.blocos:
            # Redefine borda
            bloco_info["frame"].config(highlightthickness=5, highlightbackground="#A9A9A9")

            # Remove miniatura (se houver)
            for widget in bloco_info["frame"].winfo_children():
                if isinstance(widget, tk.Label) and hasattr(widget, "image"):
                    widget.destroy()

            # Limpa os labels do top_frame (nome da imagem)
            for subwidget in bloco_info["top_frame"].winfo_children():
                if isinstance(subwidget, tk.Label):
                    subwidget.destroy()

            # Recria os labels de identificação da imagem
            label_prefixo = tk.Label(bloco_info["top_frame"],
                                     text="Imagem:",
                                     bg="#455561",
                                     fg="white",
                                     font=("Helvetica", 9, "bold"))
            label_prefixo.pack(side="left")

            label_nome = tk.Label(bloco_info["top_frame"],
                                  text="(sem arquivo)",
                                  bg="#455561",
                                  fg="cyan",
                                  font=("Helvetica", 9, "bold"))
            label_nome.pack(side="left")

            # Limpa e reposiciona os botões dentro do botoes_frame
            for widget in bloco_info["botoes_frame"].winfo_children():
                widget.pack_forget()

            bloco_info["botao_imagem"].pack(side="left", padx=5)
            bloco_info["botao_imagem"].config(state="disabled")
            bloco_info["botao_mascara"].pack(side="right", padx=5)
            bloco_info["botao_mascara"].config(state="disabled")

            # Reseta os textos de quantidade e status
            bloco_info["qtd_label"].config(text="Qtde de grãos: --")
            bloco_info["status_label"].config(text="Status: --")

        logger.debug("Área de resultados e blocos de imagem limpos.")


    # Função para garantir o encerramento do aplicativo.
    def _fechar_janela(self):
        if messagebox.askokcancel("Sair", "Tem certeza que deseja fechar o aplicativo?"):
            logger.info("Janela fechada pelo usuário.")
            logger.critical("Fim da execução com sucesso.\n")
            self.master.quit()
            self.master.destroy()


    # Função para atualizar a barra de status
    def _atualizar_status(self, mensagem, cor="white"):
        self.status_var.set(mensagem)
        self.barra_status.config(fg=cor)


    # Cria a área de drag-and-drop + botão selecionar
    def _criar_area_upload(self, parent):
        # Cria um frame "normal" (sem título embutido)
        area_upload = tk.Frame(parent,
                               bg="#455561",
                               width=300,
                               height=260,
                               bd=2,
                               relief="groove")
        area_upload.pack(pady=10, fill=tk.X)

        area_upload.pack_propagate(False)

        # Coloca o "título" como um Label manual acima
        titulo = tk.Label(area_upload,
                          text="Drag-and-Drop ou clique no botão Selecionar imagens",
                          font=("Helvetica", 10, "bold"),
                          bg="#455561",
                          fg="white")
        # Move o título mais para baixo
        titulo.pack(padx=10,pady=10)

        # Área receptora do drag-and-drop
        drop_label = tk.Label(area_upload,
                              text="\n(Arraste aqui ou clique abaixo)\n",
                              bg="#455561", fg="white",
                              relief="groove", bd=5,
                              highlightthickness=2,
                              highlightbackground="#455561",  # cor normal da borda
                              highlightcolor="#00FFFF")       # cor quando em foco
        drop_label.pack(pady=5, fill=tk.X, padx=20)

        # Eventos de foco do mouse
        drop_label.bind("<Enter>", lambda e: drop_label.config(highlightbackground="#00FFFF"))
        drop_label.bind("<Leave>", lambda e: drop_label.config(highlightbackground="#455561"))

        # Habilita a área para receber arquivos via DnD
        drop_label.drop_target_register(DND_FILES)
        drop_label.dnd_bind('<<DragEnter>>', lambda e: drop_label.config(highlightbackground="#00FFFF"))
        drop_label.dnd_bind('<<DragLeave>>', lambda e: drop_label.config(highlightbackground="#455561"))
        drop_label.dnd_bind('<<Drop>>', self._ao_arrastar_arquivos)

        # Botão tradicional de seleção
        botao = tk.Button(area_upload,
                          text="Selecionar imagens",
                          font=("Helvetica", 12),
                          width=25,
                          height=2,
                          command=self._clicar_selecionar_imagens)
        botao.pack(pady=10, fill=tk.X, padx=20)

        # Botão para processar as imagens
        botao_processar = tk.Button(area_upload,
                                    text="Processar imagens",
                                    font=("Helvetica", 12),
                                    width=25,
                                    height=2,
                                    command=self._clicar_processar_imagens)
        botao_processar.pack(pady=10, fill=tk.X, padx=20)


    # Cria o bloco de "resultados finais"
    def _criar_area_resultados(self, parent):
        # Cria um frame comum para conter tudo
        container = tk.Frame(parent, bg="#455561")
        container.pack(fill=tk.BOTH, expand=True, pady=10)

        # Adiciona um "título" manual
        titulo = tk.Label(container,
                          text="Resultados finais:",
                          font=("Helvetica", 10, "bold"),
                          bg="#455561",
                          fg="white",
                          anchor="w")
        titulo.pack(fill=tk.X, padx=10, pady=10)

        # Cria a área dos resultados (substitui LabelFrame)
        resultados = tk.Frame(container, bg="#455561", width=300, height=300, bd=2, relief="groove")
        resultados.pack(fill=tk.BOTH, expand=True)

        # Impede que o conteúdo defina a altura do frame
        resultados.pack_propagate(False)

        # Textos iniciais dos resultados (placeholders)
        labels = [
            "Média: --",
            "Desvio padrão: --",
            "Imagem 1 - Desvio: -- % - Status: --",
            "Imagem 2 - Desvio: -- % - Status: --",
            "Imagem 3 - Desvio: -- % - Status: --",
            "Imagem 4 - Desvio: -- % - Status: --",
            "Imagem 5 - Desvio: -- % - Status: --",
            "Imagem 6 - Desvio: -- % - Status: --"
        ]

        self.labels_resultados = []

        # Adiciona os textos no frame interno
        for txt in labels:
            lbl = tk.Label(resultados,
                           text=txt,
                           anchor="w",
                           bg="#455561",
                           fg="white",
                           font=("Courier New", 10))
            lbl.pack(fill=tk.X, padx=10, pady=9)
            self.labels_resultados.append(lbl)


    # Cria a galeria de 6 blocos de imagem
    def _criar_galeria_imagens(self, parent):
        galeria = tk.Frame(parent, bg="#8699A8")
        galeria.pack(expand=True, fill=tk.BOTH)
        galeria.pack_propagate(False)

        # Configurar as linhas e colunas para expandir proporcionalmente
        # (2 linhas, 3 colunas)
        for i in range(2):
            galeria.rowconfigure(i, weight=1) # Cada linha recebe peso para expandir
        for j in range(3):
            galeria.columnconfigure(j, weight=1) # Cada coluna recebe peso para expandir

        # Lista para guardar os blocos
        self.blocos = []

        # Cria 2 linhas por 3 colunas = 6 blocos
        for i in range(2):
            for j in range(3):
                bloco_info = self._criar_bloco_imagem(galeria, i * 3 + j)
                bloco_info["frame"].grid(row=i, column=j, padx=15, pady=10, sticky="nsew")
                self.blocos.append(bloco_info)


    # Função para criar os blocos onde as miniaturas serão apresentadas
    def _criar_bloco_imagem(self, parent, index):
        bloco = tk.Frame(parent,
                         bg="#455561",
                         width=220,
                         height=240,
                         bd=0,
                         highlightthickness=5,
                         highlightbackground="#A9A9A9",
                         relief="solid")
        bloco.pack_propagate(False)

        # Frame do título
        top_frame = tk.Frame(bloco, bg="#455561")
        top_frame.pack(fill=tk.X, pady=(5, 5))

        img_label = tk.Label(top_frame, text="Imagem:", bg="#455561",
                             font=("Helvetica", 9, "bold"), fg="white", anchor="w")
        img_label.pack(side="left")

        img_label_prefixo = tk.Label(top_frame, text="(sem arquivo)", bg="#455561",
                                     font=("Helvetica", 9, "bold"), fg="cyan", anchor="w")
        img_label_prefixo.pack(side="left", fill=tk.X, expand=True)

        # Informações
        qtd_label = tk.Label(bloco, text="Qtde de grãos: --", bg="#455561", fg="white", anchor="w")
        qtd_label.pack(fill=tk.X)

        status_label = tk.Label(bloco, text="Status: --", bg="#455561", fg="white", anchor="w")
        status_label.pack(fill=tk.X)

        # Frame inferior para os botões
        botoes_frame = tk.Frame(bloco, bg="#455561")
        botoes_frame.pack(side="bottom", fill=tk.X, pady=5)

        botao_imagem = tk.Button(botoes_frame,
                                  text="Mostrar imagem",
                                  font=("Helvetica", 8),
                                  state="disabled",
                                  command=lambda idx=index: self._mostrar_imagem(idx))
        botao_imagem.pack(side="left", padx=5)

        botao_mascara = tk.Button(botoes_frame,
                                  text="Mostrar máscara",
                                  font=("Helvetica", 8),
                                  state="disabled",
                                  command=lambda idx=index: self._mostrar_mascara(idx))
        botao_mascara.pack(side="right", padx=5)

        return {
            "frame": bloco,
            "qtd_label": qtd_label,
            "status_label": status_label,
            "botao_imagem": botao_imagem,
            "botao_mascara": botao_mascara,
            "top_frame": top_frame,
            "botoes_frame": botoes_frame
        }

    # Função para mostrar a imagem ajustada e recortada (com_retangulo)
    def _mostrar_imagem(self, index):
        try:
            imagemRet  = self.comparador.listaObj[index].nomeArqB + "_com_retangulo.jpg"
            caminhoRet = os.path.join(self.comparador.listaObj[index].caminho, imagemRet)
            imagem     = Image.open(caminhoRet)

            nova_janela = Toplevel(self.master)
            nova_janela.title(f"Visualização - Imagem {index + 1}")
            nova_janela.configure(bg="#2E2E2E")

            try:
                resample_filter = Image.Resampling.LANCZOS
            except AttributeError:
                resample_filter = Image.ANTIALIAS

            imagem.thumbnail((self.largura_max, self.altura_max), resample_filter)

            imagem_tk = ImageTk.PhotoImage(imagem)

            label_img = tk.Label(nova_janela, image=imagem_tk, bg="#2E2E2E")
            label_img.image = imagem_tk  # mantém referência viva
            label_img.pack(padx=10, pady=10)

            logger.info(f"Imagem exibida: {caminhoRet}")

        except Exception as e:
            logger.error(f"Erro ao abrir imagem {index}: {e}")
            messagebox.showerror("Erro", f"Não foi possível abrir a imagem:\n{e}")


    # Função para mostrar a máscara binaria utilizada no reconhecimento das particulas.
    def _mostrar_mascara(self, index):
        try:
            # Essa imagem é um numpy.ndarray e não uma miniatura PIL
            imageMasc  = self.comparador.resultados[index]["mascara"]
            imagem           = Image.fromarray(imageMasc)

            nova_janela = Toplevel(self.master)
            nova_janela.title(f"Visualização - Máscara {index + 1}")
            nova_janela.configure(bg="#2E2E2E")

            try:
                resample_filter = Image.Resampling.LANCZOS
            except AttributeError:
                resample_filter = Image.ANTIALIAS

            imagem.thumbnail((self.largura_max, self.altura_max), resample_filter)

            imagem_tk = ImageTk.PhotoImage(imagem)

            label_img = tk.Label(nova_janela, image=imagem_tk, bg="#2E2E2E")
            label_img.image = imagem_tk  # mantém referência viva
            label_img.pack(padx=10, pady=10)

            logger.info(f"Máscara exibida do arquivo: {self.comparador.listaObj[index].nomeArqB + '_com_retangulo.jpg'}")
        except Exception as e:
            logger.error(f"Erro ao abrir máscara {index}: {e}")
            messagebox.showerror("Erro", f"Não foi possível abrir a máscara:\n{e}")


    # Função para criar a barra de status
    def _criar_barra_status(self):
        self.frame_inferior = tk.Frame(self.master, bg="#2E2E2E")
        self.frame_inferior.pack(fill="x", side="bottom")

        # Botão "Sair" na barra inferior
        self.botao_sair = tk.Button(self.frame_inferior, text="Sair", command=self._fechar_janela)
        self.botao_sair.pack(side="left", padx=10, pady=2)

        # Subframe para a barra de status e a barra de progresso
        self.status_container = tk.Frame(self.frame_inferior, bg="#2E2E2E")
        self.status_container.pack(side="right", fill="x", expand=True, padx=5, pady=2)

        # Label com status (à esquerda dentro do status_container)
        self.barra_status = tk.Label(self.status_container,
                                     textvariable=self.status_var,
                                     anchor="w",
                                     bg="#2E2E2E",
                                     fg="white")

        self.barra_status.pack(fill="x", padx=5, pady=2, side="right", expand=True)

        # Configurar estilo para a barra de progresso
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TProgressbar", troughcolor="grey", background="limegreen", thickness=20)
        self.progress = ttk.Progressbar(self.status_container,
                                        length=200,
                                        mode="determinate",
                                        style="TProgressbar")

        self.progress.pack(side="right", padx=(10, 0))

        # Oculta por padrão
        self.progress.pack_forget()


    def _mostrar_progresso(self):
        self.progress.config(mode="determinate", maximum=100)
        self.progress["value"] = 0
        self.progress.pack(side="right", padx=(10, 0))


    def _ocultar_progresso(self):
        self.progress.stop()
        self.progress.pack_forget()

'==================================== Início para execução isolada do módulo =========================================='

# Executa o applicativo
if __name__ == "__main__":

    try:
        # Cria a janela principal
        root = TkinterDnD.Tk()
        # Instancia a interface
        app = ComparadorGraosUI(root)
        # Inicia o loop principal da interface
        root.mainloop()
        sys.exit(0)

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
