import streamlit as st
import database as db

st.set_page_config(
    page_title="Portal de Voluntários",
    layout="centered"
)

# --- CONEXÃO COM DB E CRIAÇÃO DE TABELAS ---
conn = db.conectar_db()
db.criar_tabelas(conn)

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.voluntario_info = None

# --- TELA DE LOGIN ---
st.title("👥 Portal de Voluntários - Ministério Infantil")
st.header("Login de Acesso")

login_email = st.text_input("Email", key="login_email")
login_senha = st.text_input("Senha", type="password", key="login_senha")

if st.button("Entrar", type="primary"):
    # Credenciais fixas para administrador
    if login_email == "admin@igreja.com" and login_senha == "admin123":
        st.session_state.logged_in = True
        st.session_state.user_role = "admin"
        st.success("Login de administrador bem-sucedido!")
        st.switch_page("pages/2_Painel_Administrador.py")
    else:
        # Autenticação de voluntário pelo banco de dados
        voluntario = db.autenticar_voluntario(conn, login_email, login_senha)
        if voluntario:
            st.session_state.logged_in = True
            st.session_state.user_role = "voluntario"
            st.session_state.voluntario_info = voluntario
            st.success(f"Bem-vindo(a), {voluntario[1]}!")
            st.switch_page("pages/1_Painel_Voluntario.py")
        else:
            st.error("Email ou senha incorretos. Tente novamente.")

st.info("Para acesso administrativo, utilize as credenciais fornecidas.")