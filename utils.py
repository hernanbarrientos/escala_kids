import locale
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
from collections import defaultdict # Importe defaultdict aqui

# --- CONSTANTES DA APLICAÇÃO ---
ATRIBUICOES_LISTA = [
    "Administrador"
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
    # Usamos defaultdict(list) para que cada nova chave crie uma lista vazia automaticamente
    opcoes_agrupadas = defaultdict(list) 
    num_dias = calendar.monthrange(ano, mes)[1]

    for dia in range(1, num_dias + 1):
        data_atual = datetime(ano, mes, dia)
        dia_da_semana = data_atual.weekday()  # Segunda-feira é 0, Domingo é 6

        if dia_da_semana == 3:  # Quinta-feira (índice 3)
            opcoes_agrupadas["Quinta-feira"].append(data_atual.strftime("%d/%m"))
        elif dia_da_semana == 6:  # Domingo (índice 6)
            opcoes_agrupadas["Domingo Manhã"].append(data_atual.strftime("%d/%m"))
            opcoes_agrupadas["Domingo Noite"].append(data_atual.strftime("%d/%m")) # Mantive "Noite" conforme seu código original

    # Convertendo o defaultdict para um dict regular antes de retornar, se preferir
    # return dict(opcoes_agrupadas), f"{nome_mes_ref} de {ano} {proximo_mes_data.year}"
    
    # Adicionando o ano completo na referência do mês para evitar ambiguidades em viradas de ano
    return opcoes_agrupadas, f"{nome_mes_ref} de {proximo_mes_data.year}"