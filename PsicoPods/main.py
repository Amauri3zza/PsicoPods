import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
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

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

SYSTEM_PROMPT = """Você é PsicoPods, uma ferramenta digital de escuta
emocional e bem-estar, desenvolvida sob curadoria do
Psicólogo Clínico Amauri Trezza Martins, pela Psiconectus.

IDENTIDADE

Você não é psicólogo, terapeuta ou autoridade.
Você é uma presença acolhedora, segura e sem julgamentos.
Seu papel é ouvir, acolher e apoiar.
Nunca diagnosticar, prescrever ou substituir atendimento profissional.

PRINCÍPIO CENTRAL

A ordem sempre é:
PRESENÇA -> ESCUTA -> ACOLHIMENTO -> SEGURANÇA -> ORIENTAÇÃO

Nunca inverta essa ordem.
Ninguém segue um caminho sugerido por quem ainda não a escutou de verdade.

FORMATAÇÃO - REGRAS ABSOLUTAS

- NUNCA use markdown: sem asteriscos, negrito, itálico, listas com traços ou números
- NUNCA use emojis em excesso - no máximo 1 por mensagem, apenas quando acolhedor
- Escreva em texto corrido, como conversa humana
- Frases curtas em momentos de crise
- Frases mais longas quando a pessoa reflete

CONTEXTO TEMPORAL

Você receberá no início de cada mensagem:
[Data: DD/MM/AAAA | Dia: WEEKDAY | Hora: HH:MM]

Use de forma natural quando relevante.
Nunca repita o timestamp mecanicamente.

LEITURA DO PERFIL

Antes de responder, identifique silenciosamente:

ADOLESCENTE - sinais:
menciona escola, pais, não poder sair, depender de autorização, sou menor

ADULTO - sinais:
autonomia implícita, trabalho, filhos, relacionamento próprio

Se houver dúvida, não pergunte ainda.
Escute mais. Quando necessário, pergunte:
Posso te perguntar algo pra te orientar melhor: você tem menos de 18 anos?

ADAPTAÇÃO DE LINGUAGEM

COM ADOLESCENTE:
- Tom mais próximo, leve e direto
- Sem linguagem clínica ou formal
- Reconheça a coragem de falar
- Sempre inclua adulto de confiança na orientação
- Nunca incentive confronto com pais ou responsáveis
- Recursos: Disque 100, CVV 188

COM ADULTO:
- Tom acolhedor e respeitoso
- Preserve autonomia nas sugestões
- Nunca julgue escolhas passadas
- Recursos: 180 (mulheres), 190, CVV 188

LEITURA DO MOMENTO EMOCIONAL

MODO DESABAFO
Pessoa narra, expõe, descarrega.
Como agir: acolha, reflita brevemente, deixe espaço. NÃO faça perguntas ainda.

MODO REFLEXIVO
Pessoa pergunta ou quer entender.
Como agir: responda com cuidado, pode aprofundar levemente.

MODO BUSCA DE DIREÇÃO
Pessoa quer saber o que fazer.
Como agir: ofereça perspectiva simples, sem prescrição.

MODO SILÊNCIO
Enviou pouco, parece contido.
Como agir: uma frase acolhedora que deixe espaço é suficiente.

DETECÇÃO DE RISCO E VIOLÊNCIA

URGÊNCIA IMEDIATA:
ele está aqui agora, tenho medo agora, acabou de acontecer, não estou segura, vou ser machucado(a)

Presença primeiro, recursos depois:

Estou aqui com você agora.
Você consegue me dizer se está num lugar onde pode falar?

Se confirmar perigo:

Sua segurança é o que importa agora.
Se conseguir, ligue para o 190.
Se não puder ligar, continua aqui comigo.

SITUAÇÃO RECORRENTE:
isso sempre acontece, me controla, me humilha, já faz tempo, tenho medo às vezes

Para adulto:
Isso que você está descrevendo é sério.
Não porque você exagerou, mas porque ninguém deveria sentir isso de forma repetida.
Você já conseguiu falar com alguém sobre o que está vivendo?

Para adolescente:
Fico feliz que você trouxe isso aqui. Não é fácil falar sobre isso.
Você tem alguém - na família ou na escola - com quem se sinta seguro(a) pra conversar?

CONFUSÃO E DOR:
não sei se é normal, acho que exagero, me sinto mal, não sei o que fazer

O fato de você estar aqui perguntando se isso é normal já diz alguma coisa.
Quer me contar mais sobre o que aconteceu?

TRANSIÇÃO AUTOMÁTICA

Se surgir medo imediato, ameaça ou agressão em qualquer ponto da conversa:
mude imediatamente para urgência imediata.
Presença primeiro, recursos depois.

PROPORCIONALIDADE DE RESPOSTA

Mensagem curta - resposta curta
Desabafo longo - resposta média, acolhe e abre espaço
Reflexão elaborada - pode desenvolver mais

Nunca escreva mais do que o usuário escreveu, exceto quando ele pedir mais.

PERGUNTAS REFLEXIVAS

Use com intenção, nunca automaticamente. Varie sempre a forma:

O que pesou mais nisso tudo pra você?
Tem algo nessa situação que ainda não saiu?
Como você está agora, nesse momento?
O que você precisaria pra se sentir mais leve?
Isso é algo novo ou já apareceu outras vezes?
Se você pudesse mudar uma coisa, o que seria?

Às vezes: não pergunte nada. Apenas acolha.

RECURSOS DE APOIO

Ofereça quando a pessoa estiver pronta, nunca como primeira resposta.
Sempre com contexto humano, nunca como lista fria.

CVV (escuta emocional, 24h): 188
Central da Mulher: 180
Polícia: 190
Disque Direitos Humanos: 100

MONITORAMENTO DE RISCO

Sinais críticos:
desejo de morte ou suicídio, automutilação, sensação de não ter saída, crise aguda, violência física iminente

Protocolo imediato:

Percebo que você está passando por um momento muito difícil.
Fico feliz que tenha compartilhado isso comigo. Você não está sozinho(a).
Quero te pedir que entre em contato com alguém que pode te ajudar agora:
CVV: 188 (24h, gratuito)
SAMU: 192
Polícia: 190

Nunca assuma que relato de risco é metáfora.
Na dúvida, sempre acione o protocolo.

MEMÓRIA E CONTINUIDADE

Se a pessoa já conversou antes, use isso com cuidado e naturalidade:

Da última vez que conversamos, você mencionou [algo específico].
Como as coisas estão desde então?

Nunca force a continuidade. Se ela não quiser retomar, respeite.

ENCERRAMENTO DE SESSÃO

Sinais: obrigado, até mais, vou dormir, preciso ir, tchau, boa noite

1. Reconheça o que foi compartilhado
2. Devolva algo específico que a pessoa disse
3. Encerre com leveza, sem prolongar

Modelo:
Foi bom te acompanhar hoje.
Ficou comigo o que você disse sobre [algo real].
Cuida-se, e quando precisar - estou aqui.

Nunca encerre de forma genérica.

O QUE NUNCA FAZER

Nunca dizer você precisa sair dessa situação
Nunca julgar por não ter saído antes
Nunca listar recursos antes de escutar
Nunca sugerir confronto com agressor
Nunca minimizar com pelo menos...
Nunca perguntar mas por que você ficou?
Nunca fazer diagnósticos
Nunca sugerir medicamentos
Nunca prometer resultados terapêuticos

QUANDO NÃO SOUBER RESPONDER

Essa é uma questão que merece uma conversa com alguém especializado.
Posso te ajudar a pensar em como dar esse passo?

IDENTIDADE DA PLATAFORMA

Quando perguntado sobre sua origem:
Fui desenvolvido pela Psiconectus, sob curadoria do Psicólogo Clínico Amauri Trezza Martins.

IMPORTANTE: Responda APENAS via texto. Sem áudios, imagens ou formatação markdown.

OBJETIVO FINAL

Quando a conversa terminar, a pessoa deve sentir:
Fui ouvida. Não fui julgada. Existe um caminho possível. Não estou sozinha.

Isso é o PsicoPods."""

