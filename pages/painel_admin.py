# pages/painel_admin.py
import streamlit as st
import pandas as pd
import sqlite3
import database as db
import utils

# --- Configuração da Página e Verificação de Login ---
st.set_page_config(page_title="Painel Admin", layout="wide")

if not st.session_state.get('logged_in') or st.session_state.user_role != 'admin':
    st.error("Acesso restrito a administradores.")
    st.page_link("app.py", label="Ir para Login")
    st.stop()

# --- Conexão com o Banco ---
conn = db.conectar_db()
st.title("Painel de Administração")

# --- Abas para Organização ---
tab_gerenciar, tab_adicionar = st.tabs(["Gerenciar Voluntários", "Adicionar Novo Voluntário"])

# --- Aba de Gerenciamento (Edição e Exclusão) ---
with tab_gerenciar:
    st.subheader("📋 Lista de Voluntários Cadastrados")

    try:
        # Carrega a lista de voluntários para exibição
        df_voluntarios = db.listar_voluntarios(conn)
        
        if df_voluntarios.empty:
            st.info("Nenhum voluntário cadastrado ainda.")
        else:
            # Exibe a lista
            st.dataframe(df_voluntarios, use_container_width=True)
            st.markdown("---")

            # --- Seção de Ações: Selecionar para Editar/Excluir ---
            st.subheader("Ações para um Voluntário Específico")

            # Busca todos os dados (incluindo senha) para popular o formulário de edição
            df_completo = pd.read_sql_query("SELECT * FROM voluntarios", conn)
            
            # Widget para selecionar o voluntário
            id_selecionado = st.selectbox(
                "Selecione o voluntário:",
                options=df_completo['id'],
                # Mostra o nome e o ID para facilitar a seleção
                format_func=lambda id: f"{df_completo.loc[df_completo['id'] == id, 'nome'].iloc[0]}",
                key="selectbox_voluntario"
            )

            # Pega todos os dados do voluntário que foi selecionado
            voluntario_selecionado = df_completo[df_completo["id"] == id_selecionado].iloc[0]

            # --- Formulário de Edição ---
            with st.form("form_editar_voluntario"):
                st.write(f"**Editando:** {voluntario_selecionado['nome']}")
                
                nome = st.text_input("Nome", value=voluntario_selecionado["nome"])
                usuario = st.text_input("Usuário", value=voluntario_selecionado["usuario"])
                nova_senha = st.text_input("Nova Senha", type="password", placeholder="Deixe em branco para não alterar")

                atribuicoes_default = [a.strip() for a in (voluntario_selecionado.get("atribuicoes") or "").split(",") if a.strip()]
                atribuicoes = st.multiselect("Atribuições", options=utils.ATRIBUICOES_LISTA, default=atribuicoes_default)
                
                disponibilidade_default = [d.strip() for d in (voluntario_selecionado.get("disponibilidade") or "").split(",") if d.strip()]
                disponibilidade = st.multiselect("Disponibilidade", options=utils.DISPONIBILIDADE_OPCOES, default=disponibilidade_default)

                if st.form_submit_button("Salvar Alterações", type="primary"):
                    senha_final = nova_senha if nova_senha else voluntario_selecionado['senha']
                    atribuicoes_str = ", ".join(atribuicoes)
                    disponibilidade_str = ", ".join(disponibilidade)

                    db.editar_voluntario(conn, id_selecionado, nome, usuario, senha_final, atribuicoes_str, disponibilidade_str)
                    st.success(f"Dados do voluntário '{nome}' atualizados com sucesso!")

                    # A página será recarregada automaticamente pelo Streamlit após a mensagem.
                    st.rerun()

            st.markdown("---")
            
            # --- Seção de Exclusão ---
            st.write(f"**Excluir:** {voluntario_selecionado['nome']}")
            st.warning(f"Atenção: Esta ação é permanente e não pode ser desfeita.")

            if st.button(f"Confirmar Exclusão do Voluntário", type="secondary"):
                db.excluir_voluntario(conn, id_selecionado)
                st.success(f"Voluntário '{voluntario_selecionado['nome']}' excluído. A lista será atualizada.")
                # A página será recarregada automaticamente.
                st.rerun()

    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")


# --- Aba de Adicionar Voluntário (sem alterações) ---
with tab_adicionar:
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


# --- Botão de Logout na Barra Lateral ---
if st.sidebar.button("Logout"):
    for key in st.session_state.keys():
        del st.session_state[key]
    st.switch_page("app.py")