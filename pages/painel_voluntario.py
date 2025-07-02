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
nome_voluntario = voluntario.get("nome", "Voluntário")

st.title(f"Portal de {nome_voluntario}")
st.markdown("---")

st.subheader("🗓️ Informar Indisponibilidade para a Próxima Escala")

# get_dias_culto_proximo_mes agora retorna um dicionário agrupado e o mês de referência
opcoes_agrupadas, mes_ref = utils.get_dias_culto_proximo_mes()
st.info(f"Atenção: A indisponibilidade informada será para a escala de **{mes_ref}**.")

st.write("Selecione os dias e horários que você **NÃO** poderá servir:")

# Crie as colunas dinamicamente
# Ordena as chaves para garantir que a ordem das colunas seja consistente (ex: Domingo Manhã, Domingo Noite, Quinta-feira)
sorted_keys = sorted(opcoes_agrupadas.keys(), key=lambda x: ("Domingo" not in x, "Manhã" in x, x))
cols = st.columns(len(sorted_keys))
datas_selecionadas = []

# Itere sobre as colunas e crie os checkboxes
for i, dia_turno in enumerate(sorted_keys):
    datas = opcoes_agrupadas[dia_turno]
    with cols[i]:
        st.write(f"**{dia_turno}**")
        for data_opcao in datas:
            # A chave única é crucial para o Streamlit
            if st.checkbox(data_opcao, key=f"{dia_turno}-{data_opcao}"):
                datas_selecionadas.append(f"{data_opcao} - {dia_turno}") # Adiciona o dia/turno para melhor clareza ao salvar

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