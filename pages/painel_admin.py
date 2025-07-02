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

# --- Função para Resetar Campos do Formulário de Adição ---
# Esta função será chamada apenas para forçar a limpeza dos text_inputs e selectbox
# após um cadastro bem-sucedido.
def reset_add_user_form_fields():
    if "add_nome_novo" in st.session_state:
        st.session_state["add_nome_novo"] = ""
    if "add_usuario_novo" in st.session_state:
        st.session_state["add_usuario_novo"] = ""
    if "add_senha_novo" in st.session_state:
        st.session_state["add_senha_novo"] = ""
    if "add_role_select_novo" in st.session_state:
        st.session_state["add_role_select_novo"] = "voluntario" # Volta para o padrão
    # Não precisamos limpar os checkboxes aqui; eles serão redesenhados vazios.


# --- Abas para Organização ---
tab_gerenciar, tab_adicionar, tab_config_escala = st.tabs(["Gerenciar Usuários", "Adicionar Novo Usuário", "Configurações de Escala"])

# --- Aba de Gerenciamento (Edição e Exclusão) ---
with tab_gerenciar:
    st.subheader("📋 Lista de Usuários Cadastrados")

    try:
        df_usuarios = db.listar_voluntarios(conn)
        
        if df_usuarios.empty:
            st.info("Nenhum usuário cadastrado ainda.")
        else:
            st.dataframe(df_usuarios, use_container_width=True)
            st.markdown("---")

            st.subheader("Ações para um Usuário Específico")

            all_usuarios_data = db.listar_voluntarios(conn)
            if not all_usuarios_data.empty:
                id_selecionado = st.selectbox(
                    "Selecione o usuário:",
                    options=all_usuarios_data['id'],
                    format_func=lambda id: f"{all_usuarios_data.loc[all_usuarios_data['id'] == id, 'nome'].iloc[0]} ({all_usuarios_data.loc[all_usuarios_data['id'] == id, 'role'].iloc[0].capitalize()})",
                    key="selectbox_usuario"
                )
                
                usuario_selecionado_row = db.get_voluntario_by_id(conn, id_selecionado)
                
                if usuario_selecionado_row:
                    usuario_selecionado = dict(usuario_selecionado_row)

                    with st.form("form_editar_usuario"):
                        st.write(f"**Editando:** {usuario_selecionado['nome']} ({usuario_selecionado['role'].capitalize()})")
                        
                        nome = st.text_input("Nome", value=usuario_selecionado["nome"], key="edit_nome")
                        usuario_login = st.text_input("Usuário (Login)", value=usuario_selecionado["usuario"], key="edit_usuario_login")
                        nova_senha = st.text_input("Nova Senha", type="password", placeholder="Deixe em branco para não alterar", key="edit_nova_senha")

                        role_options = ["voluntario", "admin"]
                        current_role_index = role_options.index(usuario_selecionado["role"])
                        novo_role = st.selectbox("Tipo de Acesso (Papel)", options=role_options, index=current_role_index, key="edit_role_select")

                        atribuicoes_selecionadas = []
                        disponibilidade_selecionada = []

                        if novo_role == "voluntario":
                            st.write("**Atribuições:**")
                            default_atribuicoes = [a.strip() for a in (usuario_selecionado.get("atribuicoes") or "").split(",") if a.strip()]
                            
                            # --- Layout em 3 COLUNAS para Atribuições (Edição) ---
                            cols_atr = st.columns(3)
                            for i, atr in enumerate(utils.ATRIBUICOES_LISTA):
                                with cols_atr[i % 3]: # Distribui em colunas (0, 1, 2, 0, 1, 2...)
                                    if st.checkbox(atr, value=(atr in default_atribuicoes), key=f"edit_atr_{atr}_{id_selecionado}"):
                                        atribuicoes_selecionadas.append(atr)
                            
                            st.write("**Disponibilidade:**")
                            default_disponibilidade = [d.strip() for d in (usuario_selecionado.get("disponibilidade") or "").split(",") if d.strip()]
                            
                            # --- Layout em 3 COLUNAS para Disponibilidade (Edição) ---
                            cols_disp = st.columns(3)
                            for i, disp in enumerate(utils.DISPONIBILIDADE_OPCOES):
                                with cols_disp[i % 3]: # Distribui em colunas (0, 1, 2, 0, 1, 2...)
                                    if st.checkbox(disp, value=(disp in default_disponibilidade), key=f"edit_disp_{disp}_{id_selecionado}"):
                                        disponibilidade_selecionada.append(disp)
                        else:
                            atribuicoes_selecionadas = [] 
                            disponibilidade_selecionada = []

                        if st.form_submit_button("Salvar Alterações", type="primary"):
                            senha_final = nova_senha if nova_senha else usuario_selecionado['senha']
                            atribuicoes_str = ", ".join(atribuicoes_selecionadas)
                            disponibilidade_str = ", ".join(disponibilidade_selecionada)

                            db.editar_voluntario(conn, id_selecionado, nome, usuario_login, senha_final, atribuicoes_str, disponibilidade_str, role=novo_role)
                            st.success(f"Dados do usuário '{nome}' atualizados com sucesso!")
                            st.rerun()
                else:
                    st.warning("Usuário selecionado não encontrado.")
            else:
                st.info("Nenhum usuário para selecionar para edição/exclusão.")

            st.markdown("---")
            
            if not all_usuarios_data.empty and usuario_selecionado_row:
                st.write(f"**Excluir:** {usuario_selecionado['nome']}")
                st.warning(f"Atenção: Esta ação é permanente e não pode ser desfeita.")

                if st.button(f"Confirmar Exclusão do Usuário", type="secondary", key="confirm_exclusao_btn"):
                    db.excluir_voluntario(conn, id_selecionado)
                    st.success(f"Usuário '{usuario_selecionado['nome']}' excluído. A lista será atualizada.")
                    st.rerun()

    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")


