# database.py
import sqlite3
import pandas as pd # Mantém o pandas para as funções de listagem

def conectar_db():
    conn = sqlite3.connect("voluntarios.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row # Permite acessar colunas pelo nome
    return conn

def criar_tabelas(conn):
    c = conn.cursor()
    # Tabela voluntarios
    c.execute('''CREATE TABLE IF NOT EXISTS voluntarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        usuario TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL,
        atribuicoes TEXT,
        disponibilidade TEXT,
        primeiro_acesso INTEGER DEFAULT 1
    )''')

    # Tabela indisponibilidades (plural, conforme seu uso atual)
    # Adicionado timestamp para rastreamento
    c.execute('''CREATE TABLE IF NOT EXISTS indisponibilidades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voluntario_id INTEGER NOT NULL,
        datas_restricao TEXT,
        ceia_passada TEXT,
        mes_referencia TEXT NOT NULL,
        timestamp_registro DATETIME DEFAULT CURRENT_TIMESTAMP, -- Novo campo
        UNIQUE(voluntario_id, mes_referencia), -- Garante apenas uma entrada por voluntário por mês/referência
        FOREIGN KEY(voluntario_id) REFERENCES voluntarios(id)
    )''')

    # Nova tabela para configurações de escala (mesmo nome que sugeri antes)
    c.execute('''CREATE TABLE IF NOT EXISTS configuracoes_escalas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mes_referencia TEXT NOT NULL UNIQUE, -- Ex: "Agosto de 2025"
        edicao_liberada BOOLEAN DEFAULT FALSE,
        ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()

# Chame criar_tabelas() ao iniciar para garantir que existam
conn_inicial = conectar_db()
criar_tabelas(conn_inicial)
conn_inicial.close()


def adicionar_voluntario(conn, nome, usuario, senha, atribuicoes, disponibilidade):
    c = conn.cursor()
    c.execute("""
        INSERT INTO voluntarios (nome, usuario, senha, atribuicoes, disponibilidade, primeiro_acesso) 
        VALUES (?, ?, ?, ?, ?, 1)
        """, (nome, usuario, senha, atribuicoes, disponibilidade))
    conn.commit()

def editar_voluntario(conn, vol_id, nome, usuario, senha, atribuicoes, disponibilidade):
    c = conn.cursor()
    c.execute("""
        UPDATE voluntarios 
        SET nome = ?, usuario = ?, senha = ?, atribuicoes = ?, disponibilidade = ?
        WHERE id = ?
    """, (nome, usuario, senha, atribuicoes, disponibilidade, vol_id))
    conn.commit()

def autenticar_voluntario(conn, usuario, senha):
    c = conn.cursor()
    query = "SELECT id, nome, usuario, atribuicoes, disponibilidade, primeiro_acesso FROM voluntarios WHERE usuario = ? AND senha = ?"
    c.execute(query, (usuario, senha))
    return c.fetchone() # Retorna um objeto Row que pode ser acessado por nome

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

def listar_voluntarios(conn):
    return pd.read_sql_query("SELECT id, nome, usuario, atribuicoes, disponibilidade, primeiro_acesso FROM voluntarios", conn)

# MODIFICAÇÃO: Função salvar_indisponibilidade agora faz UPDATE ou INSERT
def salvar_indisponibilidade(conn, voluntario_id, datas_restricao_str, ceia_passada, mes_ref):
    c = conn.cursor()
    try:
        # Tenta atualizar primeiro
        c.execute("""
            UPDATE indisponibilidades
            SET datas_restricao = ?, ceia_passada = ?, timestamp_registro = CURRENT_TIMESTAMP
            WHERE voluntario_id = ? AND mes_referencia = ?
        """, (datas_restricao_str, ceia_passada, voluntario_id, mes_ref))
        
        # Se nenhuma linha foi atualizada, insere
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

# NOVA FUNÇÃO: Carregar a indisponibilidade de um voluntário para um mês específico
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

# NOVA FUNÇÃO: Obter o status de edição liberada para um mês
def get_edicao_liberada(conn, mes_ref):
    c = conn.cursor()
    c.execute("SELECT edicao_liberada FROM configuracoes_escalas WHERE mes_referencia = ?", (mes_ref,))
    result = c.fetchone()
    if result:
        return bool(result['edicao_liberada']) # sqlite armazena BOOLEAN como 0 ou 1
    
    # Se não houver registro para o mês, por padrão não está liberado
    # E insere um registro para que o admin possa manipular no futuro
    try:
        c.execute("INSERT OR IGNORE INTO configuracoes_escalas (mes_referencia, edicao_liberada) VALUES (?, FALSE)", (mes_ref,))
        conn.commit()
        return False
    except sqlite3.Error as e:
        print(f"Erro ao inserir configuração de escala padrão: {e}")
        return False

# NOVA FUNÇÃO: Definir o status de edição liberada para um mês
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

# Função auxiliar para Admin: Obter todas as indisponibilidades para um mês
def get_all_voluntarios_indisponibilidade_for_month(conn, mes_ref):
    c = conn.cursor()
    c.execute("""
        SELECT v.nome, i.datas_restricao, i.ceia_passada
        FROM indisponibilidades i
        JOIN voluntarios v ON i.voluntario_id = v.id
        WHERE i.mes_referencia = ?
    """, (mes_ref,))
    # Retorna uma lista de objetos Row, que podem ser convertidos para DataFrame se preferir
    return c.fetchall()

# Função auxiliar para Admin: Listar todos os meses com configurações de escala
def get_all_meses_configurados(conn):
    c = conn.cursor()
    c.execute("SELECT mes_referencia, edicao_liberada, ultima_atualizacao FROM configuracoes_escalas ORDER BY mes_referencia DESC")
    return c.fetchall()

def get_voluntario_by_id(conn, voluntario_id):
    c = conn.cursor()
    c.execute("SELECT id, nome, usuario, atribuicoes, disponibilidade, primeiro_acesso FROM voluntarios WHERE id = ?", (voluntario_id,))
    return c.fetchone()