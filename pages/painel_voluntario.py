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

# Verifique a estrutura e acesse corretamente
#st.write("Debug voluntario_info:", voluntario)
nome_voluntario = voluntario.get("nome", "Voluntário")

st.title(f"Portal de {nome_voluntario}")
st.markdown("---")

st.subheader("🗓️ Informar Indisponibilidade para a Próxima Escala")

opcoes, mes_ref = utils.get_dias_culto_proximo_mes()
st.info(f"Atenção: A indisponibilidade informada será para a escala de **{mes_ref}**.")

datas_selecionadas = st.multiselect(
    "Selecione os dias e horários que você **NÃO** poderá servir:",
    options=opcoes
)

ceia_passada = st.radio("Você serviu na Ceia do mês passado?", ["Não", "Sim"])

voluntario_id = voluntario.get("id")
if not voluntario_id:
    st.error("Erro: ID do voluntário não encontrado.")
    st.stop()

if st.button("Enviar Indisponibilidade", type="primary"):
    datas_restricao_str = ", ".join(datas_selecionadas)
    db.salvar_indisponibilidade(conn, voluntario_id, datas_restricao_str, ceia_passada, mes_ref)
    st.success("Sua indisponibilidade foi registrada com sucesso!")

    

if st.sidebar.button("Logout"):
    for key in st.session_state.keys():
        del st.session_state[key]
    st.switch_page("app.py")