# --- Aba de Adicionar Novo Usuário (inclui admins) ---
with tab_adicionar:
    st.subheader("➕ Adicionar Novo Usuário")
    
    # Não inicialize os valores dos inputs aqui diretamente.
    # Apenas use as chaves, e o Streamlit as gerenciará.
    # A limpeza será feita via `reset_add_user_form_fields` no on_click.

    # Verifique e inicialize st.session_state apenas se a chave não existir
    # Isso garante que a primeira carga ou pós-rerun use um estado limpo/padrão
    if "add_nome_novo" not in st.session_state:
        st.session_state["add_nome_novo"] = ""
    if "add_usuario_novo" not in st.session_state:
        st.session_state["add_usuario_novo"] = ""
    if "add_senha_novo" not in st.session_state:
        st.session_state["add_senha_novo"] = ""
    if "add_role_select_novo" not in st.session_state:
        st.session_state["add_role_select_novo"] = "voluntario"
    
    # Widgets de entrada. Eles LERÃO E GRAVARÃO em st.session_state via 'key'.
    # Não usamos 'value' explicitamente, a menos que seja para um valor padrão que não será limpo.
    nome = st.text_input("Nome Completo", key="add_nome_novo")
    usuario = st.text_input("Nome de Usuário (Login)", key="add_usuario_novo")
    senha = st.text_input("Senha Provisória", type="password", key="add_senha_novo")
    
    # st.selectbox usará o valor da chave em st.session_state.
    # Se 'add_role_select_novo' é "voluntario", ele seleciona "voluntario".
    role_selecionado = st.selectbox("Tipo de Usuário", options=["voluntario", "admin"], key="add_role_select_novo")

    atribuicoes_selecionadas_add = []
    disponibilidade_selecionada_add = []

    # --- Lógica Condicional para Atribuições e Disponibilidade ---
    # Somente renderiza SE o papel for "voluntario"
    if role_selecionado == "voluntario":
        st.write("**Atribuições do Voluntário:**")
        # As colunas são criadas SOMENTE se este bloco for executado
        cols_atr_add = st.columns(3)
        for i, atr in enumerate(utils.ATRIBUICOES_LISTA):
            with cols_atr_add[i % 3]:
                # Os checkboxes não precisam de 'value' padrão, pois são novos e não editados
                if st.checkbox(atr, key=f"add_atr_novo_{i}"):
                    atribuicoes_selecionadas_add.append(atr)
        
        st.write("**Disponibilidade Geral:**")
        # As colunas são criadas SOMENTE se este bloco for executado
        cols_disp_add = st.columns(3)
        for i, disp in enumerate(utils.DISPONIBILIDADE_OPCOES):
            with cols_disp_add[i % 3]:
                if st.checkbox(disp, key=f"add_disp_novo_{i}"):
                    disponibilidade_selecionada_add.append(disp)

    # O formulário para o botão de submissão.
    # A chamada `on_click` garante que o reset dos campos ocorra ANTES do rerun.
    with st.form("cadastro_usuario_submit_form"):
        st.write("") # Pequeno espaço ou placeholder
        if st.form_submit_button("Cadastrar Usuário", type="primary", on_click=reset_add_user_form_fields):
            # Os valores dos campos já estão em st.session_state devido às suas keys.
            # Acessamos eles diretamente aqui.
            current_nome = st.session_state["add_nome_novo"]
            current_usuario = st.session_state["add_usuario_novo"]
            current_senha = st.session_state["add_senha_novo"]
            current_role = st.session_state["add_role_select_novo"]

            if current_nome and current_usuario and current_senha:
                try:
                    db.adicionar_voluntario(conn, current_nome, current_usuario, current_senha, 
                                            ", ".join(atribuicoes_selecionadas_add), 
                                            ", ".join(disponibilidade_selecionada_add), 
                                            role=current_role)
                    st.success(f"Usuário '{current_nome}' ({current_role.capitalize()}) cadastrado com sucesso!")
                    # reset_add_user_form_fields() já foi chamada pelo on_click.
                    # Agora, apenas forçamos a re-execução da página.
                    st.rerun() 
                except sqlite3.IntegrityError:
                    st.error(f"O nome de usuário '{current_usuario}' já existe. Por favor, escolha outro.")
                    # Não rerunnamos em caso de erro para o usuário ver a mensagem.
                except Exception as e:
                    st.error(f"Ocorreu um erro: {e}")
            else:
                st.error("Nome, Usuário (Login) e Senha Provisória são campos obrigatórios.")

