"""
PsicoPods - Bot de Escuta Emocional
Palimpsest Startup | Fundador: Amauri Frezza Martins
Versão com memória persistente via PostgreSQL
"""

import os
import json
import logging
import pg8000.dbapi as psycopg2
from datetime import datetime
from anthropic import Anthropic
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
DATABASE_URL = os.environ.get("DATABASE_URL")
PORT = int(os.environ.get("PORT", 8080))

client = Anthropic(api_key=ANTHROPIC_KEY)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é o PsicoPods, um assistente de escuta emocional criado pela Palimpsest,
startup brasileira fundada pelo Psicólogo Clínico Amauri Frezza Martins.

Seu papel é oferecer acolhimento, escuta ativa e suporte emocional.
Você NUNCA faz diagnósticos, prescrições ou substitui atendimento profissional.

REGRAS INEGOCIÁVEIS:
- Use linguagem simples, humana e acolhedora — sem termos técnicos
- NUNCA dê diagnósticos nem prescrições de qualquer tipo
- NUNCA dê conselhos diretos — prefira perguntas que ajudem a pessoa a refletir
- Termine SEMPRE cada resposta com uma pergunta aberta e acolhedora
- Respostas curtas têm mais impacto emocional — seja breve e direto
- Valide os sentimentos ANTES de qualquer outra resposta
- NUNCA minimize o que a pessoa sente
- Atenda mulheres, homens, adolescentes e idosos com igual respeito e atenção
- Você é um espaço seguro de escuta, não um terapeuta nem um chatbot genérico

SOBRE A PALIMPSEST:
A Palimpsest é uma startup brasileira que desenvolve tecnologia com propósito humano,
na interseção entre saúde mental, linguagem e inteligência artificial.
O PsicoPods é seu projeto principal."""

PALAVRAS_RISCO = [
    "me machucar",
    "me matar",
    "suicídio",
    "suicidio",
    "não quero viver",
    "nao quero viver",
    "acabar com tudo",
    "acabar com minha vida",
    "tirar minha vida",
    "me bater",
    "me agride",
    "me bateu",
    "violência doméstica",
    "violencia domestica",
    "violência",
    "violencia",
    "abuso",
    "agressão",
    "agressao",
    "estou em perigo",
    "ele me ameaça",
    "ele me ameaca",
    "socorro",
    "ajuda urgente",
    "estupro",
    "assédio",
    "assedio",
    "me sinto em perigo",
    "tenho medo de morrer",
    "ele vai me matar",
    "ela vai me matar",
    "não aguento mais",
    "nao aguento mais",
    "quero desaparecer",
    "sem saída",
    "sem saida",
    "automutilação",
    "automutilacao",
    "me cortar",
    "me cortei",
]

RESPOSTA_RISCO = """Percebi que você trouxe algo muito sério, e quero que saiba que estou aqui com você agora.

O que você está sentindo importa, e você não precisa passar por isso sozinha(o).

🆘 *Canais de ajuda imediata — todos gratuitos e 24h:*

• *CVV* (Centro de Valorização da Vida)
  Ligue *188* ou acesse cvv.org.br

• *Ligue 180* — Central de Atendimento à Mulher

• *SAMU:* 192

• *Polícia:* 190

Se estiver em perigo agora, por favor ligue imediatamente para o *190*.

Você consegue me contar um pouco mais sobre o que está acontecendo?"""


def verificar_risco(texto: str) -> bool:
    texto_lower = texto.lower()
    return any(palavra in texto_lower for palavra in PALAVRAS_RISCO)

    return psycopg2.connect(
        host=r.hostname,
        port=r.port,
        database=r.path[1:],
        user=r.username,
        password=r.password,
    )


def inicializar_banco():
    try:
        conn = conectar()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS memoria (
                user_id TEXT PRIMARY KEY,
                historico TEXT NOT NULL,
                atualizado_em TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Banco de dados inicializado com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao inicializar banco: {e}")
 logger.error(f"DATABASE_URL: {DATABASE_URL[:30] if DATABASE_URL else None}")


def carregar_historico(user_id: str) -> list:
    try:
        conn = conectar()
        cur = conn.cursor()
        cur.execute("SELECT historico FROM memoria WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return json.loads(row[0])
        return []
    except Exception as e:
        logger.error(f"Erro ao carregar histórico: {e}")
 logger.error(f"DATABASE_URL: {DATABASE_URL[:30] if DATABASE_URL else None}")
        return []


def salvar_historico(user_id: str, historico: list):
    try:
        conn = conectar()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO memoria (user_id, historico, atualizado_em)
            VALUES (%s, %s, NOW())
            ON CONFLICT (user_id)
            DO UPDATE SET historico = EXCLUDED.historico,
                          atualizado_em = NOW()
        """,
            (user_id, json.dumps(historico, ensure_ascii=False)),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Erro ao salvar histórico: {e}")


