# EPIs Inteligente — versão revisada

Aplicação local em Python + FastAPI, HTML, CSS e JavaScript, com banco SQLite e integração com YOLOv8.

## Iniciar no Windows (mais simples)

1. Extraia a pasta `EPIs inteligente Yolov8`.
2. Abra essa pasta no VS Code.
3. Dê dois cliques em `iniciar.bat`, ou execute no terminal:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

4. Abra http://127.0.0.1:8000

O terminal deve permanecer aberto enquanto o sistema estiver em uso.

## Acesso demonstrativo

- Usuário: `admin`
- Senha: `admin123`

## Treinar o YOLOv8

Com o ambiente virtual ativado e na pasta principal do projeto:

```powershell
python train.py
```

O primeiro treinamento pode baixar `yolov8n.pt` e requer conexão com a internet. Os pesos finais ficam em `runs/epis/weights/best.pt`.

## Funcionalidades

- Painel geral e quatro áreas: Entrada principal, Galpão A, Oficina e Área de carga.
- Monitoramento visual com imagens locais ilustrativas.
- Análise de imagem com YOLOv8 após o treinamento.
- Cadastro, filtro, atualização e exportação CSV de ocorrências.
- Persistência local em `epis_inteligente.db`.

## Observações importantes

- As imagens das quatro áreas são prévias ilustrativas. Câmeras ao vivo precisam ser conectadas com os endereços/streams reais.
- O dataset incluído é demonstrativo e pequeno; serve para validar o fluxo de treinamento, não para certificar segurança em ambiente industrial.
- O login é demonstrativo para execução local. Antes de publicar na internet, troque as credenciais e configure `EPIS_SESSION_SECRET` com uma chave segura.
- Para parar o servidor, volte ao terminal e pressione `Ctrl + C`.
