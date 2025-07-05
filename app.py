import streamlit as st
import database as db
import utils

# Importa as "views" da nova pasta
from views import painel_admin, painel_voluntario, alterar_senha, gerar_escala

st.set_page_config(page_title="Portal Ministério Kids", layout="wide")

if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.voluntario_info = None

utils.render_sidebar()

if st.session_state.page == 'login':
    with st.columns(3)[1]:
        with st.container(border=True):
            st.title("👶 Ministério Kids")
            st.subheader("🔒 Portal de Voluntários")
            conn = db.conectar_db()
            db.criar_tabelas(conn)
            login_usuario = st.text_input("Usuário")
            login_senha = st.text_input("Senha", type="password")

            if st.button("Entrar", type="primary", use_container_width=True):
                user_data = db.autenticar_voluntario(conn, login_usuario, login_senha)
                if user_data:
                    st.session_state.logged_in = True
                    st.session_state.user_role = user_data['role']
                    st.session_state.voluntario_info = dict(user_data)
                    
                    if user_data['role'] == 'admin':
                        st.session_state.page = 'painel_admin'
                    elif user_data['primeiro_acesso'] == 1:
                        st.session_state.page = 'alterar_senha'
                    else:
                        st.session_state.page = 'painel_voluntario'
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
            conn.close()

elif st.session_state.page == 'painel_admin':
    painel_admin.show_page()
elif st.session_state.page == 'painel_voluntario':
    painel_voluntario.show_page()
elif st.session_state.page == 'gerar_escala':
    gerar_escala.show_page()
elif st.session_state.page == 'alterar_senha':
    alterar_senha.show_page()