from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
import models, schemas
import random
import string
import os
import json
import re
from datetime import datetime
from pydantic import BaseModel
import demjson3
import requests

router = APIRouter()

# ======== Conexão com o DB ========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ======== Criar Quiz ========
@router.post("/criar_quiz")
def criar_quiz(quiz: schemas.QuizCreate, db: Session = Depends(get_db)):
    novo_quiz = models.Quiz(titulo=quiz.titulo, conteudos=quiz.conteudos)
    db.add(novo_quiz)
    db.commit()
    db.refresh(novo_quiz)

    for pergunta in quiz.perguntas:
        nova_pergunta = models.Question(enunciado=pergunta.enunciado, quiz_id=novo_quiz.id)
        db.add(nova_pergunta)
        db.commit()
        db.refresh(nova_pergunta)

        for resposta in pergunta.respostas:
            nova_resposta = models.Answer(
                texto=resposta.texto,
                correta=resposta.correta,
                question_id=nova_pergunta.id
            )
            db.add(nova_resposta)

    db.commit()
    return {"mensagem": "Quiz criado com sucesso!", "quiz_id": novo_quiz.id}

# ======== Iniciar Sessão ========
def gerar_pin():
    return ''.join(random.choices(string.digits, k=6))

@router.post("/iniciar_partida")
def iniciar_partida(dados: schemas.CriarSessao, db: Session = Depends(get_db)):
    pin = gerar_pin()
    sessao = models.Session(quiz_id=dados.quiz_id, pin=pin, pergunta_index=0)
    db.add(sessao)
    db.commit()
    db.refresh(sessao)
    return {"mensagem": "Partida iniciada com sucesso!", "pin": pin, "quiz_id": dados.quiz_id}

# ======== Entrar na Partida ========
@router.post("/entrar")
def entrar_na_partida(dados: schemas.EntrarPartida, db: Session = Depends(get_db)):
    sessao = db.query(models.Session).filter(models.Session.pin == dados.pin).first()
    if not sessao:
        return {"erro": "PIN inválido"}

    jogador = db.query(models.Player).filter_by(nome=dados.nome, session_id=sessao.id).first()
    if jogador:
        return {"mensagem": "Jogador já existe", "player_id": jogador.id}

    jogador = models.Player(
    nome=dados.nome,
    session_id=sessao.id,
    pontuacao=0,
    personagem=json.dumps(dados.personagem)
    )

    db.add(jogador)
    db.commit()
    db.refresh(jogador)
    return {"mensagem": "Entrou na partida!", "player_id": jogador.id}

# ======== Pergunta Atual ========
@router.get("/pergunta_atual")
def pegar_pergunta(pin: str, db: Session = Depends(get_db)):
    sessao = db.query(models.Session).filter(models.Session.pin == pin).first()
    if not sessao:
        return {"erro": "PIN inválido"}

    perguntas = db.query(models.Question).filter(models.Question.quiz_id == sessao.quiz_id).all()
    if not perguntas or sessao.pergunta_index >= len(perguntas):
        return {"mensagem": "Não há mais perguntas"}

    pergunta = perguntas[sessao.pergunta_index]
    respostas = db.query(models.Answer).filter(models.Answer.question_id == pergunta.id).all()

    respostas_embaralhadas = [{"id": r.id, "texto": r.texto} for r in respostas]
    random.shuffle(respostas_embaralhadas)

    sessao.ultima_pergunta_id = pergunta.id
    sessao.inicio_pergunta = datetime.utcnow()
    db.commit()

    return {
        "pergunta_id": pergunta.id,
        "enunciado": pergunta.enunciado,
        "respostas": respostas_embaralhadas
    }

# ======== Responder Pergunta ========
class RespostaRequest(BaseModel):
    player_id: int
    question_id: int
    resposta_id: int

@router.post("/responder")
def responder(dados: RespostaRequest, db: Session = Depends(get_db)):
    jogador = db.query(models.Player).filter(models.Player.id == dados.player_id).first()
    if not jogador:
        return {"success": False, "correta": False, "mensagem": "Jogador não encontrado"}

    sessao = db.query(models.Session).filter(models.Session.id == jogador.session_id).first()
    if not sessao:
        return {"success": False, "correta": False, "mensagem": "Sessão inválida"}

    resposta = db.query(models.Answer).filter(models.Answer.id == dados.resposta_id).first()
    if not resposta or resposta.question_id != dados.question_id:
        return {"success": False, "correta": False, "mensagem": "Resposta inválida"}

    # Verifica se o jogador já respondeu essa pergunta
    ja_respondeu = db.query(models.PlayerAnswer).filter_by(
        player_id=jogador.id, question_id=dados.question_id
    ).first()
    if ja_respondeu:
        return {"success": False, "correta": False, "mensagem": "Você já respondeu essa pergunta"}

    # Armazena resposta
    player_answer = models.PlayerAnswer(
        player_id=jogador.id,
        question_id=dados.question_id,
        answer_id=dados.resposta_id
    )
    db.add(player_answer)

    # Calcula pontos
    tempo_maximo = 20
    tempo_resposta = (datetime.utcnow() - sessao.inicio_pergunta).total_seconds()

    if resposta.correta:
        base = 1000
        min_pontos = 100
        pontuacao = max(min_pontos, int(base * (1 - tempo_resposta / tempo_maximo)))
        jogador.pontuacao += pontuacao
        db.commit()
        return {
            "success": True,
            "correta": True,
            "mensagem": "Resposta correta!",
            "pontuacao": jogador.pontuacao,
            "bonus": pontuacao
        }
    else:
        db.commit()
        return {
            "success": True,
            "correta": False,
            "mensagem": "Resposta incorreta.",
            "pontuacao": jogador.pontuacao
        }

