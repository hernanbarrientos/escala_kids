# app.py
import streamlit as st
import database as db
import utils

# Importa as "views" da pasta de views
from views import painel_admin, painel_voluntario, alterar_senha, gerar_escala, minha_escala, comentarios

st.set_page_config(
    page_title="Portal Ministério Kids",
    layout="wide" 
)

# Inicialização do estado da sessão
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.voluntario_info = None

# Renderiza a sidebar em todas as "páginas"
utils.render_sidebar()

# Roteador principal
if st.session_state.page == 'login':
    
    # --- CSS PARA CENTRALIZAÇÃO ---
    st.markdown("""
    <style>
        /* Centraliza a imagem */
        .stImage {
            display: flex;
            justify-content: center;
        }
        /* Centraliza o título principal (H1) */
        .login-title {
            text-align: center;
        }
        /* NOVA REGRA: Centraliza o subtítulo (H3) */
        .login-subheader {
            text-align: center;
        }
    </style>
    """, unsafe_allow_html=True)

    _, central_col, _ = st.columns([1.8, 2, 1.8])

    with central_col:
        with st.container():
            
            sub_col1, sub_col2, sub_col3 = st.columns([1, 1, 1])
            with sub_col2:
                st.image("assets/logo_renovo.png", width=150) 
            
            st.markdown("<h1 class='login-title'>👶 Ministério Kids</h1>", unsafe_allow_html=True)
            
            # --- MUDANÇA APLICADA AQUI ---
            # Substituímos st.subheader por st.markdown para aplicar o estilo.
            st.markdown("<h3 class='login-subheader'>🔒 Portal de Voluntários</h3>", unsafe_allow_html=True)

            login_usuario = st.text_input("Usuário", placeholder="Digite seu usuário", label_visibility="collapsed")
            login_senha = st.text_input("Senha", type="password", placeholder="Digite sua senha", label_visibility="collapsed")

            if st.button("Entrar", type="primary", use_container_width=True):
                conn = db.conectar_db()
                user_data = db.autenticar_voluntario(conn, login_usuario, login_senha)
                conn.close()
                
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

# Roteador para as outras páginas
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