from flask import Flask, render_template, request, jsonify
import sqlite3
import random

app = Flask(__name__)

# Armazenamento temporário de tokens ativos na memória (Tokens expiram, então não precisam de banco de dados)
tokens_ativos = {}  # Estrutura: {"nome_usuario": "654321"}

def conectar_banco():
    """Cria uma conexão com o arquivo de banco de dados SQLite."""
    conexao = sqlite3.connect('educore.db')
    conexao.row_factory = sqlite3.Row  # Permite acessar os dados pelo nome da coluna (ex: linha['email'])
    return conexao

def inicializar_banco_de_dados():
    """Cria a tabela de usuários automaticamente e adiciona os perfis padrão caso o banco esteja vazio."""
    with conectar_banco() as conn:
        cursor = conn.cursor()
        
        # Cria a tabela de usuários se ela ainda não existir
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                senha TEXT NOT NULL
            )
        ''')
        
        # Verifica se o banco de dados está vazio
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        if cursor.fetchone()[0] == 0:
            # Perfis padrão iniciais para você testar de primeira
            usuarios_padrao = [
                ("admin", "admin@educore.com", "123"),
                ("gustavo", "gustavo@educore.com", "senha123"),
                ("sofia", "sofia@educore.com", "456")
            ]
            cursor.executemany("INSERT INTO usuarios (usuario, email, senha) VALUES (?, ?, ?)", usuarios_padrao)
            print("[EduCore] Banco de dados criado e perfis padrão adicionados com sucesso!")
        
        conn.commit()

@app.route('/')
def home():
    return render_template('index.html')

# ROTA 1: Autenticação de Login Comum (Buscando no Banco de Dados)
@app.route('/api/login', methods=['POST'])
def api_login():
    dados = request.json
    usuario_alvo = dados.get('usuario', '').strip().lower()
    senha_alva = dados.get('senha', '').strip()

    with conectar_banco() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE LOWER(usuario) = ? AND senha = ?", (usuario_alvo, senha_alva))
        conta = cursor.fetchone()

    if conta:
        return jsonify({
            "status": "sucesso", 
            "usuario": conta['usuario'], 
            "email": conta['email'], 
            "senha": conta['senha']
        })
    return jsonify({"status": "erro", "mensagem": "Usuário ou senha incorretos! Tente novamente."})

# ROTA 2: Validação de Usuário/E-mail e Disparo do Token
@app.route('/api/solicitar-token', methods=['POST'])
def api_solicitar_token():
    dados = request.json
    usuario_alvo = dados.get('usuario', '').strip().lower()
    email_alvo = dados.get('email', '').strip().lower()

    with conectar_banco() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE LOWER(usuario) = ?", (usuario_alvo,))
        conta = cursor.fetchone()
    
    if not conta:
        return jsonify({"status": "erro", "mensagem": f"O usuário '{usuario_alvo}' não está cadastrado."})
    
    if conta['email'].lower() != email_alvo:
        return jsonify({"status": "erro", "mensagem": "O e-mail informado não corresponde aos nossos registros."})

    # Geração segura do Token dentro do servidor
    token_gerado = str(random.randint(100000, 999999))
    tokens_ativos[usuario_alvo] = token_gerado

    # Log interno no terminal simulando o envio real por e-mail
    print(f"\n[EduCore SEGURANÇA] Token gerado para {conta['usuario']}: {token_gerado}\n")

    return jsonify({
        "status": "sucesso", 
        "mensagem": "Token de segurança gerado!", 
        "token_exibicao": token_gerado
    })

# ROTA 3: Verificação do Token enviado
@app.route('/api/validar-token', methods=['POST'])
def api_validar_token():
    dados = request.json
    usuario_alvo = dados.get('usuario', '').strip().lower()
    token_digitado = dados.get('token', '').strip()

    token_correto = tokens_ativos.get(usuario_alvo)

    if token_correto and token_digitado == token_correto:
        with conectar_banco() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM usuarios WHERE LOWER(usuario) = ?", (usuario_alvo,))
            conta = cursor.fetchone()
            
        del tokens_ativos[usuario_alvo]  # Destrói o token após o uso
        return jsonify({
            "status": "sucesso", 
            "usuario": conta['usuario'], 
            "email": conta['email'], 
            "senha": conta['senha']
        })
    
    return jsonify({"status": "erro", "mensagem": "Token incorreto ou já expirado!"})

# ROTA 4: Criação de Nova Conta (Gravando direto no Banco de Dados)
@app.route('/api/cadastrar', methods=['POST'])
def api_cadastrar():
    dados = request.json
    usuario_alvo = dados.get('usuario', '').strip()
    email_alvo = dados.get('email', '').strip()
    senha_alva = dados.get('senha', '').strip()

    try:
        with conectar_banco() as conn:
            cursor = conn.cursor()
            # O banco de dados vai rejeitar automaticamente se o usuário já existir (por causa do UNIQUE)
            cursor.execute("INSERT INTO usuarios (usuario, email, senha) VALUES (?, ?, ?)", (usuario_alvo, email_alvo, senha_alva))
            conn.commit()
        return jsonify({"status": "sucesso", "mensagem": "Cadastro realizado com sucesso! Dados salvos permanentemente."})
    except sqlite3.IntegrityError:
        return jsonify({"status": "erro", "mensagem": "Este nome de usuário já está sendo usado!"})

if __name__ == '__main__':
    # Garante que o banco de dados e as tabelas existam antes do site ligar
    inicializar_banco_de_dados()
    app.run(debug=True)