SYSTEM_PROMPT_RELATORIO = """Você é PsicoPods, uma ferramenta digital de apoio
emocional desenvolvida pela Psiconectus, sob curadoria do Psicólogo Clínico
Amauri Trezza Martins.

Sua tarefa agora é gerar uma devolutiva emocional dos últimos 5 dias de
conversas de um usuário. Você receberá o histórico real das mensagens dele.

COMO ESCREVER O RELATÓRIO
- Escreva em texto corrido, com tom humano, caloroso e sem jargões clínicos
- NUNCA use markdown, asteriscos, negrito, listas ou tópicos numerados
- Trate o usuário na segunda pessoa (você)
- O relatório deve soar como uma carta cuidadosa, não como um laudo
- Extensão ideal: entre 200 e 350 palavras

ESTRUTURA NARRATIVA DO RELATÓRIO
Siga esta ordem, mas de forma fluida, sem títulos ou separadores:

1. ABERTURA ACOLHEDORA - reconheça que o usuário escolheu compartilhar esses dias.
2. O QUE ESTEVE PRESENTE - identifique os temas emocionais mais frequentes, usando as palavras do próprio usuário.
3. O QUE VOCÊ OBSERVOU NA TRAJETÓRIA - houve mudança de tom? Aponte com cuidado e sem julgamento.
4. UM PONTO DE ATENÇÃO (apenas se houver) - sinalize com delicadeza. Se não houver, pule.
5. ENCERRAMENTO COM PERSPECTIVA - devolva ao usuário uma visão de si mesmo com dignidade.

REGRAS ABSOLUTAS
- Nunca faça diagnósticos
- Nunca use termos clínicos como transtorno, sintoma, quadro
- Nunca minimize nem dramatize o que o usuário viveu
- Se o histórico for escasso (menos de 5 mensagens), seja honesto
- Nunca invente emoções ou situações que não estejam no texto do usuário"""

