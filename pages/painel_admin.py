# pages/painel_admin.py
import streamlit as st
import pandas as pd
import sqlite3
import database as db
import utils

# --- Configuração da Página e Verificação de Login ---
st.set_page_config(page_title="Painel Admin", layout="wide")

if not st.session_state.get('logged_in') or st.session_state.user_role != 'admin':
    st.error("Acesso restrito a administradores.")
    st.page_link("app.py", label="Ir para Login")
    st.stop()

# --- Conexão com o Banco ---
conn = db.conectar_db()
st.title("Painel de Administração")

# --- Abas para Organização ---
# Adicionamos uma nova aba para as configurações de escala
tab_gerenciar, tab_adicionar, tab_config_escala = st.tabs(["Gerenciar Voluntários", "Adicionar Novo Voluntário", "Configurações de Escala"])

# --- Aba de Gerenciamento (Edição e Exclusão) ---
with tab_gerenciar:
    st.subheader("📋 Lista de Voluntários Cadastrados")

    try:
        # Carrega a lista de voluntários para exibição
        df_voluntarios = db.listar_voluntarios(conn)
        
        if df_voluntarios.empty:
            st.info("Nenhum voluntário cadastrado ainda.")
        else:
            # Exibe a lista
            st.dataframe(df_voluntarios, use_container_width=True)
            st.markdown("---")

            # --- Seção de Ações: Selecionar para Editar/Excluir ---
            st.subheader("Ações para um Voluntário Específico")

            # Busca todos os dados (incluindo senha) para popular o formulário de edição
            # Usamos db.get_voluntario_by_id em vez de carregar tudo com pd.read_sql_query
            # para ser mais eficiente e lidar com o Row object
            
            # Primeiro, obtenha todos os IDs e nomes para o selectbox
            all_voluntarios_data = db.listar_voluntarios(conn)
            if not all_voluntarios_data.empty:
                id_selecionado = st.selectbox(
                    "Selecione o voluntário:",
                    options=all_voluntarios_data['id'],
                    # Mostra o nome e o ID para facilitar a seleção
                    format_func=lambda id: f"{all_voluntarios_data.loc[all_voluntarios_data['id'] == id, 'nome'].iloc[0]}",
                    key="selectbox_voluntario"
                )

                # Pega todos os dados do voluntário que foi selecionado usando a nova função
                voluntario_selecionado_row = db.get_voluntario_by_id(conn, id_selecionado)
                
                if voluntario_selecionado_row:
                    # Converte o Row object para um dicionário para facilitar o acesso
                    voluntario_selecionado = dict(voluntario_selecionado_row)

                    # --- Formulário de Edição ---
                    with st.form("form_editar_voluntario"):
                        st.write(f"**Editando:** {voluntario_selecionado['nome']}")
                        
                        nome = st.text_input("Nome", value=voluntario_selecionado["nome"])
                        usuario = st.text_input("Usuário", value=voluntario_selecionado["usuario"])
                        nova_senha = st.text_input("Nova Senha", type="password", placeholder="Deixe em branco para não alterar")

                        atribuicoes_default = [a.strip() for a in (voluntario_selecionado.get("atribuicoes") or "").split(",") if a.strip()]
                        atribuicoes = st.multiselect("Atribuições", options=utils.ATRIBUICOES_LISTA, default=atribuicoes_default)
                        
                        disponibilidade_default = [d.strip() for d in (voluntario_selecionado.get("disponibilidade") or "").split(",") if d.strip()]
                        disponibilidade = st.multiselect("Disponibilidade", options=utils.DISPONIBILIDADE_OPCOES, default=disponibilidade_default)

                        if st.form_submit_button("Salvar Alterações", type="primary"):
                            senha_final = nova_senha if nova_senha else voluntario_selecionado['senha']
                            atribuicoes_str = ", ".join(atribuicoes)
                            disponibilidade_str = ", ".join(disponibilidade)

                            db.editar_voluntario(conn, id_selecionado, nome, usuario, senha_final, atribuicoes_str, disponibilidade_str)
                            st.success(f"Dados do voluntário '{nome}' atualizados com sucesso!")
                            st.rerun()
                else:
                    st.warning("Voluntário selecionado não encontrado.")
            else:
                st.info("Nenhum voluntário para selecionar para edição/exclusão.")

            st.markdown("---")
            
            # --- Seção de Exclusão ---
            if not all_voluntarios_data.empty and voluntario_selecionado_row: # Garante que há um voluntário selecionado
                st.write(f"**Excluir:** {voluntario_selecionado['nome']}")
                st.warning(f"Atenção: Esta ação é permanente e não pode ser desfeita.")

                if st.button(f"Confirmar Exclusão do Voluntário", type="secondary"):
                    db.excluir_voluntario(conn, id_selecionado)
                    st.success(f"Voluntário '{voluntario_selecionado['nome']}' excluído. A lista será atualizada.")
                    st.rerun()

    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")


