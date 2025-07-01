import locale
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar

# --- CONSTANTES DA APLICAÇÃO ---
ATRIBUICOES_LISTA = [
    "Lider da escala",
    "Recepção",
    "Baby Historia",
    "Baby Auxiliar",
    "Inclusão",
    "Primario/Juvenil",
    "Auxiliar"
]

DISPONIBILIDADE_OPCOES = [
    "Domingo manhã",
    "Domingo tarde",
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
    """Gera uma lista de opções para indisponibilidade (quintas e domingos) do próximo mês."""
    configurar_localidade()
    hoje = datetime.now()
    proximo_mes_data = hoje + relativedelta(months=1)
    ano = proximo_mes_data.year
    mes = proximo_mes_data.month

    nome_mes_ref = proximo_mes_data.strftime("%B").capitalize()
    opcoes_indisponibilidade = []
    num_dias = calendar.monthrange(ano, mes)[1]

    for dia in range(1, num_dias + 1):
        data_atual = datetime(ano, mes, dia)
        dia_da_semana = data_atual.weekday()  # Segunda-feira é 0, Domingo é 6

        if dia_da_semana == 3:  # Quinta-feira
            opcoes_indisponibilidade.append(f"{data_atual.strftime('%d/%m')} - Quinta-feira")
        elif dia_da_semana == 6:  # Domingo
            opcoes_indisponibilidade.append(f"{data_atual.strftime('%d/%m')} - Domingo Manhã")
            opcoes_indisponibilidade.append(f"{data_atual.strftime('%d/%m')} - Domingo Noite")

    return opcoes_indisponibilidade, f"{nome_mes_ref} de {ano}"