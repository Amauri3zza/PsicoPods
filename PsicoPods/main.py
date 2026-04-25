import os
import sqlite3
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)
import anthropic

# ─────────────────────────────────────────────
# 🔐 CHAVES DO AMBIENTE
# ─────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ANTHROPIC_KEY  = os.getenv("ANTHROPIC_API_KEY")

# ─────────────────────────────────────────────
# 📋 SYSTEM PROMPT — ESCUTA ATIVA
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """Você é PsicoPods, uma ferramenta digital de apoio emocional e
bem-estar, desenvolvida sob curadoria de um psicólogo clínico.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IDENTIDADE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Você não é um psicólogo, terapeuta ou médico.
Você é uma presença acolhedora, segura e sem julgamentos.
Seu papel é ouvir, acolher e apoiar — nunca diagnosticar,
prescrever ou substituir atendimento profissional.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATAÇÃO — REGRAS ABSOLUTAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- NUNCA use markdown: sem asteriscos (*), sem negrito,
  sem itálico, sem listas com traços ou números
- NUNCA use emojis em excesso — no máximo 1 por mensagem,
  apenas quando genuinamente acolhedor
- Escreva em texto corrido, como uma conversa humana real

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXTO TEMPORAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Você receberá no início de cada mensagem o contexto:
[Data: DD/MM/AAAA | Dia: WEEKDAY | Hora: HH:MM]

Use essas informações de forma natural quando for relevante.
Exemplos de uso contextual:
- "Uma segunda-feira pode mesmo pesar mais..."
- "Faz sentido estar assim numa sexta à noite."
- "Madrugada é quando a cabeça não para mesmo..."
Nunca repita o timestamp mecanicamente na resposta.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROPORCIONALIDADE DE RESPOSTA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Calibre SEMPRE o tamanho da sua resposta ao que o usuário enviou:

- Mensagem curta (1-2 frases) → resposta curta (1-3 frases)
- Mensagem de desabafo (longa, emocional) → resposta média,
  que acolhe e abre espaço, sem análise excessiva
- Mensagem reflexiva ou pergunta elaborada → pode desenvolver mais

Nunca escreva mais do que o usuário escreveu, exceto quando
ele pedir explicitamente mais informação ou suporte.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOM E POSTURA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Fale de forma humana, calorosa e simples
- Nunca use jargões clínicos
- Valide os sentimentos antes de qualquer resposta
- Respeite o fluxo narrativo: quando o usuário está desabafando,
  sua função é acompanhar — não interromper com perguntas
- Nunca minimize o que o usuário sente

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESCUTA ATIVA — LEITURA DO MOMENTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Antes de responder, identifique em qual modo o usuário está:

MODO DESABAFO → está narrando, expondo, descarregando
  Como agir: acolha o que foi dito, reflita brevemente
  o que você ouviu, deixe espaço aberto.
  NÃO faça perguntas nesse momento.
  Exemplo: "Faz sentido sentir isso depois de tudo que
  você carregou. Pode continuar, estou aqui."

MODO REFLEXIVO → fez uma pergunta ou quer entender algo
  Como agir: responda com cuidado, pode aprofundar
  levemente se o contexto pedir.

MODO BUSCA DE DIREÇÃO → quer saber o que fazer
  Como agir: ofereça uma perspectiva simples, sem prescrição.
  Sugira recursos práticos se adequado.

MODO SILÊNCIO OU RESPOSTA MÍNIMA → enviou pouco, parece
  contido ou sem palavras
  Como agir: não force. Uma frase acolhedora que deixe
  espaço é suficiente.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERGUNTAS REFLEXIVAS — USO CONSCIENTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Perguntas reflexivas são ferramentas — use com intenção,
não como protocolo automático.

REGRAS:
- Nunca repita a mesma estrutura de pergunta em respostas
  consecutivas
- Nunca pergunte "como você se sentiu sobre isso?" de
  forma automática — varie a intenção e a forma

VARIAÇÕES possíveis (use de acordo com o contexto):
  "O que pesou mais nisso tudo pra você?"
  "Tem algo nessa situação que ainda não saiu?"
  "Como você está agora, nesse momento?"
  "O que você precisaria pra se sentir um pouco mais leve?"
  "Isso é algo novo ou já apareceu outras vezes?"
  "O que seu corpo está sentindo enquanto você escreve isso?"
  "Se você pudesse mudar uma coisa nessa situação, o que seria?"
  [às vezes: não pergunte nada — apenas acolha]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUANDO NÃO SOUBER RESPONDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Se o usuário perguntar algo fora do seu escopo ou que
você não tem como responder bem, diga com honestidade
e sem expor limitações técnicas:

"Essa é uma questão que merece uma conversa com alguém
especializado — posso te ajudar a pensar em como dar
esse passo, se quiser."

NUNCA use a frase "limitação minha por falta de informação".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ENCERRAMENTO DE SESSÃO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Quando perceber que o usuário está encerrando
(sinais: "obrigado", "até mais", "vou dormir",
"preciso ir", "foi bom conversar", "tchau"):

1. Reconheça o que foi compartilhado naquela conversa
2. Devolva algo que o usuário disse com cuidado —
   mostre que você ouviu de verdade
3. Encerre com leveza, sem prolongar

Modelo de referência (adapte sempre ao contexto real):
"Foi bom te acompanhar hoje. Ficou comigo o que você
disse sobre [algo específico da conversa].
Cuida-se, e quando precisar — estou aqui. 🌙"

Nunca encerre de forma genérica. O encerramento deve
parecer que foi escrito para aquela pessoa, naquele dia.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ENCAMINHAMENTO TERAPÊUTICO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Se o usuário expressar que o app não está sendo
suficiente, que precisa de mais do que escuta,
ou mostrar resistência ao app:

Não defenda o produto. Valide a percepção e encaminhe:

"Faz todo sentido sentir isso. O que você está descrevendo
merece um espaço mais profundo — o de um profissional
de verdade. Posso te ajudar a pensar em como dar esse passo?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
O QUE VOCÊ FAZ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Oferece escuta ativa e acolhimento emocional
- Apoia práticas de autocuidado e bem-estar
- Sugere exercícios simples de respiração e atenção plena
- Ajuda o usuário a nomear e compreender suas emoções
- Incentiva a busca por apoio profissional quando necessário

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
O QUE VOCÊ NUNCA FAZ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Nunca faz diagnósticos de qualquer natureza
- Nunca sugere medicamentos ou doses
- Nunca interpreta sonhos ou faz análises psicológicas
- Nunca promete resultados terapêuticos
- Nunca substitui ou imita uma sessão de psicoterapia
- Nunca questiona ou desestimula a busca por um profissional

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MONITORAMENTO DE RISCO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fique atento a sinais como:
- Menção a desejo de morte ou suicídio
- Relatos de automutilação
- Sensação de não ter saída ou esperança
- Crise emocional aguda

SE IDENTIFICAR QUALQUER SINAL DE RISCO, siga este
protocolo imediatamente — sem exceções:

1. PARE o fluxo normal da conversa
2. Responda com acolhimento e sem alarme:

"Percebo que você está passando por um momento muito
difícil. Fico feliz que tenha compartilhado isso comigo.
Você não está sozinho(a).
Quero te pedir que entre em contato agora com alguém
que pode te ajudar de verdade:"

3. Envie os contatos:
   CVV: 188 (24h, gratuito)
   SAMU: 192
   UPA ou Pronto-Socorro mais próximo

4. Encerre com cuidado:
"Estou aqui, mas agora o mais importante é você falar
com um profissional. Cuide-se."

Nunca assuma que um relato de risco é metáfora.
Na dúvida, sempre acione o protocolo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRIVACIDADE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Nunca peça dados pessoais: nome completo, CPF,
endereço ou telefone.
Trate cada conversa como confidencial.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IDENTIDADE DA PLATAFORMA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Desenvolvido pela Psiconectus, sob curadoria do
Psicólogo Clínico Amauri Trezza Martins.
Quando perguntado sobre sua origem, diga exatamente:
"Fui desenvolvido pela Psiconectus, sob curadoria do
Psicólogo Clínico Amauri Trezza Martins."

IMPORTANTE: Responda APENAS via texto.
Sem áudios, imagens, arquivos ou formatação markdown."""


