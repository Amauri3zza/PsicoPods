import os, json, logging
import psycopg
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
DATABASE_URL = os.environ.get("DATABASE_URL")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 8080))
client = Anthropic(api_key=ANTHROPIC_KEY)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é o PsicoPods, um assistente de escuta emocional criado pela Palimpsest, startup brasileira fundada pelo Psicólogo Clínico Amauri Trezza Martins. Seu papel é oferecer acolhimento, escuta ativa e suporte emocional. Você NUNCA faz diagnósticos, prescrições ou substitui atendimento profissional. Use linguagem simples, humana e acolhedora. NUNCA dê diagnósticos nem prescrições. NUNCA dê conselhos diretos. Termine SEMPRE com uma pergunta aberta. Respostas curtas têm mais impacto. Valide os sentimentos ANTES de qualquer resposta. NUNCA minimize o que a pessoa sente."""

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
    "violência doméstica",
    "violencia domestica",
    "abuso",
    "agressão",
    "agressao",
    "estou em perigo",
    "socorro",
    "ajuda urgente",
    "estupro",
    "assédio",
    "assedio",
    "não aguento mais",
    "nao aguento mais",
    "quero desaparecer",
    "automutilação",
    "automutilacao",
    "me cortar",
    "me cortei",
]

RESPOSTA_RISCO = """Percebi que você trouxe algo muito sério, e quero que saiba que estou aqui com você agora.\n\nO que você está sentindo importa, e você não precisa passar por isso sozinha(o).\n\n🆘 *Canais de ajuda imediata:*\n• *CVV* — Ligue *188*\n• *Ligue 180* — Atendimento à Mulher\n• *SAMU:* 192 | *Polícia:* 190\n\nVocê consegue me contar mais sobre o que está acontecendo?"""


def verificar_risco(texto):
    return any(p in texto.lower() for p in PALAVRAS_RISCO)


def conectar():
    return psycopg2.connect(DATABASE_URL)


def inicializar_banco():
    conn = conectar()
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS memoria (user_id TEXT PRIMARY KEY, historico TEXT NOT NULL)"
    )
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Banco PostgreSQL OK")


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
        await update.message.reply_text(
            "Ainda não temos histórico suficiente. Continue conversando e volte aqui depois. 💙"
        )
        return
    du = [m for m in msgs if m["role"] == "user"]
    await update.message.reply_text(
        f"📊 *Resumo da sua jornada*\n\n🗓️ {datetime.now().strftime('%d/%m/%Y às %H:%M')}\n💬 Trocas: {len(msgs) // 2}\n✍️ Suas mensagens: {len(du)}\n\nA Palimpsest agradece sua confiança. 💙",
        parse_mode="Markdown",
    )


async def limpar(update, context):
    limpar_historico(str(update.effective_user.id))
    await update.message.reply_text(
        "Tudo bem. Começamos do zero. ✨\n\nO que você gostaria de compartilhar agora?"
    )


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
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=historico,
        )
        tr = resp.content[0].text
        historico.append({"role": "assistant", "content": tr})
        salvar_historico(user_id, historico)
        await update.message.reply_text(tr)
    except Exception as e:
        logger.error(f"Erro API: {e}")
        await update.message.reply_text(
            "Estou com uma dificuldade técnica. Pode tentar em instantes? 🙏"
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
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
        )
