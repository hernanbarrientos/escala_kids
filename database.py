# database.py
import streamlit as st
import pandas as pd
import utils
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

@st.cache_resource
def get_engine():
    """Cria e armazena em cache o engine de conexão SQLAlchemy para performance."""
    try:
        db_url = st.secrets["DATABASE_URL"]
        return create_engine(db_url)
    except Exception as e:
        st.error(f"Erro crítico ao configurar a conexão com o banco de dados: {e}")
        st.stop()

def criar_tabelas():
    """Executa os comandos CREATE TABLE IF NOT EXISTS no banco de dados."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            with conn.begin() as transaction:
                conn.execute(text("CREATE TABLE IF NOT EXISTS voluntarios (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, usuario TEXT UNIQUE NOT NULL, senha TEXT NOT NULL, atribuicoes TEXT, disponibilidade TEXT, primeiro_acesso INTEGER DEFAULT 1, role TEXT DEFAULT 'voluntario')"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_voluntarios_usuario_case_insensitive ON voluntarios (LOWER(usuario));"))
                conn.execute(text("CREATE TABLE IF NOT EXISTS disponibilidades (id SERIAL PRIMARY KEY, voluntario_id INTEGER NOT NULL REFERENCES voluntarios(id) ON DELETE CASCADE, datas_disponiveis TEXT, ceia_passada TEXT, mes_referencia TEXT NOT NULL, indisponivel_o_mes_todo BOOLEAN DEFAULT FALSE, timestamp_registro TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, UNIQUE(voluntario_id, mes_referencia))"))
                conn.execute(text("CREATE TABLE IF NOT EXISTS configuracoes_escalas (id SERIAL PRIMARY KEY, mes_referencia TEXT NOT NULL UNIQUE, edicao_liberada BOOLEAN DEFAULT FALSE, ultima_atualizacao TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP)"))
                conn.execute(text("CREATE TABLE IF NOT EXISTS escala_gerada (id SERIAL PRIMARY KEY, mes_referencia TEXT NOT NULL, data_culto TEXT NOT NULL, funcao TEXT NOT NULL, voluntario_id INTEGER REFERENCES voluntarios(id) ON DELETE SET NULL, voluntario_nome TEXT)"))
                conn.execute(text("CREATE TABLE IF NOT EXISTS solicitacoes_troca (id SERIAL PRIMARY KEY, escala_original_id INTEGER NOT NULL REFERENCES escala_gerada(id) ON DELETE CASCADE, solicitante_id INTEGER NOT NULL REFERENCES voluntarios(id) ON DELETE CASCADE, substituto_id INTEGER NOT NULL REFERENCES voluntarios(id) ON DELETE CASCADE, solicitante_nome TEXT NOT NULL, substituto_nome TEXT NOT NULL, data_culto TEXT NOT NULL, funcao TEXT NOT NULL, status TEXT DEFAULT 'pendente', timestamp_solicitacao TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP)"))
                conn.execute(text("CREATE TABLE IF NOT EXISTS feedbacks (id SERIAL PRIMARY KEY, voluntario_id INTEGER NOT NULL REFERENCES voluntarios(id) ON DELETE CASCADE, voluntario_nome TEXT NOT NULL, data_culto TEXT NOT NULL, funcao TEXT NOT NULL, comentario TEXT NOT NULL, status TEXT DEFAULT 'novo', timestamp_criacao TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP)"))
                conn.execute(text("CREATE TABLE IF NOT EXISTS vinculos_voluntarios (id SERIAL PRIMARY KEY, voluntario_a_id INTEGER NOT NULL REFERENCES voluntarios(id) ON DELETE CASCADE, voluntario_b_id INTEGER NOT NULL REFERENCES voluntarios(id) ON DELETE CASCADE, UNIQUE(voluntario_a_id, voluntario_b_id))"))

                result = conn.execute(text("SELECT COUNT(*) FROM voluntarios WHERE usuario ILIKE :user"), {'user': 'admin'}).scalar_one()
                if result == 0:
                    senha_hash = utils.hash_password("admin123")
                    conn.execute(text("INSERT INTO voluntarios (nome, usuario, senha, primeiro_acesso, role) VALUES (:nome, :user, :senha, 0, 'admin')"), {'nome': 'Administrador', 'user': 'admin', 'senha': senha_hash})
                transaction.commit()
    except Exception as e:
        print(f"Erro ao criar tabelas: {e}")

def adicionar_voluntario(nome, usuario, senha, atribuicoes, disponibilidade, role='voluntario'):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            hashed_senha = utils.hash_password(senha)
            conn.execute(text("INSERT INTO voluntarios (nome, usuario, senha, atribuicoes, disponibilidade, primeiro_acesso, role) VALUES (:n, :u, :s, :a, :d, 1, :r)"), {'n': nome, 'u': usuario, 's': hashed_senha, 'a': atribuicoes, 'd': disponibilidade, 'r': role})
            transaction.commit()

def editar_voluntario(vol_id, nome, usuario, senha, atribuicoes, disponibilidade, role):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            query_parts = ["nome = :nome", "usuario = :usuario", "atribuicoes = :atribuicoes", "disponibilidade = :disponibilidade", "role = :role"]
            params = {'vol_id': vol_id, 'nome': nome, 'usuario': usuario, 'atribuicoes': atribuicoes, 'disponibilidade': disponibilidade, 'role': role}
            if senha:
                query_parts.append("senha = :senha")
                params['senha'] = utils.hash_password(senha)
            query = f"UPDATE voluntarios SET {', '.join(query_parts)} WHERE id = :vol_id"
            conn.execute(text(query), params)
            transaction.commit()

def autenticar_voluntario(usuario, senha_fornecida):
    engine = get_engine()
    with engine.connect() as conn:
        query = text("SELECT * FROM voluntarios WHERE usuario ILIKE :user")
        result = conn.execute(query, {'user': usuario}).fetchone()
        if result:
            user_data = result._asdict()
            if utils.check_password(senha_fornecida, user_data['senha']):
                return user_data
    return None

def alterar_senha_e_status(voluntario_id, nova_senha):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            hashed_nova_senha = utils.hash_password(nova_senha)
            conn.execute(text("UPDATE voluntarios SET senha = :senha, primeiro_acesso = 0 WHERE id = :id"), {'senha': hashed_nova_senha, 'id': voluntario_id})
            transaction.commit()

def excluir_voluntario(vol_id):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            conn.execute(text("DELETE FROM voluntarios WHERE id = :id"), {'id': vol_id})
            transaction.commit()

def listar_voluntarios():
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql("SELECT id, nome, usuario, atribuicoes, disponibilidade, primeiro_acesso, role FROM voluntarios ORDER BY nome", conn)

def get_voluntario_by_id(voluntario_id):
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM voluntarios WHERE id = :id"), {'id': voluntario_id}).fetchone()
        return result._asdict() if result else None

def salvar_disponibilidade(voluntario_id, datas_disponiveis_str, ceia_passada, mes_ref):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            conn.execute(text("""
                INSERT INTO disponibilidades (voluntario_id, mes_referencia, datas_disponiveis, ceia_passada)
                VALUES (:vol_id, :mes_ref, :datas, :ceia)
                ON CONFLICT (voluntario_id, mes_referencia)
                DO UPDATE SET datas_disponiveis = EXCLUDED.datas_disponiveis, ceia_passada = EXCLUDED.ceia_passada, timestamp_registro = CURRENT_TIMESTAMP;
            """), {'vol_id': voluntario_id, 'mes_ref': mes_ref, 'datas': datas_disponiveis_str, 'ceia': ceia_passada})
            transaction.commit()
    return True

def carregar_disponibilidade(voluntario_id, mes_ref):
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT datas_disponiveis, ceia_passada FROM disponibilidades WHERE voluntario_id = :id AND mes_referencia = :mes_ref"), {'id': voluntario_id, 'mes_ref': mes_ref}).fetchone()
        if result: return result._asdict()
    return None

def listar_disponibilidades_por_mes(mes_referencia):
    engine = get_engine()
    with engine.connect() as conn:
        query = text("SELECT v.id AS voluntario_id, v.nome AS voluntario_nome, d.datas_disponiveis, d.ceia_passada FROM disponibilidades d JOIN voluntarios v ON v.id = d.voluntario_id WHERE d.mes_referencia = :mes_ref")
        return pd.read_sql(query, conn, params={'mes_ref': mes_referencia})

def get_edicao_liberada(mes_ref):
    engine = get_engine()
    with engine.connect() as conn:
        query = text("SELECT edicao_liberada FROM configuracoes_escalas WHERE mes_referencia = :mes_ref")
        result = conn.execute(query, {'mes_ref': mes_ref}).scalar_one_or_none()
        if result is None:
            with conn.begin() as transaction:
                conn.execute(text("INSERT INTO configuracoes_escalas (mes_referencia, edicao_liberada) VALUES (:mes_ref, FALSE) ON CONFLICT (mes_referencia) DO NOTHING"), {'mes_ref': mes_ref})
                transaction.commit()
            return False
        return bool(result)

def set_edicao_liberada(mes_ref, status):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            conn.execute(text("UPDATE configuracoes_escalas SET edicao_liberada = :status, ultima_atualizacao = CURRENT_TIMESTAMP WHERE mes_referencia = :mes_ref"), {'status': status, 'mes_ref': mes_ref})
            transaction.commit()
    return True

def get_all_meses_configurados():
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT mes_referencia FROM configuracoes_escalas ORDER BY mes_referencia DESC")).fetchall()
        return [row._asdict() for row in result]

def salvar_escala_gerada(mes_referencia, escala_df_pronto):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            conn.execute(text("DELETE FROM escala_gerada WHERE mes_referencia = :mes_ref"), {'mes_ref': mes_referencia})
            escala_df_pronto.to_sql('escala_gerada', conn, if_exists='append', index=False)
            transaction.commit()
    return True

def get_escala_por_voluntario(voluntario_id):
    engine = get_engine()
    with engine.connect() as conn:
        query = text("SELECT id, data_culto, funcao FROM escala_gerada WHERE voluntario_id = :id ORDER BY data_culto")
        return pd.read_sql(query, conn, params={'id': voluntario_id})

def verificar_existencia_escala(mes_referencia):
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 FROM escala_gerada WHERE mes_referencia = :mes_ref LIMIT 1"), {'mes_ref': mes_referencia}).scalar_one_or_none()
    return result is not None

def listar_escala_completa_por_mes(mes_referencia):
    engine = get_engine()
    with engine.connect() as conn:
        query = text("SELECT data_culto, funcao, voluntario_nome FROM escala_gerada WHERE mes_referencia = :mes_ref")
        return pd.read_sql(query, conn, params={'mes_ref': mes_referencia})

def get_contagem_servicos_passados(mes_referencia_atual):
    engine = get_engine()
    with engine.connect() as conn:
        query = text("SELECT voluntario_id, COUNT(*) as contagem FROM escala_gerada WHERE mes_referencia < :mes_ref AND voluntario_id IS NOT NULL GROUP BY voluntario_id")
        return pd.read_sql(query, conn, params={'mes_ref': mes_referencia_atual})

def salvar_feedback(voluntario_id, voluntario_nome, data_culto, funcao, comentario):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            conn.execute(text("INSERT INTO feedbacks (voluntario_id, voluntario_nome, data_culto, funcao, comentario) VALUES (:vol_id, :vol_nome, :data, :funcao, :comentario)"), {'vol_id': voluntario_id, 'vol_nome': voluntario_nome, 'data': data_culto, 'funcao': funcao, 'comentario': comentario})
            transaction.commit()
    return True

def get_feedbacks(status_filter: list = None):
    engine = get_engine()
    with engine.connect() as conn:
        if status_filter is None: status_filter = ['novo', 'boa_ideia', 'resolvido']
        query = text("SELECT * FROM feedbacks WHERE status = ANY(:status_filter) ORDER BY timestamp_criacao DESC")
        return pd.read_sql(query, conn, params={'status_filter': tuple(status_filter)})

def atualizar_status_feedback(feedback_id, novo_status):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            conn.execute(text("UPDATE feedbacks SET status = :status WHERE id = :id"), {'status': novo_status, 'id': feedback_id})
            transaction.commit()
    return True

def feedback_ja_enviado(voluntario_id, data_culto, funcao):
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 FROM feedbacks WHERE voluntario_id = :vol_id AND data_culto = :data AND funcao = :funcao"), {'vol_id': voluntario_id, 'data': data_culto, 'funcao': funcao}).scalar_one_or_none()
    return result is not None

def criar_solicitacao_substituicao(escala_original_id, solicitante_id, solicitante_nome, substituto_id, substituto_nome, data_culto, funcao):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            conn.execute(text("INSERT INTO solicitacoes_troca (escala_original_id, solicitante_id, solicitante_nome, substituto_id, substituto_nome, data_culto, funcao) VALUES (:escala_id, :sol_id, :sol_nome, :sub_id, :sub_nome, :data, :funcao)"), {'escala_id': escala_original_id, 'sol_id': solicitante_id, 'sol_nome': solicitante_nome, 'sub_id': substituto_id, 'sub_nome': substituto_nome, 'data': data_culto, 'funcao': funcao})
            transaction.commit()
    return True

def get_solicitacoes_pendentes():
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql("SELECT * FROM solicitacoes_troca WHERE status = 'pendente' ORDER BY timestamp_solicitacao DESC", conn)

def get_solicitacao_by_id(solicitacao_id):
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM solicitacoes_troca WHERE id = :id"), {'id': solicitacao_id}).fetchone()
        return result._asdict() if result else None

def processar_solicitacao(solicitacao_id, novo_status):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            if novo_status == 'aprovada':
                solicitacao = get_solicitacao_by_id(solicitacao_id)
                if not solicitacao: raise ValueError("Solicitação não encontrada.")
                conn.execute(text("UPDATE escala_gerada SET voluntario_id = :sub_id, voluntario_nome = :sub_nome WHERE id = :escala_id"), {'sub_id': solicitacao['substituto_id'], 'sub_nome': solicitacao['substituto_nome'], 'escala_id': solicitacao['escala_original_id']})
                if solicitacao['funcao'] == 'Recepção':
                    conn.execute(text("UPDATE escala_gerada SET voluntario_id = :sub_id, voluntario_nome = :sub_nome WHERE data_culto = :data AND funcao = 'Apoio' AND voluntario_id = :sol_id"), {'sub_id': solicitacao['substituto_id'], 'sub_nome': solicitacao['substituto_nome'], 'data': solicitacao['data_culto'], 'sol_id': solicitacao['solicitante_id']})
            conn.execute(text("UPDATE solicitacoes_troca SET status = :status WHERE id = :id"), {'status': novo_status, 'id': solicitacao_id})
            transaction.commit()
    return True

def get_status_indisponibilidade_mes(voluntario_id, mes_referencia):
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT indisponivel_o_mes_todo FROM disponibilidades WHERE voluntario_id = :id AND mes_referencia = :mes_ref"), {'id': voluntario_id, 'mes_ref': mes_referencia}).fetchone()
        if result and result._asdict().get('indisponivel_o_mes_todo') is not None:
            return result._asdict()['indisponivel_o_mes_todo']
    return False

def set_status_indisponibilidade_mes(voluntario_id, mes_referencia, status: bool):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            conn.execute(text("""
                INSERT INTO disponibilidades (voluntario_id, mes_referencia, indisponivel_o_mes_todo)
                VALUES (:vol_id, :mes_ref, :status)
                ON CONFLICT (voluntario_id, mes_referencia)
                DO UPDATE SET indisponivel_o_mes_todo = :status;
            """), {'vol_id': voluntario_id, 'mes_ref': mes_referencia, 'status': status})
            transaction.commit()
    return True

def get_ids_indisponiveis_para_o_mes(mes_referencia):
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text("SELECT voluntario_id FROM disponibilidades WHERE mes_referencia = :mes_ref AND indisponivel_o_mes_todo = TRUE"), conn, params={'mes_ref': mes_referencia})
        return df['voluntario_id'].tolist()

def criar_vinculo(voluntario_a_id, voluntario_b_id):
    if voluntario_a_id == voluntario_b_id: return
    id_1, id_2 = min(voluntario_a_id, voluntario_b_id), max(voluntario_a_id, voluntario_b_id)
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            try:
                conn.execute(text("INSERT INTO vinculos_voluntarios (voluntario_a_id, voluntario_b_id) VALUES (:id1, :id2)"), {'id1': id_1, 'id2': id_2})
                transaction.commit()
            except IntegrityError:
                transaction.rollback()

def listar_vinculos():
    engine = get_engine()
    with engine.connect() as conn:
        query = text("""
            SELECT v.id as vinculo_id, v.voluntario_a_id, va.nome as nome_a, v.voluntario_b_id, vb.nome as nome_b
            FROM vinculos_voluntarios v
            JOIN voluntarios va ON v.voluntario_a_id = va.id
            JOIN voluntarios vb ON v.voluntario_b_id = vb.id
            ORDER BY va.nome, vb.nome
        """)
        return pd.read_sql(query, conn)

def excluir_vinculo(vinculo_id):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            conn.execute(text("DELETE FROM vinculos_voluntarios WHERE id = :id"), {'id': vinculo_id})
            transaction.commit()

def get_vinculos_para_geracao():
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT voluntario_a_id, voluntario_b_id FROM vinculos_voluntarios")).fetchall()
        return [(row[0], row[1]) for row in result]# database.py
import streamlit as st
import pandas as pd
import utils
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

@st.cache_resource
def get_engine():
    """Cria e armazena em cache o engine de conexão SQLAlchemy para performance."""
    try:
        db_url = st.secrets["DATABASE_URL"]
        return create_engine(db_url)
    except Exception as e:
        st.error(f"Erro crítico ao configurar a conexão com o banco de dados: {e}")
        st.stop()

def criar_tabelas():
    """Executa os comandos CREATE TABLE IF NOT EXISTS no banco de dados."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            with conn.begin() as transaction:
                conn.execute(text("CREATE TABLE IF NOT EXISTS voluntarios (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, usuario TEXT UNIQUE NOT NULL, senha TEXT NOT NULL, atribuicoes TEXT, disponibilidade TEXT, primeiro_acesso INTEGER DEFAULT 1, role TEXT DEFAULT 'voluntario')"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_voluntarios_usuario_case_insensitive ON voluntarios (LOWER(usuario));"))
                conn.execute(text("CREATE TABLE IF NOT EXISTS disponibilidades (id SERIAL PRIMARY KEY, voluntario_id INTEGER NOT NULL REFERENCES voluntarios(id) ON DELETE CASCADE, datas_disponiveis TEXT, ceia_passada TEXT, mes_referencia TEXT NOT NULL, indisponivel_o_mes_todo BOOLEAN DEFAULT FALSE, timestamp_registro TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, UNIQUE(voluntario_id, mes_referencia))"))
                conn.execute(text("CREATE TABLE IF NOT EXISTS configuracoes_escalas (id SERIAL PRIMARY KEY, mes_referencia TEXT NOT NULL UNIQUE, edicao_liberada BOOLEAN DEFAULT FALSE, ultima_atualizacao TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP)"))
                conn.execute(text("CREATE TABLE IF NOT EXISTS escala_gerada (id SERIAL PRIMARY KEY, mes_referencia TEXT NOT NULL, data_culto TEXT NOT NULL, funcao TEXT NOT NULL, voluntario_id INTEGER REFERENCES voluntarios(id) ON DELETE SET NULL, voluntario_nome TEXT)"))
                conn.execute(text("CREATE TABLE IF NOT EXISTS solicitacoes_troca (id SERIAL PRIMARY KEY, escala_original_id INTEGER NOT NULL REFERENCES escala_gerada(id) ON DELETE CASCADE, solicitante_id INTEGER NOT NULL REFERENCES voluntarios(id) ON DELETE CASCADE, substituto_id INTEGER NOT NULL REFERENCES voluntarios(id) ON DELETE CASCADE, solicitante_nome TEXT NOT NULL, substituto_nome TEXT NOT NULL, data_culto TEXT NOT NULL, funcao TEXT NOT NULL, status TEXT DEFAULT 'pendente', timestamp_solicitacao TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP)"))
                conn.execute(text("CREATE TABLE IF NOT EXISTS feedbacks (id SERIAL PRIMARY KEY, voluntario_id INTEGER NOT NULL REFERENCES voluntarios(id) ON DELETE CASCADE, voluntario_nome TEXT NOT NULL, data_culto TEXT NOT NULL, funcao TEXT NOT NULL, comentario TEXT NOT NULL, status TEXT DEFAULT 'novo', timestamp_criacao TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP)"))
                conn.execute(text("CREATE TABLE IF NOT EXISTS vinculos_voluntarios (id SERIAL PRIMARY KEY, voluntario_a_id INTEGER NOT NULL REFERENCES voluntarios(id) ON DELETE CASCADE, voluntario_b_id INTEGER NOT NULL REFERENCES voluntarios(id) ON DELETE CASCADE, UNIQUE(voluntario_a_id, voluntario_b_id))"))

                result = conn.execute(text("SELECT COUNT(*) FROM voluntarios WHERE usuario ILIKE :user"), {'user': 'admin'}).scalar_one()
                if result == 0:
                    senha_hash = utils.hash_password("admin123")
                    conn.execute(text("INSERT INTO voluntarios (nome, usuario, senha, primeiro_acesso, role) VALUES (:nome, :user, :senha, 0, 'admin')"), {'nome': 'Administrador', 'user': 'admin', 'senha': senha_hash})
                transaction.commit()
    except Exception as e:
        print(f"Erro ao criar tabelas: {e}")

def adicionar_voluntario(nome, usuario, senha, atribuicoes, disponibilidade, role='voluntario'):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            hashed_senha = utils.hash_password(senha)
            conn.execute(text("INSERT INTO voluntarios (nome, usuario, senha, atribuicoes, disponibilidade, primeiro_acesso, role) VALUES (:n, :u, :s, :a, :d, 1, :r)"), {'n': nome, 'u': usuario, 's': hashed_senha, 'a': atribuicoes, 'd': disponibilidade, 'r': role})
            transaction.commit()

def editar_voluntario(vol_id, nome, usuario, senha, atribuicoes, disponibilidade, role):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            query_parts = ["nome = :nome", "usuario = :usuario", "atribuicoes = :atribuicoes", "disponibilidade = :disponibilidade", "role = :role"]
            params = {'vol_id': vol_id, 'nome': nome, 'usuario': usuario, 'atribuicoes': atribuicoes, 'disponibilidade': disponibilidade, 'role': role}
            if senha:
                query_parts.append("senha = :senha")
                params['senha'] = utils.hash_password(senha)
            query = f"UPDATE voluntarios SET {', '.join(query_parts)} WHERE id = :vol_id"
            conn.execute(text(query), params)
            transaction.commit()

def autenticar_voluntario(usuario, senha_fornecida):
    engine = get_engine()
    with engine.connect() as conn:
        query = text("SELECT * FROM voluntarios WHERE usuario ILIKE :user")
        result = conn.execute(query, {'user': usuario}).fetchone()
        if result:
            user_data = result._asdict()
            if utils.check_password(senha_fornecida, user_data['senha']):
                return user_data
    return None

def alterar_senha_e_status(voluntario_id, nova_senha):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            hashed_nova_senha = utils.hash_password(nova_senha)
            conn.execute(text("UPDATE voluntarios SET senha = :senha, primeiro_acesso = 0 WHERE id = :id"), {'senha': hashed_nova_senha, 'id': voluntario_id})
            transaction.commit()

def excluir_voluntario(vol_id):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            conn.execute(text("DELETE FROM voluntarios WHERE id = :id"), {'id': vol_id})
            transaction.commit()

def listar_voluntarios():
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql("SELECT id, nome, usuario, atribuicoes, disponibilidade, primeiro_acesso, role FROM voluntarios ORDER BY nome", conn)

def get_voluntario_by_id(voluntario_id):
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM voluntarios WHERE id = :id"), {'id': voluntario_id}).fetchone()
        return result._asdict() if result else None

def salvar_disponibilidade(voluntario_id, datas_disponiveis_str, ceia_passada, mes_ref):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            conn.execute(text("""
                INSERT INTO disponibilidades (voluntario_id, mes_referencia, datas_disponiveis, ceia_passada)
                VALUES (:vol_id, :mes_ref, :datas, :ceia)
                ON CONFLICT (voluntario_id, mes_referencia)
                DO UPDATE SET datas_disponiveis = EXCLUDED.datas_disponiveis, ceia_passada = EXCLUDED.ceia_passada, timestamp_registro = CURRENT_TIMESTAMP;
            """), {'vol_id': voluntario_id, 'mes_ref': mes_ref, 'datas': datas_disponiveis_str, 'ceia': ceia_passada})
            transaction.commit()
    return True

def carregar_disponibilidade(voluntario_id, mes_ref):
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT datas_disponiveis, ceia_passada FROM disponibilidades WHERE voluntario_id = :id AND mes_referencia = :mes_ref"), {'id': voluntario_id, 'mes_ref': mes_ref}).fetchone()
        if result: return result._asdict()
    return None

def listar_disponibilidades_por_mes(mes_referencia):
    engine = get_engine()
    with engine.connect() as conn:
        query = text("SELECT v.id AS voluntario_id, v.nome AS voluntario_nome, d.datas_disponiveis, d.ceia_passada FROM disponibilidades d JOIN voluntarios v ON v.id = d.voluntario_id WHERE d.mes_referencia = :mes_ref")
        return pd.read_sql(query, conn, params={'mes_ref': mes_referencia})

def get_edicao_liberada(mes_ref):
    engine = get_engine()
    with engine.connect() as conn:
        query = text("SELECT edicao_liberada FROM configuracoes_escalas WHERE mes_referencia = :mes_ref")
        result = conn.execute(query, {'mes_ref': mes_ref}).scalar_one_or_none()
        if result is None:
            with conn.begin() as transaction:
                conn.execute(text("INSERT INTO configuracoes_escalas (mes_referencia, edicao_liberada) VALUES (:mes_ref, FALSE) ON CONFLICT (mes_referencia) DO NOTHING"), {'mes_ref': mes_ref})
                transaction.commit()
            return False
        return bool(result)

def set_edicao_liberada(mes_ref, status):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            conn.execute(text("UPDATE configuracoes_escalas SET edicao_liberada = :status, ultima_atualizacao = CURRENT_TIMESTAMP WHERE mes_referencia = :mes_ref"), {'status': status, 'mes_ref': mes_ref})
            transaction.commit()
    return True

def get_all_meses_configurados():
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT mes_referencia FROM configuracoes_escalas ORDER BY mes_referencia DESC")).fetchall()
        return [row._asdict() for row in result]

def salvar_escala_gerada(mes_referencia, escala_df_pronto):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            conn.execute(text("DELETE FROM escala_gerada WHERE mes_referencia = :mes_ref"), {'mes_ref': mes_referencia})
            escala_df_pronto.to_sql('escala_gerada', conn, if_exists='append', index=False)
            transaction.commit()
    return True

def get_escala_por_voluntario(voluntario_id):
    engine = get_engine()
    with engine.connect() as conn:
        query = text("SELECT id, data_culto, funcao FROM escala_gerada WHERE voluntario_id = :id ORDER BY data_culto")
        return pd.read_sql(query, conn, params={'id': voluntario_id})

def verificar_existencia_escala(mes_referencia):
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 FROM escala_gerada WHERE mes_referencia = :mes_ref LIMIT 1"), {'mes_ref': mes_referencia}).scalar_one_or_none()
    return result is not None

def listar_escala_completa_por_mes(mes_referencia):
    engine = get_engine()
    with engine.connect() as conn:
        query = text("SELECT data_culto, funcao, voluntario_nome FROM escala_gerada WHERE mes_referencia = :mes_ref")
        return pd.read_sql(query, conn, params={'mes_ref': mes_referencia})

def get_contagem_servicos_passados(mes_referencia_atual):
    engine = get_engine()
    with engine.connect() as conn:
        query = text("SELECT voluntario_id, COUNT(*) as contagem FROM escala_gerada WHERE mes_referencia < :mes_ref AND voluntario_id IS NOT NULL GROUP BY voluntario_id")
        return pd.read_sql(query, conn, params={'mes_ref': mes_referencia_atual})

def salvar_feedback(voluntario_id, voluntario_nome, data_culto, funcao, comentario):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            conn.execute(text("INSERT INTO feedbacks (voluntario_id, voluntario_nome, data_culto, funcao, comentario) VALUES (:vol_id, :vol_nome, :data, :funcao, :comentario)"), {'vol_id': voluntario_id, 'vol_nome': voluntario_nome, 'data': data_culto, 'funcao': funcao, 'comentario': comentario})
            transaction.commit()
    return True

def get_feedbacks(status_filter: list = None):
    engine = get_engine()
    with engine.connect() as conn:
        if status_filter is None: status_filter = ['novo', 'boa_ideia', 'resolvido']
        query = text("SELECT * FROM feedbacks WHERE status = ANY(:status_filter) ORDER BY timestamp_criacao DESC")
        return pd.read_sql(query, conn, params={'status_filter': tuple(status_filter)})

def atualizar_status_feedback(feedback_id, novo_status):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            conn.execute(text("UPDATE feedbacks SET status = :status WHERE id = :id"), {'status': novo_status, 'id': feedback_id})
            transaction.commit()
    return True

def feedback_ja_enviado(voluntario_id, data_culto, funcao):
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 FROM feedbacks WHERE voluntario_id = :vol_id AND data_culto = :data AND funcao = :funcao"), {'vol_id': voluntario_id, 'data': data_culto, 'funcao': funcao}).scalar_one_or_none()
    return result is not None

def criar_solicitacao_substituicao(escala_original_id, solicitante_id, solicitante_nome, substituto_id, substituto_nome, data_culto, funcao):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            conn.execute(text("INSERT INTO solicitacoes_troca (escala_original_id, solicitante_id, solicitante_nome, substituto_id, substituto_nome, data_culto, funcao) VALUES (:escala_id, :sol_id, :sol_nome, :sub_id, :sub_nome, :data, :funcao)"), {'escala_id': escala_original_id, 'sol_id': solicitante_id, 'sol_nome': solicitante_nome, 'sub_id': substituto_id, 'sub_nome': substituto_nome, 'data': data_culto, 'funcao': funcao})
            transaction.commit()
    return True

def get_solicitacoes_pendentes():
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql("SELECT * FROM solicitacoes_troca WHERE status = 'pendente' ORDER BY timestamp_solicitacao DESC", conn)

def get_solicitacao_by_id(solicitacao_id):
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM solicitacoes_troca WHERE id = :id"), {'id': solicitacao_id}).fetchone()
        return result._asdict() if result else None

def processar_solicitacao(solicitacao_id, novo_status):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            if novo_status == 'aprovada':
                solicitacao = get_solicitacao_by_id(solicitacao_id)
                if not solicitacao: raise ValueError("Solicitação não encontrada.")
                conn.execute(text("UPDATE escala_gerada SET voluntario_id = :sub_id, voluntario_nome = :sub_nome WHERE id = :escala_id"), {'sub_id': solicitacao['substituto_id'], 'sub_nome': solicitacao['substituto_nome'], 'escala_id': solicitacao['escala_original_id']})
                if solicitacao['funcao'] == 'Recepção':
                    conn.execute(text("UPDATE escala_gerada SET voluntario_id = :sub_id, voluntario_nome = :sub_nome WHERE data_culto = :data AND funcao = 'Apoio' AND voluntario_id = :sol_id"), {'sub_id': solicitacao['substituto_id'], 'sub_nome': solicitacao['substituto_nome'], 'data': solicitacao['data_culto'], 'sol_id': solicitacao['solicitante_id']})
            conn.execute(text("UPDATE solicitacoes_troca SET status = :status WHERE id = :id"), {'status': novo_status, 'id': solicitacao_id})
            transaction.commit()
    return True

def get_status_indisponibilidade_mes(voluntario_id, mes_referencia):
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT indisponivel_o_mes_todo FROM disponibilidades WHERE voluntario_id = :id AND mes_referencia = :mes_ref"), {'id': voluntario_id, 'mes_ref': mes_referencia}).fetchone()
        if result and result._asdict().get('indisponivel_o_mes_todo') is not None:
            return result._asdict()['indisponivel_o_mes_todo']
    return False

def set_status_indisponibilidade_mes(voluntario_id, mes_referencia, status: bool):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            conn.execute(text("""
                INSERT INTO disponibilidades (voluntario_id, mes_referencia, indisponivel_o_mes_todo)
                VALUES (:vol_id, :mes_ref, :status)
                ON CONFLICT (voluntario_id, mes_referencia)
                DO UPDATE SET indisponivel_o_mes_todo = :status;
            """), {'vol_id': voluntario_id, 'mes_ref': mes_referencia, 'status': status})
            transaction.commit()
    return True

def get_ids_indisponiveis_para_o_mes(mes_referencia):
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text("SELECT voluntario_id FROM disponibilidades WHERE mes_referencia = :mes_ref AND indisponivel_o_mes_todo = TRUE"), conn, params={'mes_ref': mes_referencia})
        return df['voluntario_id'].tolist()

def criar_vinculo(voluntario_a_id, voluntario_b_id):
    if voluntario_a_id == voluntario_b_id: return
    id_1, id_2 = min(voluntario_a_id, voluntario_b_id), max(voluntario_a_id, voluntario_b_id)
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            try:
                conn.execute(text("INSERT INTO vinculos_voluntarios (voluntario_a_id, voluntario_b_id) VALUES (:id1, :id2)"), {'id1': id_1, 'id2': id_2})
                transaction.commit()
            except IntegrityError:
                transaction.rollback()

def listar_vinculos():
    engine = get_engine()
    with engine.connect() as conn:
        query = text("""
            SELECT v.id as vinculo_id, v.voluntario_a_id, va.nome as nome_a, v.voluntario_b_id, vb.nome as nome_b
            FROM vinculos_voluntarios v
            JOIN voluntarios va ON v.voluntario_a_id = va.id
            JOIN voluntarios vb ON v.voluntario_b_id = vb.id
            ORDER BY va.nome, vb.nome
        """)
        return pd.read_sql(query, conn)

def excluir_vinculo(vinculo_id):
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            conn.execute(text("DELETE FROM vinculos_voluntarios WHERE id = :id"), {'id': vinculo_id})
            transaction.commit()

def get_vinculos_para_geracao():
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT voluntario_a_id, voluntario_b_id FROM vinculos_voluntarios")).fetchall()
        return [(row[0], row[1]) for row in result]