# app.py
import streamlit as st
import database as db
import utils
from views import (
    painel_admin,
    painel_voluntario, # Roteamento direto para as páginas
    minha_escala,     # Roteamento direto para as páginas
    alterar_senha,
    gerar_escala,
    comentarios,
    solicitacoes_troca
)

# Configuração inicial da página
st.set_page_config(
    page_title="Portal Ministério Kids",
    layout="wide"
)

# CSS Responsivo Global
st.markdown("""
    <style>
        /* Por padrão (desktop), esconde a barra de navegação mobile */
        .mobile-nav {
            display: none;
        }

        /* Regra para telas pequenas (celulares) com largura máxima de 768px */
        @media (max-width: 768px) {
            /* Esconde a sidebar do desktop */
            [data-testid="stSidebar"] {
                display: none;
            }
            /* Mostra a barra de navegação mobile e a fixa no rodapé */
            .mobile-nav {
                display: block;
                position: fixed;
                bottom: 0;
                left: 0;
                width: 100%;
                background-color: #0E1117; /* Cor de fundo do tema escuro do Streamlit */
                padding: 10px 5px 5px 5px;
                border-top: 1px solid #31333F;
                z-index: 100;
            }
        }
    </style>
""", unsafe_allow_html=True)


# Garante que as tabelas existam na primeira execução da aplicação
db.criar_tabelas()

# Inicialização do estado da sessão
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.voluntario_info = None

# --- RENDERIZAÇÃO INTELIGENTE DA NAVEGAÇÃO ---
# Chama a função de navegação apropriada com base no perfil do usuário logado.
if st.session_state.get("logged_in"):
    if st.session_state.user_role == 'admin':
        utils.render_sidebar()  # Mostra a sidebar do Admin
    elif st.session_state.user_role == 'voluntario':
        # Renderiza AMBOS os menus do voluntário. O CSS acima decide qual mostrar.
        utils.render_volunteer_sidebar()
        utils.render_mobile_nav()


# --- ROTEADOR PRINCIPAL DE PÁGINAS ---
page = st.session_state.get('page', 'login')

if page == 'login' and not st.session_state.get("logged_in"):
    # --- PÁGINA DE LOGIN ---
    st.markdown("""
    <style>
        .stImage { display: flex; justify-content: center; }
        .login-title { text-align: center; }
        .login-subheader { text-align: center; }
        .logo-image { display: block; margin-left: auto; margin-right: auto; } /* Nova linha para centralizar a imagem */
    </style>
    """, unsafe_allow_html=True)
    
    _, central_col, _ = st.columns([2, 2, 2])
    with central_col:
        with st.container():
            sub_col1, sub_col2, sub_col3 = st.columns([1.5, 2, 1.5])
            with sub_col2:
                st.image("assets/logo_renovo.png", width=180)
            
            st.markdown("<h1 class='login-title'>👶 Ministério Kids</h1>", unsafe_allow_html=True)
            st.markdown("<h3 class='login-subheader'>🔒 Portal de Voluntários</h3>", unsafe_allow_html=True)

            login_usuario = st.text_input("Usuário", placeholder="Digite seu usuário", label_visibility="collapsed")
            login_senha = st.text_input("Senha", type="password", placeholder="Digite sua senha", label_visibility="collapsed")

            if st.button("Entrar", type="primary", use_container_width=True):
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
                        st.session_state.page = 'painel_voluntario' # Página inicial do voluntário
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

# Roteamento de páginas para usuários logados
elif st.session_state.get("logged_in"):
    if page == 'painel_admin':
        painel_admin.show_page()
    elif page == 'gerar_escala':
        gerar_escala.show_page()
    elif page == 'comentarios':
        comentarios.show_page()
    elif page == 'solicitacoes_troca':
        solicitacoes_troca.show_page()
    elif page == 'painel_voluntario':
        painel_voluntario.show_page()
    elif page == 'minha_escala':
        minha_escala.show_page()
    elif page == 'alterar_senha':
        alterar_senha.show_page()
    else:
        # Página padrão caso o estado se perca
        if st.session_state.user_role == 'admin':
            st.session_state.page = 'painel_admin'
        else:
            st.session_state.page = 'painel_voluntario'
        st.rerun()
else:
    # Se por algum motivo não estiver logado e não estiver na página de login, força o login
    st.session_state.page = 'login'
    st.rerun()



