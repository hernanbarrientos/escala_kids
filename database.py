# database.py

import sqlite3
import pandas as pd

def conectar_db():
    conn = sqlite3.connect("voluntarios.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def criar_tabelas(conn):
    c = conn.cursor()
    # MODIFICAÇÃO: Adicionando a coluna 'role' à tabela voluntarios
    c.execute('''CREATE TABLE IF NOT EXISTS voluntarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        usuario TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL,
        atribuicoes TEXT,
        disponibilidade TEXT,
        primeiro_acesso INTEGER DEFAULT 1,
        role TEXT DEFAULT 'voluntario' -- Nova coluna 'role' com valor padrão 'voluntario'
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS indisponibilidades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voluntario_id INTEGER NOT NULL,
        datas_restricao TEXT,
        ceia_passada TEXT,
        mes_referencia TEXT NOT NULL,
        timestamp_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(voluntario_id, mes_referencia),
        FOREIGN KEY(voluntario_id) REFERENCES voluntarios(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS configuracoes_escalas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mes_referencia TEXT NOT NULL UNIQUE,
        edicao_liberada BOOLEAN DEFAULT FALSE,
        ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()

# Garante que as tabelas são criadas quando o módulo é importado
conn_inicial_check = conectar_db()
criar_tabelas(conn_inicial_check)
conn_inicial_check.close() # Fecha a conexão inicial


# MODIFICAÇÃO: Adicionar um novo campo 'role' à função
def adicionar_voluntario(conn, nome, usuario, senha, atribuicoes, disponibilidade, role='voluntario'):
    c = conn.cursor()
    c.execute("""
        INSERT INTO voluntarios (nome, usuario, senha, atribuicoes, disponibilidade, primeiro_acesso, role) 
        VALUES (?, ?, ?, ?, ?, 1, ?)
        """, (nome, usuario, senha, atribuicoes, disponibilidade, role))
    conn.commit()

# MODIFICAÇÃO: Editar 'usuario' e 'role' (se aplicável)
def editar_voluntario(conn, vol_id, nome, usuario, senha, atribuicoes, disponibilidade, role=None):
    c = conn.cursor()
    # Constrói a query dinamicamente para permitir não alterar a senha ou o role se não fornecidos
    query_parts = ["nome = ?", "usuario = ?", "atribuicoes = ?", "disponibilidade = ?"]
    params = [nome, usuario, atribuicoes, disponibilidade]

    if senha: # Apenas atualiza a senha se uma nova for fornecida
        query_parts.append("senha = ?")
        params.append(senha)
    if role: # Apenas atualiza o role se um novo for fornecido
        query_parts.append("role = ?")
        params.append(role)
    
    query = f"UPDATE voluntarios SET {', '.join(query_parts)} WHERE id = ?"
    params.append(vol_id)

    c.execute(query, tuple(params))
    conn.commit()

# MODIFICAÇÃO: Autentica com 'usuario' e retorna 'role'
def autenticar_voluntario(conn, usuario, senha):
    c = conn.cursor()
    # Agora selecionamos também a coluna 'role'
    query = "SELECT id, nome, usuario, atribuicoes, disponibilidade, primeiro_acesso, role FROM voluntarios WHERE usuario = ? AND senha = ?"
    c.execute(query, (usuario, senha))
    return c.fetchone()

def alterar_senha_e_status(conn, voluntario_id, nova_senha):
    c = conn.cursor()
    c.execute("""
        UPDATE voluntarios
        SET senha = ?, primeiro_acesso = 0
        WHERE id = ?
    """, (nova_senha, voluntario_id))
    conn.commit()

def excluir_voluntario(conn, vol_id):
    c = conn.cursor()
    c.execute("DELETE FROM voluntarios WHERE id = ?", (vol_id,))
    conn.commit()

# MODIFICAÇÃO: Incluir 'role' na listagem de voluntários
def listar_voluntarios(conn):
    return pd.read_sql_query("SELECT id, nome, usuario, atribuicoes, disponibilidade, primeiro_acesso, role FROM voluntarios", conn)


#INDISPONIBILIDADES:
def listar_indisponibilidades_por_mes(conn, mes_referencia):
    c = conn.cursor()
    c.execute('''
        SELECT v.id AS voluntario_id, v.nome, i.datas_restricao, i.ceia_passada
        FROM indisponibilidades i
        JOIN voluntarios v ON v.id = i.voluntario_id
        WHERE i.mes_referencia = ?
    ''', (mes_referencia,))
    
    rows = c.fetchall()
    colunas = ['voluntario_id', 'nome', 'datas_restricao', 'ceia_passada']
    return pd.DataFrame(rows, columns=colunas)

def salvar_indisponibilidade(conn, voluntario_id, datas_restricao_str, ceia_passada, mes_ref):
    c = conn.cursor()
    try:
        c.execute("""
            UPDATE indisponibilidades
            SET datas_restricao = ?, ceia_passada = ?, timestamp_registro = CURRENT_TIMESTAMP
            WHERE voluntario_id = ? AND mes_referencia = ?
        """, (datas_restricao_str, ceia_passada, voluntario_id, mes_ref))
        
        if c.rowcount == 0:
            c.execute("""
                INSERT INTO indisponibilidades (voluntario_id, datas_restricao, ceia_passada, mes_referencia)
                VALUES (?, ?, ?, ?)
            """, (voluntario_id, datas_restricao_str, ceia_passada, mes_ref))
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Erro ao salvar/atualizar indisponibilidade: {e}")
        conn.rollback()
        return False

def carregar_indisponibilidade(conn, voluntario_id, mes_ref):
    c = conn.cursor()
    c.execute("""
        SELECT datas_restricao, ceia_passada
        FROM indisponibilidades
        WHERE voluntario_id = ? AND mes_referencia = ?
    """, (voluntario_id, mes_ref))
    result = c.fetchone()
    if result:
        return {'datas_restricao': result['datas_restricao'], 'ceia_passada': result['ceia_passada']}
    return None

def get_edicao_liberada(conn, mes_ref):
    c = conn.cursor()
    c.execute("SELECT edicao_liberada FROM configuracoes_escalas WHERE mes_referencia = ?", (mes_ref,))
    result = c.fetchone()
    if result:
        return bool(result['edicao_liberada'])
    
    try:
        c.execute("INSERT OR IGNORE INTO configuracoes_escalas (mes_referencia, edicao_liberada) VALUES (?, FALSE)", (mes_ref,))
        conn.commit()
        return False
    except sqlite3.Error as e:
        print(f"Erro ao inserir configuração de escala padrão: {e}")
        return False

def set_edicao_liberada(conn, mes_ref, status):
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO configuracoes_escalas (mes_referencia, edicao_liberada, ultima_atualizacao)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(mes_referencia) DO UPDATE SET
            edicao_liberada = ?, ultima_atualizacao = CURRENT_TIMESTAMP
        """, (mes_ref, status, status))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Erro ao definir status de edição: {e}")
        conn.rollback()
        return False

def get_all_voluntarios_indisponibilidade_for_month(conn, mes_ref):
    c = conn.cursor()
    c.execute("""
        SELECT v.nome, i.datas_restricao, i.ceia_passada
        FROM indisponibilidades i
        JOIN voluntarios v ON i.voluntario_id = v.id
        WHERE i.mes_referencia = ?
    """, (mes_ref,))
    return c.fetchall()

def get_all_meses_configurados(conn):
    c = conn.cursor()
    c.execute("SELECT mes_referencia, edicao_liberada, ultima_atualizacao FROM configuracoes_escalas ORDER BY mes_referencia DESC")
    return c.fetchall()

# MODIFICAÇÃO: Incluir 'role' na busca por ID
def get_voluntario_by_id(conn, voluntario_id):
    c = conn.cursor()
    c.execute("""
        SELECT id, nome, usuario, senha, atribuicoes, disponibilidade, primeiro_acesso, role
        FROM voluntarios
        WHERE id = ?
    """, (voluntario_id,))
    return c.fetchone()