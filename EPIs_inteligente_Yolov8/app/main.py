from __future__ import annotations

import base64
import csv
import io
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image, UnidentifiedImageError
from starlette.middleware.sessions import SessionMiddleware

# Todos os caminhos são calculados a partir deste arquivo, não do terminal.
ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"
ASSETS_DIR = ROOT / "assets"
DB_PATH = ROOT / "epis_inteligente.db"
DEFAULT_WEIGHTS = ROOT / "runs" / "epis" / "weights" / "best.pt"

AREAS = ["Entrada principal", "Galpão A", "Oficina", "Área de carga"]
EVENTOS = ["Capacete ausente", "Luvas ausentes", "Colete ausente", "Outro"]
STATUSES = ["Aberto", "Em análise", "Concluído"]
PRIORIDADES = ["Alta", "Média", "Baixa"]

for required_dir in (STATIC_DIR, TEMPLATES_DIR, ASSETS_DIR):
    if not required_dir.is_dir():
        raise RuntimeError(f"Pasta obrigatória não encontrada: {required_dir}")

app = FastAPI(title="EPIs Inteligente", version="1.0.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("EPIS_SESSION_SECRET", "chave-local-epis-inteligente-altere-em-producao"),
    same_site="lax",
    https_only=False,  # aplicação local em http://127.0.0.1
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def db_connect() -> sqlite3.Connection:
    con = sqlite3.connect(str(DB_PATH), timeout=15)
    con.row_factory = sqlite3.Row
    return con


def db_init() -> None:
    """Cria a tabela sem apagar registros já existentes."""
    with db_connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS ocorrencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT NOT NULL,
                area TEXT NOT NULL,
                evento TEXT NOT NULL,
                status TEXT NOT NULL,
                prioridade TEXT NOT NULL
            )"""
        )
        total = con.execute("SELECT COUNT(*) FROM ocorrencias").fetchone()[0]
        if total == 0:
            exemplos = [
                ("09:42", "Entrada principal", "Capacete ausente", "Aberto", "Alta"),
                ("09:18", "Galpão A", "Colete ausente", "Em análise", "Média"),
                ("08:51", "Oficina", "Luvas ausentes", "Concluído", "Média"),
            ]
            con.executemany(
                "INSERT INTO ocorrencias(data_hora,area,evento,status,prioridade) VALUES(?,?,?,?,?)",
                exemplos,
            )


def get_records() -> list[dict[str, Any]]:
    with db_connect() as con:
        rows = con.execute(
            "SELECT id,data_hora,area,evento,status,prioridade FROM ocorrencias ORDER BY id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def require_login(request: Request) -> None:
    if not request.session.get("logged"):
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")


@app.on_event("startup")
def startup() -> None:
    db_init()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "aplicacao": "EPIs Inteligente"}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    if not request.session.get("logged"):
        return templates.TemplateResponse(
            request=request, name="login.html", context={"error": None}
        )
    return templates.TemplateResponse(
        request=request, name="index.html", context={"username": "Administrador"}
    )


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if username == "admin" and password == "admin123":
        request.session["logged"] = True
        request.session["username"] = "Administrador"
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": "Credenciais inválidas."},
        status_code=401,
    )


@app.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@app.get("/api/ocorrencias")
async def api_records(request: Request):
    require_login(request)
    return get_records()


@app.post("/api/ocorrencias")
async def add_record(
    request: Request,
    area: str = Form(...),
    evento: str = Form(...),
    prioridade: str = Form(...),
):
    require_login(request)
    if area not in AREAS or evento not in EVENTOS or prioridade not in PRIORIDADES:
        raise HTTPException(status_code=400, detail="Dados inválidos.")
    with db_connect() as con:
        con.execute(
            "INSERT INTO ocorrencias(data_hora,area,evento,status,prioridade) VALUES(?,?,?,?,?)",
            (datetime.now().strftime("%d/%m/%Y %H:%M"), area, evento, "Aberto", prioridade),
        )
    return {"ok": True}


@app.patch("/api/ocorrencias/{record_id}")
async def update_record(
    record_id: int,
    request: Request,
    status: str = Form(...),
):
    require_login(request)
    if status not in STATUSES:
        raise HTTPException(status_code=400, detail="Status inválido.")
    with db_connect() as con:
        cursor = con.execute(
            "UPDATE ocorrencias SET status=? WHERE id=?", (status, record_id)
        )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada.")
    return {"ok": True}


@app.get("/api/exportar")
async def export_csv(request: Request):
    require_login(request)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["ID", "Data/Hora", "Área", "Evento", "Status", "Prioridade"])
    for record in get_records():
        writer.writerow([
            record["id"], record["data_hora"], record["area"], record["evento"],
            record["status"], record["prioridade"],
        ])
    data = output.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=registros_epis.csv"},
    )


@app.post("/api/analisar")
async def analyze(
    request: Request,
    imagem: UploadFile = File(...),
    pesos: str = Form("runs/epis/weights/best.pt"),
):
    require_login(request)
    if imagem.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Envie uma imagem JPG, PNG ou WEBP.")
    raw = await imagem.read()
    if not raw:
        raise HTTPException(status_code=400, detail="O arquivo enviado está vazio.")
    try:
        image = Image.open(io.BytesIO(raw)).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="Não foi possível abrir a imagem enviada.")

    weight_path = Path(pesos)
    if not weight_path.is_absolute():
        weight_path = ROOT / weight_path
    weight_path = weight_path.resolve()
    if not weight_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Pesos do modelo não encontrados em {weight_path}. Execute python train.py.",
        )
    try:
        from ultralytics import YOLO

        model = YOLO(str(weight_path))
        result = model.predict(source=image, conf=0.25, verbose=False)[0]
        plotted = Image.fromarray(result.plot()[:, :, ::-1])
        buffer = io.BytesIO()
        plotted.save(buffer, format="JPEG", quality=90)
        detections = []
        if result.boxes is not None:
            for box in result.boxes:
                class_id = int(box.cls.item())
                detections.append({
                    "classe": model.names.get(class_id, "Objeto"),
                    "confianca": round(float(box.conf.item()) * 100, 1),
                })
        return {
            "imagem": "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii"),
            "deteccoes": detections,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Falha na análise YOLOv8: {exc}") from exc


@app.get("/api/status")
async def model_status(request: Request):
    require_login(request)
    return {
        "modelo_encontrado": DEFAULT_WEIGHTS.is_file(),
        "caminho_modelo": str(DEFAULT_WEIGHTS),
        "ocorrencias": len(get_records()),
    }
