import sqlite3
import pandas as pd

def conectar_db():
    """Cria e retorna uma conexão com o banco de dados."""
    # check_same_thread=False é necessário para o Streamlit
    conn = sqlite3.connect("voluntarios.db", check_same_thread=False)
    return conn

def criar_tabelas(conn):
    """Cria as tabelas do banco de dados, se não existirem."""
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS voluntarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL,
        atribuicoes TEXT,
        disponibilidade TEXT
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

def adicionar_voluntario(conn, nome, email, senha, atribuicoes, disponibilidade):
    c = conn.cursor()
    c.execute("INSERT INTO voluntarios (nome, email, senha, atribuicoes, disponibilidade) VALUES (?, ?, ?, ?, ?)",
              (nome, email, senha, atribuicoes, disponibilidade))
    conn.commit()

def editar_voluntario(conn, vol_id, nome, email, senha, atribuicoes, disponibilidade):
    c = conn.cursor()
    c.execute("""
        UPDATE voluntarios 
        SET nome = ?, email = ?, senha = ?, atribuicoes = ?, disponibilidade = ?
        WHERE id = ?
    """, (nome, email, senha, atribuicoes, disponibilidade, vol_id))
    conn.commit()

def excluir_voluntario(conn, vol_id):
    c = conn.cursor()
    c.execute("DELETE FROM voluntarios WHERE id = ?", (vol_id,))
    conn.commit()

def listar_voluntarios(conn):
    return pd.read_sql_query("SELECT * FROM voluntarios", conn)

def autenticar_voluntario(conn, email, senha):
    c = conn.cursor()
    query = "SELECT * FROM voluntarios WHERE email = ? AND senha = ?"
    c.execute(query, (email, senha))
    return c.fetchone()

def salvar_indisponibilidade(conn, voluntario_id, datas, ceia, mes):
    c = conn.cursor()
    # Verifica se já existe um registro para este voluntário e mês
    c.execute("SELECT id FROM indisponibilidades WHERE voluntario_id = ? AND mes_referencia = ?", (voluntario_id, mes))
    registro_existente = c.fetchone()

    if registro_existente:
        # Atualiza o registro existente
        c.execute("""
            UPDATE indisponibilidades
            SET datas_restricao = ?, ceia_passada = ?
            WHERE id = ?
        """, (datas, ceia, registro_existente[0]))
    else:
        # Insere um novo registro
        c.execute("""
            INSERT INTO indisponibilidades (voluntario_id, datas_restricao, ceia_passada, mes_referencia)
            VALUES (?, ?, ?, ?)
        """, (voluntario_id, datas, ceia, mes))
    conn.commit()