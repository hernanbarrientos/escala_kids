import streamlit as st
import pandas as pd
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar

# Importando nossos módulos
import database as db
import utils
from escala_config import NECESSIDADES_ESCALA

st.set_page_config(page_title="Gerar Escala", layout="wide")

# --- VERIFICAÇÃO DE LOGIN (AUTH GUARD) ---
if not st.session_state.get('logged_in') or st.session_state.user_role != 'admin':
    st.error("Acesso restrito a administradores.")
    if st.button("Ir para Login"):
        st.switch_page("app.py")
    st.stop()

# --- CONTEÚDO DA PÁGINA ---
conn = db.conectar_db()
st.title("🤖 Gerador Automático de Escalas")
st.markdown("---")

# Define o mês de referência para a escala (próximo mês)
hoje = datetime.now()
proximo_mes_data = hoje + relativedelta(months=1)
utils.configurar_localidade()
mes_referencia = f"{proximo_mes_data.strftime('%B').capitalize()} de {proximo_mes_data.year}"

st.info(f"A escala a ser gerada é para o mês de: **{mes_referencia}**")

if st.button("Gerar Nova Escala", type="primary"):
    with st.spinner("Processando regras e montando a escala... Isso pode levar um momento."):
        # 1. CARREGAR DADOS NECESSÁRIOS
        voluntarios_df = db.listar_voluntarios(conn)
        indisponibilidades_df = db.listar_indisponibilidades_por_mes(conn, mes_referencia)

        # Estrutura para armazenar a escala final
        escala_gerada = []

        # 2. ITERAR SOBRE OS DIAS DO MÊS
        ano = proximo_mes_data.year
        mes = proximo_mes_data.month
        num_dias_mes = calendar.monthrange(ano, mes)[1]

        for dia in range(1, num_dias_mes + 1):
            data_atual = datetime(ano, mes, dia)
            dia_semana = data_atual.weekday() # Seg=0, Dom=6

            tipos_culto_dia = []
            if dia_semana == 3: # Quinta-feira
                tipos_culto_dia.append(f"{data_atual.strftime('%d/%m')} - Quinta-feira")
            elif dia_semana == 6: # Domingo
                tipos_culto_dia.append(f"{data_atual.strftime('%d/%m')} - Domingo Manhã")
                tipos_culto_dia.append(f"{data_atual.strftime('%d/%m')} - Domingo Noite")

            # 3. PARA CADA CULTO, PREENCHER AS VAGAS
            for culto_str in tipos_culto_dia:
                tipo_culto_key = culto_str.split(' - ')[1] # "Quinta-feira", "Domingo Manhã", etc
                
                if tipo_culto_key not in NECESSIDADES_ESCALA:
                    continue

                necessidades = NECESSIDADES_ESCALA[tipo_culto_key]

                # Lista para rastrear quem já foi escalado NESTE culto
                ja_escalados_neste_culto = []

                for atribuicao, quantidade in necessidades.items():
                    for i in range(quantidade): # Para cada vaga da atribuição
                        
                        # 4. APLICAR REGRAS E FILTROS
                        
                        # REGRA 1: Possui a atribuição correta
                        candidatos = voluntarios_df[voluntarios_df['atribuicoes'].str.contains(atribuicao, na=False)]
                        
                        # REGRA 2: Não está indisponível
                        ids_indisponiveis = indisponibilidades_df[indisponibilidades_df['datas_restricao'].str.contains(culto_str, na=False)]['voluntario_id']
                        candidatos = candidatos[~candidatos['id'].isin(ids_indisponiveis)]
                        
                        # REGRA 3: Não serviu na ceia passada (se for o primeiro domingo)
                        # O primeiro domingo é o primeiro dia da semana que é domingo (weekday == 6)
                        if tipo_culto_key.startswith("Domingo") and dia <= 7:
                            ids_serviram_ceia = indisponibilidades_df[indisponibilidades_df['ceia_passada'] == 'Sim']['voluntario_id']
                            candidatos = candidatos[~candidatos['id'].isin(ids_serviram_ceia)]
                        
                        # REGRA 4: Não foi escalado para outra função NESTE MESMO CULTO
                        candidatos = candidatos[~candidatos['id'].isin(ja_escalados_neste_culto)]

                        # 5. SELECIONAR VOLUNTÁRIO
                        if not candidatos.empty:
                            # Seleciona um voluntário aleatoriamente da lista de candidatos
                            voluntario_escolhido = candidatos.sample(n=1).iloc[0]
                            nome_escolhido = voluntario_escolhido['nome']
                            id_escolhido = voluntario_escolhido['id']

                            # Adiciona à escala e marca como já escalado
                            escala_gerada.append({'Data': culto_str, 'Função': atribuicao, 'Voluntário Escalado': nome_escolhido})
                            ja_escalados_neste_culto.append(id_escolhido)
                        else:
                            # Se não houver ninguém, marca a vaga como não preenchida
                            escala_gerada.append({'Data': culto_str, 'Função': atribuicao, 'Voluntário Escalado': '**VAGA NÃO PREENCHIDA**'})
        
        # 6. EXIBIR A ESCALA
        st.success("✅ Escala gerada com sucesso!")
        
        if escala_gerada:
            escala_df = pd.DataFrame(escala_gerada)
            
            # Formata a exibição para agrupar por data
            escala_final_formatada = escala_df.pivot_table(index='Data', columns='Função', values='Voluntário Escalado', aggfunc='first').fillna('')
            
            st.subheader("🗓️ Escala Proposta")
            st.dataframe(escala_final_formatada, use_container_width=True)

            # Mostra um aviso para vagas não preenchidas
            vagas_abertas = escala_df[escala_df['Voluntário Escalado'] == '**VAGA NÃO PREENCHIDA**']
            if not vagas_abertas.empty:
                st.warning("Atenção: As seguintes vagas não puderam ser preenchidas automaticamente:")
                st.dataframe(vagas_abertas.drop(columns=['Voluntário Escalado']), use_container_width=True)
        else:
            st.error("Não foi possível gerar a escala. Verifique se há cultos configurados para o próximo mês.")


if st.sidebar.button("Logout"):
    for key in st.session_state.keys():
        del st.session_state[key]
    st.switch_page("app.py")