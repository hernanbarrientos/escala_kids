# views/alterar_senha.py
import streamlit as st
import database as db
import utils

def show_page():
    """
    Função principal que renderiza a página de alteração de senha.
    """
    # --- Verificação de Login ---
    if not st.session_state.get('logged_in'):
        st.error("Você precisa estar logado para alterar sua senha.")
        if st.button("Ir para Login"):
            st.session_state.page = 'login'
            st.rerun()
        st.stop()

    # --- Conteúdo da Página ---
    
    voluntario_info = st.session_state.voluntario_info

    # Centraliza o formulário na tela
    with st.columns(3)[1]:
        with st.container(border=True):
            st.title(f"🔑 Alterar Senha")
            st.write(f"Usuário: **{voluntario_info['nome']}**")
            
            # Mensagem especial para o primeiro acesso
            if voluntario_info.get('primeiro_acesso') == 1:
                st.info("Este é seu primeiro acesso. Por segurança, por favor, crie uma nova senha.")
            
            st.markdown("---")

            with st.form("form_alterar_senha"):
                nova_senha = st.text_input("Digite sua nova senha", type="password")
                confirmar_senha = st.text_input("Confirme sua nova senha", type="password")
                
                submitted = st.form_submit_button("Salvar Nova Senha", type="primary", use_container_width=True)

                if submitted:
                    if not nova_senha or not confirmar_senha:
                        st.error("Ambos os campos de senha devem ser preenchidos.")
                    elif len(nova_senha) < 6:
                        st.error("A nova senha deve ter pelo menos 6 caracteres.")
                    elif nova_senha != confirmar_senha:
                        st.error("As senhas não coincidem. Tente novamente.")
                    else:
                        try:
                            # Chama a função do banco que salva a senha criptografada
                            db.alterar_senha_e_status(voluntario_info['id'], nova_senha)
                            
                            # Atualiza a informação na sessão para refletir a mudança
                            st.session_state.voluntario_info['primeiro_acesso'] = 0
                            
                            st.success("Senha alterada com sucesso!")
                            st.balloons()
                            
                            # Redireciona para a página principal do usuário após a troca
                            if st.session_state.user_role == 'admin':
                                st.session_state.page = 'painel_admin'
                            else:
                                st.session_state.page = 'painel_voluntario'
                            st.rerun()

                        except Exception as e:
                            st.error(f"Ocorreu um erro ao salvar a senha: {e}")
