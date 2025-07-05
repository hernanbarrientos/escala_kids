# views/painel_voluntario.py
import streamlit as st
import database as db
import utils

def show_page():
    # --- Verificação de Login e Permissão ---
    if not st.session_state.get('logged_in') or st.session_state.user_role != 'voluntario':
        st.error("Você precisa estar logado como voluntário para acessar esta página.")
        if st.button("Ir para Login"):
            st.session_state.page = 'login'
            st.rerun()
        st.stop()

    # --- Conteúdo da Página ---
    conn = db.conectar_db()
    voluntario = st.session_state.voluntario_info
    nome_voluntario = voluntario.get("nome", "Voluntário")

    st.title(f"Portal de {nome_voluntario}")
    st.markdown("---")

    st.subheader("🗓️ Confirmar Disponibilidade para a Próxima Escala")

    disponibilidade_geral = [d.strip() for d in voluntario.get("disponibilidade", "").split(',') if d.strip()]
    opcoes_agrupadas, mes_ref = utils.get_dias_culto_proximo_mes(disponibilidade_geral)
    st.info(f"Atenção: Sua disponibilidade será registrada para a escala de **{mes_ref}**.")

    # --- CARREGAR INFORMAÇÕES ANTERIORES ---
    disponibilidade_salva = db.carregar_disponibilidade(conn, voluntario.get("id"), mes_ref)
    datas_disponiveis_salvas = []
    serviu_ceia_salvo = "Não" # Padrão

    # <<<--- CORREÇÃO DEFINITIVA APLICADA AQUI ---<<<
    if disponibilidade_salva:
        # Acessa os dados usando colchetes ['chave'], que é o método correto para sqlite3.Row
        datas_raw = disponibilidade_salva['datas_disponiveis']
        if datas_raw:
            datas_disponiveis_salvas = [d.strip() for d in datas_raw.split(',') if d.strip()]
        
        # Acessa a outra coluna também com colchetes
        serviu_ceia_salvo = disponibilidade_salva['ceia_passada'] or "Não"

    # --- VERIFICAR STATUS DE EDIÇÃO ---
    edicao_liberada = db.get_edicao_liberada(conn, mes_ref)

    if not edicao_liberada:
        st.warning(f"As edições para a escala de **{mes_ref}** estão bloqueadas.")
    else:
        st.success(f"As edições para a escala de **{mes_ref}** estão liberadas.")

    st.markdown("---")
    st.write("Selecione os dias e horários que você **ESTÁ DISPONÍVEL** para servir:")

    if not opcoes_agrupadas:
        st.info("No momento, não há datas disponíveis para seleção com base no seu perfil. Fale com o administrador.")
    else:
        cols_to_display = sorted(opcoes_agrupadas.keys())
        cols = st.columns(len(cols_to_display))
        datas_selecionadas_atuais = []

        for i, dia_turno in enumerate(cols_to_display):
            datas = opcoes_agrupadas[dia_turno]
            with cols[i]:
                st.write(f"**{dia_turno}**")
                for data_opcao_str in datas:
                    full_option_str = f"{data_opcao_str} - {dia_turno}"
                    is_checked = full_option_str in datas_disponiveis_salvas
                    
                    if st.checkbox(data_opcao_str, key=f"{dia_turno}-{data_opcao_str}", value=is_checked, disabled=not edicao_liberada):
                        datas_selecionadas_atuais.append(full_option_str)

    st.markdown("---")
    ceia_passada_radio_value = st.radio(
        "Você serviu na Ceia do mês passado?",
        ["Não", "Sim"],
        index=0 if serviu_ceia_salvo == "Não" else 1,
        disabled=not edicao_liberada
    )

    voluntario_id = voluntario.get("id")
    if not voluntario_id:
        st.error("Erro: ID do voluntário não encontrado.")
        st.stop()

    if st.button("Salvar Disponibilidade", type="primary", disabled=not edicao_liberada):
        datas_disponiveis_final = ", ".join(datas_selecionadas_atuais)
        if db.salvar_disponibilidade(conn, voluntario_id, datas_disponiveis_final, ceia_passada_radio_value, mes_ref):
            st.success("Sua disponibilidade foi registrada/atualizada com sucesso!")
            st.rerun()
        else:
            st.error("Ocorreu um erro ao registrar/atualizar sua disponibilidade.")

    conn.close()