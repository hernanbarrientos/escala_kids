# views/solicitacoes_troca.py
import streamlit as st
import pandas as pd
import database as db
import utils

def show_page():
    """
    Função principal que renderiza a página de gerenciamento de solicitações de troca.
    """
    # --- Verificação de Login e Permissão de Administrador ---
    if not st.session_state.get('logged_in') or st.session_state.user_role != 'admin':
        st.error("Acesso restrito a administradores.")
        if st.button("Ir para Login"):
            st.session_state.page = 'login'
            st.rerun()
        st.stop()
    
    # --- Conteúdo da Página ---
    st.title("🔄 Solicitações de Troca de Escala")
    st.markdown("---")

    st.subheader("Solicitações Pendentes de Aprovação")

    try:
        solicitacoes_pendentes_df = db.get_solicitacoes_pendentes()

        if solicitacoes_pendentes_df.empty:
            st.info("Não há nenhuma solicitação de troca pendente no momento.")
        else:
            for _, solicitacao in solicitacoes_pendentes_df.iterrows():
                with st.container(border=True):
                    solicitacao_id = solicitacao['id']
                    
                    st.write(f"**Solicitante:** {solicitacao['solicitante_nome']}")
                    st.write(f"**Substituto Sugerido:** {solicitacao['substituto_nome']}")
                    st.write(f"**Escala Original:** {solicitacao['data_culto']} - {solicitacao['funcao']}")
                    st.caption(f"Pedido feito em: {pd.to_datetime(solicitacao['timestamp_solicitacao']).strftime('%d/%m/%Y %H:%M')}")

                    col1, col2, _ = st.columns([1, 1, 4])
                    with col1:
                        if st.button("✅ Aprovar", key=f"aprovar_{solicitacao_id}", use_container_width=True, type="primary"):
                            if db.processar_solicitacao(solicitacao_id, 'aprovada'):
                                st.success("Troca aprovada e escala atualizada com sucesso!")
                                st.rerun()
                            else:
                                st.error("Ocorreu um erro ao aprovar a solicitação.")
                    
                    with col2:
                        if st.button("❌ Negar", key=f"negar_{solicitacao_id}", use_container_width=True):
                            if db.processar_solicitacao(solicitacao_id, 'negada'):
                                st.warning("Solicitação negada.")
                                st.rerun()
                            else:
                                st.error("Ocorreu um erro ao negar a solicitação.")
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar as solicitações: {e}")