import os
import sys
import argparse
import numpy as np

# adiciona raiz do projeto ao path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from app.App_comparator import ComparadorParticulas


def run(image_paths):
    print("\n[INFO] Starting granule detection pipeline...\n")

    comparador = ComparadorParticulas()

    # define lista de imagens diretamente (sem GUI)
    comparador.criar_atributos(image_paths)

    print(f"[INFO] Loading {len(image_paths)} images...")
    comparador.carregar_imagens_em_memoria()

    print("[INFO] Processing images...")
    comparador.processar_imagens()

    # resultados
    resultados = comparador.resultados

    if not resultados:
        print("[ERROR] No results generated.")
        return

    quantidades = [r["quantidade"] for r in resultados]
    media = np.mean(quantidades)
    desvio = np.std(quantidades)

    print("\n===== RESULTS =====")
    print(f"Mean granules count : {media:.2f}")
    print(f"Std deviation       : {desvio:.2f}")
    print("-" * 40)

    for r in resultados:
        print(f"{r['nome']:<25} | Qty: {r['quantidade']:<5} | "
              f"Dev: {r['desvio_percentual']:<6}% | Status: {r['status']}")

    print("\n[INFO] Pipeline finished successfully.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Granule detection pipeline")
    parser.add_argument(
        "--images",
        nargs="+",
        required=True,
        help="List of image paths"
    )

    args = parser.parse_args()

    run(args.images)