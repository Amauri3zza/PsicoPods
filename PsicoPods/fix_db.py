with open("main.py", "r") as f:
    code = f.read()

# registrar_usuario
old = """def registrar_usuario(user_id):
  conn = sqlite3.connect("psicopods.db")
  c = conn.cursor()
  c.execute("INSERT OR IGNORE INTO usuarios (user_id) VALUES (?)", (user_id,))
  c.execute(
      "UPDATE usuarios SET ultimo_acesso = ? WHERE user_id = ?",
      (datetime.now(), user_id),
  )
  conn.commit()
  conn.close()"""
new = """def registrar_usuario(user_id):
  sb.table("usuarios").upsert({
      "user_id": user_id,
      "ultimo_acesso": datetime.now().isoformat()
  }).execute()"""
if old in code:
    code = code.replace(old, new)
    print("OK: registrar_usuario")
else:
    print("NAO ENCONTRADO: registrar_usuario")

# salvar_mensagem
old = """def salvar_mensagem(user_id, role, content, humor="neutro"):
  conn = sqlite3.connect("psicopods.db")
  c = conn.cursor()
  c.execute(
      "INSERT INTO mensagens (user_id, role, content, humor) VALUES (?, ?, ?, ?)",
      (user_id, role, content, humor),
  )
  conn.commit()
  conn.close()"""
new = """def salvar_mensagem(user_id, role, content, humor="neutro"):
  sb.table("mensagens").insert({
      "user_id": user_id,
      "role": role,
      "content": content,
      "humor": humor
  }).execute()"""
if old in code:
    code = code.replace(old, new)
    print("OK: salvar_mensagem")
else:
    print("NAO ENCONTRADO: salvar_mensagem")

with open("main.py", "w") as f:
    f.write(code)

print("CONCLUIDO")
