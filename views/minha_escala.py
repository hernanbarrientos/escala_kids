# views/minha_escala.py
import streamlit as st
import pandas as pd
import database as db
import utils
from datetime import datetime, date

def show_page():
    # --- Verificação de Login e Permissão ---
    if not st.session_state.get('logged_in') or st.session_state.user_role != 'voluntario':
        st.error("Você precisa estar logado como voluntário para acessar esta página.")
        if st.button("Ir para Login"):
            st.session_state.page = 'login'
            st.rerun()
        st.stop()
    
    # --- Conteúdo da Página ---
    
    voluntario_info = st.session_state.voluntario_info
    
    # Lógica para exibir a mensagem de sucesso (para feedbacks)
    if 'feedback_salvo_sucesso' in st.session_state and st.session_state.feedback_salvo_sucesso:
        st.success("✅ Seu feedback foi enviado com sucesso! Obrigado.")
        del st.session_state.feedback_salvo_sucesso

    nome_voluntario = voluntario_info.get("nome", "Voluntário")
    st.title(f"🗓️ Minha Escala")
    st.write(f"Olá, **{nome_voluntario}**! Aqui estão os seus compromissos.")
    st.markdown("---")

    # Ferramenta de teste para simular datas na sidebar
    with st.sidebar:
        st.subheader("⚙️ Ferramentas de Teste")
        data_simulada = st.date_input("Simular Data Atual:", value=date.today(), key="sim_date")
        st.caption("Mude esta data para o futuro para testar o envio de feedbacks.")

    try:
        minha_escala_df = db.get_escala_por_voluntario(voluntario_info['id'])

        if minha_escala_df.empty:
            st.info("Você ainda não foi escalado(a) para nenhuma data.")
        else:
            # Lógica para separar escalas futuras e passadas usando a data simulada
            minha_escala_df['data_culto_dt'] = pd.to_datetime(minha_escala_df['data_culto'].str.split(' - ').str[0], format='%d/%m')
            hoje = datetime.combine(data_simulada, datetime.min.time())
            minha_escala_df['data_culto_dt'] = minha_escala_df['data_culto_dt'].apply(
                lambda dt: dt.replace(year=hoje.year + 1) if dt.month < hoje.month else dt.replace(year=hoje.year)
            )
            escalas_futuras = minha_escala_df[minha_escala_df['data_culto_dt'].dt.date >= hoje.date()]
            escalas_passadas = minha_escala_df[minha_escala_df['data_culto_dt'].dt.date < hoje.date()]

            # --- SEÇÃO 1: PRÓXIMAS ESCALAS E SOLICITAÇÃO DE TROCA ---
            st.subheader("Próximas Escalas")
            st.caption("Clique em uma escala para ver as opções de substituição.")

            if not escalas_futuras.empty:
                # Layout em duas colunas
                col1, col2 = st.columns(2)
                cols = [col1, col2]

                if 'form_troca_aberto' not in st.session_state:
                    st.session_state.form_troca_aberto = None

                for idx, (_, linha) in enumerate(escalas_futuras.iterrows()):
                    col_atual = cols[idx % 2]
                    with col_atual:
                        escala_id = linha['id']
                        data_culto = linha['data_culto']
                        funcao = linha['funcao']

                        # Cada escala é um botão que controla a visibilidade do formulário
                        if st.button(f"**{data_culto}** - Função: **{funcao}**", key=f"btn_escala_{escala_id}", use_container_width=True):
                            st.session_state.form_troca_aberto = escala_id if st.session_state.form_troca_aberto != escala_id else None
                            st.rerun() # Força o recarregamento para mostrar/ocultar o formulário
                        
                        # Se o formulário para esta escala deve estar aberto, exibe-o
                        if st.session_state.form_troca_aberto == escala_id:
                            with st.container(border=True):
                                if funcao == 'Apoio':
                                    st.warning("A função de Apoio é vinculada à Recepção. Para trocas, solicite na escala de 'Recepção'.", icon="ℹ️")
                                else:
                                    solicitacoes_pendentes_df = db.get_solicitacoes_pendentes()
                                    ja_solicitado = escala_id in solicitacoes_pendentes_df['escala_original_id'].values

                                    if ja_solicitado:
                                        st.info("Você já tem uma solicitação pendente para esta escala.")
                                    else:
                                        with st.form(key=f"form_troca_{escala_id}"):
                                            todos_voluntarios_df = db.listar_voluntarios()
                                            voluntarios_aptos = todos_voluntarios_df[
                                                (todos_voluntarios_df['atribuicoes'].str.contains(funcao, na=False)) &
                                                (todos_voluntarios_df['id'] != voluntario_info['id'])
                                            ]
                                            
                                            if voluntarios_aptos.empty:
                                                st.warning("Não há outros voluntários qualificados para esta função no momento.")
                                            else:
                                                lista_nomes = voluntarios_aptos['nome'].tolist()
                                                substituto_nome = st.selectbox("Selecione o voluntário substituto:", options=lista_nomes)
                                                
                                                if st.form_submit_button("Enviar Solicitação"):
                                                    if substituto_nome:
                                                        substituto_id = int(voluntarios_aptos[voluntarios_aptos['nome'] == substituto_nome].iloc[0]['id'])
                                                        db.criar_solicitacao_substituicao(escala_id, voluntario_info['id'], voluntario_info['nome'], substituto_id, substituto_nome, data_culto, funcao)
                                                        st.success("Solicitação de troca enviada com sucesso!")
                                                        st.session_state.form_troca_aberto = None # Fecha o formulário
                                                        st.rerun()
                                                    else:
                                                        st.error("Você precisa selecionar um substituto.")
            else:
                st.info("Nenhuma escala futura encontrada.")

            # --- SEÇÃO 2: FEEDBACK DE ESCALAS ANTERIORES ---
            st.markdown("---")
            st.subheader("Deixar Feedback de Escalas Anteriores")

            if not escalas_passadas.empty:
                for _, linha in escalas_passadas.iterrows():
                    data_culto = linha['data_culto']
                    funcao = linha['funcao']
                    
                    with st.expander(f"**{data_culto}** - Função: **{funcao}**"):
                        feedback_enviado = db.feedback_ja_enviado(voluntario_info['id'], data_culto, funcao)
                        
                        if feedback_enviado:
                            st.success("✔️ Você já enviou seu feedback para esta escala específica. Obrigado!")
                        else:
                            form_key = f"form_feedback_{data_culto}_{funcao}".replace(" ", "_")
                            with st.form(key=form_key):
                                comentario = st.text_area("Deixe seu comentário ou sugestão:", key=f"comment_{form_key}", height=100)
                                if st.form_submit_button("Enviar Feedback"):
                                    if comentario:
                                        if db.salvar_feedback(voluntario_info['id'], voluntario_info['nome'], data_culto, funcao, comentario):
                                            st.session_state.feedback_salvo_sucesso = True
                                            st.rerun()
                                        else:
                                            st.error("Ocorreu um erro ao enviar seu feedback.")
                                    else:
                                        st.warning("Por favor, escreva um comentário.")
            else:
                st.info("Nenhuma escala anterior encontrada para deixar feedback.")
            
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar sua escala: {e}")