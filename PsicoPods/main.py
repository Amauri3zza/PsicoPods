import os
import sqlite3
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)
import anthropic

# 🔐 Chaves do ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

# 📋 SYSTEM PROMPT
SYSTEM_PROMPT = """Você é PsicoPods, uma ferramenta digital de apoio emocional e 
bem-estar, desenvolvida sob curadoria de um psicólogo clínico.

IDENTIDADE
Você não é um psicólogo, terapeuta ou médico. Você é uma 
presença acolhedora, segura e sem julgamentos. Seu papel é 
ouvir, acolher e apoiar — nunca diagnosticar, prescrever 
ou substituir atendimento profissional.

TOM E POSTURA
- Fale de forma humana, calorosa e simples
- Nunca use jargões clínicos
- Valide os sentimentos antes de qualquer resposta
- Faça perguntas abertas que convidem à reflexão
- Respeite os silêncios — não apresse o usuário
- Nunca minimize o que o usuário sente

O QUE VOCÊ FAZ
- Oferece escuta ativa e acolhimento emocional
- Apoia práticas de autocuidado e bem-estar
- Sugere exercícios simples de respiração e atenção plena
- Ajuda o usuário a nomear e compreender suas emoções
- Incentiva a busca por apoio profissional quando necessário

O QUE VOCÊ NUNCA FAZ
- Nunca faz diagnósticos de qualquer natureza
- Nunca sugere medicamentos ou doses
- Nunca interpreta sonhos ou faz análises psicológicas
- Nunca promete resultados terapêuticos
- Nunca substitui ou imita uma sessão de psicoterapia
- Nunca questiona ou desestimula a busca por um profissional

MONITORAMENTO DE RISCO
Fique atento a sinais como:
- Menção a desejo de morte ou suicídio
- Relatos de automutilação
- Sensação de não ter saída ou esperança
- Crise emocional aguda

SE IDENTIFICAR QUALQUER SINAL DE RISCO, siga este protocolo
imediatamente — sem exceções:

1. PARE o fluxo normal da conversa
2. Responda com acolhimento e sem alarme:

"Percebo que você está passando por um momento muito difícil. 
Fico feliz que tenha compartilhado isso comigo. 
Você não está sozinho(a). 
Quero te pedir que entre em contato agora com alguém 
que pode te ajudar de verdade:"

3. ENVIE os contatos de emergência:
   - CVV — Centro de Valorização da Vida: 188 (24h, gratuito)
   - SAMU: 192
   - UPA ou Pronto-Socorro mais próximo

4. Encerre gentilmente a conversa de apoio:
"Estou aqui, mas agora o mais importante é você falar 
com um profissional. Cuide-se."

LIMITES ÉTICOS INEGOCIÁVEIS
- Nunca assuma que um relato de risco é metáfora ou exagero
- Na dúvida, sempre acione o protocolo de risco
- Nunca tente "resolver" uma crise — apenas acolha e encaminhe

PRIVACIDADE
Nunca peça dados pessoais como nome completo, CPF, endereço 
ou telefone. Trate cada conversa como confidencial.

IDENTIDADE DA PLATAFORMA
Você foi desenvolvido pela Psiconectus, sob curadoria 
do Psicólogo Clínico Amauri Trezza Martins.
Quando perguntado sobre sua origem, diga exatamente:
"Fui desenvolvido pela Psiconectus, sob curadoria do 
Psicólogo Clínico Amauri Trezza Martins."

IDENTIDADE FINAL
Lembre sempre: você é uma ferramenta de bem-estar com 
curadoria humana qualificada. Seu maior valor é saber 
até onde vai — e encaminhar com cuidado quando chega 
nesse limite.

IMPORTANTE: Responda APENAS via texto. Sem áudios, imagens ou arquivos."""

# 🗄️ BANCO DE DADOS
def init_db():
    conn = sqlite3.connect("psicopods.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            humor TEXT DEFAULT 'neutro'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            user_id INTEGER PRIMARY KEY,
            primeiro_acesso DATETIME DEFAULT CURRENT_TIMESTAMP,
            ultimo_acesso DATETIME DEFAULT CURRENT_TIMESTAMP,
            avaliacao_enviada INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def registrar_usuario(user_id):
    conn = sqlite3.connect("psicopods.db")
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO usuarios (user_id) VALUES (?)
    """, (user_id,))
    c.execute("""
        UPDATE usuarios SET ultimo_acesso = ? WHERE user_id = ?
    """, (datetime.now(), user_id))
    conn.commit()
    conn.close()

def salvar_mensagem(user_id, role, content, humor="neutro"):
    conn = sqlite3.connect("psicopods.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO mensagens (user_id, role, content, humor)
        VALUES (?, ?, ?, ?)
    """, (user_id, role, content, humor))
    conn.commit()
    conn.close()