# --- Aba de Adicionar Voluntário (sem alterações) ---
with tab_adicionar:
    st.subheader("➕ Adicionar Novo Voluntário")
    with st.form("cadastro_voluntario", clear_on_submit=True):
        nome = st.text_input("Nome Completo")
        usuario = st.text_input("Nome de Usuário")
        senha = st.text_input("Senha Provisória", type="password")
        atribuicoes = st.multiselect("Atribuições do Voluntário", options=utils.ATRIBUICOES_LISTA)
        disponibilidade = st.multiselect("Disponibilidade Geral", options=utils.DISPONIBILIDADE_OPCOES)

        if st.form_submit_button("Cadastrar Voluntário", type="primary"):
            if nome and usuario and senha:
                try:
                    db.adicionar_voluntario(conn, nome, usuario, senha, ", ".join(atribuicoes), ", ".join(disponibilidade))
                    st.success(f"Voluntário '{nome}' com usuário '{usuario}' cadastrado com sucesso!")
                except sqlite3.IntegrityError:
                    st.error(f"O nome de usuário '{usuario}' já existe. Por favor, escolha outro.")
                except Exception as e:
                    st.error(f"Ocorreu um erro: {e}")
            else:
                st.error("Nome, Usuário e Senha Provisória são campos obrigatórios.")

# --- NOVA ABA: Configurações de Escala ---
with tab_config_escala:
    st.subheader("⚙️ Configurações de Edição de Escala")

    # Obtém o mês de referência atual (próximo mês)
    _, mes_ref_proximo_mes = utils.get_dias_culto_proximo_mes()

    # Carrega o status atual de edição para o próximo mês
    edicao_liberada_atual = db.get_edicao_liberada(conn, mes_ref_proximo_mes)

    st.write(f"**Status de Edição para {mes_ref_proximo_mes}:**")
    status_display = "LIBERADA" if edicao_liberada_atual else "BLOQUEADA"
    st.info(f"Atualmente a edição de indisponibilidade está **{status_display}**.")

    nova_situacao = st.radio(
        "Deseja liberar ou bloquear as edições para este mês?",
        ["Liberar Edição", "Bloquear Edição"],
        index=0 if edicao_liberada_atual else 1 # Define a opção inicial baseada no status atual
    )

    if st.button("Salvar Configuração", type="primary", key="btn_salvar_config_escala"):
        status_to_save = (nova_situacao == "Liberar Edição")
        if db.set_edicao_liberada(conn, mes_ref_proximo_mes, status_to_save):
            st.success(f"Status de edição para {mes_ref_proximo_mes} atualizado para **{nova_situacao.upper()}**.")
            st.rerun()
        else:
            st.error("Erro ao atualizar o status de edição.")

    st.markdown("---")
    st.subheader("📋 Resumo das Indisponibilidades Enviadas")

    st.info("Aqui você pode ver as indisponibilidades informadas pelos voluntários.")

    # Selecionar o mês para visualizar
    meses_configurados_rows = db.get_all_meses_configurados(conn)
    meses_disponiveis = [m['mes_referencia'] for m in meses_configurados_rows] # Acessa pelo nome da coluna

    if meses_disponiveis:
        mes_selecionado = st.selectbox(
            "Selecione o mês para visualizar as indisponibilidades:",
            options=meses_disponiveis,
            index=meses_disponiveis.index(mes_ref_proximo_mes) if mes_ref_proximo_mes in meses_disponiveis else 0,
            key="select_mes_indisponibilidade" # Chave única para o selectbox
        )

        if mes_selecionado:
            voluntarios_indisponibilidade_rows = db.get_all_voluntarios_indisponibilidade_for_month(conn, mes_selecionado)

            if voluntarios_indisponibilidade_rows:
                st.write(f"**Indisponibilidades para {mes_selecionado}:**")
                # Converte a lista de Row objects para um DataFrame para exibição mais bonita
                df_indisponibilidades = pd.DataFrame([dict(row) for row in voluntarios_indisponibilidade_rows])
                # Renomeia as colunas para melhor visualização
                df_indisponibilidades.columns = ['Voluntário', 'Datas de Restrição', 'Serviu Ceia Mês Passado']
                st.dataframe(df_indisponibilidades, use_container_width=True)
            else:
                st.info(f"Nenhum voluntário informou indisponibilidade para {mes_selecionado} ainda.")
    else:
        st.info("Nenhum mês de escala configurado ainda.")


# --- Botão de Logout na Barra Lateral ---
if st.sidebar.button("Logout"):
    for key in st.session_state.keys():
        del st.session_state[key]
    conn.close()
    st.switch_page("app.py")

conn.close() # Garante que a conexão seja fechada ao final