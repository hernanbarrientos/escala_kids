# views/gerar_escala.py
import streamlit as st
import pandas as pd
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
import database as db
import utils
from escala_config import NECESSIDADES_ESCALA

def show_page():
    """
    Função principal que renderiza toda a página do Gerador de Escalas.
    """
    # --- Verificação de Login e Permissão ---
    if not st.session_state.get('logged_in') or st.session_state.user_role != 'admin':
        st.error("Acesso restrito a administradores.")
        if st.button("Ir para Login"):
            st.session_state.page = 'login'
            st.rerun()
        st.stop()

    # --- Conteúdo da Página ---
    conn = db.conectar_db()
    st.title("🤖 Gerador Automático de Escalas")
    st.markdown("---")

    hoje = datetime.now()
    proximo_mes_data = hoje + relativedelta(months=1)
    try:
        utils.configurar_localidade()
    except Exception as e:
        print(f"Não foi possível configurar localidade: {e}")
        
    mes_referencia = f"{proximo_mes_data.strftime('%B').capitalize()} de {proximo_mes_data.year}"
    st.info(f"A escala a ser gerada é para o mês de: **{mes_referencia}**")

    if st.button("Gerar Nova Escala", type="primary"):
        with st.spinner("Processando regras e montando a escala... Isso pode levar um momento."):
            voluntarios_df = db.listar_voluntarios(conn)
            disponibilidades_df = db.listar_disponibilidades_por_mes(conn, mes_referencia)
            escala_gerada = []

            ano = proximo_mes_data.year
            mes = proximo_mes_data.month
            num_dias_mes = calendar.monthrange(ano, mes)[1]

            for dia in range(1, num_dias_mes + 1):
                data_atual = datetime(ano, mes, dia)
                dia_semana = data_atual.weekday()

                tipos_culto_dia = []
                if dia_semana == 3:
                    tipos_culto_dia.append(f"{data_atual.strftime('%d/%m')} - Quinta-feira")
                elif dia_semana == 6:
                    tipos_culto_dia.append(f"{data_atual.strftime('%d/%m')} - Domingo Manhã")
                    tipos_culto_dia.append(f"{data_atual.strftime('%d/%m')} - Domingo Noite")

                for culto_str in tipos_culto_dia:
                    tipo_culto_key = culto_str.split(' - ')[1]
                    if tipo_culto_key not in NECESSIDADES_ESCALA:
                        continue
                    
                    necessidades = NECESSIDADES_ESCALA[tipo_culto_key]
                    ja_escalados_neste_culto = []

                    for atribuicao, quantidade in necessidades.items():
                        for i in range(quantidade):
                            # Filtra candidatos com a atribuição correta
                            candidatos = voluntarios_df[voluntarios_df['atribuicoes'].str.contains(atribuicao, na=False, regex=False)]
                            
                            # Filtra APENAS quem ESTÁ disponível
                            ids_disponiveis = disponibilidades_df[disponibilidades_df['datas_disponiveis'].str.contains(culto_str, na=False, regex=False)]['voluntario_id']
                            candidatos = candidatos[candidatos['id'].isin(ids_disponiveis)]
                            
                            # Regra da Ceia
                            if tipo_culto_key.startswith("Domingo") and dia <= 7:
                                ids_serviram_ceia = disponibilidades_df[disponibilidades_df['ceia_passada'] == 'Sim']['voluntario_id']
                                candidatos = candidatos[~candidatos['id'].isin(ids_serviram_ceia)]
                            
                            # Não escalar a mesma pessoa duas vezes no mesmo culto
                            candidatos = candidatos[~candidatos['id'].isin(ja_escalados_neste_culto)]

                            if not candidatos.empty:
                                voluntario_escolhido = candidatos.sample(n=1).iloc[0]
                                nome_escolhido = voluntario_escolhido['nome']
                                id_escolhido = voluntario_escolhido['id']
                                escala_gerada.append({'Data': culto_str, 'Função': atribuicao, 'Voluntário Escalado': nome_escolhido})
                                ja_escalados_neste_culto.append(id_escolhido)
                            else:
                                escala_gerada.append({'Data': culto_str, 'Função': atribuicao, 'Voluntário Escalado': '**VAGA NÃO PREENCHIDA**'})
            
            st.success("✅ Escala gerada com sucesso!")
            
            # Regra Recepção/Apoio
            entradas_apoio = []
            for entrada in escala_gerada:
                if entrada['Função'] == 'Recepção':
                    nova_entrada_apoio = {'Data': entrada['Data'], 'Função': 'Apoio', 'Voluntário Escalado': entrada['Voluntário Escalado']}
                    entradas_apoio.append(nova_entrada_apoio)
            escala_gerada.extend(entradas_apoio)

            if escala_gerada:
                escala_df = pd.DataFrame(escala_gerada)
                
                # Garante que a coluna Apoio exista, mesmo que não haja Recepção
                if 'Apoio' not in escala_df['Função'].unique():
                    escala_df.loc[len(escala_df)] = {'Data': '', 'Função': 'Apoio', 'Voluntário Escalado': ''}

                ordem_colunas = ['Recepção', 'Apoio'] + [col for col in sorted(escala_df['Função'].unique()) if col not in ['Recepção', 'Apoio']]
                
                escala_final_formatada = escala_df.pivot_table(
                    index='Data', columns='Função', values='Voluntário Escalado', aggfunc='first'
                ).fillna('')
                
                # Remove a linha em branco se ela foi adicionada
                if '' in escala_final_formatada.index:
                    escala_final_formatada = escala_final_formatada.drop('')

                escala_final_formatada = escala_final_formatada.reindex(columns=ordem_colunas).fillna('')

                st.subheader("🗓️ Escala Proposta")
                st.dataframe(escala_final_formatada, use_container_width=True)

                vagas_abertas = escala_df[escala_df['Voluntário Escalado'] == '**VAGA NÃO PREENCHIDA**']
                if not vagas_abertas.empty:
                    st.warning("Atenção: As seguintes vagas não puderam ser preenchidas automaticamente:")
                    st.dataframe(vagas_abertas.drop(columns=['Voluntário Escalado']), use_container_width=True)
            else:
                st.error("Não foi possível gerar a escala. Verifique as configurações e disponibilidades.")
    
    conn.close()