# Aplicativo com painel de administração para voluntários

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
import locale

# --- CONFIGURAÇÃO DA PÁGINA E LOCALIDADE ---
st.set_page_config(page_title="Gestão de Voluntários - Ministério Infantil")

# Define a localidade para português do Brasil para obter nomes de meses corretos
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    # Fallback para outros sistemas operacionais
    locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')


# --- CONEXÃO COM BANCO DE DADOS ---
conn = sqlite3.connect("voluntarios.db")
c = conn.cursor()

# --- CRIAÇÃO DAS TABELAS (se não existirem) ---
c.execute('''CREATE TABLE IF NOT EXISTS voluntarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT,
    senha TEXT,
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

# --- FUNÇÕES AUXILIARES ---

def get_dias_culto_proximo_mes():
    """
    Gera uma lista de opções para indisponibilidade baseada nas quintas e domingos
    do próximo mês.
    """
    hoje = datetime.now()
    proximo_mes_data = hoje + relativedelta(months=1)
    ano = proximo_mes_data.year
    mes = proximo_mes_data.month

    # Obtém o nome do mês em português, capitalizado
    nome_mes_ref = proximo_mes_data.strftime("%B").capitalize()

    opcoes_indisponibilidade = []
    # Obtém o número de dias no mês
    num_dias = calendar.monthrange(ano, mes)[1]

    for dia in range(1, num_dias + 1):
        data_atual = datetime(ano, mes, dia)
        dia_da_semana = data_atual.weekday()  # Segunda-feira é 0 e Domingo é 6

        # Quinta-feira (weekday == 3)
        if dia_da_semana == 3:
            opcoes_indisponibilidade.append(f"{data_atual.strftime('%d/%m')} - Quinta-feira")
        # Domingo (weekday == 6)
        elif dia_da_semana == 6:
            opcoes_indisponibilidade.append(f"{data_atual.strftime('%d/%m')} - Domingo Manhã")
            opcoes_indisponibilidade.append(f"{data_atual.strftime('%d/%m')} - Domingo Noite")

    return opcoes_indisponibilidade, f"{nome_mes_ref} de {ano}"


def adicionar_voluntario(nome, email, senha, atribuicoes, disponibilidade):
    c.execute("INSERT INTO voluntarios (nome, email, senha, atribuicoes, disponibilidade) VALUES (?, ?, ?, ?, ?)",
              (nome, email, senha, atribuicoes, disponibilidade))
    conn.commit()

def editar_voluntario(vol_id, nome, email, senha, atribuicoes, disponibilidade):
    c.execute("""
        UPDATE voluntarios 
        SET nome = ?, email = ?, senha = ?, atribuicoes = ?, disponibilidade = ?
        WHERE id = ?
    """, (nome, email, senha, atribuicoes, disponibilidade, vol_id))
    conn.commit()

def excluir_voluntario(vol_id):
    c.execute("DELETE FROM voluntarios WHERE id = ?", (vol_id,))
    conn.commit()

def listar_voluntarios():
    return pd.read_sql_query("SELECT * FROM voluntarios", conn)

def autenticar_voluntario(email, senha):
    query = "SELECT * FROM voluntarios WHERE email = ? AND senha = ?"
    c.execute(query, (email, senha))
    return c.fetchone()

def salvar_indisponibilidade(voluntario_id, datas, ceia, mes):
    c.execute("""
        INSERT INTO indisponibilidades (voluntario_id, datas_restricao, ceia_passada, mes_referencia)
        VALUES (?, ?, ?, ?)
    """, (voluntario_id, datas, ceia, mes))
    conn.commit()


# --- INTERFACE ---
st.title("👥 Portal de Voluntários - Ministério Infantil")

menu = st.sidebar.selectbox("Acesso", ["Login Voluntário", "Painel Administrador"])

ATRIBUICOES_LISTA = [
    "Recepção",
    "Baby Historia",
    "Baby auxiliar 1",
    "Baby auxiliar 2",
    "Apoio",
    "Inclusão",
    "Primario/Juvenil",
    "Auxiliar"
]

DISPONIBILIDADE_OPCOES = [
    "Domingo manhã",
    "Domingo tarde",
    "Quinta-feira"
]

if menu == "Login Voluntário":
    st.subheader("🔐 Acesso do Voluntário")
    login_email = st.text_input("Email")
    login_senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        voluntario = autenticar_voluntario(login_email, login_senha)
        if voluntario:
            st.session_state.logged_in = True
            st.session_state.voluntario_info = voluntario
        else:
            st.error("Email ou senha incorretos. Tente novamente.")
            st.session_state.logged_in = False

    if 'logged_in' in st.session_state and st.session_state.logged_in:
        voluntario = st.session_state.voluntario_info
        st.success(f"Bem-vindo(a), {voluntario[1]}!")
        st.markdown("---")
        st.subheader("🗓️ Informar Indisponibilidade do Mês")
        
        # Gera as opções de indisponibilidade para o próximo mês
        opcoes, mes_ref = get_dias_culto_proximo_mes()
        
        st.info(f"Mês de referência para a escala: **{mes_ref}**")

        datas_selecionadas = st.multiselect(
            "Selecione os dias e horários que você **NÃO** poderá servir:",
            options=opcoes
        )
        
        ceia_passada = st.radio("Você serviu na Ceia passada?", ["Sim", "Não"])

        if st.button("Enviar Indisponibilidade"):
            # Converte a lista de seleções em uma única string separada por vírgulas
            datas_restricao_str = ", ".join(datas_selecionadas)
            salvar_indisponibilidade(voluntario[0], datas_restricao_str, ceia_passada, mes_ref)
            st.success("Informações de indisponibilidade registradas com sucesso!")


elif menu == "Painel Administrador":
    # Adicionar uma senha simples para o painel de administrador
    admin_password = st.text_input("Senha de Administrador", type="password")
    if admin_password == "admin123":  # Troque "admin123" por uma senha segura

        aba = st.radio("Selecionar ação", ["Visualizar voluntários", "Adicionar voluntário"])

        if aba == "Visualizar voluntários":
            st.subheader("📋 Lista de Voluntários")
            df = listar_voluntarios()
            if "senha" in df.columns:
                st.dataframe(df.drop(columns=["senha"]))
            else:
                st.dataframe(df)

            if not df.empty:
                id_selecionado = st.selectbox("Selecionar voluntário para editar ou excluir:", df["id"])
                voluntario_selecionado = df[df["id"] == id_selecionado].iloc[0]

                with st.form("Editar voluntário"):
                    st.write(f"Editando ID: {voluntario_selecionado['id']}")
                    nome = st.text_input("Nome", voluntario_selecionado["nome"])
                    email = st.text_input("Email", voluntario_selecionado["email"])
                    senha = st.text_input("Nova Senha (deixe em branco para não alterar)", type="password")
                    
                    atribuicoes_default = [a.strip() for a in voluntario_selecionado["atribuicoes"].split(",") if a.strip() in ATRIBUICOES_LISTA]
                    atribuicoes_selecionadas = st.multiselect("Atribuições", options=ATRIBUICOES_LISTA, default=atribuicoes_default)

                    disponibilidade_default = [a.strip() for a in voluntario_selecionado["disponibilidade"].split(",") if a.strip() in DISPONIBILIDADE_OPCOES]
                    disponibilidade_selecionada = st.multiselect("Disponibilidade", options=DISPONIBILIDADE_OPCOES, default=disponibilidade_default)
                    
                    editar = st.form_submit_button("Salvar alterações")

                    if editar:
                        senha_final = senha if senha else voluntario_selecionado["senha"]
                        atribuicoes_str = ", ".join(atribuicoes_selecionadas)
                        disponibilidade_str = ", ".join(disponibilidade_selecionada)
                        editar_voluntario(id_selecionado, nome, email, senha_final, atribuicoes_str, disponibilidade_str)
                        st.success("Voluntário atualizado com sucesso!")
                        st.rerun()

                if st.button("Excluir voluntário"):
                    excluir_voluntario(id_selecionado)
                    st.warning("Voluntário excluído.")
                    st.rerun()

        elif aba == "Adicionar voluntário":
            st.subheader("➕ Adicionar Novo Voluntário")
            with st.form("cadastro_voluntario", clear_on_submit=True):
                nome = st.text_input("Nome")
                email = st.text_input("Email")
                senha = st.text_input("Senha", type="password")
                atribuicoes_selecionadas = st.multiselect("Atribuições", options=ATRIBUICOES_LISTA)
                disponibilidade_selecionada = st.multiselect("Disponibilidade", options=DISPONIBILIDADE_OPCOES)
                enviar = st.form_submit_button("Cadastrar")

                if enviar:
                    if nome and email and senha:
                        atribuicoes_str = ", ".join(atribuicoes_selecionadas)
                        disponibilidade_str = ", ".join(disponibilidade_selecionada)
                        adicionar_voluntario(nome, email, senha, atribuicoes_str, disponibilidade_str)
                        st.success("Voluntário adicionado com sucesso!")
                    else:
                        st.error("Por favor, preencha todos os campos obrigatórios (Nome, Email, Senha).")
    elif admin_password:
        st.error("Senha de administrador incorreta.")