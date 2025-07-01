# pages/painel_admin.py
import streamlit as st
import pandas as pd
import database as db
import utils
import sqlite3

st.set_page_config(page_title="Painel Admin", layout="wide")

if not st.session_state.get('logged_in') or st.session_state.user_role != 'admin':
    st.error("Acesso restrito a administradores.")
    st.page_link("app.py", label="Ir para Login")
    st.stop()

conn = db.conectar_db()
st.title("Painel de Administração")

# --- Atualizar Painel Voluntário ---

aba = st.tabs(["Visualizar Voluntários", "Adicionar Voluntário"])

with aba[0]:
    st.subheader("📋 Lista de Voluntários Cadastrados")
    df = db.listar_voluntarios(conn)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.markdown("---")

        st.subheader("✏️ Editar ou Excluir Voluntário")
        # Lógica de edição atualizada
        id_selecionado = st.selectbox("Selecione um voluntário pelo ID:", df["id"], key="edit_select")
        voluntario_selecionado_df = df[df["id"] == id_selecionado]
        if not voluntario_selecionado_df.empty:
            voluntario_selecionado = voluntario_selecionado_df.iloc[0]
            with st.form("Editar voluntário"):
                st.write(f"Editando: **{voluntario_selecionado['nome']}**")
                nome = st.text_input("Nome", voluntario_selecionado["nome"])
                usuario = st.text_input("Usuário", voluntario_selecionado["usuario"]) # MODIFICADO
                senha_atual = st.text_input("Senha Atual", type="password", help="A senha não é mostrada. Digite uma nova senha para alterá-la.")

                # Restante do formulário...
                atribuicoes_default = [a.strip() for a in (voluntario_selecionado.get("atribuicoes", "") or "").split(",") if a.strip()]
                atribuicoes = st.multiselect("Atribuições", options=utils.ATRIBUICOES_LISTA, default=atribuicoes_default, key="edit_atr")
                
                disponibilidade_default = [d.strip() for d in (voluntario_selecionado.get("disponibilidade", "") or "").split(",") if d.strip()]
                disponibilidade = st.multiselect("Disponibilidade", options=utils.DISPONIBILIDADE_OPCOES, default=disponibilidade_default, key="edit_disp")
                
                if st.form_submit_button("Salvar Alterações", type="primary"):
                    st.warning("Funcionalidade de edição de senha via admin desativada por segurança. Peça ao usuário para redefinir.")

                    # db.editar_voluntario(conn, id_selecionado, nome, usuario, senha_atual, ",".join(atribuicoes), ",".join(disponibilidade))
                    st.success("Dados do voluntário atualizados (exceto senha).")
                    st.rerun()

with aba[1]:
    st.subheader("➕ Adicionar Novo Voluntário")
    with st.form("cadastro_voluntario", clear_on_submit=True):
        nome = st.text_input("Nome Completo")
        usuario = st.text_input("Nome de Usuário")
        senha = st.text_input("Senha Provisória", type="password") 
        atribuicoes = st.multiselect("Atribuições", options=utils.ATRIBUICOES_LISTA)
        disponibilidade = st.multiselect("Disponibilidade", options=utils.DISPONIBILIDADE_OPCOES)

        if st.form_submit_button("Cadastrar Voluntário", type="primary"):
            if nome and usuario and senha:
                try:
                    db.adicionar_voluntario(conn, nome, usuario, senha, ", ".join(atribuicoes), ", ".join(disponibilidade))
                    st.success(f"Voluntário '{nome}' com usuário '{usuario}' cadastrado com sucesso!")
                except sqlite3.IntegrityError:
                    st.error(f"O nome de usuário '{usuario}' já existe. Por favor, escolha outro.")
                except Exception as e:
                    st.error(f"Ocorreu um erro: {e}")
            else:
                st.error("Nome, Usuário e Senha Provisória são campos obrigatórios.")


if st.sidebar.button("Logout"):
    for key in st.session_state.keys():
        del st.session_state[key]
    st.switch_page("app.py")