# database.py
import sqlite3
import pandas as pd
import utils

def conectar_db():
    conn = sqlite3.connect("voluntarios.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def criar_tabelas(conn):
    c = conn.cursor()
    # Cria a tabela de voluntários
    c.execute('''CREATE TABLE IF NOT EXISTS voluntarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        usuario TEXT UNIQUE NOT NULL COLLATE NOCASE,
        senha TEXT NOT NULL,
        atribuicoes TEXT,
        disponibilidade TEXT,
        primeiro_acesso INTEGER DEFAULT 1,
        role TEXT DEFAULT 'voluntario'
    )''')

    # Cria a tabela de disponibilidades
    c.execute('''CREATE TABLE IF NOT EXISTS disponibilidades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voluntario_id INTEGER NOT NULL,
        datas_disponiveis TEXT,
        ceia_passada TEXT,
        mes_referencia TEXT NOT NULL,
        timestamp_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(voluntario_id, mes_referencia),
        FOREIGN KEY(voluntario_id) REFERENCES voluntarios(id)
    )''')

    # Cria a tabela de configurações
    c.execute('''CREATE TABLE IF NOT EXISTS configuracoes_escalas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mes_referencia TEXT NOT NULL UNIQUE,
        edicao_liberada BOOLEAN DEFAULT FALSE,
        ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()

    # --- LÓGICA DE CRIAÇÃO AUTOMÁTICA DO ADMIN (SEEDING) ---
    c.execute("SELECT COUNT(*) FROM voluntarios WHERE usuario = ?", ('admin',))
    admin_existe = c.fetchone()[0]

    if admin_existe == 0:
        print("Usuário 'admin' não encontrado. Criando usuário administrador padrão...")
        senha_padrao_hash = utils.hash_password("admin123") # Criptografa a senha padrão
        c.execute("""
            INSERT INTO voluntarios (nome, usuario, senha, atribuicoes, disponibilidade, primeiro_acesso, role) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, 
            ("Administrador", "admin", senha_padrao_hash, "", "", 0, "admin") # primeiro_acesso = 0 para não pedir troca de senha
        )
        conn.commit()
        print("Usuário 'admin' criado com sucesso com a senha 'admin123'.")

    # --- NOVA TABELA PARA ARMAZENAR A ESCALA FINAL E EXIBIR PARA O VOLUNTÁRIO ---
    c.execute('''CREATE TABLE IF NOT EXISTS escala_gerada (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mes_referencia TEXT NOT NULL,
        data_culto TEXT NOT NULL,
        funcao TEXT NOT NULL,
        voluntario_id INTEGER,
        voluntario_nome TEXT,
        FOREIGN KEY(voluntario_id) REFERENCES voluntarios(id)
    )''')
    conn.commit()

    
    # --- NOVA TABELA PARA FEEDBACKS ---
    c.execute('''CREATE TABLE IF NOT EXISTS feedbacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voluntario_id INTEGER NOT NULL,
        voluntario_nome TEXT NOT NULL,
        data_culto TEXT NOT NULL,
        funcao TEXT NOT NULL, -- <<< COLUNA ADICIONADA
        comentario TEXT NOT NULL,
        status TEXT DEFAULT 'novo',
        timestamp_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(voluntario_id) REFERENCES voluntarios(id)
    )''')
    conn.commit()


def adicionar_voluntario(conn, nome, usuario, senha, atribuicoes, disponibilidade, role='voluntario'):
    c = conn.cursor()
    hashed_senha = utils.hash_password(senha)
    c.execute("""
        INSERT INTO voluntarios (nome, usuario, senha, atribuicoes, disponibilidade, primeiro_acesso, role) 
        VALUES (?, ?, ?, ?, ?, 1, ?)
        """, (nome, usuario, hashed_senha, atribuicoes, disponibilidade, role))
    conn.commit()

def editar_voluntario(conn, vol_id, nome, usuario, senha, atribuicoes, disponibilidade, role):
    c = conn.cursor()
    query_parts = ["nome = ?", "usuario = ?", "atribuicoes = ?", "disponibilidade = ?", "role = ?"]
    params = [nome, usuario, atribuicoes, disponibilidade, role]

    if senha:
        query_parts.append("senha = ?")
        params.append(utils.hash_password(senha))
    
    query = f"UPDATE voluntarios SET {', '.join(query_parts)} WHERE id = ?"
    params.append(vol_id)
    c.execute(query, tuple(params))
    conn.commit()

def autenticar_voluntario(conn, usuario, senha_fornecida):
    c = conn.cursor()
    c.execute("SELECT * FROM voluntarios WHERE usuario = ?", (usuario,))
    user_data = c.fetchone()
    
    if user_data:
        hashed_senha_db = user_data['senha']
        if utils.check_password(senha_fornecida, hashed_senha_db):
            return user_data
    return None

def alterar_senha_e_status(conn, voluntario_id, nova_senha):
    c = conn.cursor()
    hashed_nova_senha = utils.hash_password(nova_senha)
    c.execute("""
        UPDATE voluntarios SET senha = ?, primeiro_acesso = 0 WHERE id = ?
    """, (hashed_nova_senha, voluntario_id))
    conn.commit()

# --- Manter as demais funções ---
def excluir_voluntario(conn, vol_id):
    c = conn.cursor()
    c.execute("DELETE FROM voluntarios WHERE id = ?", (vol_id,))
    conn.commit()

def listar_voluntarios(conn):
    return pd.read_sql_query("SELECT id, nome, usuario, atribuicoes, disponibilidade, primeiro_acesso, role FROM voluntarios", conn)

def get_voluntario_by_id(conn, voluntario_id):
    c = conn.cursor()
    c.execute("SELECT * FROM voluntarios WHERE id = ?", (voluntario_id,))
    return c.fetchone()

# Funções de disponibilidade
def salvar_disponibilidade(conn, voluntario_id, datas_disponiveis_str, ceia_passada, mes_ref):
    c = conn.cursor()
    try:
        c.execute("""
            UPDATE disponibilidades SET datas_disponiveis = ?, ceia_passada = ?, timestamp_registro = CURRENT_TIMESTAMP
            WHERE voluntario_id = ? AND mes_referencia = ?
        """, (datas_disponiveis_str, ceia_passada, voluntario_id, mes_ref))
        if c.rowcount == 0:
            c.execute("""
                INSERT INTO disponibilidades (voluntario_id, datas_disponiveis, ceia_passada, mes_referencia)
                VALUES (?, ?, ?, ?)
            """, (voluntario_id, datas_disponiveis_str, ceia_passada, mes_ref))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Erro ao salvar/atualizar disponibilidade: {e}")
        conn.rollback()
        return False

def carregar_disponibilidade(conn, voluntario_id, mes_ref):
    c = conn.cursor()
    c.execute("""
        SELECT datas_disponiveis, ceia_passada
        FROM disponibilidades
        WHERE voluntario_id = ? AND mes_referencia = ?
    """, (voluntario_id, mes_ref))
    result = c.fetchone()
    
    # MUDANÇA: Converte o resultado para um dicionário Python antes de retornar
    if result:
        return dict(result) # Garante que sempre retornamos um dicionário
    return None # Retorna None se nada for encontrado

def listar_disponibilidades_por_mes(conn, mes_referencia):
    return pd.read_sql_query("""
        SELECT v.id AS voluntario_id, v.nome, d.datas_disponiveis, d.ceia_passada
        FROM disponibilidades d
        JOIN voluntarios v ON v.id = d.voluntario_id
        WHERE d.mes_referencia = ?
    """, conn, params=(mes_referencia,))

# Funções de configuração
def get_edicao_liberada(conn, mes_ref):
    c = conn.cursor()
    c.execute("SELECT edicao_liberada FROM configuracoes_escalas WHERE mes_referencia = ?", (mes_ref,))
    result = c.fetchone()
    if result: return bool(result['edicao_liberada'])
    c.execute("INSERT OR IGNORE INTO configuracoes_escalas (mes_referencia, edicao_liberada) VALUES (?, FALSE)", (mes_ref,))
    conn.commit()
    return False

def set_edicao_liberada(conn, mes_ref, status):
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO configuracoes_escalas (mes_referencia, edicao_liberada, ultima_atualizacao)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(mes_referencia) DO UPDATE SET
            edicao_liberada = excluded.edicao_liberada, ultima_atualizacao = CURRENT_TIMESTAMP
        """, (mes_ref, status))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Erro ao definir status de edição: {e}")
        conn.rollback()
        return False

def get_all_meses_configurados(conn):
    c = conn.cursor()
    c.execute("SELECT mes_referencia FROM configuracoes_escalas ORDER BY mes_referencia DESC")
    return c.fetchall()

# --- NOVAS FUNÇÕES PARA GERENCIAR A ESCALA SALVA ---

def salvar_escala_gerada(conn, mes_referencia, escala_df_pronto):
    """Apaga a escala antiga do mês e salva a nova que já vem pronta."""
    c = conn.cursor()
    try:
        # Apaga qualquer escala existente para este mês para evitar duplicatas
        c.execute("DELETE FROM escala_gerada WHERE mes_referencia = ?", (mes_referencia,))
        
        # O DataFrame já vem com a coluna 'mes_referencia', então apenas o inserimos
        escala_df_pronto.to_sql('escala_gerada', conn, if_exists='append', index=False)
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao salvar escala gerada: {e}")
        conn.rollback()
        return False

def get_escala_por_voluntario(conn, voluntario_id):
    """Busca no banco todas as datas que um voluntário específico foi escalado."""
    query = """
        SELECT data_culto, funcao
        FROM escala_gerada
        WHERE voluntario_id = ?
        ORDER BY data_culto
    """
    return pd.read_sql_query(query, conn, params=(voluntario_id,))

def verificar_existencia_escala(conn, mes_referencia):
    """Verifica se já existe uma escala salva para o mês de referência."""
    c = conn.cursor()
    c.execute("SELECT 1 FROM escala_gerada WHERE mes_referencia = ? LIMIT 1", (mes_referencia,))
    return c.fetchone() is not None

def listar_escala_completa_por_mes(conn, mes_referencia):
    """Busca a escala completa de um mês para o editor."""
    return pd.read_sql_query(
        "SELECT data_culto, funcao, voluntario_nome FROM escala_gerada WHERE mes_referencia = ?",
        conn,
        params=(mes_referencia,)
    )

def get_contagem_servicos_passados(conn, mes_referencia_atual):
    """
    Conta quantas vezes cada voluntário foi escalado em meses ANTERIORES
    ao mês de referência atual. Retorna um DataFrame com [voluntario_id, contagem].
    """
    query = """
        SELECT voluntario_id, COUNT(*) as contagem
        FROM escala_gerada
        WHERE mes_referencia < ? AND voluntario_id IS NOT NULL
        GROUP BY voluntario_id
    """
    return pd.read_sql_query(query, conn, params=(mes_referencia_atual,))

def salvar_feedback(conn, voluntario_id, voluntario_nome, data_culto, funcao, comentario):
    """Salva um novo feedback no banco de dados, incluindo a função."""
    try:
        c = conn.cursor()
        # Adicionada a coluna 'funcao' na inserção
        c.execute("""
            INSERT INTO feedbacks (voluntario_id, voluntario_nome, data_culto, funcao, comentario)
            VALUES (?, ?, ?, ?, ?)
        """, (voluntario_id, voluntario_nome, data_culto, funcao, comentario))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao salvar feedback: {e}")
        conn.rollback()
        return False

def get_feedbacks(conn, status_filter: list = None):
    """Busca feedbacks, opcionalmente filtrando por uma lista de status."""
    if status_filter is None:
        status_filter = ['novo', 'boa_ideia'] # Por padrão, não mostra a lixeira
    
    placeholders = ','.join('?' for status in status_filter)
    query = f"SELECT * FROM feedbacks WHERE status IN ({placeholders}) ORDER BY timestamp_criacao DESC"
    
    return pd.read_sql_query(query, conn, params=status_filter)

def atualizar_status_feedback(conn, feedback_id, novo_status):
    """Atualiza o status de um feedback (ex: para 'boa_ideia' ou 'lixeira')."""
    try:
        c = conn.cursor()
        c.execute("UPDATE feedbacks SET status = ? WHERE id = ?", (novo_status, feedback_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao atualizar status do feedback: {e}")
        conn.rollback()
        return False

def feedback_ja_enviado(conn, voluntario_id, data_culto, funcao):
    """Verifica se um voluntário já enviou feedback para um culto e função específicos."""
    c = conn.cursor()
    c.execute("SELECT 1 FROM feedbacks WHERE voluntario_id = ? AND data_culto = ? AND funcao = ?", (voluntario_id, data_culto, funcao))
    return c.fetchone() is not None