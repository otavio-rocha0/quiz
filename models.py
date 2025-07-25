from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from datetime import datetime
from sqlalchemy.orm import relationship
from database import Base

# Modelo de Quiz
class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, nullable=False)
    conteudos = Column(String, nullable=True)

    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")


# Modelo de Pergunta
class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    enunciado = Column(String, nullable=False)

    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")
    quiz = relationship("Quiz", back_populates="questions")


# Modelo de Resposta
class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    texto = Column(String, nullable=False)
    correta = Column(Boolean, nullable=False)

    question = relationship("Question", back_populates="answers")


# Modelo de Sessão
class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    pin = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="esperando", nullable=False)
    pergunta_index = Column(Integer, default=0, nullable=False)
    ultima_pergunta_id = Column(Integer, nullable=True)
    inicio_pergunta = Column(DateTime, default=datetime.utcnow)

    jogadores = relationship("Player", back_populates="sessao", cascade="all, delete-orphan")
    quiz = relationship("Quiz")


# Modelo de Jogador
class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    pontuacao = Column(Integer, default=0, nullable=False)
    personagem = Column(String)

    sessao = relationship("Session", back_populates="jogadores")

# Modelo de Resposta do Jogador
class PlayerAnswer(Base):
    __tablename__ = "player_answers"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    answer_id = Column(Integer, ForeignKey("answers.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    player = relationship("Player")
    question = relationship("Question")
    answer = relationship("Answer")
