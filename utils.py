# utils.py
import streamlit as st
from collections import defaultdict
import locale
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
import bcrypt
import io
import pandas as pd
from weasyprint import HTML, CSS

# --- CONSTANTES DA APLICAÇÃO ---
ATRIBUICOES_LISTA = [
    "Lider da escala", "Recepção", "Auxiliar", "Baby Historia",
    "Primario/Juvenil", "Inclusão", "Baby Auxiliar",    
]

DISPONIBILIDADE_OPCOES = ["Domingo Manhã", "Domingo Noite", "Quinta-feira"]

# --- FUNÇÃO DE RENDERIZAÇÃO DA SIDEBAR ---
def render_sidebar():
    # A sidebar só aparece para admins
    if st.session_state.get('user_role') != 'admin':
        return # Não faz nada se não for admin

    with st.sidebar:
        st.title("Ministério Kids")
        st.markdown("---")
        
        nome_usuario = st.session_state.get('voluntario_info', {}).get('nome', 'Admin')
        st.write(f"Bem-vindo(a), **{nome_usuario}**!")
        
        st.header("Menu do Administrador")
        if st.button("Administração", use_container_width=True, type="primary" if st.session_state.get('page') == "painel_admin" else "secondary"):
            st.session_state.page = "painel_admin"; st.rerun()
        if st.button("Gerar e Editar Escala", use_container_width=True, type="primary" if st.session_state.get('page') == "gerar_escala" else "secondary"):
            st.session_state.page = "gerar_escala"; st.rerun()
        if st.button("Ver Comentários", use_container_width=True, type="primary" if st.session_state.get('page') == "comentarios" else "secondary"):
            st.session_state.page = "comentarios"; st.rerun()
        if st.button("Solicitações de Troca", use_container_width=True, type="primary" if st.session_state.get('page') == "solicitacoes_troca" else "secondary"):
            st.session_state.page = "solicitacoes_troca"; st.rerun()
        
        # Botão de Alterar Senha específico para o admin
        if st.button("Alterar Senha", use_container_width=True, type="primary" if st.session_state.get('page') == "alterar_senha" else "secondary"):
            st.session_state.page = "alterar_senha"; st.rerun()

        st.markdown("---")
        if st.button("🚪 Sair (Logout)", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.page = 'login'
            st.rerun()

        #     st.markdown("---")
        #     if user_role == 'admin':
        #         with st.expander("Modo Avançado"):
        #             st.toggle("Habilitar Ferramentas de Desenvolvedor", key="dev_mode")
        #         st.markdown("---")
        #     if st.button("Logout", use_container_width=True):
        #         for key in ['logged_in', 'user_role', 'voluntario_info', 'dev_mode']:
        #             if key in st.session_state: del st.session_state[key]
        #         st.session_state.page = "login"; st.rerun()
        # else:
        #     st.info("Faça o login para acessar o sistema.")

# --- FUNÇÕES DE DATA E LOCALIDADE ---
def configurar_localidade():
    try: locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    except locale.Error:
        try: locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
        except locale.Error: print("Localidade pt_BR não encontrada.")

def get_dias_culto_proximo_mes(disponibilidade_geral_voluntario: list = None):
    configurar_localidade()
    if disponibilidade_geral_voluntario is None:
        disponibilidade_geral_voluntario = DISPONIBILIDADE_OPCOES
    hoje = datetime.now()
    proximo_mes_data = hoje + relativedelta(months=1)
    ano, mes = proximo_mes_data.year, proximo_mes_data.month
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
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed_password):
    try: return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except (ValueError, TypeError): return False