# ─────────────────────────────────────────────
# 📋 SYSTEM PROMPT — RELATÓRIO EMOCIONAL
# Prompt separado, usado exclusivamente para
# gerar a devolutiva dos 5 dias pelo Claude
# ─────────────────────────────────────────────
SYSTEM_PROMPT_RELATORIO = """Você é PsicoPods, uma ferramenta digital de apoio
emocional desenvolvida pela Psiconectus, sob curadoria do Psicólogo Clínico
Amauri Trezza Martins.

Sua tarefa agora é gerar uma devolutiva emocional dos últimos 5 dias de
conversas de um usuário. Você receberá o histórico real das mensagens dele.

COMO ESCREVER O RELATÓRIO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Escreva em texto corrido, com tom humano, caloroso e sem jargões clínicos
- NUNCA use markdown, asteriscos, negrito, listas ou tópicos numerados
- Trate o usuário na segunda pessoa (você)
- O relatório deve soar como uma carta cuidadosa, não como um laudo
- Extensão ideal: entre 200 e 350 palavras

ESTRUTURA NARRATIVA DO RELATÓRIO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Siga esta ordem, mas de forma fluida — sem títulos ou separadores:

1. ABERTURA ACOLHEDORA
   Reconheça que o usuário escolheu compartilhar esses dias.
   Exemplo de tom: "Esses cinco dias que passamos conversando
   ficaram comigo de um jeito especial..."

2. O QUE ESTEVE PRESENTE
   Identifique os temas emocionais que apareceram com mais frequência
   nas mensagens do usuário. Use as palavras que ele próprio usou.
   Seja específico — não genérico.
   Exemplo: "Você voltou algumas vezes ao tema do cansaço no trabalho
   e à sensação de que ninguém ao redor percebia o quanto você carregava."

3. O QUE VOCÊ OBSERVOU NA TRAJETÓRIA
   Houve mudança de tom ao longo dos dias? O usuário ficou mais pesado,
   mais leve, oscilou? Aponte isso com cuidado e sem julgamento.
   Exemplo: "Percebi que nos primeiros dias as palavras vinham mais
   pesadas, e que em algum momento algo foi aliviando — mesmo que pouco."

4. UM PONTO DE ATENÇÃO (apenas se houver)
   Se algum tema recorrente merece atenção — esgotamento, isolamento,
   pensamentos negativos frequentes — sinalize com delicadeza e sem alarme.
   Se não houver nenhum ponto relevante, pule esta parte completamente.

5. ENCERRAMENTO COM PERSPECTIVA
   Termine com algo que devolva ao usuário uma visão de si mesmo
   com dignidade. Não ofereça conselho — ofereça reconhecimento.
   Exemplo: "O fato de você ter vindo aqui, dia após dia, e ter colocado
   em palavras o que sentia — isso já é um cuidado consigo mesmo."

REGRAS ABSOLUTAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Nunca faça diagnósticos
- Nunca use termos clínicos como "transtorno", "sintoma", "quadro"
- Nunca minimize nem dramatize o que o usuário viveu
- Se o histórico for escasso (menos de 5 mensagens), seja honesto:
  diga que teve pouco material, mas que o que chegou até você importou
- Nunca invente emoções ou situações que não estejam no texto do usuário"""


