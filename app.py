# app.py
import streamlit as st
import database as db

st.set_page_config(page_title="Portal de Voluntários", layout="centered")

conn = db.conectar_db()
db.criar_tabelas(conn)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.voluntario_info = None

st.title("👥 Portal de Voluntários - Ministério Infantil")
st.header("Login de Acesso")

# MODIFICAÇÃO: Campo de 'Usuário' em vez de 'Email'
login_usuario = st.text_input("Usuário", key="login_usuario")
login_senha = st.text_input("Senha", type="password", key="login_senha")

if st.button("Entrar", type="primary"):
    # Login do admin continua o mesmo (pode ser um usuário/email específico)
    if login_usuario == "admin" and login_senha == "admin123":
        st.session_state.logged_in = True
        st.session_state.user_role = "admin"
        st.success("Login de administrador bem-sucedido!")
        st.switch_page("pages/2_Painel_Administrador.py")
    else:
        voluntario = db.autenticar_voluntario(conn, login_usuario, login_senha)
        if voluntario:
            st.session_state.logged_in = True
            st.session_state.user_role = "voluntario"
            st.session_state.voluntario_info = dict(voluntario) # Converte para dicionário

            # NOVA LÓGICA: Verifica se é o primeiro acesso
            if voluntario['primeiro_acesso'] == 1:
                st.info("Detectamos que este é seu primeiro acesso. Por favor, altere sua senha.")
                st.switch_page("pages/4_Alterar_Senha.py")
            else:
                st.success(f"Bem-vindo(a) de volta, {voluntario['nome']}!")
                st.switch_page("pages/1_Painel_Voluntario.py")
        else:
            st.error("Usuário ou senha incorretos. Tente novamente.")

st.info("Para acesso administrativo, utilize o usuário 'admin'.")