import logging
import os
import __main__

# Filtro que adiciona uma linha em branco no final da execução (uma vez)
class FinalBlankLineFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self.executado = False

    def filter(self, record):
        if record.levelno >= logging.CRITICAL and not self.executado:
            with open(record.log_filename, "a", encoding='utf-8') as f:
                f.write("\n")
            self.executado = True
        return True

# Função para criar e retorna um logger configurado com o nome do módulo que o chama.
def configurar_logger(nome_modulo: str, nivel_console: int = logging.WARNING):
    logger = logging.getLogger(nome_modulo)

    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            fmt='%(asctime)s [%(levelname)s] [%(name)s.%(funcName)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Determina o nome do arquivo que chamou o logger
        script_nome = os.path.splitext(os.path.basename(__main__.__file__))[0]
        nome_log    = f"log_{script_nome}.log"

        # Adiciona o nome do arquivo de log ao record para uso no filtro
        logging.LogRecord.log_filename = nome_log

        # Console handler com nível parametrizável
        console = logging.StreamHandler()
        console.setLevel(nivel_console)
        console.setFormatter(formatter)
        logger.addHandler(console)

        # File handler com todos os logs
        file_handler = logging.FileHandler(nome_log, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.addFilter(FinalBlankLineFilter())
        logger.addHandler(file_handler)

    return logger

