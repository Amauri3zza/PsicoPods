with open('main.py', 'r') as f:
    code = f.read()

# Remove init_db
start = code.find('def init_db():')
end = code.find('\ndef registrar_usuario')
code = code[:start] + 'def init_db():\n pass\n' + code[end:]

# Substitui registrar_usuario
start = code.find('def registrar_usuario(user_id):')
end = code.find('\ndef salvar_mensagem')
code = code[:start] + '''def registrar_usuario(user_id):
    sb.table("usuarios").upsert({
        "user_id": user_id,
        "ultimo_acesso": datetime.now().isoformat()
    }).execute()
''' + code[end:]

# Substitui salvar_mensagem
start = code.find('def salvar_mensagem(user_id, role, content, humor="neutro"):')
end = code.find('\ndef buscar_historico')
code = code[:start] + '''def salvar_mensagem(user_id, role, content, humor="neutro"):
    sb.table("mensagens").insert({
        "user_id": user_id,
        "role": role,
        "content": content,
        "humor": humor
    }).execute()
''' + code[end:]

with open('main.py', 'w') as f:
    f.write(code)
print('OK')