# --- NOVA E FINAL FUNÇÃO DE GERAÇÃO DE PDF ---
def gerar_pdf_escala(dados_agrupados: dict, mes_referencia: str):
    """
    Gera um PDF da escala em 3 colunas, formato retrato, usando HTML e WeasyPrint.
    """
    
    # Extrai somente o "MÊS / ANO"
    titulo_pdf = mes_referencia.replace(' de ', ' / ').upper()

    css_string = """
    @page { 
        size: 22cm 35cm; /* Página em pé (retrato) */
        margin: 0.75cm;
    }
    body { 
        font-family: Arial, sans-serif; 
        font-size: 7pt;
        color: #333;
    }
    .titulo_principal {
        text-align: center;
        font-size: 18pt;
        font-weight: bold;
        margin-bottom: 16px;
        margin-top: 0;
    }
    .container_colunas {
        display: flex;
        justify-content: space-between; /* Espaçamento entre as colunas */
        align-items: flex-start;
        gap: 2px; /* Espaço entre as colunas */
    }
    .coluna {
        flex: 1; /* Faz as colunas terem a mesma largura */
        display: flex;
        flex-direction: column;
        gap: 8px; /* Espaço entre os blocos de data */
    }
    .titulo_coluna {
        background-color: #333;
        color: white;
        text-align: center;
        padding: 4px;
        font-weight: bold;
        border-radius: 5px;
        font-size: 8pt;
    }
    .bloco_data {
        border: 1px solid #ccc;
        border-radius: 5px;
        overflow: hidden; /* Garante que o conteúdo não saia das bordas arredondadas */
    }
    .data_cabecalho {
        background-color: #f2f2f2;
        text-align: center;
        padding: 4px;
        font-weight: bold;
    }
    .tabela_atribuicoes {
        width: 100%;
        border-collapse: collapse;
    }
    .tabela_atribuicoes td {
        padding: 4px 6px;
        border-top: 1px solid #eee; /* Linha sutil entre as atribuições */
    }
    .tabela_atribuicoes .funcao {
        font-weight: bold;
        width: 40%; /* Ajusta a largura da coluna de função */
    }
    """

    # Monta o HTML do corpo do PDF
    html_colunas = ""
    ordem_colunas = ["Domingo Manhã", "Domingo Noite", "Quinta-feira"]

    for nome_coluna in ordem_colunas:
        html_colunas += '<div class="coluna">'
        html_colunas += f'<div class="titulo_coluna">{nome_coluna.upper()}</div>'
        
        # Verifica se existe dados para esta coluna
        if nome_coluna in dados_agrupados:
            # Ordena as datas para garantir que apareçam em ordem cronológica
            datas_ordenadas = sorted(dados_agrupados[nome_coluna].keys())

            for data in datas_ordenadas:
                html_colunas += '<div class="bloco_data">'
                html_colunas += f'<div class="data_cabecalho">{data}/{titulo_pdf.split(" / ")[1]}</div>'
                html_colunas += '<table class="tabela_atribuicoes">'
                
                # Pega a lista de atribuições para a data
                atribuicoes = dados_agrupados[nome_coluna][data]
                for funcao, voluntario in atribuicoes:
                    html_colunas += f'<tr><td class="funcao">{funcao}</td><td>{voluntario}</td></tr>'
                
                html_colunas += '</table></div>'
        
        html_colunas += '</div>'


    # Monta o documento HTML final
    html_string = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Escala {mes_referencia}</title>
        <style>{css_string}</style>
    </head>
    <body>
        <div class="titulo_principal">{titulo_pdf}</div>
        <div class="container_colunas">{html_colunas}</div>
    </body>
    </html>
    """

    return HTML(string=html_string).write_pdf()

#responsividade
# NOVA SIDEBAR - apenas para voluntários no desktop
def render_volunteer_sidebar():
    """Cria a sidebar de navegação para voluntários, visível apenas em desktop."""
    with st.sidebar:
        st.title(f"Olá, {st.session_state.voluntario_info['nome']}!")
        st.markdown("---")
        if st.button("Confirmar Disponibilidade", use_container_width=True):
            st.session_state.page = 'painel_voluntario'
            st.rerun()
        if st.button("Ver Minha Escala", use_container_width=True):
            st.session_state.page = 'minha_escala'
            st.rerun()
        if st.button("Alterar Senha", use_container_width=True):
            st.session_state.page = 'alterar_senha'
            st.rerun()
        st.markdown("---")
        if st.button("🚪 Sair (Logout)", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.page = 'login'
            st.rerun()

# NOVA BARRA DE NAVEGAÇÃO - apenas para voluntários no celular
def render_mobile_nav():
    """Cria a barra de navegação no rodapé, visível apenas em mobile."""
    st.markdown('<div class="mobile-nav">', unsafe_allow_html=True)
    cols = st.columns(4)
    with cols[0]:
        if st.button("🗓️ Disponibilidade", use_container_width=True, help="Confirmar Disponibilidade"):
            st.session_state.page = 'painel_voluntario'; st.rerun()
    with cols[1]:
        if st.button("📅 Escala", use_container_width=True, help="Ver Minha Escala"):
            st.session_state.page = 'minha_escala'; st.rerun()
    with cols[2]:
        if st.button("🔒 Senha", use_container_width=True, help="Alterar Senha"):
            st.session_state.page = 'alterar_senha'; st.rerun()
    with cols[3]:
        if st.button("🚪 Sair", use_container_width=True, help="Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.page = 'login'; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)