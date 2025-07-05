import streamlit as st
import database as db
import utils



st.set_page_config(
    page_title="Portal Ministério Kids",
    layout="centered",  # Centraliza os elementos
    initial_sidebar_state="collapsed"  # Esconde o sidebar no login
)
utils.render_sidebar()

# --- Remove o menu e footer padrão do Streamlit ---
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {max-width: 500px; margin: auto;}
    </style>
""", unsafe_allow_html=True)

# --- Inicializa sessão ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None

# --- Conexão com banco ---
conn = db.conectar_db()

# --- Login ---
st.title("👶 Ministério Kids")
st.subheader("🔒 Portal de Voluntários")

login_usuario = st.text_input("Usuário")
login_senha = st.text_input("Senha", type="password")

if st.button("Entrar", type="primary"):
    user_data = db.autenticar_voluntario(conn, login_usuario, login_senha)

    if user_data:
        st.session_state.logged_in = True
        st.session_state.user_role = user_data['role']
        st.session_state.voluntario_info = dict(user_data)
        st.success(f"Bem-vindo(a), {user_data['nome']}!")

        # Redireciona com base no papel
        if st.session_state.user_role == "admin":
            st.switch_page("pages/painel_admin.py")
        else:
            if user_data['primeiro_acesso'] == 1:
                st.switch_page("pages/alterar_senha.py")
            else:
                st.switch_page("pages/painel_voluntario.py")
    else:
        st.error("Usuário ou senha incorretos.")

conn.close()
