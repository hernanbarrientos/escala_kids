# views/painel_voluntario.py
import streamlit as st
import database as db
import utils

def show_page():
#     # --- Verificação de Login e Permissão ---
#     if not st.session_state.get('logged_in') or st.session_state.user_role != 'voluntario':
#         st.error("Você precisa estar logado como voluntário para acessar esta página.")
#         if st.button("Ir para Login"):
#             st.session_state.page = 'login'
#             st.rerun()
#         st.stop()
# def render_content(): # A função agora se chama render_content


    # --- Conteúdo da Página ---
    voluntario = st.session_state.voluntario_info
    
    if 'disponibilidade_salva_sucesso' in st.session_state and st.session_state.disponibilidade_salva_sucesso:
        st.success("✅ Sua disponibilidade foi registrada/atualizada com sucesso!")
        del st.session_state.disponibilidade_salva_sucesso

    nome_voluntario = voluntario.get("nome", "Voluntário")
    # st.title(f"Portal de {nome_voluntario}")
    st.subheader("🗓️ Confirmar Disponibilidade para a Próxima Escala")

    disponibilidade_geral = [d.strip() for d in voluntario.get("disponibilidade", "").split(',') if d.strip()]
    opcoes_agrupadas, mes_ref = utils.get_dias_culto_proximo_mes(disponibilidade_geral)
    st.info(f"Atenção: Sua disponibilidade será registrada para a escala de **{mes_ref}**.")

    disponibilidade_salva = db.carregar_disponibilidade(voluntario.get("id"), mes_ref)
    datas_disponiveis_salvas = []
    serviu_ceia_salvo = "Não"
    if disponibilidade_salva:
        datas_raw = disponibilidade_salva.get('datas_disponiveis', '')
        if datas_raw:
            datas_disponiveis_salvas = [d.strip() for d in datas_raw.split(',') if d.strip()]
        serviu_ceia_salvo = disponibilidade_salva.get('ceia_passada', 'Não')

    edicao_liberada = db.get_edicao_liberada(mes_ref)
    if not edicao_liberada:
        st.warning(f"As edições para a escala de **{mes_ref}** estão bloqueadas.")


    # AJUSTE DE LAYOUT: A pergunta da Ceia foi movida para ANTES da lista de datas.
    ceia_passada_radio_value = st.radio(
        "Você serviu na Ceia do mês passado?",
        ["Não", "Sim"],
        index=0 if serviu_ceia_salvo == "Não" else 1,
        disabled=not edicao_liberada,
        horizontal=True # Deixa os botões lado a lado
    )
    
    # st.markdown("---")
    st.write("Selecione os dias e horários que você **ESTÁ DISPONÍVEL** para servir:")

    if not opcoes_agrupadas:
        st.info("No momento, não há datas disponíveis para seleção com base no seu perfil de disponibilidade. Fale com o administrador se achar que isso é um erro.")
    else:
        # NOVA REGRA: Identifica o primeiro domingo do mês para aplicar a lógica de bloqueio.
        primeiro_domingo_data = None
        # Pega a lista de datas de Domingo Manhã ou Noite, se existirem
        domingo_manha_datas = opcoes_agrupadas.get('Domingo Manhã', [])
        domingo_noite_datas = opcoes_agrupadas.get('Domingo Noite', [])
        
        # O primeiro domingo é a primeira data que aparece em qualquer uma das listas
        if domingo_manha_datas:
            primeiro_domingo_data = domingo_manha_datas[0]
        elif domingo_noite_datas:
            primeiro_domingo_data = domingo_noite_datas[0]

        serviu_na_ceia = (ceia_passada_radio_value == "Sim")
        
        cols_to_display = sorted(opcoes_agrupadas.keys())
        cols = st.columns(len(cols_to_display))
        datas_selecionadas_atuais = []

        for i, dia_turno in enumerate(cols_to_display):
            datas = opcoes_agrupadas[dia_turno]
            with cols[i]:
                st.write(f"**{dia_turno}**")
                for data_opcao_str in datas:
                    full_option_str = f"{data_opcao_str} - {dia_turno}"
                    is_checked_default = full_option_str in datas_disponiveis_salvas
                    
                    # NOVA REGRA: Verifica se o checkbox deve ser desabilitado
                    is_primeiro_domingo = (primeiro_domingo_data is not None) and (data_opcao_str == primeiro_domingo_data)
                    desabilitar_por_ceia = is_primeiro_domingo and serviu_na_ceia
                    
                    # O checkbox é desabilitado pela regra geral do admin OU pela regra da ceia
                    final_disabled_state = (not edicao_liberada) or desabilitar_por_ceia
                    
                    # Se for para desabilitar pela regra da ceia, garantimos que ele fique desmarcado
                    if desabilitar_por_ceia:
                        is_checked_default = False
                    
                    if st.checkbox(data_opcao_str, key=f"{dia_turno}-{data_opcao_str}", value=is_checked_default, disabled=final_disabled_state):
                        datas_selecionadas_atuais.append(full_option_str)

    st.markdown("---")
    
    voluntario_id = voluntario.get("id")
    if not voluntario_id:
        st.error("Erro: ID do voluntário não encontrado.")
        st.stop()

    if st.button("Salvar Disponibilidade", type="primary", disabled=not edicao_liberada):
        # Lógica de segurança para garantir que o primeiro domingo não seja salvo se "Sim" foi marcado
        if serviu_na_ceia and primeiro_domingo_data:
            datas_selecionadas_atuais = [
                d for d in datas_selecionadas_atuais 
                if not d.startswith(primeiro_domingo_data)
            ]

        datas_disponiveis_final = ", ".join(datas_selecionadas_atuais)
        if db.salvar_disponibilidade(voluntario_id, datas_disponiveis_final, ceia_passada_radio_value, mes_ref):
            st.session_state.disponibilidade_salva_sucesso = True
            st.rerun()
        else:
            st.error("Ocorreu um erro ao registrar/atualizar sua disponibilidade.")

    