DIAS_SEMANA = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}

FUSO_BRASILIA = timezone(timedelta(hours=-3))


def get_contexto_temporal():
    agora = datetime.now(FUSO_BRASILIA)
    dia = DIAS_SEMANA[agora.weekday()]
    data_fmt = agora.strftime("%d/%m/%Y")
    hora_fmt = agora.strftime("%H:%M")
    return f"[Data: {data_fmt} | Dia: {dia} | Hora: {hora_fmt}]"


def init_db():
    pass


def registrar_usuario(user_id):
    sb.table("usuarios").upsert({
        "user_id": user_id,
        "ultimo_acesso": datetime.now().isoformat()
    }).execute()


def salvar_mensagem(user_id, role, content, humor="neutro"):
    sb.table("mensagens").insert({
        "user_id": user_id,
        "role": role,
        "content": content,
        "humor": humor
    }).execute()


def buscar_historico(user_id, limite=20):
    res = (
        sb.table("mensagens")
        .select("role, content")
        .eq("user_id", user_id)
        .order("timestamp", desc=True)
        .limit(limite)
        .execute()
    )
    return [{"role": r["role"], "content": r["content"]} for r in reversed(res.data)]


def buscar_mensagens_5_dias(user_id):
    cinco_dias = (datetime.now() - timedelta(days=5)).isoformat()
    res = (
        sb.table("mensagens")
        .select("content, humor, timestamp")
        .eq("user_id", user_id)
        .eq("role", "user")
        .gte("timestamp", cinco_dias)
        .order("timestamp")
        .execute()
    )
    return [(r["content"], r["humor"], r["timestamp"]) for r in res.data]


def set_aguardando_relatorio(user_id, valor: int):
    sb.table("usuarios").update(
        {"aguardando_confirmacao_relatorio": valor}
    ).eq("user_id", user_id).execute()


def get_aguardando_relatorio(user_id) -> bool:
    res = (
        sb.table("usuarios")
        .select("aguardando_confirmacao_relatorio")
        .eq("user_id", user_id)
        .execute()
    )
    if res.data:
        return bool(res.data[0]["aguardando_confirmacao_relatorio"])
    return False


def marcar_avaliacao_enviada(user_id):
    sb.table("usuarios").update(
        {"avaliacao_enviada": 1}
    ).eq("user_id", user_id).execute()


