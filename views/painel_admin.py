# views/painel_admin.py
import streamlit as st
import pandas as pd
import sqlite3
import database as db
import utils

def show_page():
    """
    Função principal que renderiza toda a página do Painel de Administração.
    """
    # --- Verificação de Login e Permissão de Administrador ---
    if not st.session_state.get('logged_in') or st.session_state.user_role != 'admin':
        st.error("Acesso restrito a administradores.")
        if st.button("Ir para Login"):
            st.session_state.page = 'login'
            st.rerun()
        st.stop()

    # --- Conexão com o Banco e Título da Página ---
    conn = db.conectar_db()
    st.title("🛠️ Painel de Administração")

    # --- Abas para Organização ---
    tab_gerenciar, tab_adicionar, tab_config_escala = st.tabs(["👥 Gerenciar Usuários", "➕ Adicionar Usuário", "⚙️ Configurar Escala"])

    # =================================================
    # ABA 1: Gerenciar Usuários (Edição e Exclusão)
    # =================================================
    with tab_gerenciar:
        st.subheader("Lista de Usuários Cadastrados")
        try:
            df_usuarios = db.listar_voluntarios(conn)
            if df_usuarios.empty:
                st.info("Nenhum usuário cadastrado ainda.")
            else:
                st.dataframe(df_usuarios, use_container_width=True)
                st.markdown("---")

                st.subheader("Ações para um Usuário Específico")
                
                id_selecionado = st.selectbox(
                    "Selecione o usuário:",
                    options=df_usuarios['id'],
                    format_func=lambda id: f"{df_usuarios.loc[df_usuarios['id'] == id, 'nome'].iloc[0]}",
                    key="selectbox_usuario_gerenciar"
                )
                
                usuario_selecionado_row = db.get_voluntario_by_id(conn, id_selecionado)
                
                if usuario_selecionado_row:
                    usuario = dict(usuario_selecionado_row)

                    with st.form("form_editar_usuario"):
                        st.write(f"**Editando:** {usuario['nome']}")
                        
                        nome = st.text_input("Nome", value=usuario["nome"])
                        usuario_login = st.text_input("Usuário (Login)", value=usuario["usuario"])
                        nova_senha = st.text_input("Nova Senha", type="password", placeholder="Deixe em branco para não alterar")
                        st.text_input("Tipo de Acesso (Papel)", value=usuario["role"].capitalize(), disabled=True)

                        atribuicoes_selecionadas = []
                        disponibilidade_selecionada = []

                        if usuario["role"] == "voluntario":
                            st.write("**Atribuições:**")
                            default_atribuicoes = [a.strip() for a in (usuario.get("atribuicoes") or "").split(",") if a.strip()]
                            cols_atr = st.columns(3)
                            for i, atr in enumerate(utils.ATRIBUICOES_LISTA):
                                with cols_atr[i % 3]:
                                    if st.checkbox(atr, value=(atr in default_atribuicoes), key=f"edit_atr_{id_selecionado}_{atr}"):
                                        atribuicoes_selecionadas.append(atr)
                            
                            st.write("**Disponibilidade Geral:**")
                            default_disponibilidade = [d.strip() for d in (usuario.get("disponibilidade") or "").split(",") if d.strip()]
                            cols_disp = st.columns(3)
                            for i, disp in enumerate(utils.DISPONIBILIDADE_OPCOES):
                                with cols_disp[i % 3]:
                                    if st.checkbox(disp, value=(disp in default_disponibilidade), key=f"edit_disp_{id_selecionado}_{disp}"):
                                        disponibilidade_selecionada.append(disp)

                        if st.form_submit_button("💾 Salvar Alterações"):
                            senha_para_salvar = nova_senha if nova_senha else None
                            atribuicoes_str = ",".join(atribuicoes_selecionadas)
                            disponibilidade_str = ",".join(disponibilidade_selecionada)
                            
                            db.editar_voluntario(conn, id_selecionado, nome, usuario_login, senha_para_salvar, atribuicoes_str, disponibilidade_str, role=usuario['role'])
                            # st.success(f"Dados do usuário '{nome}' atualizados com sucesso!")
                            st.toast(f"Dados do usuário '{nome}' atualizados com sucesso!", icon="✅")
                            # st.rerun()

                    st.markdown("---")

                    if usuario['role'] != 'admin':
                        st.write(f"**Excluir:** {usuario['nome']}")
                        if st.button(f"🗑️ Confirmar Exclusão do Usuário", type="secondary"):
                            db.excluir_voluntario(conn, id_selecionado)
                            st.warning(f"Usuário '{usuario['nome']}' excluído.")
                            st.rerun()
                    else:
                        st.info("O usuário Administrador não pode ser excluído.")
        except Exception as e:
            st.error(f"Ocorreu um erro inesperado na aba Gerenciar Usuários: {e}")

    # =================================================
    # ABA 2: Adicionar Novo Usuário
    # =================================================
    with tab_adicionar:
        st.subheader("➕ Adicionar Novo Usuário")
        with st.form("form_adicionar_usuario", clear_on_submit=True):
            nome = st.text_input("Nome que irá aparecer na escala")
            usuario = st.text_input("Nome de Usuário (Login)")
            senha = st.text_input("Senha Provisória", type="password")
            role = st.selectbox("Tipo de Usuário", ["voluntario", "admin"])
            st.markdown("---")

            atribuicoes_selecionadas = []
            disponibilidade_selecionada = []

            if role == "voluntario":
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
            
            if st.form_submit_button("➕ Cadastrar Usuário"):
                if nome and usuario and senha:
                    try:
                        db.adicionar_voluntario(conn, nome, usuario, senha, ",".join(atribuicoes_selecionadas), ",".join(disponibilidade_selecionada), role=role)
                        # st.success(f"Usuário '{nome}' ({role.capitalize()}) cadastrado com sucesso!")
                        st.toast(f"Usuário '{nome}' ({role.capitalize()}) cadastrado com sucesso!", icon="✅")
                        # st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(f"O nome de usuário '{usuario}' já existe. Por favor, escolha outro.")
                    except Exception as e:
                        st.error(f"Ocorreu um erro: {e}")
                else:
                    st.error("Nome, Usuário (Login), Senha Provisória, Atribuições e Disponibilidade Geral são campos obrigatórios.")

    # =================================================
    # ABA 3: Configurações de Escala
    # =================================================
    with tab_config_escala:
        st.subheader("⚙️ Configurações da Escala")
        # A função get_dias_culto não precisa de argumento aqui, pois queremos todos os dias para o admin
        _, mes_ref = utils.get_dias_culto_proximo_mes()
        edicao_liberada = db.get_edicao_liberada(conn, mes_ref)
        
        status_texto = '✅ Liberada' if edicao_liberada else '❌ Bloqueada'
        st.write(f"**Status de Edição para {mes_ref}:** {status_texto}")

        liberar = st.radio("Alterar Status:", ["Liberar Edição", "Bloquear Edição"], index=0 if edicao_liberada else 1)

        if st.button("💾 Salvar Configuração"):
            status = liberar == "Liberar Edição"
            db.set_edicao_liberada(conn, mes_ref, status)
            # st.success("Configuração atualizada!")
            # st.rerun()
            st.toast("Configuração atualizada!", icon="✅")

        st.markdown("---")
        st.subheader("📋 Resumo de Disponibilidades Confirmadas")
        st.info("Aqui você pode ver as disponibilidades confirmadas pelos voluntários.")

        meses_configurados_rows = db.get_all_meses_configurados(conn)
        if meses_configurados_rows:
            meses_disponiveis = [m['mes_referencia'] for m in meses_configurados_rows]
            mes_selecionado = st.selectbox("Selecione o mês:", sorted(list(set(meses_disponiveis))))
            
            df_disponibilidades = db.listar_disponibilidades_por_mes(conn, mes_selecionado)
            
            if not df_disponibilidades.empty:
                st.write(f"**Disponibilidades para {mes_selecionado}:**")
                df_disponibilidades.columns = ['ID Voluntário', 'Voluntário', 'Datas Disponíveis', 'Serviu Ceia']
                st.dataframe(df_disponibilidades[['Voluntário', 'Datas Disponíveis', 'Serviu Ceia']], use_container_width=True)
            else:
                st.info(f"Nenhuma disponibilidade registrada para {mes_selecionado}.")
        else:
            st.info("Nenhum mês configurado ainda.")

    conn.close()