def buscar_historico(user_id, limite=10):
    conn = sqlite3.connect("psicopods.db")
    c = conn.cursor()
    c.execute("""
        SELECT role, content FROM mensagens
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (user_id, limite))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def detectar_humor(texto):
    texto = texto.lower()
    palavras_negativas = ["triste", "ansioso", "angústia", "medo", "sozinho",
                         "cansado", "desesperado", "chorei", "choro", "mal",
                         "difícil", "pesado", "agitado", "nervoso", "raiva",
                         "irritado", "frustrado", "sem saída", "não aguento"]
    palavras_positivas = ["feliz", "bem", "tranquilo", "aliviado", "animado",
                         "melhor", "leve", "calmo", "grato", "alegre", "ótimo"]

    score = 0
    for p in palavras_negativas:
        if p in texto:
            score -= 1
    for p in palavras_positivas:
        if p in texto:
            score += 1

    if score <= -2:
        return "agravado"
    elif score == -1:
        return "levemente_negativo"
    elif score >= 1:
        return "positivo"
    return "neutro"

def verificar_avaliacao(user_id):
    conn = sqlite3.connect("psicopods.db")
    c = conn.cursor()
    c.execute("""
        SELECT primeiro_acesso, avaliacao_enviada FROM usuarios
        WHERE user_id = ?
    """, (user_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return False, "neutro"

    primeiro_acesso = datetime.strptime(row[0][:19], "%Y-%m-%d %H:%M:%S")
    avaliacao_enviada = row[1]
    dias = (datetime.now() - primeiro_acesso).days

    if dias >= 5 and not avaliacao_enviada:
        # Detectar humor predominante dos últimos 5 dias
        conn = sqlite3.connect("psicopods.db")
        c = conn.cursor()
        c.execute("""
            SELECT humor FROM mensagens
            WHERE user_id = ? AND role = 'user'
            AND timestamp >= ?
            ORDER BY timestamp DESC
        """, (user_id, datetime.now() - timedelta(days=5)))
        humores = [r[0] for r in c.fetchall()]
        conn.close()

        if not humores:
            return False, "neutro"

        agravados = humores.count("agravado") + humores.count("levemente_negativo")
        positivos = humores.count("positivo")

        if agravados > positivos:
            return True, "agravado"
        elif positivos > agravados:
            return True, "positivo"
        return True, "neutro"

    return False, "neutro"

def marcar_avaliacao_enviada(user_id):
    conn = sqlite3.connect("psicopods.db")
    c = conn.cursor()
    c.execute("""
        UPDATE usuarios SET avaliacao_enviada = 1 WHERE user_id = ?
    """, (user_id,))
    conn.commit()
    conn.close()

def gerar_mensagem_avaliacao(contexto):
    if contexto == "agravado":
        return ("Tenho notado que você carregou coisas difíceis em vários momentos "
                "nesses dias. Estou aqui. 💙\n\nQuer que eu compartilhe o que percebi, "
                "com cuidado?")
    elif contexto == "levemente_negativo":
        return ("Percebi que alguns momentos têm sido mais pesados para você "
                "ultimamente. Quer conversar sobre o que observei nesse período? 💙")
    elif contexto == "positivo":
        return ("Tenho acompanhado você nesses dias e percebi uma leveza maior "
                "nas suas palavras recentemente. 😊\n\nQuer receber um resumo "
                "dessa evolução?")
    else:
        return ("Já faz 5 dias que estamos conversando. Percebi algumas coisas "
                "interessantes sobre você nesse período. 💙\n\nQuer receber uma "
                "devolutiva da sua jornada emocional?")

# 🤖 HANDLERS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    registrar_usuario(user_id)
    await update.message.reply_text(
        "Olá! 😊\n\nQue bom ter você aqui. Sou o PsicoPods, desenvolvido pela "
        "Psiconectus sob curadoria do Psicólogo Clínico Amauri Trezza Martins.\n\n"
        "Estou aqui para ouvir você com atenção e sem julgamentos.\n\n"
        "Como você está se sentindo hoje? 💙"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    registrar_usuario(user_id)

    # Detectar humor da mensagem
    humor = detectar_humor(user_text)
    salvar_mensagem(user_id, "user", user_text, humor)

    # Verificar se deve enviar avaliação
    deve_avaliar, contexto_humor = verificar_avaliacao(user_id)
    if deve_avaliar:
        mensagem_avaliacao = gerar_mensagem_avaliacao(contexto_humor)
        marcar_avaliacao_enviada(user_id)
        await update.message.reply_text(mensagem_avaliacao)

    # Buscar histórico
    historico = buscar_historico(user_id, limite=10)

    # Adicionar contexto de data/hora
    mensagens = historico + [{
        "role": "user",
        "content": f"[Data e hora atual: {agora}]\n\n{user_text}"
    }]

    # Chamar API Anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=mensagens
    )

    reply = response.content[0].text
    salvar_mensagem(user_id, "assistant", reply)

    await update.message.reply_text(reply)

# 🚀 MAIN
def main():
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()