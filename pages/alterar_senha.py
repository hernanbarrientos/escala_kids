# pages/alterar_senha.py
import streamlit as st
import database as db
import utils

st.set_page_config(page_title="Alterar Senha", layout="centered")
utils.render_sidebar()

# --- VERIFICAÇÃO DE LOGIN E STATUS DE PRIMEIRO ACESSO ---
if not st.session_state.get('logged_in') or st.session_state.get('voluntario_info', {}).get('primeiro_acesso') != 1:
    st.error("Para mudar a senha, entre em contato com o administrador")
    st.page_link("app.py", label="Ir para a página de Login")
    st.stop()

# --- CONTEÚDO DA PÁGINA ---
conn = db.conectar_db()
voluntario_info = st.session_state.voluntario_info

st.title(f"Bem-vindo(a), {voluntario_info['nome']}!")
st.subheader("Para sua segurança, por favor, crie uma nova senha.")
st.markdown("---")

with st.form("alterar_senha_form"):
    nova_senha = st.text_input("Digite sua nova senha", type="password")
    confirmar_senha = st.text_input("Confirme sua nova senha", type="password")
    
    submitted = st.form_submit_button("Salvar Nova Senha", type="primary")

    if submitted:
        if not nova_senha or not confirmar_senha:
            st.error("Ambos os campos de senha devem ser preenchidos.")
        elif nova_senha != confirmar_senha:
            st.error("As senhas não coincidem. Tente novamente.")
        else:
            try:
                # Chama a nova função do banco de dados
                db.alterar_senha_e_status(conn, voluntario_info['id'], nova_senha)
                
                # Atualiza o estado da sessão
                st.session_state.voluntario_info['primeiro_acesso'] = 0
                st.session_state.voluntario_info['senha'] = nova_senha

                st.success("Senha alterada com sucesso! Você será redirecionado para o portal.")
                st.switch_page("pages/painel_voluntario.py")
            except Exception as e:
                st.error(f"Ocorreu um erro ao salvar a senha: {e}")