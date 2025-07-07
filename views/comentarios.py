# views/comentarios.py
import streamlit as st
import pandas as pd
import database as db

def show_page():
    """
    Função principal que renderiza a página de gerenciamento de feedbacks.
    """
    # --- Verificação de Login e Permissão de Administrador ---
    if not st.session_state.get('logged_in') or st.session_state.user_role != 'admin':
        st.error("Acesso restrito a administradores.")
        if st.button("Ir para Login"):
            st.session_state.page = 'login'
            st.rerun()
        st.stop()
    
    # --- Conteúdo da Página ---
    conn = st.session_state.db_conn
    st.title("📮 Comentários e Feedbacks dos Voluntários")
    st.markdown("---")

    # --- Abas para cada status de feedback ---
    tab_novos, tab_ideias, tab_lixeira = st.tabs(["📬 Novos Comentários", "💡 Boas Ideias", "🗑️ Lixeira"])

    # --- Aba de Novos Comentários ---
    with tab_novos:
        st.subheader("Feedbacks recentes aguardando análise")
        df_novos = db.get_feedbacks(conn, status_filter=['novo'])
        
        if df_novos.empty:
            st.info("Nenhum novo comentário no momento.")
        else:
            for _, row in df_novos.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([0.7, 0.3])
                    with col1:
                        st.write(f"**De:** {row['voluntario_nome']}")
                        st.caption(f"**Culto:** {row['data_culto']} | **Enviado em:** {pd.to_datetime(row['timestamp_criacao']).strftime('%d/%m/%Y %H:%M')}")
                    
                    st.write(row['comentario'])
                    
                    # Botões de Ação
                    b_col1, b_col2, _ = st.columns([1, 1, 4])
                    with b_col1:
                        if st.button("💡 Marcar como Boa Ideia", key=f"idea_{row['id']}", use_container_width=True):
                            db.atualizar_status_feedback(conn, row['id'], 'boa_ideia')
                            st.toast("Movido para 'Boas Ideias'!", icon="💡")
                            st.rerun()
                    with b_col2:
                        if st.button("🗑️ Mover para Lixeira", key=f"trash_{row['id']}", use_container_width=True):
                            db.atualizar_status_feedback(conn, row['id'], 'lixeira')
                            st.toast("Movido para a lixeira.", icon="🗑️")
                            st.rerun()

    # --- Aba de Boas Ideias ---
    with tab_ideias:
        st.subheader("Ideias e sugestões salvas para serem trabalhadas")
        df_ideias = db.get_feedbacks(conn, status_filter=['boa_ideia'])

        if df_ideias.empty:
            st.info("Nenhuma ideia marcada no momento.")
        else:
            for _, row in df_ideias.iterrows():
                with st.container(border=True):
                    # (Exibição similar à aba de novos, mas com ações diferentes)
                    st.write(f"**De:** {row['voluntario_nome']} | **Culto:** {row['data_culto']}")
                    st.write(row['comentario'])
                    if st.button("🗑️ Mover para Lixeira", key=f"trash_idea_{row['id']}", use_container_width=True):
                        db.atualizar_status_feedback(conn, row['id'], 'lixeira')
                        st.toast("Movido para a lixeira.", icon="🗑️")
                        st.rerun()

    # --- Aba da Lixeira ---
    with tab_lixeira:
        st.subheader("Comentários movidos para a lixeira")
        df_lixeira = db.get_feedbacks(conn, status_filter=['lixeira'])

        if df_lixeira.empty:
            st.info("A lixeira está vazia.")
        else:
            for _, row in df_lixeira.iterrows():
                with st.container(border=True):
                    # (Exibição similar, mas com ação de restaurar)
                    st.write(f"**De:** {row['voluntario_nome']} | **Culto:** {row['data_culto']}")
                    st.write(f"_{row['comentario']}_") # Itálico para indicar que está na lixeira
                    if st.button("♻️ Restaurar Comentário", key=f"restore_{row['id']}", use_container_width=True):
                        db.atualizar_status_feedback(conn, row['id'], 'novo')
                        st.toast("Comentário restaurado para 'Novos Comentários'.", icon="♻️")
                        st.rerun()