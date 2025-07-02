# app.py
import streamlit as st
import database as db

st.set_page_config(page_title="Portal de Voluntários", layout="centered")

conn = db.conectar_db()
# A chamada a criar_tabelas() já está no próprio database.py (fora das funções),
# mas mantê-la aqui não causa problemas devido ao IF NOT EXISTS.
# db.criar_tabelas(conn) # Pode remover esta linha se preferir confiar na chamada global em database.py

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.voluntario_info = None

st.title("👥 Portal de Voluntários - Ministério Infantil")
st.header("Login de Acesso")

login_usuario = st.text_input("Usuário", key="login_usuario")
login_senha = st.text_input("Senha", type="password", key="login_senha")

if st.button("Entrar", type="primary"):
    # NOVA LÓGICA: Autentica todos os usuários através do banco de dados
    user_data = db.autenticar_voluntario(conn, login_usuario, login_senha) # user_data agora pode ser admin ou voluntario

    if user_data:
        st.session_state.logged_in = True
        st.session_state.user_role = user_data['role'] # Define o papel do usuário com base no DB
        st.session_state.voluntario_info = dict(user_data) # Armazena todas as info do usuário

        if st.session_state.user_role == "admin":
            st.success("Login de administrador bem-sucedido!")
            st.switch_page("pages/painel_admin.py")
        elif st.session_state.user_role == "voluntario":
            # Lógica de primeiro acesso para voluntários (mantida)
            if user_data['primeiro_acesso'] == 1:
                st.info("Detectamos que este é seu primeiro acesso. Por favor, altere sua senha.")
                st.switch_page("pages/alterar_senha.py")
            else:
                st.success(f"Bem-vindo(a) de volta, {user_data['nome']}!")
                st.switch_page("pages/painel_voluntario.py") # Ajustei para painel_voluntario.py
        else:
            # Caso algum papel inesperado seja encontrado no DB
            st.error("Erro de configuração de usuário. Papel desconhecido.")
    else:
        st.error("Usuário ou senha incorretos. Tente novamente.")


# st.info("Para acesso administrativo, utilize o usuário 'admin'.")

conn.close() # Garante que a conexão seja fechada