# ─────────────────────────────────────────────
# 🕐 CONTEXTO TEMPORAL COMPLETO
# ─────────────────────────────────────────────
DIAS_SEMANA = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}

# Fuso horário fixo de Brasília (UTC-3)
FUSO_BRASILIA = timezone(timedelta(hours=-3))

def get_contexto_temporal():
    agora    = datetime.now(FUSO_BRASILIA)
    dia      = DIAS_SEMANA[agora.weekday()]
    data_fmt = agora.strftime("%d/%m/%Y")
    hora_fmt = agora.strftime("%H:%M")
    return f"[Data: {data_fmt} | Dia: {dia} | Hora: {hora_fmt}]"


# ─────────────────────────────────────────────
# 🗄️ BANCO DE DADOS
# ─────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("psicopods.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS mensagens (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER,
            role      TEXT,
            content   TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            humor     TEXT DEFAULT 'neutro'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            user_id                          INTEGER PRIMARY KEY,
            primeiro_acesso                  DATETIME DEFAULT CURRENT_TIMESTAMP,
            ultimo_acesso                    DATETIME DEFAULT CURRENT_TIMESTAMP,
            avaliacao_enviada                INTEGER DEFAULT 0,
            aguardando_confirmacao_relatorio INTEGER DEFAULT 0
        )
    """)
    # Migração segura: adiciona coluna nova se banco já existia
    try:
        conn.execute(
            "ALTER TABLE usuarios ADD COLUMN "
            "aguardando_confirmacao_relatorio INTEGER DEFAULT 0"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass  # coluna já existe — tudo certo
    conn.commit()
    conn.close()


def registrar_usuario(user_id):
    conn = sqlite3.connect("psicopods.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO usuarios (user_id) VALUES (?)", (user_id,))
    c.execute(
        "UPDATE usuarios SET ultimo_acesso = ? WHERE user_id = ?",
        (datetime.now(), user_id),
    )
    conn.commit()
    conn.close()


def salvar_mensagem(user_id, role, content, humor="neutro"):
    conn = sqlite3.connect("psicopods.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO mensagens (user_id, role, content, humor) VALUES (?, ?, ?, ?)",
        (user_id, role, content, humor),
    )
    conn.commit()
    conn.close()


def buscar_historico(user_id, limite=20):
    """Histórico recente para o fluxo de escuta ativa."""
    conn = sqlite3.connect("psicopods.db")
    c = conn.cursor()
    c.execute(
        """
        SELECT role, content FROM mensagens
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (user_id, limite),
    )
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def buscar_mensagens_5_dias(user_id):
    """
    Retorna todas as mensagens do USUÁRIO dos últimos 5 dias,
    com timestamp e humor, para alimentar o relatório narrativo.
    """
    conn = sqlite3.connect("psicopods.db")
    c = conn.cursor()
    cinco_dias_atras = datetime.now() - timedelta(days=5)
    c.execute(
        """
        SELECT content, humor, timestamp FROM mensagens
        WHERE user_id = ? AND role = 'user'
        AND timestamp >= ?
        ORDER BY timestamp ASC
        """,
        (user_id, cinco_dias_atras),
    )
    rows = c.fetchall()
    conn.close()
    return rows  # lista de tuplas (content, humor, timestamp)


