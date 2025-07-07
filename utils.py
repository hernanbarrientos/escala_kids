# utils.py
import streamlit as st
from collections import defaultdict
import locale
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
import bcrypt

# --- CONSTANTES DA APLICAÇÃO ---
ATRIBUICOES_LISTA = [
    "Lider da escala",
    "Recepção",
    "Auxiliar",
    "Baby Historia",
    "Primario/Juvenil",
    "Inclusão",
    "Baby Auxiliar",    
]

DISPONIBILIDADE_OPCOES = [
    "Domingo Manhã",  
    "Domingo Noite", 
    "Quinta-feira"
]

# --- FUNÇÃO DE RENDERIZAÇÃO DA SIDEBAR (VERSÃO ESTÁVEL) ---
def render_sidebar():
    """
    Cria a barra lateral de navegação de forma defensiva e estável, sem st.rerun().
    """
    with st.sidebar:
        st.title("Ministério Kids")
        st.markdown("---")

        if st.session_state.get("logged_in"):
            nome_usuario = st.session_state.get('voluntario_info', {}).get('nome', 'Usuário')
            st.write(f"Bem-vindo(a), **{nome_usuario}**!")
            
            user_role = st.session_state.get('user_role')

            if user_role == 'admin':
                st.header("Menu do Administrador")
                if st.button("Administração", use_container_width=True, type="primary" if st.session_state.get('page') == "painel_admin" else "secondary"):
                    st.session_state.page = "painel_admin"
                if st.button("Gerar Escala", use_container_width=True, type="primary" if st.session_state.get('page') == "gerar_escala" else "secondary"):
                    st.session_state.page = "gerar_escala"
                if st.button("Ver Comentários", use_container_width=True, type="primary" if st.session_state.get('page') == "comentarios" else "secondary"):
                    st.session_state.page = "comentarios"

            elif user_role == 'voluntario':
                st.header("Menu do Voluntário")
                if st.button("Confirmar Disponibilidade", use_container_width=True, type="primary" if st.session_state.get('page') == "painel_voluntario" else "secondary"):
                    st.session_state.page = "painel_voluntario"
                if st.button("Ver Minha Escala", use_container_width=True, type="primary" if st.session_state.get('page') == "minha_escala" else "secondary"):
                    st.session_state.page = "minha_escala"

            if st.button("Alterar Senha", use_container_width=True, type="primary" if st.session_state.get('page') == "alterar_senha" else "secondary"):
                st.session_state.page = "alterar_senha"

            st.markdown("---")
            if st.button("Logout", use_container_width=True):
                keys_to_clear = ['logged_in', 'user_role', 'voluntario_info']
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.session_state.page = "login"
                # st.rerun() é implicitamente chamado ao mudar de página via session_state no app.py
        else:
            st.info("Faça o login para acessar o sistema.")


# --- FUNÇÕES DE DATA E LOCALIDADE ---
def configurar_localidade():
    """Define a localidade para português para obter nomes de meses corretos."""
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
        except locale.Error:
            print("Localidade pt_BR não encontrada, usando padrão do sistema.")

def get_dias_culto_proximo_mes(disponibilidade_geral_voluntario: list = None):
    """
    Gera um dicionário de opções de culto para o próximo mês, filtrado pela
    disponibilidade geral do voluntário.
    """
    configurar_localidade()
    
    if disponibilidade_geral_voluntario is None:
        disponibilidade_geral_voluntario = DISPONIBILIDADE_OPCOES
    
    hoje = datetime.now()
    proximo_mes_data = hoje + relativedelta(months=1)
    ano = proximo_mes_data.year
    mes = proximo_mes_data.month
    nome_mes_ref = proximo_mes_data.strftime("%B").capitalize()

    opcoes_agrupadas = defaultdict(list)
    num_dias = calendar.monthrange(ano, mes)[1]

    for dia in range(1, num_dias + 1):
        data_atual = datetime(ano, mes, dia)
        dia_formatado = data_atual.strftime('%d/%m')
        dia_da_semana = data_atual.weekday()

        if dia_da_semana == 3 and "Quinta-feira" in disponibilidade_geral_voluntario:
            opcoes_agrupadas["Quinta-feira"].append(dia_formatado)
        elif dia_da_semana == 6:
            if "Domingo Manhã" in disponibilidade_geral_voluntario:
                opcoes_agrupadas["Domingo Manhã"].append(dia_formatado)
            if "Domingo Noite" in disponibilidade_geral_voluntario:
                opcoes_agrupadas["Domingo Noite"].append(dia_formatado)

    return dict(opcoes_agrupadas), f"{nome_mes_ref} de {ano}"


# --- FUNÇÕES DE SEGURANÇA (SENHAS) ---
def hash_password(password):
    """
    Gera um hash bcrypt da senha fornecida.
    """
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')

def check_password(password, hashed_password):
    """
    Verifica se a senha fornecida corresponde ao hash armazenado.
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except (ValueError, TypeError):
        return False