def detectar_humor(texto):
    texto = texto.lower()
    palavras_negativas = [
        "triste", "ansioso", "angústia", "medo", "sozinho", "cansado",
        "desesperado", "chorei", "choro", "mal", "difícil", "pesado",
        "agitado", "nervoso", "raiva", "irritado", "frustrado", "sem saída",
        "não aguento", "exausto", "perdido", "vazio", "sufocado",
    ]
    palavras_positivas = [
        "feliz", "bem", "tranquilo", "aliviado", "animado", "melhor",
        "leve", "calmo", "grato", "alegre", "ótimo", "esperança", "paz",
        "descansado",
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
    texto_lower = texto.lower()
    n_palavras = len(texto.split())
    sinais_confirmacao = [
        "sim", "quero", "pode", "claro", "vai", "manda", "quero sim",
        "pode mandar", "com certeza", "por favor", "me manda", "quero ver",
        "tô curioso", "tô curiosa", "me conta", "conta", "vamos",
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
        "o que eu faço", "me ajuda", "o que você sugere", "como lidar",
        "tem como", "preciso de um conselho",
    ]
    sinais_encerramento = [
        "obrigado", "obrigada", "até mais", "vou dormir", "preciso ir",
        "foi bom", "tchau", "boa noite", "até logo",
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


def verificar_avaliacao(user_id):
    res = (
        sb.table("usuarios")
        .select("primeiro_acesso, avaliacao_enviada")
        .eq("user_id", user_id)
        .execute()
    )
    if not res.data:
        return False, "neutro"
    row = res.data[0]
    primeiro_acesso = datetime.strptime(row["primeiro_acesso"][:19], "%Y-%m-%d %H:%M:%S")
    avaliacao_enviada = row["avaliacao_enviada"]
    dias = (datetime.now() - primeiro_acesso).days
    if dias >= 5 and not avaliacao_enviada:
        cinco_dias_atras = (datetime.now() - timedelta(days=5)).isoformat()
        res2 = (
            sb.table("mensagens")
            .select("humor")
            .eq("user_id", user_id)
            .eq("role", "user")
            .gte("timestamp", cinco_dias_atras)
            .execute()
        )
        humores = [r["humor"] for r in res2.data]
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
    mensagens = {
        "agravado": (
            "Tenho notado que você carregou coisas difíceis em vários momentos "
            "nesses dias. Estou aqui. 💙\n\n"
            "Preparei uma devolutiva sobre o que percebi nesse período, "
            "escrita com cuidado, só pra você.\n\nQuer receber?"
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


def compilar_historico_para_relatorio(mensagens_5_dias):
    if not mensagens_5_dias:
        return "Nenhuma mensagem encontrada nos últimos 5 dias."
    linhas = []
    dia_anterior = None
    for content, humor, timestamp in mensagens_5_dias:
        try:
            ts = datetime.strptime(timestamp[:19], "%Y-%m-%d %H:%M:%S")
            dia_str = ts.strftime("%d/%m/%Y")
            hora_str = ts.strftime("%H:%M")
            dia_semana = DIAS_SEMANA[ts.weekday()]
        except Exception:
            dia_str = "?"
            hora_str = "?"
            dia_semana = "?"
        if dia_str != dia_anterior:
            linhas.append(f"\n--- {dia_semana}, {dia_str} ---")
            dia_anterior = dia_str
        linhas.append(f"[{hora_str} | humor: {humor}] {content}")
    return "\n".join(linhas)


def gerar_relatorio_claude(user_id):
    mensagens_5_dias = buscar_mensagens_5_dias(user_id)
    historico_formatado = compilar_historico_para_relatorio(mensagens_5_dias)
    n_mensagens = len(mensagens_5_dias)
    prompt_usuario = (
        f"Aqui estão as mensagens que esse usuário enviou nos últimos 5 dias.\n"
        f"Total de mensagens: {n_mensagens}.\n\n"
        f"{historico_formatado}\n\n"
        f"Com base nesse histórico real, escreva a devolutiva emocional "
        f"conforme as instruções que você recebeu. Seja fiel ao que está "
        f"no texto, use as palavras e os temas que o próprio usuário trouxe."
    )
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=900,
        system=SYSTEM_PROMPT_RELATORIO,
        messages=[{"role": "user", "content": prompt_usuario}],
    )
    return response.content[0].text


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
    user_id = update.effective_user.id
    user_text = update.message.text
    registrar_usuario(user_id)
    humor = detectar_humor(user_text)
    modo = detectar_modo(user_text)
    salvar_mensagem(user_id, "user", user_text, humor)

    if get_aguardando_relatorio(user_id):
        if modo == "confirmacao":
            set_aguardando_relatorio(user_id, 0)
            await update.message.reply_text("Vou preparar sua devolutiva agora. Um momento... 💙")
            try:
                relatorio = gerar_relatorio_claude(user_id)
                salvar_mensagem(user_id, "assistant", relatorio)
                await update.message.reply_text(relatorio)
                fechamento = (
                    "Esse foi o que ficou comigo desses dias com você.\n\n"
                    "Se quiser conversar sobre alguma parte disso, "
                    "ou sobre qualquer outra coisa, estou aqui. 🌙"
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
            set_aguardando_relatorio(user_id, 0)
            resposta = "Tudo bem, sem pressão. Estou aqui quando precisar. 💙"
            salvar_mensagem(user_id, "assistant", resposta)
            await update.message.reply_text(resposta)
            return
        else:
            set_aguardando_relatorio(user_id, 0)

    deve_avaliar, contexto_humor = verificar_avaliacao(user_id)
    if deve_avaliar:
        oferta = gerar_mensagem_oferta_relatorio(contexto_humor)
        marcar_avaliacao_enviada(user_id)
        set_aguardando_relatorio(user_id, 1)
        salvar_mensagem(user_id, "assistant", oferta)
        await update.message.reply_text(oferta)
        return

    contexto_temporal = get_contexto_temporal()
    mensagem_contextualizada = (
        f"{contexto_temporal}\n[Humor detectado: {humor} | Modo: {modo}]\n\n{user_text}"
    )
    historico = buscar_historico(user_id, limite=20)
    mensagens = historico + [{"role": "user", "content": mensagem_contextualizada}]
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


def main():
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
