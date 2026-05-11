import os, json, logging
import pg8000.dbapi as pg
import urllib.parse
from datetime import datetime
import pytz
from anthropic import Anthropic
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes,
)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 8080))
client = Anthropic(api_key=ANTHROPIC_KEY)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FUSO_BR = pytz.timezone("America/Sao_Paulo")
DIAS_SEMANA = ["segunda-feira","terça-feira","quarta-feira","quinta-feira","sexta-feira","sábado","domingo"]

def data_hora_br():
    agora = datetime.now(FUSO_BR)
    dia_semana = DIAS_SEMANA[agora.weekday()]
    return agora.strftime(f"{dia_semana}, %d/%m/%Y às %H:%M")

SYSTEM_PROMPT_BASE = """Você é o PsicoPods, um assistente de escuta emocional criado pela Palimpsest, startup brasileira fundada pelo Psicólogo Clínico Amauri Trezza Martins. Seu papel é oferecer acolhimento, escuta ativa e suporte emocional.

REGRAS ESSENCIAIS:
- NUNCA faça diagnósticos, prescrições ou substitua atendimento profissional
- Use linguagem simples, humana e acolhedora
- NUNCA dê conselhos diretos
- Valide os sentimentos ANTES de qualquer resposta
- NUNCA minimize o que a pessoa sente
- Respostas CURTAS têm mais impacto — máximo 3 parágrafos curtos
- Termine SEMPRE com uma pergunta aberta

ESTILO NATURAL:
Quando a conversa estiver fluindo bem e a pessoa estiver em momento mais leve ou reflexivo, você pode criar pontes culturais de forma espontânea e calorosa. Exemplos:
- "Isso que você disse me faz lembrar uma música do Caetano Veloso... você conhece 'Sozinho'?"
- "Tem um filme que captura exatamente isso que você está sentindo — já assistiu 'Amores Expressos'?"
- "Isso me lembra um poema de Adélia Prado... você gosta de poesia?"
- "Uma caminhada no parque às vezes ajuda a organizar esses pensamentos... tem um lugar assim perto de você?"

Faça isso apenas quando a conversa permitir — nunca force em momentos de crise ou sofrimento intenso."""

PALAVRAS_RISCO = [
    "me machucar","me matar","suicídio","suicidio","não quero viver",
    "nao quero viver","acabar com tudo","acabar com minha vida","tirar minha vida",
    "violência doméstica","violencia domestica",
    "sofri abuso","estou sofrendo abuso","abuso sexual","abuso físico","abuso fisico",
    "agressão física","agressao fisica","agressão doméstica","agressao domestica",
    "estou em perigo","socorro","ajuda urgente","estupro",
    "assédio sexual","assedio sexual",
    "não aguento mais","nao aguento mais","quero desaparecer","automutilação",
    "automutilacao","me cortar","me cortei",
]

RESPOSTA_RISCO = """Percebi que você trouxe algo muito sério, e quero que saiba que estou aqui com você agora.\n\nO que você está sentindo importa, e você não precisa passar por isso sozinha(o).\n\n🆘 *Canais de ajuda imediata:*\n• *CVV* — Ligue *188*\n• *Ligue 180* — Atendimento à Mulher\n• *SAMU:* 192 | *Polícia:* 190\n\nVocê consegue me contar mais sobre o que está acontecendo?"""


def verificar_risco(texto):
    return any(p in texto.lower() for p in PALAVRAS_RISCO)


def conectar():
    conn = pg.connect(DATABASE_URL)
    return conn


def inicializar_banco():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS memoria (user_id TEXT PRIMARY KEY, historico TEXT NOT NULL)")
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Banco OK")


def carregar_historico(user_id):
    try:
        conn = conectar()
        cur = conn.cursor()
        cur.execute("SELECT historico FROM memoria WHERE user_id=%s", (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return json.loads(row[0]) if row else []
    except Exception as e:
        logger.error(f"Erro carregar: {e}")
        return []


def salvar_historico(user_id, historico):
    try:
        conn = conectar()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO memoria (user_id, historico) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET historico=EXCLUDED.historico",
            (user_id, json.dumps(historico, ensure_ascii=False)),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Erro salvar: {e}")


def limpar_historico(user_id):
    try:
        conn = conectar()
        cur = conn.cursor()
        cur.execute("DELETE FROM memoria WHERE user_id=%s", (user_id,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Erro limpar: {e}")


async def start(update, context):
    nome = update.effective_user.first_name or "você"
    await update.message.reply_text(
        f"Olá, {nome}! 💙\n\nEu sou o *PsicoPods*, um espaço de escuta criado pela *Palimpsest*.\n\nAqui você pode falar sobre o que está sentindo, no seu ritmo e do seu jeito.\n\nO que está passando pela sua cabeça agora?",
        parse_mode="Markdown",
    )


async def relatorio(update, context):
    user_id = str(update.effective_user.id)
    msgs = carregar_historico(user_id)
    if not msgs:
        await update.message.reply_text("Ainda não temos histórico suficiente. Continue conversando e volte aqui depois. 💙")
        return
    du = [m for m in msgs if m["role"] == "user"]
    await update.message.reply_text(
        f"📊 *Resumo da sua jornada*\n\n🗓️ {data_hora_br()}\n💬 Trocas: {len(msgs) // 2}\n✍️ Suas mensagens: {len(du)}\n\nA Palimpsest agradece sua confiança. 💙",
        parse_mode="Markdown",
    )


async def limpar(update, context):
    limpar_historico(str(update.effective_user.id))
    await update.message.reply_text("Tudo bem. Começamos do zero. ✨\n\nO que você gostaria de compartilhar agora?")


async def ajuda(update, context):
    await update.message.reply_text(
        "📋 *Comandos:*\n\n/start — Reinicia\n/relatorio — Resumo\n/limpar — Apaga histórico\n/ajuda — Esta lista\n\nOu escreva o que está sentindo. 💙",
        parse_mode="Markdown",
    )


async def responder(update, context):
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
    system_prompt = f"{SYSTEM_PROMPT_BASE}\n\nData e hora atual em Brasília: {data_hora_br()}"
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=300,
            system=system_prompt,
            messages=historico,
        )
        tr = resp.content[0].text
        historico.append({"role": "assistant", "content": tr})
        salvar_historico(user_id, historico)
        await update.message.reply_text(tr)
    except Exception as e:
        logger.error(f"Erro API: {e}")
        await update.message.reply_text("Estou com uma dificuldade técnica. Pode tentar em instantes? 🙏")


def main():
    try:
        inicializar_banco()
        logger.info("Banco inicializado com sucesso")
    except Exception as e:
        logger.error(f"Erro banco: {e}")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("relatorio", relatorio))
    app.add_handler(CommandHandler("limpar", limpar))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
    if WEBHOOK_URL:
        app.run_webhook(
            listen="0.0.0.0", port=PORT, url_path=TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
        )
    else:
        import time
        time.sleep(10)
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
