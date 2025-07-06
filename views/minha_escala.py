# views/minha_escala.py
import streamlit as st
import database as db

def show_page():
    # --- Verificação de Login ---
    if not st.session_state.get('logged_in'):
        st.error("Você precisa estar logado para acessar esta página.")
        st.session_state.page = 'login'
        st.rerun()
        st.stop()
    
    # --- Conteúdo da Página ---
    conn = st.session_state.db_conn
    voluntario_info = st.session_state.voluntario_info
    
    st.title(f"🗓️ Minha Escala")
    st.write(f"Olá, **{voluntario_info['nome']}**! Aqui estão os dias e funções para os quais você foi escalado(a).")
    st.markdown("---")
        # --- AVISO ADICIONADO AQUI ---
    st.warning("🚨 **Atenção:** Esta escala é uma prévia e poderá sofrer alterações sem aviso prévio", icon="🚨")
    st.markdown("---")

    try:
        minha_escala_df = db.get_escala_por_voluntario(conn, voluntario_info['id'])

        if minha_escala_df.empty:
            st.info("Você ainda não foi escalado(a) para nenhuma data.")
        else:
            # Renomeia as colunas para exibição
            minha_escala_df.columns = ["Data do Culto", "Minha Função"]
            st.dataframe(minha_escala_df, hide_index=True, use_container_width=True)
            
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar sua escala: {e}")