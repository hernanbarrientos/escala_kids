# app.py
import streamlit as st
import database as db
import utils
from views import painel_admin, painel_voluntario, alterar_senha, gerar_escala, minha_escala, comentarios, solicitacoes_troca

st.set_page_config(
    page_title="Portal Ministério Kids",
    layout="wide"
)

# Garante que as tabelas existam na primeira execução da aplicação.
db.criar_tabelas()

# Inicialização do estado da sessão
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.voluntario_info = None

# A sidebar é renderizada aqui
utils.render_sidebar()

# Roteador principal
if st.session_state.page == 'login':
    st.markdown("""
    <style>
        .stImage { display: flex; justify-content: center; }
        .login-title { text-align: center; }
        .login-subheader { text-align: center; }
    </style>
    """, unsafe_allow_html=True)

    _, central_col, _ = st.columns([1.2, 2, 1.2])
    with central_col:
        with st.container():
            sub_col1, sub_col2, sub_col3 = st.columns([0.8, 1.5, 0.8])
            with sub_col2:
                st.image("assets/logo_renovo.png", width=150)
            
            st.markdown("<h1 class='login-title'>👶 Ministério Kids</h1>", unsafe_allow_html=True)
            st.markdown("<h3 class='login-subheader'>🔒 Portal de Voluntários</h3>", unsafe_allow_html=True)

            login_usuario = st.text_input("Usuário", placeholder="Digite seu usuário", label_visibility="collapsed")
            login_senha = st.text_input("Senha", type="password", placeholder="Digite sua senha", label_visibility="collapsed")

            if st.button("Entrar", type="primary", use_container_width=True):
                # Cada função do banco agora gerencia sua própria conexão
                user_data = db.autenticar_voluntario(login_usuario, login_senha)
                
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

# O roteador agora não precisa mais passar a conexão para as páginas
elif st.session_state.page == 'painel_admin':
    painel_admin.show_page()
elif st.session_state.page == 'painel_voluntario':
    painel_voluntario.show_page()
elif st.session_state.page == 'gerar_escala':
    gerar_escala.show_page()
elif st.session_state.page == 'alterar_senha':
    alterar_senha.show_page()
elif st.session_state.page == 'minha_escala':
    minha_escala.show_page()
elif st.session_state.page == 'comentarios':
    comentarios.show_page()
elif st.session_state.page == 'solicitacoes_troca':
    solicitacoes_troca.show_page()