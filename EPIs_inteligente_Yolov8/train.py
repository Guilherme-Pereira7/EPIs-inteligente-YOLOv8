"""Treina o modelo YOLOv8 com o dataset incluído no projeto."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "dataset"


def main() -> int:
    data_yaml = DATASET / "data.yaml"
    for split in ("train", "val"):
        image_dir = DATASET / "images" / split
        label_dir = DATASET / "labels" / split
        if not image_dir.is_dir() or not label_dir.is_dir():
            print(f"ERRO: pasta de imagens/etiquetas ausente para '{split}'.")
            return 1
        if not list(image_dir.glob("*.jpg")) and not list(image_dir.glob("*.png")):
            print(f"ERRO: não há imagens na pasta {image_dir}")
            return 1
    if not data_yaml.is_file():
        print(f"ERRO: arquivo de configuração não encontrado: {data_yaml}")
        return 1

    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERRO: YOLOv8 não instalado. Execute: python -m pip install ultralytics")
        return 1

    # Gera um YAML temporário com caminho absoluto: funciona mesmo se o terminal
    # estiver aberto fora da pasta do projeto ou em outro computador Windows.
    temporary_yaml = ROOT / "dataset" / "data_local.yaml"
    yaml_text = (
        f'path: "{DATASET.as_posix()}"\n'
        "train: images/train\n"
        "val: images/val\n"
        "names:\n"
        "  0: capacete\n"
        "  1: luvas\n"
        "  2: colete\n"
    )
    temporary_yaml.write_text(yaml_text, encoding="utf-8")
    try:
        print("Carregando YOLOv8n e iniciando o treinamento...")
        model = YOLO("yolov8n.pt")
        model.train(
            data=str(temporary_yaml),
            epochs=50,
            imgsz=640,
            batch=8,
            project=str(ROOT / "runs"),
            name="epis",
            patience=15,
            exist_ok=True,
        )
        best = ROOT / "runs" / "epis" / "weights" / "best.pt"
        if best.is_file():
            print(f"\nTreinamento concluído! Pesos salvos em: {best}")
            return 0
        print("Treinamento terminou, mas best.pt não foi encontrado no caminho esperado.")
        return 1
    except Exception as exc:
        print(f"\nERRO durante o treinamento: {exc}")
        return 1
    finally:
        try:
            temporary_yaml.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
