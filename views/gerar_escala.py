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
    Função principal que renderiza toda a página do Gerador e Editor de Escalas.
    """
    if not st.session_state.get('logged_in') or st.session_state.user_role != 'admin':
        st.error("Acesso restrito a administradores.")
        if st.button("Ir para Login"):
            st.session_state.page = 'login'
            st.rerun()
        st.stop()

    conn = st.session_state.db_conn
    st.title("🤖 Gerador e Editor de Escalas")
    st.markdown("---")

    hoje = datetime.now()
    proximo_mes_data = hoje + relativedelta(months=1)
    try:
        utils.configurar_localidade()
    except Exception as e:
        print(f"Não foi possível configurar localidade: {e}")
        
    mes_referencia = f"{proximo_mes_data.strftime('%B').capitalize()} de {proximo_mes_data.year}"
    st.info(f"A escala a ser gerada e editada é para o mês de: **{mes_referencia}**")

    if st.button("Gerar Nova Escala (Substitui a escala salva)", type="primary"):
        with st.spinner("Processando regras com balanceamento de carga e montando a escala..."):
            voluntarios_df = db.listar_voluntarios(conn)
            
            # --- LÓGICA DE BALANCEAMENTO DE CARGA (INÍCIO) ---
            # 1. Busca a contagem de serviços de meses passados.
            contagem_df = db.get_contagem_servicos_passados(conn, mes_referencia)
            
            # 2. Junta a contagem com a lista de voluntários.
            voluntarios_df = pd.merge(voluntarios_df, contagem_df, left_on='id', right_on='voluntario_id', how='left')
            voluntarios_df.drop(columns=['voluntario_id'], inplace=True) # Remove coluna duplicada
            voluntarios_df['contagem'].fillna(0, inplace=True) # Preenche com 0 para quem nunca serviu
            voluntarios_df['contagem'] = voluntarios_df['contagem'].astype(int) # Garante que a contagem é um número inteiro
            # --- FIM DA LÓGICA DE BALANCEAMENTO ---

            disponibilidades_df = db.listar_disponibilidades_por_mes(conn, mes_referencia)
            escala_gerada = []
            
            ano, mes = proximo_mes_data.year, proximo_mes_data.month
            num_dias_mes = calendar.monthrange(ano, mes)[1]

            for dia in range(1, num_dias_mes + 1):
                data_atual = datetime(ano, mes, dia)
                dia_semana = data_atual.weekday()

                tipos_culto_dia = []
                if dia_semana == 3: tipos_culto_dia.append(f"{data_atual.strftime('%d/%m')} - Quinta-feira")
                elif dia_semana == 6:
                    tipos_culto_dia.append(f"{data_atual.strftime('%d/%m')} - Domingo Manhã")
                    tipos_culto_dia.append(f"{data_atual.strftime('%d/%m')} - Domingo Noite")

                for culto_str in tipos_culto_dia:
                    tipo_culto_key = culto_str.split(' - ')[1]
                    if tipo_culto_key not in NECESSIDADES_ESCALA: continue
                    
                    necessidades = NECESSIDADES_ESCALA[tipo_culto_key]
                    ja_escalados_neste_culto = []

                    for atribuicao, quantidade in necessidades.items():
                        for i in range(quantidade):
                            candidatos = voluntarios_df[voluntarios_df['atribuicoes'].str.contains(atribuicao, na=False, regex=False)]
                            ids_disponiveis = disponibilidades_df[disponibilidades_df['datas_disponiveis'].str.contains(culto_str, na=False, regex=False)]['voluntario_id']
                            candidatos = candidatos[candidatos['id'].isin(ids_disponiveis)]
                            
                            if tipo_culto_key.startswith("Domingo") and dia <= 7:
                                ids_serviram_ceia = disponibilidades_df[disponibilidades_df['ceia_passada'] == 'Sim']['voluntario_id']
                                candidatos = candidatos[~candidatos['id'].isin(ids_serviram_ceia)]
                            
                            candidatos = candidatos[~candidatos['id'].isin(ja_escalados_neste_culto)]

                            if not candidatos.empty:
                                # --- LÓGICA DE BALANCEAMENTO (SELEÇÃO) ---
                                # 3. Ordena os candidatos por quem serviu menos vezes e pega o primeiro.
                                # Em caso de empate, a ordem original (ou aleatória do merge) decide.
                                voluntario_escolhido = candidatos.sort_values(by='contagem', ascending=True).iloc[0]
                                
                                nome_escolhido = voluntario_escolhido['nome']
                                id_escolhido = voluntario_escolhido['id']
                                escala_gerada.append({'Data': culto_str, 'Função': atribuicao, 'Voluntário Escalado': nome_escolhido})
                                ja_escalados_neste_culto.append(id_escolhido)
                                
                                # 4. Atualiza a contagem em memória para que ele não seja o primeiro a ser escolhido de novo neste mês.
                                voluntarios_df.loc[voluntarios_df['id'] == id_escolhido, 'contagem'] += 1
                                # --- FIM DA LÓGICA DE SELEÇÃO ---
                            else:
                                escala_gerada.append({'Data': culto_str, 'Função': atribuicao, 'Voluntário Escalado': '**VAGA NÃO PREENCHIDA**'})
            

            if escala_gerada:
                escala_df = pd.DataFrame(escala_gerada)
                
                # Regra Recepção/Apoio
                entradas_apoio = []
                for _, entrada in escala_df.iterrows():
                    if entrada['Função'] == 'Recepção':
                        entradas_apoio.append({'Data': entrada['Data'], 'Função': 'Apoio', 'Voluntário Escalado': entrada['Voluntário Escalado']})
                if entradas_apoio:
                    escala_df = pd.concat([escala_df, pd.DataFrame(entradas_apoio)], ignore_index=True)

                mapa_nome_id = pd.Series(voluntarios_df.id.values, index=voluntarios_df.nome).to_dict()
                escala_df['voluntario_id'] = escala_df['Voluntário Escalado'].map(mapa_nome_id)
                escala_df['mes_referencia'] = mes_referencia
                df_para_salvar = escala_df.rename(columns={'Data': 'data_culto', 'Função': 'funcao', 'Voluntário Escalado': 'voluntario_nome'})
                
                colunas_para_salvar = ['mes_referencia', 'data_culto', 'funcao', 'voluntario_id', 'voluntario_nome']
                df_final = df_para_salvar[colunas_para_salvar]

                if db.salvar_escala_gerada(conn, mes_referencia, df_final):
                    st.success("✅ Nova escala gerada e salva com sucesso!")
                else:
                    st.error("A escala foi gerada, mas houve um erro ao salvá-la.")
    
    st.markdown("---")
    st.header("🗓️ Editor da Escala Atual")

    # Carrega a escala mais recente do banco de dados para edição
    escala_salva_df = db.listar_escala_completa_por_mes(conn, mes_referencia)

    if escala_salva_df.empty:
        st.warning("Nenhuma escala foi gerada para este mês ainda. Clique em 'Gerar Nova Escala' acima.")
    else:
        # Prepara a tabela para o formato de exibição (pivot)
        escala_pivot = escala_salva_df.pivot_table(
            index='data_culto',
            columns='funcao',
            values='voluntario_nome',
            aggfunc='first'
        ).fillna("**VAGA NÃO PREENCHIDA**") # Preenche células vazias

        st.markdown("---")
        st.header("📄 Exportar Escala")
        
        # Gera o PDF em memória usando a função do utils
        pdf_bytes = utils.gerar_pdf_escala(escala_pivot, mes_referencia)

        st.download_button(
            label="📥 Baixar Escala em PDF",
            data=pdf_bytes,
            file_name=f"escala_kids_{mes_referencia.replace(' de ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

        # --- LÓGICA PARA OPÇÕES DE EDIÇÃO INTELIGENTES ---
        voluntarios_df = db.listar_voluntarios(conn)
        opcoes_por_funcao = {}
        
        # Cria uma lista de todas as funções possíveis a partir da configuração
        todas_as_funcoes = set()
        for dia in NECESSIDADES_ESCALA.values():
            for funcao in dia.keys():
                todas_as_funcoes.add(funcao)
        
        for funcao in todas_as_funcoes:
            voluntarios_aptos = voluntarios_df[voluntarios_df['atribuicoes'].str.contains(funcao, na=False)]['nome'].tolist()
            opcoes_por_funcao[funcao] = ["**VAGA NÃO PREENCHIDA**"] + sorted(voluntarios_aptos)

        if 'Recepção' in opcoes_por_funcao:
            opcoes_por_funcao['Apoio'] = opcoes_por_funcao['Recepção']

        configuracao_colunas = {}
        for coluna in escala_pivot.columns:
            if coluna in opcoes_por_funcao:
                configuracao_colunas[coluna] = st.column_config.SelectboxColumn(
                    f"Substituir para {coluna}",
                    options=opcoes_por_funcao[coluna],
                    required=True
                )

        st.info("Clique duas vezes em um nome na tabela para abrir as opções e fazer uma troca.")
        
        escala_editada_df = st.data_editor(
            escala_pivot,
            column_config=configuracao_colunas,
            use_container_width=True,
            key="editor_escala"
        )

        if st.button("💾 Salvar Alterações Manuais", type="primary"):
            # Converte a tabela editada de volta ao formato longo para salvar
            escala_long_format = escala_editada_df.reset_index().melt(
                id_vars='data_culto',
                var_name='funcao',
                value_name='voluntario_nome'
            )
            
            mapa_nome_id = pd.Series(voluntarios_df.id.values, index=voluntarios_df.nome).to_dict()
            escala_long_format['voluntario_id'] = escala_long_format['voluntario_nome'].map(mapa_nome_id)
            escala_long_format['mes_referencia'] = mes_referencia

            df_final_para_salvar = escala_long_format[['mes_referencia', 'data_culto', 'funcao', 'voluntario_id', 'voluntario_nome']]

            if db.salvar_escala_gerada(conn, mes_referencia, df_final_para_salvar):
                st.success("Alterações manuais na escala foram salvas com sucesso!")
            else:
                st.error("Ocorreu um erro ao salvar as alterações manuais.")