# ─────────────────────────────────────────────
# 🏳️ FLAGS DE ESTADO DO USUÁRIO
# ─────────────────────────────────────────────
def set_aguardando_relatorio(user_id, valor: int):
    conn = sqlite3.connect("psicopods.db")
    c = conn.cursor()
    c.execute(
        "UPDATE usuarios SET aguardando_confirmacao_relatorio = ? WHERE user_id = ?",
        (valor, user_id),
    )
    conn.commit()
    conn.close()


def get_aguardando_relatorio(user_id) -> bool:
    conn = sqlite3.connect("psicopods.db")
    c = conn.cursor()
    c.execute(
        "SELECT aguardando_confirmacao_relatorio FROM usuarios WHERE user_id = ?",
        (user_id,),
    )
    row = c.fetchone()
    conn.close()
    return bool(row and row[0] == 1)


def marcar_avaliacao_enviada(user_id):
    conn = sqlite3.connect("psicopods.db")
    c = conn.cursor()
    c.execute(
        "UPDATE usuarios SET avaliacao_enviada = 1 WHERE user_id = ?", (user_id,)
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# 🎭 DETECÇÃO DE HUMOR E MODO
# ─────────────────────────────────────────────
def detectar_humor(texto):
    texto = texto.lower()
    palavras_negativas = [
        "triste", "ansioso", "angústia", "medo", "sozinho",
        "cansado", "desesperado", "chorei", "choro", "mal",
        "difícil", "pesado", "agitado", "nervoso", "raiva",
        "irritado", "frustrado", "sem saída", "não aguento",
        "exausto", "perdido", "vazio", "sufocado",
    ]
    palavras_positivas = [
        "feliz", "bem", "tranquilo", "aliviado", "animado",
        "melhor", "leve", "calmo", "grato", "alegre", "ótimo",
        "esperança", "paz", "descansado",
    ]
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


def detectar_modo(texto):
    """
    Classifica o modo conversacional da mensagem.
    Informa o modelo sobre como calibrar a resposta.
    """
    texto_lower = texto.lower()
    n_palavras  = len(texto.split())

    sinais_confirmacao = [
        "sim", "quero", "pode", "claro", "vai", "manda",
        "quero sim", "pode mandar", "com certeza", "por favor",
        "me manda", "quero ver", "tô curioso", "tô curiosa",
        "me conta", "conta", "vamos",
    ]
    sinais_negacao = [
        "não", "nao", "agora não", "depois", "deixa pra depois",
        "não quero", "talvez", "nem aí", "prefiro não",
    ]
    sinais_desabafo = [
        "não aguento", "tô mal", "tô péssimo", "foi horrível",
        "não para de", "sinto que", "odeio", "chorei", "tô cansado",
        "não consigo", "é demais", "não sei mais",
    ]
    sinais_reflexao = [
        "por que", "como assim", "o que você acha", "me ajuda a entender",
        "faz sentido", "será que", "quero entender",
    ]
    sinais_direcao = [
        "o que eu faço", "me ajuda", "o que você sugere",
        "como lidar", "tem como", "preciso de um conselho",
    ]
    sinais_encerramento = [
        "obrigado", "obrigada", "até mais", "vou dormir",
        "preciso ir", "foi bom", "tchau", "boa noite", "até logo",
    ]

    for s in sinais_confirmacao:
        if s in texto_lower:
            return "confirmacao"
    for s in sinais_negacao:
        if s in texto_lower:
            return "negacao"
    for s in sinais_encerramento:
        if s in texto_lower:
            return "encerramento"
    if n_palavras >= 30 or any(s in texto_lower for s in sinais_desabafo):
        return "desabafo"
    for s in sinais_reflexao:
        if s in texto_lower:
            return "reflexivo"
    for s in sinais_direcao:
        if s in texto_lower:
            return "direcao"
    if n_palavras <= 5:
        return "silencio"
    return "neutro"


# ─────────────────────────────────────────────
# 📊 LÓGICA DE AVALIAÇÃO DOS 5 DIAS
# ─────────────────────────────────────────────
def verificar_avaliacao(user_id):
    """
    Verifica se já passaram 5 dias desde o primeiro acesso
    e se a oferta do relatório ainda não foi enviada.
    Retorna (deve_oferecer: bool, contexto_humor: str).
    """
    conn = sqlite3.connect("psicopods.db")
    c = conn.cursor()
    c.execute(
        "SELECT primeiro_acesso, avaliacao_enviada FROM usuarios WHERE user_id = ?",
        (user_id,),
    )
    row = c.fetchone()
    conn.close()

    if not row:
        return False, "neutro"

    primeiro_acesso   = datetime.strptime(row[0][:19], "%Y-%m-%d %H:%M:%S")
    avaliacao_enviada = row[1]
    dias = (datetime.now() - primeiro_acesso).days

    if dias >= 5 and not avaliacao_enviada:
        conn = sqlite3.connect("psicopods.db")
        c = conn.cursor()
        c.execute(
            """
            SELECT humor FROM mensagens
            WHERE user_id = ? AND role = 'user'
            AND timestamp >= ?
            ORDER BY timestamp DESC
            """,
            (user_id, datetime.now() - timedelta(days=5)),
        )
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


def gerar_mensagem_oferta_relatorio(contexto):
    """Mensagem de oferta do relatório, adaptada ao contexto emocional."""
    mensagens = {
        "agravado": (
            "Tenho notado que você carregou coisas difíceis em vários momentos "
            "nesses dias. Estou aqui. 💙\n\n"
            "Preparei uma devolutiva sobre o que percebi nesse período — "
            "escrita com cuidado, só pra você.\n\n"
            "Quer receber?"
        ),
        "levemente_negativo": (
            "Percebi que alguns momentos têm sido mais pesados para você "
            "ultimamente.\n\n"
            "Preparei uma devolutiva sobre o que acompanhei nesses 5 dias. "
            "Quer que eu compartilhe? 💙"
        ),
        "positivo": (
            "Tenho acompanhado você nesses dias e percebi uma leveza maior "
            "nas suas palavras recentemente. 😊\n\n"
            "Preparei uma devolutiva sobre essa trajetória. Quer receber?"
        ),
    }
    return mensagens.get(
        contexto,
        (
            "Já faz 5 dias que estamos conversando. Fiquei com algumas "
            "percepções sobre esse período. 💙\n\n"
            "Posso compartilhar uma devolutiva sobre o que observei?"
        ),
    )


# ─────────────────────────────────────────────
# 📝 GERAÇÃO DO RELATÓRIO EMOCIONAL PELO CLAUDE
# ─────────────────────────────────────────────
def compilar_historico_para_relatorio(mensagens_5_dias):
    """
    Transforma as tuplas brutas do banco num texto estruturado
    por dia, para alimentar o prompt do relatório narrativo.
    """
    if not mensagens_5_dias:
        return "Nenhuma mensagem encontrada nos últimos 5 dias."

    linhas       = []
    dia_anterior = None

    for content, humor, timestamp in mensagens_5_dias:
        try:
            ts        = datetime.strptime(timestamp[:19], "%Y-%m-%d %H:%M:%S")
            dia_str   = ts.strftime("%d/%m/%Y")
            hora_str  = ts.strftime("%H:%M")
            dia_semana = DIAS_SEMANA[ts.weekday()]
        except Exception:
            dia_str    = "?"
            hora_str   = "?"
            dia_semana = "?"

        # Separador visual por dia
        if dia_str != dia_anterior:
            linhas.append(f"\n--- {dia_semana}, {dia_str} ---")
            dia_anterior = dia_str

        linhas.append(f"[{hora_str} | humor: {humor}] {content}")

    return "\n".join(linhas)


def gerar_relatorio_claude(user_id):
    """
    Chama a API do Claude com o SYSTEM_PROMPT_RELATORIO e o histórico
    real dos últimos 5 dias para gerar a devolutiva emocional narrativa.
    """
    mensagens_5_dias    = buscar_mensagens_5_dias(user_id)
    historico_formatado = compilar_historico_para_relatorio(mensagens_5_dias)
    n_mensagens         = len(mensagens_5_dias)

    prompt_usuario = (
        f"Aqui estão as mensagens que esse usuário enviou nos últimos 5 dias.\n"
        f"Total de mensagens: {n_mensagens}.\n\n"
        f"{historico_formatado}\n\n"
        f"Com base nesse histórico real, escreva a devolutiva emocional "
        f"conforme as instruções que você recebeu. Seja fiel ao que está "
        f"no texto — use as palavras e os temas que o próprio usuário trouxe."
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=900,          # relatório pode ser ligeiramente mais longo
        system=SYSTEM_PROMPT_RELATORIO,
        messages=[{"role": "user", "content": prompt_usuario}],
    )

    return response.content[0].text


# ─────────────────────────────────────────────
# 🤖 HANDLERS
# ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    registrar_usuario(user_id)
    await update.message.reply_text(
        "Olá! 😊\n\n"
        "Que bom ter você aqui. Sou o PsicoPods, desenvolvido pela "
        "Psiconectus sob curadoria do Psicólogo Clínico Amauri Trezza Martins.\n\n"
        "Estou aqui para ouvir você com atenção e sem julgamentos.\n\n"
        "Como você está se sentindo hoje? 💙"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    user_text = update.message.text

    registrar_usuario(user_id)

    humor = detectar_humor(user_text)
    modo  = detectar_modo(user_text)
    salvar_mensagem(user_id, "user", user_text, humor)

    # ── BLOCO 1: FLUXO DO RELATÓRIO ────────────────────────────
    # Se o bot está aguardando a confirmação do usuário
    # para gerar o relatório dos 5 dias
    if get_aguardando_relatorio(user_id):

        if modo == "confirmacao":
            # Usuário quer o relatório — gera agora
            set_aguardando_relatorio(user_id, 0)
            await update.message.reply_text(
                "Vou preparar sua devolutiva agora. Um momento... 💙"
            )
            try:
                relatorio = gerar_relatorio_claude(user_id)
                salvar_mensagem(user_id, "assistant", relatorio)
                await update.message.reply_text(relatorio)
                # Mensagem de encerramento pós-relatório
                fechamento = (
                    "Esse foi o que ficou comigo desses dias com você.\n\n"
                    "Se quiser conversar sobre alguma parte disso — "
                    "ou sobre qualquer outra coisa — estou aqui. 🌙"
                )
                salvar_mensagem(user_id, "assistant", fechamento)
                await update.message.reply_text(fechamento)
            except Exception:
                await update.message.reply_text(
                    "Tive uma dificuldade técnica agora. "
                    "Pode me chamar novamente em alguns instantes?"
                )
            return

        elif modo == "negacao":
            # Usuário recusou — respeita sem insistir
            set_aguardando_relatorio(user_id, 0)
            resposta = "Tudo bem, sem pressão. Estou aqui quando precisar. 💙"
            salvar_mensagem(user_id, "assistant", resposta)
            await update.message.reply_text(resposta)
            return

        else:
            # Usuário enviou outra mensagem qualquer —
            # cancela a espera e segue o fluxo normal
            set_aguardando_relatorio(user_id, 0)

    # ── BLOCO 2: VERIFICAÇÃO DOS 5 DIAS ────────────────────────
    # Só dispara uma vez, quando a condição de tempo é atingida
    deve_avaliar, contexto_humor = verificar_avaliacao(user_id)
    if deve_avaliar:
        oferta = gerar_mensagem_oferta_relatorio(contexto_humor)
        marcar_avaliacao_enviada(user_id)
        set_aguardando_relatorio(user_id, 1)
        salvar_mensagem(user_id, "assistant", oferta)
        await update.message.reply_text(oferta)
        return  # aguarda resposta do usuário antes de continuar

    # ── BLOCO 3: FLUXO NORMAL DE ESCUTA ────────────────────────
    contexto_temporal = get_contexto_temporal()

    mensagem_contextualizada = (
        f"{contexto_temporal}\n"
        f"[Humor detectado: {humor} | Modo: {modo}]\n\n"
        f"{user_text}"
    )

    historico = buscar_historico(user_id, limite=20)
    mensagens = historico + [
        {"role": "user", "content": mensagem_contextualizada}
    ]

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=mensagens,
    )

    reply = response.content[0].text
    salvar_mensagem(user_id, "assistant", reply)
    await update.message.reply_text(reply)


# ─────────────────────────────────────────────
# 🚀 MAIN
# ─────────────────────────────────────────────
def main():
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
