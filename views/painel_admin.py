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
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            st.subheader("Lista de Usuários Cadastrados")
        with col2:
            if st.button("🔄 Atualizar Lista", use_container_width=True, help="Clique aqui para recarregar a lista de usuários."):
                st.rerun()
        
        try:
            df_usuarios = db.listar_voluntarios(conn)
            if df_usuarios.empty:
                st.info("Nenhum usuário cadastrado ainda.")
            else:
                st.dataframe(df_usuarios.set_index('id'), use_container_width=True)

                st.subheader("Ações para um Usuário Específico")
                
                id_selecionado = st.selectbox(
                    "Selecione o usuário:",
                    options=df_usuarios['id'],
                    format_func=lambda id: f"{df_usuarios.loc[df_usuarios['id'] == id, 'nome'].iloc[0]} (ID: {id})",
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
                            st.write("**Atribuições (obrigatório):**")
                            default_atribuicoes = [a.strip() for a in (usuario.get("atribuicoes") or "").split(",") if a.strip()]
                            cols_atr = st.columns(3)
                            for i, atr in enumerate(utils.ATRIBUICOES_LISTA):
                                with cols_atr[i % 3]:
                                    if st.checkbox(atr, value=(atr in default_atribuicoes), key=f"edit_atr_{id_selecionado}_{atr}"):
                                        atribuicoes_selecionadas.append(atr)
                            
                            st.write("**Disponibilidade Geral (obrigatório):**")
                            default_disponibilidade = [d.strip() for d in (usuario.get("disponibilidade") or "").split(",") if d.strip()]
                            cols_disp = st.columns(3)
                            for i, disp in enumerate(utils.DISPONIBILIDADE_OPCOES):
                                with cols_disp[i % 3]:
                                    if st.checkbox(disp, value=(disp in default_disponibilidade), key=f"edit_disp_{id_selecionado}_{disp}"):
                                        disponibilidade_selecionada.append(disp)

                        if st.form_submit_button("💾 Salvar Alterações"):
                            is_valid = True
                            if usuario["role"] == "voluntario" and (not atribuicoes_selecionadas or not disponibilidade_selecionada):
                                is_valid = False
                                st.error("Para voluntários, é obrigatório selecionar pelo menos uma Atribuição e uma Disponibilidade.")
                            
                            if is_valid:
                                senha_para_salvar = nova_senha if nova_senha else None
                                db.editar_voluntario(conn, id_selecionado, nome, usuario_login, senha_para_salvar, ",".join(atribuicoes_selecionadas), ",".join(disponibilidade_selecionada), role=usuario['role'])
                                st.toast(f"Dados de '{nome}' atualizados!", icon="✅")

                    
                    if usuario['role'] != 'admin':
                                                
                        confirm_key = f"confirm_delete_{usuario['id']}"
                        if confirm_key not in st.session_state:
                            st.session_state[confirm_key] = False

                        if st.button("🗑️ Excluir Usuário", type="secondary"):
                            st.session_state[confirm_key] = True
                            st.rerun()

                        if st.session_state.get(confirm_key):
                            st.warning(f"**Você tem certeza que deseja excluir {usuario['nome']}?**")
                            col_sim, col_nao, _ = st.columns([1, 1, 4])
                            with col_sim:
                                if st.button("SIM, EXCLUIR", type="primary", use_container_width=True):
                                    db.excluir_voluntario(conn, usuario['id'])
                                    del st.session_state[confirm_key]                                    
                                    st.rerun()
                            with col_nao:
                                if st.button("Cancelar", use_container_width=True):
                                    st.session_state[confirm_key] = False
                                    st.rerun()
                    else:
                        st.info("O usuário Administrador não pode ser excluído.")
        except Exception as e:
            st.error(f"Ocorreu um erro inesperado: {e}")

    # =================================================
    # ABA 2: Adicionar Novo Usuário
    # =================================================
    with tab_adicionar:
        st.subheader("➕ Adicionar Novo Usuário")
        
        # PASSO 1: Seleção de papel FORA do formulário.
        role = st.selectbox("Primeiro, selecione o Tipo de Usuário:", ["voluntario", "admin"], key="add_role_select")

        # PASSO 2: O formulário é desenhado. clear_on_submit=True limpará os campos no sucesso.
        with st.form("form_adicionar_usuario", clear_on_submit=True):
            nome = st.text_input("Nome que irá aparecer na escala")
            usuario = st.text_input("Nome de Usuário (Login)")
            senha = st.text_input("Senha Provisória", type="password")
            
            atribuicoes_selecionadas = []
            disponibilidade_selecionada = []

            # PASSO 3: Campos de voluntário são desenhados condicionalmente.
            if role == "voluntario":
                st.markdown("---")
                st.write("**Atribuições do Voluntário (obrigatório):**")
                cols_atr_add = st.columns(3)
                for i, atr in enumerate(utils.ATRIBUICOES_LISTA):
                    with cols_atr_add[i % 3]:
                        if st.checkbox(atr, key=f"add_atr_{i}"):
                            atribuicoes_selecionadas.append(atr)
                
                st.write("**Disponibilidade Geral (obrigatório):**")
                cols_disp_add = st.columns(3)
                for i, disp in enumerate(utils.DISPONIBILIDADE_OPCOES):
                    with cols_disp_add[i % 3]:
                        if st.checkbox(disp, key=f"add_disp_{i}"):
                            disponibilidade_selecionada.append(disp)
            
            submitted = st.form_submit_button("➕ Cadastrar Usuário")

            if submitted:
                # PASSO 4: Validação ocorre aqui.
                is_valid = True
                if not nome or not usuario or not senha:
                    st.error("Nome, Usuário (Login) e Senha são campos obrigatórios.")
                    is_valid = False
                
                if role == "voluntario" and (not atribuicoes_selecionadas or not disponibilidade_selecionada):
                    st.error("Para voluntários, é obrigatório selecionar pelo menos uma Atribuição e uma Disponibilidade.")
                    is_valid = False
                
                if is_valid:
                    try:
                        db.adicionar_voluntario(conn, nome, usuario, senha, ",".join(atribuicoes_selecionadas), ",".join(disponibilidade_selecionada), role=role)
                        st.success(f"Usuário '{nome}' cadastrado com sucesso!")
                    except sqlite3.IntegrityError:
                        st.error(f"O nome de usuário '{usuario}' já existe.")
                    except Exception as e:
                        st.error(f"Ocorreu um erro: {e}")

    # =================================================
    # ABA 3: Configurações de Escala
    # =================================================
    with tab_config_escala:
        st.subheader("⚙️ Configurações da Escala")
        _, mes_ref = utils.get_dias_culto_proximo_mes()
        edicao_liberada = db.get_edicao_liberada(conn, mes_ref)
        
        status_texto = '✅ Liberada' if edicao_liberada else '❌ Bloqueada'
        st.write(f"**Status de Edição para {mes_ref}:** {status_texto}")

        liberar = st.radio("Alterar Status:", ["Liberar Edição", "Bloquear Edição"], index=0 if edicao_liberada else 1)

        if st.button("💾 Salvar Configuração"):
            status = liberar == "Liberar Edição"
            db.set_edicao_liberada(conn, mes_ref, status)
            st.toast("Configuração atualizada!", icon="✅")

        # st.markdown("---")
        st.subheader("📋 Resumo de Disponibilidades Confirmadas")
        
        meses_configurados_rows = db.get_all_meses_configurados(conn)
        if meses_configurados_rows:
            meses_disponiveis = [m['mes_referencia'] for m in meses_configurados_rows]
            mes_selecionado = st.selectbox("Selecione o mês para ver as disponibilidades:", sorted(list(set(meses_disponiveis))))
            
            # --- AJUSTE APLICADO AQUI ---
            col_titulo, col_botao = st.columns([0.8, 0.2])
            with col_titulo:
                st.write(f"**Disponibilidades para {mes_selecionado}:**")
            with col_botao:
                if st.button("🔄 Atualizar", key="update_disponibilidades", use_container_width=True):
                    st.rerun()

            df_disponibilidades = db.listar_disponibilidades_por_mes(conn, mes_selecionado)
            
            if not df_disponibilidades.empty:
                df_disponibilidades.columns = ['ID Voluntário', 'Voluntário', 'Datas Disponíveis', 'Serviu Ceia']
                st.dataframe(df_disponibilidades[['Voluntário', 'Datas Disponíveis', 'Serviu Ceia']], use_container_width=True)
            else:
                st.info(f"Nenhuma disponibilidade registrada para {mes_selecionado}.")
        else:
            st.info("Nenhum mês configurado ainda.")

    conn.close()