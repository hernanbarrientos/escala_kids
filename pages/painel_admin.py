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
            
            # Usamos o mesmo DataFrame para evitar uma segunda chamada ao banco
            id_selecionado = st.selectbox(
                "Selecione o usuário:",
                options=df_usuarios['id'],
                format_func=lambda id: f"{df_usuarios.loc[df_usuarios['id'] == id, 'nome'].iloc[0]}",
                key="selectbox_usuario_gerenciar"
            )
            
            usuario_selecionado_row = db.get_voluntario_by_id(conn, id_selecionado)
            
            if usuario_selecionado_row:
                usuario_selecionado = dict(usuario_selecionado_row)

                # --- Formulário de Edição ---
                with st.form("form_editar_usuario"):
                    st.write(f"**Editando:** {usuario_selecionado['nome']}")
                    
                    nome = st.text_input("Nome", value=usuario_selecionado["nome"])
                    usuario_login = st.text_input("Usuário (Login)", value=usuario_selecionado["usuario"])
                    nova_senha = st.text_input("Nova Senha", type="password", placeholder="Deixe em branco para não alterar")
                    st.text_input("Tipo de Acesso (Papel)", value=usuario_selecionado["role"].capitalize(), disabled=True)

                    atribuicoes_selecionadas = []
                    disponibilidade_selecionada = []

                    if usuario_selecionado["role"] == "voluntario":
                        st.write("**Atribuições:**")
                        default_atribuicoes = [a.strip() for a in (usuario_selecionado.get("atribuicoes") or "").split(",") if a.strip()]
                        cols_atr = st.columns(3)
                        for i, atr in enumerate(utils.ATRIBUICOES_LISTA):
                            with cols_atr[i % 3]:
                                if st.checkbox(atr, value=(atr in default_atribuicoes), key=f"edit_atr_{atr}_{id_selecionado}"):
                                    atribuicoes_selecionadas.append(atr)
                        
                        st.write("**Disponibilidade:**")
                        default_disponibilidade = [d.strip() for d in (usuario_selecionado.get("disponibilidade") or "").split(",") if d.strip()]
                        cols_disp = st.columns(3)
                        for i, disp in enumerate(utils.DISPONIBILIDADE_OPCOES):
                            with cols_disp[i % 3]:
                                if st.checkbox(disp, value=(disp in default_disponibilidade), key=f"edit_disp_{disp}_{id_selecionado}"):
                                    disponibilidade_selecionada.append(disp)

                    if st.form_submit_button("Salvar Alterações", type="primary"):
                        senha_final = nova_senha if nova_senha else usuario_selecionado['senha']
                        atribuicoes_str = ", ".join(atribuicoes_selecionadas)
                        disponibilidade_str = ", ".join(disponibilidade_selecionada)
                        db.editar_voluntario(conn, id_selecionado, nome, usuario_login, senha_final, atribuicoes_str, disponibilidade_str, role=usuario_selecionado['role'])
                        st.success(f"Dados do usuário '{nome}' atualizados com sucesso!")
                        st.rerun()

                st.markdown("---")

                # --- Seção de Exclusão ---
                if usuario_selecionado['role'] != 'admin':
                    st.write(f"**Excluir:** {usuario_selecionado['nome']}")
                    st.warning(f"Atenção: Esta ação é permanente.")
                    if st.button(f"Confirmar Exclusão do Usuário", type="secondary"):
                        db.excluir_voluntario(conn, id_selecionado)
                        st.success(f"Usuário '{usuario_selecionado['nome']}' excluído.")
                        st.rerun()
                else:
                    st.info("Não é possível excluir um usuário com o papel de Administrador.")

    except Exception as e:
        st.error(f"Ocorreu um erro inesperado na aba Gerenciar Usuários: {e}")


# --- Aba de Adicionar Novo Usuário ---
with tab_adicionar:
    st.subheader("➕ Adicionar Novo Usuário")
    
    with st.form("form_adicionar_usuario", clear_on_submit=True):
        nome = st.text_input("Nome Completo")
        usuario = st.text_input("Nome de Usuário (Login)")
        senha = st.text_input("Senha Provisória", type="password")
        role_selecionado = st.selectbox("Tipo de Usuário", options=["voluntario", "admin"])

        st.markdown("---")
        atribuicoes_selecionadas = []
        disponibilidade_selecionada = []

        if role_selecionado == "voluntario":
            st.write("**Atribuições do Voluntário:**")
            cols_atr_add = st.columns(3)
            for i, atr in enumerate(utils.ATRIBUICOES_LISTA):
                with cols_atr_add[i % 3]:
                    if st.checkbox(atr, key=f"add_atr_{i}"):
                        atribuicoes_selecionadas.append(atr)
            
            st.write("**Disponibilidade Geral:**")
            cols_disp_add = st.columns(3)
            for i, disp in enumerate(utils.DISPONIBILIDADE_OPCOES):
                with cols_disp_add[i % 3]:
                    if st.checkbox(disp, key=f"add_disp_{i}"):
                        disponibilidade_selecionada.append(disp)
        
        if st.form_submit_button("Cadastrar Usuário", type="primary"):
            if nome and usuario and senha:
                try:
                    db.adicionar_voluntario(conn, nome, usuario, senha, ", ".join(atribuicoes_selecionadas), ", ".join(disponibilidade_selecionada), role=role_selecionado)
                    st.success(f"Usuário '{nome}' ({role_selecionado.capitalize()}) cadastrado com sucesso!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error(f"O nome de usuário '{usuario}' já existe. Por favor, escolha outro.")
                except Exception as e:
                    st.error(f"Ocorreu um erro: {e}")
            else:
                st.error("Nome, Usuário (Login) e Senha Provisória são campos obrigatórios.")


# --- Aba: Configurações de Escala (Mantida da sua versão) ---
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
        index=0 if edicao_liberada_atual else 1
    )

    if st.button("Salvar Configuração", type="primary"):
        status_to_save = (nova_situacao == "Liberar Edição")
        if db.set_edicao_liberada(conn, mes_ref_proximo_mes, status_to_save):
            st.success(f"Status de edição para {mes_ref_proximo_mes} atualizado para **{nova_situacao.upper().split(' ')[0]}**.")
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
            index=meses_disponiveis.index(mes_ref_proximo_mes) if mes_ref_proximo_mes in meses_disponiveis else 0
        )
        if mes_selecionado:
            indisponibilidades_rows = db.get_all_voluntarios_indisponibilidade_for_month(conn, mes_selecionado)
            if indisponibilidades_rows:
                st.write(f"**Indisponibilidades para {mes_selecionado}:**")
                df_indisponibilidades = pd.DataFrame([dict(row) for row in indisponibilidades_rows])
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