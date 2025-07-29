# views/alterar_senha.py
import streamlit as st
import database as db

# def render_content():
def show_page():
    """Esta função contém toda a lógica e os elementos visuais da página."""

    # --- PONTO DA CORREÇÃO: Criação das colunas para centralizar o conteúdo ---
    col1, col2, col3 = st.columns([1, 2, 1])  # Margem | Conteúdo Principal | Margem

    with col2: # Todo o conteúdo vai para a coluna central
        st.subheader("Defina sua nova senha")

        with st.form(key="change_password_form"):
            nova_senha = st.text_input("Nova Senha", type="password", key="nova_senha_1")
            confirmacao_senha = st.text_input("Confirme a Nova Senha", type="password", key="nova_senha_2")
            
            submitted = st.form_submit_button("Salvar Nova Senha")

            if submitted:
                if not nova_senha or not confirmacao_senha:
                    st.warning("Por favor, preencha ambos os campos.")
                elif len(nova_senha) < 6:
                    st.warning("A senha deve ter no mínimo 6 caracteres.")
                elif nova_senha != confirmacao_senha:
                    st.error("As senhas não coincidem. Tente novamente.")
                else:
                    try:
                        voluntario_id = st.session_state.voluntario_info['id']
                        db.alterar_senha_e_status(voluntario_id, nova_senha)
                        
                        st.session_state.voluntario_info['primeiro_acesso'] = 0
                        
                        st.success("Senha alterada com sucesso!")
                        st.info("Você pode continuar navegando ou fazer logout.")
                        
                        if 'page_within_dashboard' in st.session_state:
                            del st.session_state['page_within_dashboard']

                    except Exception as e:
                        st.error(f"Ocorreu um erro ao alterar a senha: {e}")

# def show_page():
#     """
#     Esta função serve como ponto de entrada para o roteador principal (app.py),
#     especialmente para o fluxo do administrador.
#     """
#     st.title("🔑 Alteração de Senha")
#     st.markdown("---")
#     render_content()