# ======== Próxima Pergunta ========
@router.post("/proxima_pergunta")
def proxima_pergunta(pin: str, db: Session = Depends(get_db)):
    sessao = db.query(models.Session).filter(models.Session.pin == pin).first()
    if not sessao:
        return {"erro": "PIN inválido"}

    sessao.pergunta_index += 1
    db.commit()
    return {"mensagem": "Avançou para a próxima pergunta"}

# ======== Cliente DeepInfra ========
DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY") or "RudaSZEs8YmkrpbLhaGk9RcT1vihGT9d"

def gerar_com_deepinfra(prompt: str):
    url = "https://api.deepinfra.com/v1/openai/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "meta-llama/Meta-Llama-3-8B-Instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 700
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        return {
            "erro": "Falha ao chamar DeepInfra",
            "status": response.status_code,
            "detalhes": response.text
        }

    return response.json()["choices"][0]["message"]["content"]

# ======== IA: Gerar Pergunta ========
@router.post("/gerar_pergunta")
def gerar_pergunta_ia(dados: dict):
    conteudo = dados.get("conteudo")
    prompt_personalizado = dados.get("prompt", "")

    prompt = f"""
Baseado no seguinte conteúdo estudado:

{conteudo}

Gere **apenas uma** pergunta de múltipla escolha com 4 alternativas e indique a correta.

⚠️ Responda SOMENTE com um bloco marcado com [[JSON]] e [[/JSON]] contendo o seguinte formato:

[[JSON]]
{{
  "pergunta": "enunciado da pergunta",
  "respostas": [
    {{ "texto": "alternativa A", "correta": false }},
    {{ "texto": "alternativa B", "correta": true }},
    {{ "texto": "alternativa C", "correta": false }},
    {{ "texto": "alternativa D", "correta": false }}
  ]
}}
[[/JSON]]

Não explique nada, apenas envie o JSON dentro da marcação acima.
Prompt extra do professor: {prompt_personalizado}
"""
    try:
        resposta_gerada = gerar_com_deepinfra(prompt)

        match = re.search(r"\[\[JSON\]\](.*?)\[\[/JSON\]\]", resposta_gerada, re.DOTALL)
        if not match:
            return {
                "erro": "Não foi possível encontrar bloco [[JSON]]",
                "resposta_bruta": resposta_gerada
            }

        json_bruto = match.group(1).strip()
        try:
            pergunta_json = json.loads(json_bruto)
        except Exception:
            pergunta_json = demjson3.decode(json_bruto)

        random.shuffle(pergunta_json["respostas"])
        return pergunta_json

    except Exception as e:
        return {
            "erro": "Erro ao processar resposta da IA",
            "mensagem_ia": resposta_gerada if 'resposta_gerada' in locals() else None,
            "erro_detalhado": str(e)
        }

# ======== Resultado da Questão ========
@router.get("/perguntas/{pin}")
def obter_perguntas(pin: str, db: Session = Depends(get_db)):
    sessao = db.query(models.Session).filter_by(pin=pin).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    quiz = db.query(models.Quiz).filter_by(id=sessao.quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz não encontrado")

    perguntas = db.query(models.Question).filter_by(quiz_id=quiz.id).all()
    resultado = []

    for pergunta in perguntas:
        respostas = db.query(models.Answer).filter_by(question_id=pergunta.id).all()
        resultado.append({
            "id": pergunta.id,
            "enunciado": pergunta.enunciado,
            "respostas": [{"id": r.id, "texto": r.texto} for r in respostas]
        })

    return resultado


@router.get("/resultado_pergunta")
def resultado_pergunta(pin: str, db: Session = Depends(get_db)):
    sessao = db.query(models.Session).filter_by(pin=pin).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    pergunta_id = sessao.ultima_pergunta_id
    if not pergunta_id:
        raise HTTPException(status_code=400, detail="Nenhuma pergunta foi enviada ainda")

    respostas = db.query(models.Answer).filter_by(question_id=pergunta_id).all()

    resultado = []
    for resposta in respostas:
        total = db.query(models.PlayerAnswer).filter_by(answer_id=resposta.id).count()
        resultado.append({
            "texto": resposta.texto,
            "correta": resposta.correta,
            "quantidade": total
        })

    return {
        "pergunta_id": pergunta_id,
        "respostas": resultado
    }

# ======== Resultado da Questão (Ranking por PIN) ========
@router.get("/ranking/{pin}")
def obter_ranking(pin: str, db: Session = Depends(get_db)):
    # Busca a sessão com base no PIN
    sessao = db.query(models.Session).filter(models.Session.pin == pin).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    jogadores = db.query(models.Player).filter(models.Player.session_id == sessao.id).all()
    if not jogadores:
        raise HTTPException(status_code=404, detail="Nenhum jogador encontrado para esta sessão")

    ranking = [{
        "nome": jogador.nome,
        "pontuacao": jogador.pontuacao,
        "personagem": jogador.personagem  # 👈 incluído aqui
    } for jogador in jogadores]

    # Ordena os jogadores por pontuação
    ranking.sort(key=lambda x: x["pontuacao"], reverse=True)

    return ranking
