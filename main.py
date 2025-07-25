from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from quiz_routes import router as quiz_router
import os

app = FastAPI()

# Ativando o CORS (muito importante para aceitar chamadas do navegador)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Coloque seu domínio aqui depois para segurança
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui as rotas da API
app.include_router(quiz_router)

# Servir os arquivos do frontend (HTML, JS, CSS) da pasta public/
app.mount("/", StaticFiles(directory="public", html=True), name="public")
