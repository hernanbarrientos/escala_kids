# pages/painel_admin.py
import streamlit as st
import pandas as pd
import sqlite3
import database as db
import utils

st.set_page_config(page_title="Painel Admin", layout="wide")

if not st.session_state.get('logged_in') or st.session_state.user_role != 'admin':
    st.error("Acesso restrito a administradores.")
    st.page_link("app.py", label="Ir para Login")
    st.stop()

conn = db.conectar_db()
st.title("Painel de Administração")

aba = st.tabs(["Visualizar e Editar Voluntários", "Adicionar Voluntário"])

with aba[0]:
    st.subheader("📋 Lista de Voluntários Cadastrados")
    df = db.listar_voluntarios(conn)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.markdown("---")

        st.subheader("✏️ Editar ou Excluir Voluntário")
        
        # Precisamos buscar os dados novamente para ter a senha, que não vem no 'listar_voluntarios'
        df_completo = pd.read_sql_query("SELECT * FROM voluntarios", conn)

        id_selecionado = st.selectbox("Selecione um voluntário pelo ID:", df_completo["id"], key="edit_select")
        voluntario_selecionado = df_completo[df_completo["id"] == id_selecionado].iloc[0]
        
        with st.form("Editar voluntário"):
            st.write(f"Editando: **{voluntario_selecionado['nome']}** (ID: {voluntario_selecionado['id']})")
            
            # Inputs do formulário
            nome = st.text_input("Nome", voluntario_selecionado["nome"])
            usuario = st.text_input("Usuário", voluntario_selecionado["usuario"])
            nova_senha = st.text_input("Nova Senha", type="password", help="Deixe em branco para não alterar a senha.")

            atribuicoes_default = [a.strip() for a in (voluntario_selecionado.get("atribuicoes", "") or "").split(",") if a.strip()]
            atribuicoes = st.multiselect("Atribuições", options=utils.ATRIBUICOES_LISTA, default=atribuicoes_default, key="edit_atr")
            
            disponibilidade_default = [d.strip() for d in (voluntario_selecionado.get("disponibilidade", "") or "").split(",") if d.strip()]
            disponibilidade = st.multiselect("Disponibilidade", options=utils.DISPONIBILIDADE_OPCOES, default=disponibilidade_default, key="edit_disp")
            
            # Botão de Salvar dentro do formulário
            if st.form_submit_button("Salvar Alterações", type="primary"):
                # CORREÇÃO: Lógica para salvar no banco foi restaurada
                # Se uma nova senha foi digitada, usa a nova. Senão, mantém a antiga.
                senha_final = nova_senha if nova_senha else voluntario_selecionado['senha']
                
                # Junta as listas de multiselect em strings
                atribuicoes_str = ", ".join(atribuicoes)
                disponibilidade_str = ", ".join(disponibilidade)

                try:
                    db.editar_voluntario(conn, voluntario_selecionado['id'], nome, usuario, senha_final, atribuicoes_str, disponibilidade_str)
                    st.success(f"Dados do voluntário '{nome}' atualizados com sucesso!")
                    st.rerun() # Recarrega a página para mostrar os dados atualizados
                except Exception as e:
                    st.error(f"Ocorreu um erro ao atualizar: {e}")

        # CORREÇÃO: Botão Excluir foi restaurado e colocado fora do formulário
        if st.button("Excluir Voluntário Selecionado", type="secondary"):
            try:
                db.excluir_voluntario(conn, voluntario_selecionado['id'])
                st.warning(f"Voluntário '{voluntario_selecionado['nome']}' foi excluído.")
                st.rerun() # Recarrega a página para atualizar a lista
            except Exception as e:
                st.error(f"Ocorreu um erro ao excluir: {e}")

with aba[1]:
    # adicionar voluntário
    st.subheader("➕ Adicionar Novo Voluntário")
    with st.form("cadastro_voluntario", clear_on_submit=True):
        nome = st.text_input("Nome Completo")
        usuario = st.text_input("Nome de Usuário")
        senha = st.text_input("Senha Provisória", type="password")
        atribuicoes = st.multiselect("Atribuições do Voluntário", options=utils.ATRIBUICOES_LISTA)
        disponibilidade = st.multiselect("Disponibilidade Geral", options=utils.DISPONIBILIDADE_OPCOES)

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