# --- Aba: Configurações de Escala (Mantida) ---
with tab_config_escala:
    st.subheader("⚙️ Configurações de Edição de Escala")
    
    _, mes_ref_proximo_mes = utils.get_dias_culto_proximo_mes()

    edicao_liberada_atual = db.get_edicao_liberada(conn, mes_ref_proximo_mes)

    st.write(f"**Status de Edição para {mes_ref_proximo_mes}:**")
    status_display = "LIBERADA" if edicao_liberada_atual else "BLOQUEADA"
    st.info(f"Atualmente a edição de indisponibilidade está **{status_display}**.")

    nova_situacao = st.radio(
        "Deseja liberar ou bloquear as edições para este mês?",
        ["Liberar Edição", "Bloquear Edição"],
        index=0 if edicao_liberada_atual else 1,
        key="radio_liberar_bloquear"
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

    meses_configurados_rows = db.get_all_meses_configurados(conn)
    meses_disponiveis = [m['mes_referencia'] for m in meses_configurados_rows]

    if meses_disponiveis:
        mes_selecionado = st.selectbox(
            "Selecione o mês para visualizar as indisponibilidades:",
            options=meses_disponiveis,
            index=meses_disponiveis.index(mes_ref_proximo_mes) if mes_ref_proximo_mes in meses_disponiveis else 0,
            key="select_mes_indisponibilidade"
        )

        if mes_selecionado:
            voluntarios_indisponibilidade_rows = db.get_all_voluntarios_indisponibilidade_for_month(conn, mes_selecionado)

            if voluntarios_indisponibilidade_rows:
                st.write(f"**Indisponibilidades para {mes_selecionado}:**")
                df_indisponibilidades = pd.DataFrame([dict(row) for row in voluntarios_indisponibilidade_rows])
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

conn.close()