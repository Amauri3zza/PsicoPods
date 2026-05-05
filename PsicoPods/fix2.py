with open('main.py', 'r') as f:
    code = f.read()

# buscar_historico
start = code.find('def buscar_historico(user_id, limite=20):')
end = code.find('\ndef buscar_mensagens_5_dias')
code = code[:start] + '''def buscar_historico(user_id, limite=20):
    res = sb.table("mensagens").select("role, content").eq("user_id", user_id).order("timestamp", desc=True).limit(limite).execute()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(res.data)]
''' + code[end:]

# buscar_mensagens_5_dias
start = code.find('def buscar_mensagens_5_dias(user_id):')
end = code.find('\ndef set_aguardando_relatorio')
code = code[:start] + '''def buscar_mensagens_5_dias(user_id):
    cinco_dias = (datetime.now() - timedelta(days=5)).isoformat()
    res = sb.table("mensagens").select("content, humor, timestamp").eq("user_id", user_id).eq("role", "user").gte("timestamp", cinco_dias).order("timestamp").execute()
    return [(r["content"], r["humor"], r["timestamp"]) for r in res.data]
''' + code[end:]

# set_aguardando_relatorio
start = code.find('def set_aguardando_relatorio(user_id, valor: int):')
end = code.find('\ndef get_aguardando_relatorio')
code = code[:start] + '''def set_aguardando_relatorio(user_id, valor: int):
    sb.table("usuarios").update({"aguardando_confirmacao_relatorio": valor}).eq("user_id", user_id).execute()
''' + code[end:]

# get_aguardando_relatorio
start = code.find('def get_aguardando_relatorio(user_id) -> bool:')
end = code.find('\ndef marcar_avaliacao_enviada')
code = code[:start] + '''def get_aguardando_relatorio(user_id) -> bool:
    res = sb.table("usuarios").select("aguardando_confirmacao_relatorio").eq("user_id", user_id).execute()
    if res.data:
        return bool(res.data[0]["aguardando_confirmacao_relatorio"])
    return False
''' + code[end:]

# marcar_avaliacao_enviada
start = code.find('def marcar_avaliacao_enviada(user_id):')
end = code.find('\ndef verificar_avaliacao')
code = code[:start] + '''def marcar_avaliacao_enviada(user_id):
    sb.table("usuarios").update({"avaliacao_enviada": 1}).eq("user_id", user_id).execute()
''' + code[end:]

with open('main.py', 'w') as f:
    f.write(code)
print('OK')