def limpar_historico(user_id: str):
    try:
        conn = conectar()
        cur = conn.cursor()
        cur.execute("DELETE FROM memoria WHERE user_id = %s", (user_id,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Erro ao limpar histórico: {e}")


def gerar_relatorio(user_id: str) -> str:
    msgs = carregar_historico(user_id)
    if not msgs:
        return (
            "Ainda não temos histórico suficiente para gerar um relatório. "
            "Continue conversando e volte aqui depois. 💙"
        )
    do_usuario = [m for m in msgs if m["role"] == "user"]
    total = len(msgs)
    data_agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    return (
        f"📊 *Resumo da sua jornada no PsicoPods*\n\n"
        f"🗓️ Gerado em: {data_agora}\n"
        f"💬 Trocas realizadas: {total // 2}\n"
        f"✍️ Suas mensagens: {len(do_usuario)}\n\n"
        f"_Este resumo é apenas um espelho do caminho que você percorreu aqui. "
        f"Para aprofundar o que descobriu, considere conversar com um profissional de saúde mental._\n\n"
        f"A Palimpsest agradece sua confiança. 💙"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    nome = update.effective_user.first_name or "você"
    historico = carregar_historico(user_id)
    if not historico:
        salvar_historico(user_id, [])
    mensagem = (
        f"Olá, {nome}! 💙\n\n"
        f"Eu sou o *PsicoPods*, um espaço de escuta criado pela *Palimpsest*.\n\n"
        f"Aqui você pode falar sobre o que está sentindo, no seu ritmo e do seu jeito. "
        f"Não há julgamento, não há pressa.\n\n"
        f"O que está passando pela sua cabeça agora?"
    )
    await update.message.reply_text(mensagem, parse_mode="Markdown")


async def relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    texto = gerar_relatorio(user_id)
    await update.message.reply_text(texto, parse_mode="Markdown")


async def limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    limpar_historico(user_id)
    await update.message.reply_text(
        "Tudo bem. Começamos do zero. ✨\n\nO que você gostaria de compartilhar agora?"
    )


async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Comandos disponíveis:*\n\n"
        "/start — Reinicia a apresentação\n"
        "/relatorio — Veja um resumo da sua jornada aqui\n"
        "/limpar — Apaga o histórico e começa nova conversa\n"
        "/ajuda — Mostra esta lista\n\n"
        "Ou simplesmente *escreva o que está sentindo* — estou aqui. 💙",
        parse_mode="Markdown",
    )


async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    texto = update.message.text.strip()
    historico = carregar_historico(user_id)

    if verificar_risco(texto):
        historico.append({"role": "user", "content": texto})
        historico.append({"role": "assistant", "content": RESPOSTA_RISCO})
        salvar_historico(user_id, historico)
        await update.message.reply_text(RESPOSTA_RISCO, parse_mode="Markdown")
        return

    historico.append({"role": "user", "content": texto})
    if len(historico) > 20:
        historico = historico[-20:]

    try:
        resposta = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=historico,
        )
        texto_resposta = resposta.content[0].text
        historico.append({"role": "assistant", "content": texto_resposta})
        salvar_historico(user_id, historico)
        await update.message.reply_text(texto_resposta)

    except Exception as e:
        logger.error(f"Erro na API Anthropic: {e}")
        await update.message.reply_text(
            "Estou com uma dificuldade técnica agora. "
            "Pode tentar novamente em instantes? 🙏"
        )


def main():
    inicializar_banco()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("relatorio", relatorio))
    app.add_handler(CommandHandler("limpar", limpar))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    if WEBHOOK_URL:
        logger.info(f"Iniciando em modo WEBHOOK: {WEBHOOK_URL}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
        )
    else:
        logger.info("Iniciando em modo POLLING")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
