import streamlit as st
import database as db
import utils

st.set_page_config(page_title="Portal do Voluntário", layout="wide")

# --- VERIFICAÇÃO DE LOGIN (AUTH GUARD) ---
if not st.session_state.get('logged_in') or st.session_state.user_role != 'voluntario':
    st.error("Você precisa estar logado como voluntário para acessar esta página.")
    if st.button("Ir para Login"):
        st.switch_page("app.py")
    st.stop()

# --- CONTEÚDO DA PÁGINA ---
conn = db.conectar_db()
voluntario = st.session_state.voluntario_info

nome_voluntario = voluntario.get("nome", "Voluntário")

st.title(f"Portal de {nome_voluntario}")
st.markdown("---")

st.subheader("🗓️ Informar Indisponibilidade para a Próxima Escala")

opcoes_agrupadas, mes_ref = utils.get_dias_culto_proximo_mes()
st.info(f"Atenção: A indisponibilidade informada será para a escala de **{mes_ref}**.")

# --- CARREGAR INFORMAÇÕES ANTERIORES ---
indisponibilidade_anterior = db.carregar_indisponibilidade(conn, voluntario.get("id"), mes_ref)
datas_restricao_salvas = []
serviu_ceia_salvo = "Não" # Padrão
if indisponibilidade_anterior:
    # Separa as datas em uma lista
    datas_restricao_salvas = [d.strip() for d in indisponibilidade_anterior['datas_restricao'].split(',') if d.strip()]
    serviu_ceia_salvo = indisponibilidade_anterior['serviu_ceia']

# --- VERIFICAR STATUS DE EDIÇÃO ---
edicao_liberada = db.get_edicao_liberada(conn, mes_ref)

if not edicao_liberada:
    st.warning(f"As edições para a escala de **{mes_ref}** estão bloqueadas no momento. Você pode visualizar suas opções enviadas, mas não poderá alterá-las.")
else:
    st.success(f"As edições para a escala de **{mes_ref}** estão liberadas. Você pode alterar suas opções.")


st.write("Selecione os dias e horários que você **NÃO** poderá servir:")

cols_to_display = sorted(opcoes_agrupadas.keys(), key=lambda x: ("Domingo" not in x, "Manhã" in x, x))
cols = st.columns(len(cols_to_display))
datas_selecionadas_atuais = []

for i, dia_turno in enumerate(cols_to_display):
    datas = opcoes_agrupadas[dia_turno]
    with cols[i]:
        st.write(f"**{dia_turno}**")
        for data_opcao_str in datas:
            # Formato completo para comparação com o salvo
            full_option_str = f"{data_opcao_str} - {dia_turno}" 
            
            # Define o estado inicial do checkbox baseado nas opções salvas
            is_checked = full_option_str in datas_restricao_salvas
            
            # O checkbox é desabilitado se a edição não estiver liberada
            if st.checkbox(data_opcao_str, key=f"{dia_turno}-{data_opcao_str}", value=is_checked, disabled=not edicao_liberada):
                datas_selecionadas_atuais.append(full_option_str)

# Define o valor padrão do radio button com base no que foi salvo
ceia_passada_radio_value = st.radio(
    "Você serviu na Ceia do mês passado?",
    ["Não", "Sim"],
    index=0 if serviu_ceia_salvo == "Não" else 1, # Define o índice baseado no valor salvo
    disabled=not edicao_liberada
)

voluntario_id = voluntario.get("id")
if not voluntario_id:
    st.error("Erro: ID do voluntário não encontrado.")
    conn.close() # Garante que a conexão seja fechada em caso de erro crítico
    st.stop()

if st.button("Enviar Indisponibilidade", type="primary", disabled=not edicao_liberada):
    datas_restricao_final = ", ".join(datas_selecionadas_atuais)
    if db.salvar_indisponibilidade(conn, voluntario_id, datas_restricao_final, ceia_passada_radio_value, mes_ref):
        st.success("Sua indisponibilidade foi registrada/atualizada com sucesso!")
        # Atualiza o estado da sessão para refletir as mudanças imediatamente
        st.session_state.indisponibilidade_enviada = True # Pode usar para forçar um re-render se necessário
        st.rerun() # Recarrega a página para mostrar as opções atualizadas e o status
    else:
        st.error("Ocorreu um erro ao registrar/atualizar sua indisponibilidade.")


if st.sidebar.button("Logout"):
    for key in st.session_state.keys():
        del st.session_state[key]
    conn.close()
    st.switch_page("app.py")

conn.close() # Garante que a conexão seja fechada ao final da execução do script