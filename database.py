# database.py
import sqlite3
import pandas as pd

def conectar_db():
    conn = sqlite3.connect("voluntarios.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row # Permite acessar colunas pelo nome
    return conn

def criar_tabelas(conn):
    c = conn.cursor()
    # MODIFICAÇÃO: Trocamos 'email' por 'usuario' e adicionamos 'primeiro_acesso'
    c.execute('''CREATE TABLE IF NOT EXISTS voluntarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        usuario TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL,
        atribuicoes TEXT,
        disponibilidade TEXT,
        primeiro_acesso INTEGER DEFAULT 1
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS indisponibilidades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voluntario_id INTEGER,
    datas_restricao TEXT,
    ceia_passada TEXT,
    mes_referencia TEXT,
    FOREIGN KEY(voluntario_id) REFERENCES voluntarios(id)
)''')
    conn.commit()

# MODIFICAÇÃO: Recebe 'usuario' em vez de 'email' e seta primeiro_acesso
def adicionar_voluntario(conn, nome, usuario, senha, atribuicoes, disponibilidade):
    c = conn.cursor()
    c.execute("""
        INSERT INTO voluntarios (nome, usuario, senha, atribuicoes, disponibilidade, primeiro_acesso) 
        VALUES (?, ?, ?, ?, ?, 1)
        """, (nome, usuario, senha, atribuicoes, disponibilidade))
    conn.commit()

# MODIFICAÇÃO: Edita 'usuario'
def editar_voluntario(conn, vol_id, nome, usuario, senha, atribuicoes, disponibilidade):
    c = conn.cursor()
    c.execute("""
        UPDATE voluntarios 
        SET nome = ?, usuario = ?, senha = ?, atribuicoes = ?, disponibilidade = ?
        WHERE id = ?
    """, (nome, usuario, senha, atribuicoes, disponibilidade, vol_id))
    conn.commit()

# MODIFICAÇÃO: Autentica com 'usuario'
def autenticar_voluntario(conn, usuario, senha):
    c = conn.cursor()
    query = "SELECT * FROM voluntarios WHERE usuario = ? AND senha = ?"
    c.execute(query, (usuario, senha))
    return c.fetchone()

# NOVA FUNÇÃO: Altera a senha e marca o primeiro acesso como concluído
def alterar_senha_e_status(conn, voluntario_id, nova_senha):
    c = conn.cursor()
    c.execute("""
        UPDATE voluntarios
        SET senha = ?, primeiro_acesso = 0
        WHERE id = ?
    """, (nova_senha, voluntario_id))
    conn.commit()

# Mantenha as outras funções (excluir_voluntario, listar_voluntarios, etc.) como estão
def excluir_voluntario(conn, vol_id):
    c = conn.cursor()
    c.execute("DELETE FROM voluntarios WHERE id = ?", (vol_id,))
    conn.commit()

def listar_voluntarios(conn):
    return pd.read_sql_query("SELECT id, nome, usuario, atribuicoes, disponibilidade, primeiro_acesso FROM voluntarios", conn)

def salvar_indisponibilidade(conn, voluntario_id, datas, ceia, mes):
    # (Esta função permanece inalterada)
    c = conn.cursor()
    c.execute("SELECT id FROM indisponibilidades WHERE voluntario_id = ? AND mes_referencia = ?", (voluntario_id, mes))
    registro_existente = c.fetchone()
    if registro_existente:
        c.execute("UPDATE indisponibilidades SET datas_restricao = ?, ceia_passada = ? WHERE id = ?", (datas, ceia, registro_existente['id']))
    else:
        c.execute("INSERT INTO indisponibilidades (voluntario_id, datas_restricao, ceia_passada, mes_referencia) VALUES (?, ?, ?, ?)", (voluntario_id, datas, ceia, mes))
    conn.commit()

def listar_indisponibilidades_por_mes(conn, mes_referencia):
    # (Esta função permanece inalterada)
    query = """
        SELECT v.id as voluntario_id, v.nome, i.datas_restricao, i.ceia_passada
        FROM indisponibilidades i
        JOIN voluntarios v ON i.voluntario_id = v.id
        WHERE i.mes_referencia = ?
    """
    return pd.read_sql_query(query, conn, params=(mes_referencia,))