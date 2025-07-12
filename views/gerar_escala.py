# views/gerar_escala.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
import database as db
import utils
from escala_config import NECESSIDADES_ESCALA

# Lista de ordenação final e limpa
ORDEM_FUNCOES = [
    "Lider da escala", "Recepção", "Baby Historia", "Baby Auxiliar 1", 
    "Baby Auxiliar 2", "Apoio", "Inclusão", "Primario/Juvenil", "Auxiliar"
]

def show_page():
    if not st.session_state.get('logged_in') or st.session_state.user_role != 'admin':
        st.error("Acesso restrito a administradores.")
        st.rerun()
        st.stop()
    
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

    col_gerar, col_exportar, _ = st.columns([1, 1, 2])
    with col_gerar:
        if st.button("💥 Gerar Nova Escala", type="primary", use_container_width=True, help="Gera uma nova escala do zero, substituindo a escala salva para este mês."):
            with st.spinner("Processando regras..."):
                voluntarios_df = db.listar_voluntarios()
                ids_travados = db.get_ids_indisponiveis_para_o_mes(mes_referencia)
                if ids_travados:
                    voluntarios_df = voluntarios_df[~voluntarios_df['id'].isin(ids_travados)]
                contagem_df = db.get_contagem_servicos_passados(mes_referencia)
                voluntarios_df = pd.merge(voluntarios_df, contagem_df, left_on='id', right_on='voluntario_id', how='left')
                if 'voluntario_id' in voluntarios_df.columns:
                    voluntarios_df.drop(columns=['voluntario_id'], inplace=True, errors='ignore')
                voluntarios_df['contagem'].fillna(0, inplace=True)
                voluntarios_df['contagem'] = voluntarios_df['contagem'].astype(int)
                disponibilidades_df = db.listar_disponibilidades_por_mes(mes_referencia)
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
                                partes_atribuicao = atribuicao.split(' ')
                                base_atribuicao = atribuicao
                                if len(partes_atribuicao) > 1 and partes_atribuicao[-1].isdigit():
                                    base_atribuicao = ' '.join(partes_atribuicao[:-1])
                                candidatos = voluntarios_df[voluntarios_df['atribuicoes'].str.contains(base_atribuicao, na=False, regex=False)]
                                if not disponibilidades_df.empty:
                                    ids_disponiveis = disponibilidades_df[disponibilidades_df['datas_disponiveis'].str.contains(culto_str, na=False, regex=False)]['voluntario_id']
                                    candidatos = candidatos[candidatos['id'].isin(ids_disponiveis)]
                                if tipo_culto_key.startswith("Domingo") and dia <= 7 and not disponibilidades_df.empty:
                                    ids_serviram_ceia = disponibilidades_df[disponibilidades_df['ceia_passada'] == 'Sim']['voluntario_id']
                                    candidatos = candidatos[~candidatos['id'].isin(ids_serviram_ceia)]
                                candidatos = candidatos[~candidatos['id'].isin(ja_escalados_neste_culto)]
                                if not candidatos.empty:
                                    candidatos_com_desempate = candidatos.copy()
                                    candidatos_com_desempate['desempate_aleatorio'] = np.random.rand(len(candidatos_com_desempate))
                                    voluntario_escolhido = candidatos_com_desempate.sort_values(by=['contagem', 'desempate_aleatorio'], ascending=[True, True]).iloc[0]
                                    nome_escolhido = voluntario_escolhido['nome']
                                    id_escolhido = voluntario_escolhido['id']
                                    escala_gerada.append({'Data': culto_str, 'Função': atribuicao, 'Voluntário Escalado': nome_escolhido})
                                    ja_escalados_neste_culto.append(id_escolhido)
                                    voluntarios_df.loc[voluntarios_df['id'] == id_escolhido, 'contagem'] += 1
                                else:
                                    escala_gerada.append({'Data': culto_str, 'Função': atribuicao, 'Voluntário Escalado': '**VAGA NÃO PREENCHIDA**'})
                if escala_gerada:
                    escala_df = pd.DataFrame(escala_gerada)
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
                    if db.salvar_escala_gerada(mes_referencia, df_final):
                        st.success("✅ Nova escala gerada e salva com sucesso!")
                        st.rerun()

    escala_salva_df = db.listar_escala_completa_por_mes(mes_referencia)

    if not escala_salva_df.empty:
        escala_salva_df.sort_values('voluntario_nome', na_position='last', inplace=True)
        escala_salva_df.drop_duplicates(subset=['data_culto', 'funcao'], keep='first', inplace=True)
    
    escala_pivot = pd.DataFrame()
    if not escala_salva_df.empty:
        escala_pivot = escala_salva_df.pivot_table(index='data_culto', columns='funcao', values='voluntario_nome', aggfunc=lambda x: ' '.join(str(v) for v in x))

    if 'Baby Auxiliar' in escala_pivot.columns:
        escala_pivot = escala_pivot.drop(columns=['Baby Auxiliar'])
    
    # --- PONTO CENTRAL DA CORREÇÃO ---
    if not escala_pivot.empty:
        # 1. Garante que a coluna 'Apoio' seja sempre um espelho da 'Recepção'
        # Isso força a regra de negócio diretamente na tabela que será exibida
        if 'Recepção' in escala_pivot.columns and 'Apoio' in escala_pivot.columns:
            escala_pivot['Apoio'] = escala_pivot['Recepção']

        # 2. Lógica inteligente de preenchimento que roda DEPOIS da regra de negócio
        for data_culto, row in escala_pivot.iterrows():
            tipo_culto = data_culto.split(' - ')[1]
            
            # Precisamos considerar 'Apoio' como uma função necessária se 'Recepção' for
            funcoes_necessarias_base = list(NECESSIDADES_ESCALA.get(tipo_culto, {}).keys())
            if 'Recepção' in funcoes_necessarias_base:
                funcoes_necessarias_base.append('Apoio')

            for funcao, valor in row.items():
                if pd.isna(valor):
                    if funcao in funcoes_necessarias_base:
                        escala_pivot.loc[data_culto, funcao] = "**VAGA NÃO PREENCHIDA**"
                    else:
                        escala_pivot.loc[data_culto, funcao] = "--NÃO APLICA--"
    # --- FIM DA CORREÇÃO ---

    with col_exportar:
        if not escala_salva_df.empty:
            df_para_pdf = escala_salva_df.copy()
            # Garante que a regra Apoio=Recepção também seja aplicada nos dados do PDF
            if 'Recepção' in df_para_pdf['funcao'].values:
                recepcao_df = df_para_pdf[df_para_pdf['funcao'] == 'Recepção'].copy()
                recepcao_df['funcao'] = 'Apoio'
                df_para_pdf = pd.concat([df_para_pdf[df_para_pdf['funcao'] != 'Apoio'], recepcao_df]).drop_duplicates(subset=['data_culto', 'funcao'], keep='last')

            df_para_pdf['voluntario_nome'].fillna("-", inplace=True)
            df_para_pdf[['data_str', 'tipo_culto']] = df_para_pdf['data_culto'].str.split(' - ', expand=True)
            dados_agrupados = {}
            ordem_colunas_pdf = ["Domingo Manhã", "Domingo Noite", "Quinta-feira"]
            
            for tipo_culto in ordem_colunas_pdf:
                df_culto = df_para_pdf[df_para_pdf['tipo_culto'] == tipo_culto]
                if not df_culto.empty:
                    dados_agrupados[tipo_culto] = {}
                    for data, grupo in df_culto.groupby('data_str'):
                        grupo_ordenado = grupo.copy()
                        grupo_ordenado['funcao'] = pd.Categorical(grupo_ordenado['funcao'], categories=ORDEM_FUNCOES, ordered=True)
                        grupo_ordenado.sort_values('funcao', inplace=True)
                        dados_agrupados[tipo_culto][data] = list(zip(grupo_ordenado['funcao'], grupo_ordenado['voluntario_nome']))

            pdf_bytes = utils.gerar_pdf_escala(dados_agrupados, mes_referencia)
            st.download_button(
                label="📄 Baixar Escala em PDF",
                data=pdf_bytes,
                file_name=f"escala_kids_{mes_referencia.replace(' de ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    st.markdown("---")
    st.header("🗓️ Editor da Escala Atual")

    if escala_pivot.empty:
        st.warning("Nenhuma escala foi gerada para este mês ainda.")
    else:
        voluntarios_df_editor = db.listar_voluntarios()
        ids_travados_editor = db.get_ids_indisponiveis_para_o_mes(mes_referencia)
        if ids_travados_editor:
            voluntarios_df_editor = voluntarios_df_editor[~voluntarios_df_editor['id'].isin(ids_travados_editor)]
        
        opcoes_por_funcao = {}
        todas_as_funcoes = set(escala_pivot.columns)
        
        for funcao in todas_as_funcoes:
            if funcao == "--NÃO APLICA--": continue
            base_funcao = funcao.replace(" 1", "").replace(" 2", "")
            voluntarios_aptos = voluntarios_df_editor[voluntarios_df_editor['atribuicoes'].str.contains(base_funcao, na=False)]['nome'].tolist()
            opcoes_por_funcao[funcao] = ["**VAGA NÃO PREENCHIDA**"] + sorted(voluntarios_aptos)
        
        # Garante que as opções do Apoio sejam as mesmas da Recepção
        if 'Recepção' in opcoes_por_funcao:
            opcoes_por_funcao['Apoio'] = opcoes_por_funcao['Recepção']

        configuracao_colunas = {}
        for coluna in escala_pivot.columns:
            if coluna in opcoes_por_funcao:
                configuracao_colunas[coluna] = st.column_config.SelectboxColumn(f"Substituir para {coluna}", options=opcoes_por_funcao[coluna], required=True)
        
        st.info("Clique duas vezes em um nome na tabela para abrir as opções e fazer uma troca.")
        escala_editada_df = st.data_editor(escala_pivot, column_config=configuracao_colunas, use_container_width=True, key="editor_escala")

        if st.button("💾 Salvar Alterações Manuais", type="primary"):
            escala_long_format = escala_editada_df.reset_index().melt(id_vars='data_culto', var_name='funcao', value_name='voluntario_nome')
            
            escala_long_format.replace("--NÃO APLICA--", pd.NA, inplace=True)
            
            # Força a regra de negócio Apoio=Recepção ANTES de salvar
            for index, row in escala_long_format.iterrows():
                if row['funcao'] == 'Recepção':
                    apoio_index = escala_long_format[(escala_long_format['data_culto'] == row['data_culto']) & (escala_long_format['funcao'] == 'Apoio')].index
                    if not apoio_index.empty:
                        escala_long_format.loc[apoio_index, 'voluntario_nome'] = row['voluntario_nome']

            escala_long_format.replace("**VAGA NÃO PREENCHIDA**", pd.NA, inplace=True)
            
            mapa_nome_id = pd.Series(voluntarios_df_editor.id.values, index=voluntarios_df_editor.nome).to_dict()
            escala_long_format['voluntario_id'] = escala_long_format['voluntario_nome'].map(mapa_nome_id)
            escala_long_format['mes_referencia'] = mes_referencia
            df_final_para_salvar = escala_long_format[['mes_referencia', 'data_culto', 'funcao', 'voluntario_id', 'voluntario_nome']]
            
            if db.salvar_escala_gerada(mes_referencia, df_final_para_salvar):
                st.success("Alterações manuais na escala foram salvas com sucesso!")
                st.rerun()