# views/minha_escala.py
import streamlit as st
import pandas as pd
import database as db
from datetime import datetime

def show_page():
    # --- Verificação de Login ---
    if not st.session_state.get('logged_in') or st.session_state.user_role != 'voluntario':
        st.error("Você precisa estar logado como voluntário para acessar esta página.")
        if st.button("Ir para Login"):
            st.session_state.page = 'login'
            st.rerun()
        st.stop()
    
    # --- Conteúdo da Página ---
    conn = st.session_state.db_conn
    voluntario_info = st.session_state.voluntario_info
    
    st.title(f"🗓️ Minha Escala")
    st.write(f"Olá, **{voluntario_info['nome']}**! Aqui estão os seus compromissos e a oportunidade de deixar seu feedback.")
    st.markdown("---")

    # --- AJUSTE PARA TESTE ---
    # Adicionamos um checkbox para ativar/desativar o modo de teste
    with st.expander("Opções de Teste (Apenas para desenvolvimento)"):
        modo_teste = st.checkbox("Ativar modo de teste de feedback (trata todas as escalas como passadas)")
    st.markdown("---")
    # -------------------------

    try:
        minha_escala_df = db.get_escala_por_voluntario(conn, voluntario_info['id'])

        if minha_escala_df.empty:
            st.info("Você ainda não foi escalado(a) para nenhuma data.")
        else:
            # Converte a coluna de data para o formato datetime para comparação
            minha_escala_df['data_culto_dt'] = pd.to_datetime(minha_escala_df['data_culto'].str.split(' - ').str[0], format='%d/%m')
            hoje = datetime.now()
            minha_escala_df['data_culto_dt'] = minha_escala_df['data_culto_dt'].apply(
                lambda dt: dt.replace(year=hoje.year + 1) if dt.month < hoje.month else dt.replace(year=hoje.year)
            )

            # --- LÓGICA DE TESTE APLICADA AQUI ---
            if modo_teste:
                # Se o modo de teste estiver ativo, todas as escalas são consideradas "passadas"
                escalas_futuras = pd.DataFrame()
                escalas_passadas = minha_escala_df
            else:
                # Comportamento normal da aplicação
                escalas_futuras = minha_escala_df[minha_escala_df['data_culto_dt'].dt.date >= hoje.date()]
                escalas_passadas = minha_escala_df[minha_escala_df['data_culto_dt'].dt.date < hoje.date()]
            # ------------------------------------

            st.subheader("Próximas Escalas")
            if not escalas_futuras.empty:
                st.dataframe(
                    escalas_futuras[['data_culto', 'funcao']].rename(columns={'data_culto': 'Data do Culto', 'funcao': 'Minha Função'}), 
                    hide_index=True, 
                    use_container_width=True
                )
            else:
                st.info("Nenhuma escala futura encontrada.")

            st.markdown("---")
            st.subheader("Deixar Feedback de Escalas Anteriores")

            if not escalas_passadas.empty:
                for _, linha in escalas_passadas.iterrows():
                    data_culto = linha['data_culto']
                    funcao = linha['funcao']
                    
                    with st.expander(f"**{data_culto}** - Função: **{funcao}**"):
                        feedback_enviado = db.feedback_ja_enviado(conn, voluntario_info['id'], data_culto)
                        
                        if feedback_enviado:
                            st.success("✔️ Você já enviou seu feedback para este dia. Obrigado!")
                        else:
                            with st.form(key=f"form_{data_culto}"):
                                comentario = st.text_area("Deixe seu comentário, sugestão ou ponto de melhoria:", key=f"comment_{data_culto}", height=150)
                                if st.form_submit_button("Enviar Feedback"):
                                    if comentario:
                                        if db.salvar_feedback(conn, voluntario_info['id'], voluntario_info['nome'], data_culto, comentario):
                                            st.success("Seu feedback foi enviado com sucesso!")
                                            st.rerun()
                                        else:
                                            st.error("Ocorreu um erro ao enviar seu feedback.")
                                    else:
                                        st.warning("Por favor, escreva um comentário antes de enviar.")
            else:
                st.info("Nenhuma escala anterior encontrada para deixar feedback.")
            
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar sua escala: {e}")