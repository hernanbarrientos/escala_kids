# utils.py

import locale
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
from collections import defaultdict
import bcrypt 
import streamlit as st

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

# --- FUNÇÕES AUXILIARES ---
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
    # --- CORREÇÃO APLICADA AQUI ---
    # Garante que a localidade seja definida para Português
    configurar_localidade()
    
    if disponibilidade_geral_voluntario is None:
        # Se nenhuma disponibilidade for fornecida, retorna todos os dias de culto possíveis
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
        elif dia_da_semana == 6: # Domingo
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
    
def render_sidebar():
    with st.sidebar:
        st.title("Ministério Kids")
        st.markdown("---")

        if st.session_state.get("logged_in"):
            st.write(f"Bem-vindo(a), **{st.session_state.voluntario_info['nome']}**!")
            
            if st.session_state.user_role == 'admin':
                st.header("Menu do Administrador")
                if st.button("Administração", use_container_width=True, type="primary" if st.session_state.page == "painel_admin" else "secondary"):
                    st.session_state.page = "painel_admin"
                    st.rerun()
                if st.button("Gerar Escala", use_container_width=True, type="primary" if st.session_state.page == "gerar_escala" else "secondary"):
                    st.session_state.page = "gerar_escala"
                    st.rerun()
            else: # 'voluntario'
                st.header("Menu do Voluntário")
                if st.button("Meu Painel", use_container_width=True, type="primary" if st.session_state.page == "painel_voluntario" else "secondary"):
                    st.session_state.page = "painel_voluntario"
                    st.rerun()

            if st.button("Alterar Senha", use_container_width=True, type="primary" if st.session_state.page == "alterar_senha" else "secondary"):
                st.session_state.page = "alterar_senha"
                st.rerun()

            st.markdown("---")
            if st.button("Logout", use_container_width=True):
                keys_to_keep = ['page']
                for key in list(st.session_state.keys()):
                    if key not in keys_to_keep: del st.session_state[key]
                st.session_state.logged_in = False
                st.session_state.page = "login"
                st.rerun()
        else:
            st.info("Faça o login para acessar o sistema.")