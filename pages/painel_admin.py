import streamlit as st
import pandas as pd
import database as db
import utils

st.set_page_config(page_title="Painel Admin", layout="wide")

# --- VERIFICAÇÃO DE LOGIN (AUTH GUARD) ---
if not st.session_state.get('logged_in') or st.session_state.user_role != 'admin':
    st.error("Acesso restrito a administradores.")
    if st.button("Ir para Login"):
        st.switch_page("app.py")
    st.stop()

# --- CONTEÚDO DA PÁGINA ---
conn = db.conectar_db()
st.title("Painel de Administração")

aba = st.tabs(["Visualizar Voluntários", "Adicionar Voluntário"])

with aba[0]:
    st.subheader("📋 Lista de Voluntários Cadastrados")
    df = db.listar_voluntarios(conn)
    
    if not df.empty:
        # Esconde a coluna de senha por segurança
        st.dataframe(df.drop(columns=["senha"]), use_container_width=True)
        st.markdown("---")

        st.subheader("✏️ Editar ou Excluir Voluntário")
        id_selecionado = st.selectbox("Selecione um voluntário pelo ID:", df["id"])
        voluntario_selecionado = df[df["id"] == id_selecionado].iloc[0]

        with st.form("Editar voluntário"):
            st.write(f"Editando: **{voluntario_selecionado['nome']}**")
            nome = st.text_input("Nome", voluntario_selecionado["nome"])
            email = st.text_input("Email", voluntario_selecionado["email"])
            senha = st.text_input("Nova Senha (deixe em branco para não alterar)", type="password")

            atribuicoes_default = [a.strip() for a in voluntario_selecionado["atribuicoes"].split(",") if a.strip()]
            atribuicoes = st.multiselect("Atribuições", options=utils.ATRIBUICOES_LISTA, default=atribuicoes_default)

            disponibilidade_default = [d.strip() for d in voluntario_selecionado["disponibilidade"].split(",") if d.strip()]
            disponibilidade = st.multiselect("Disponibilidade", options=utils.DISPONIBILIDADE_OPCOES, default=disponibilidade_default)

            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Salvar Alterações", use_container_width=True, type="primary"):
                    senha_final = senha if senha else voluntario_selecionado["senha"]
                    db.editar_voluntario(conn, id_selecionado, nome, email, senha_final, ", ".join(atribuicoes), ", ".join(disponibilidade))
                    st.success("Voluntário atualizado!")
                    st.rerun()

        if st.button("Excluir Voluntário", type="secondary"):
            db.excluir_voluntario(conn, id_selecionado)
            st.warning(f"Voluntário {voluntario_selecionado['nome']} excluído.")
            st.rerun()
    else:
        st.info("Nenhum voluntário cadastrado ainda.")

with aba[1]:
    st.subheader("➕ Adicionar Novo Voluntário")
    with st.form("cadastro_voluntario", clear_on_submit=True):
        nome = st.text_input("Nome Completo")
        email = st.text_input("Email")
        senha = st.text_input("Senha Provisória", type="password")
        atribuicoes = st.multiselect("Atribuições do Voluntário", options=utils.ATRIBUICOES_LISTA)
        disponibilidade = st.multiselect("Disponibilidade Geral", options=utils.DISPONIBILIDADE_OPCOES)

        if st.form_submit_button("Cadastrar Voluntário", type="primary"):
            if nome and email and senha:
                db.adicionar_voluntario(conn, nome, email, senha, ", ".join(atribuicoes), ", ".join(disponibilidade))
                st.success(f"Voluntário {nome} cadastrado com sucesso!")
            else:
                st.error("Nome, email e senha são campos obrigatórios.")

if st.sidebar.button("Logout"):
    for key in st.session_state.keys():
        del st.session_state[key]
    st.switch_page("app.py")