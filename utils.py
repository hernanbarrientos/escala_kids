# utils.py

import locale
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
from collections import defaultdict
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

def get_dias_culto_proximo_mes():
    """
    Gera um dicionário de opções para indisponibilidade (quintas e domingos) do próximo mês,
    agrupadas por dia da semana e turno.
    """
    configurar_localidade()
    hoje = datetime.now()
    proximo_mes_data = hoje + relativedelta(months=1)
    ano = proximo_mes_data.year
    mes = proximo_mes_data.month

    nome_mes_ref = proximo_mes_data.strftime("%B").capitalize()
    opcoes_agrupadas = defaultdict(list) 
    num_dias = calendar.monthrange(ano, mes)[1]

    for dia in range(1, num_dias + 1):
        data_atual = datetime(ano, mes, dia)
        dia_da_semana = data_atual.weekday() # Segunda-feira é 0, Domingo é 6

        if dia_da_semana == 3: # Quinta-feira (índice 3)
            opcoes_agrupadas["Quinta-feira"].append(data_atual.strftime("%d/%m"))
        elif dia_da_semana == 6: # Domingo (índice 6)
            opcoes_agrupadas["Domingo Manhã"].append(data_atual.strftime("%d/%m"))
            opcoes_agrupadas["Domingo Noite"].append(data_atual.strftime("%d/%m"))

    # Retorna o defaultdict e o nome do mês de referência
    return opcoes_agrupadas, f"{nome_mes_ref} de {proximo_mes_data.year}"

# --- FUNÇÕES DE SEGURANÇA (SENHAS) ---
def hash_password(password):
    """
    Gera um hash bcrypt da senha fornecida.
    A senha deve ser codificada para bytes antes de ser hasheada.
    """
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8') # Decodifica de volta para string para armazenamento

def check_password(password, hashed_password):
    """
    Verifica se a senha fornecida corresponde ao hash armazenado.
    Ambas devem ser codificadas para bytes.
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        # Lida com casos onde o hash armazenado pode estar malformado
        return False