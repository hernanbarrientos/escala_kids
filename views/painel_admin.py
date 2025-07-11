# views/painel_admin.py
import streamlit as st
import pandas as pd
import sqlite3
import database as db
import utils
import os
from datetime import datetime

def show_page():
    if not st.session_state.get('logged_in') or st.session_state.user_role != 'admin':
        st.error("Acesso restrito a administradores.")
        if st.button("Ir para Login"):
            st.session_state.page = 'login'
            st.rerun()
        st.stop()
    
    conn = st.session_state.db_conn
    st.title("🛠️ Painel de Administração")

    tab_gerenciar, tab_adicionar, tab_config_escala = st.tabs(["👥 Gerenciar Usuários", "➕ Adicionar Usuário", "⚙️ Configurar Escala"])

    with tab_gerenciar:
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            st.subheader("Lista de Usuários Cadastrados")
        with col2:
            if st.button("🔄 Atualizar Lista", use_container_width=True, help="Clique para recarregar a lista de usuários."):
                st.rerun()
        
        try:
            df_usuarios = db.listar_voluntarios(conn)
            if df_usuarios.empty:
                st.info("Nenhum usuário cadastrado ainda.")
            else:
                df_usuarios_sorted = df_usuarios.sort_values(by='nome', key=lambda col: col.str.lower())
                st.dataframe(df_usuarios_sorted.set_index('id'), use_container_width=True)
                st.markdown("---")
                st.subheader("Ações para um Usuário Específico")
                
                id_selecionado = st.selectbox(
                    "Selecione o usuário:",
                    options=df_usuarios_sorted['id'],
                    format_func=lambda id: f"{df_usuarios_sorted.loc[df_usuarios_sorted['id'] == id, 'nome'].iloc[0]}",
                    key="selectbox_usuario_gerenciar"
                )
                
                usuario_selecionado_row = db.get_voluntario_by_id(conn, id_selecionado)
                
                if usuario_selecionado_row:
                    usuario = dict(usuario_selecionado_row)
                    
                    with st.form("form_editar_usuario"):
                        st.write(f"**Editando Dados:** {usuario['nome']}")
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
                            
                                 
                        with st.container(border=True):
                            st.markdown(f"🔒 Trava de Segurança para **{usuario['nome']}**")
                            _, mes_ref_proximo = utils.get_dias_culto_proximo_mes()
                            status_atual = db.get_status_indisponibilidade_mes(conn, id_selecionado, mes_ref_proximo)
                            
                            novo_status = st.checkbox(
                                f"NÃO escalar durante todo o mês de **{mes_ref_proximo.split(' de ')[0]}**",
                                value=status_atual,
                                key=f"lock_{id_selecionado}"
                            )
                            
                            if novo_status != status_atual:
                                if db.set_status_indisponibilidade_mes(conn, id_selecionado, mes_ref_proximo, novo_status):
                                    st.toast(f"Status de indisponibilidade de {usuario['nome']} atualizado!", icon="🔒")
                                    st.rerun()
                                else:
                                    st.error("Erro ao atualizar o status.")

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
                        # st.write(f"**Excluir:** {usuario['nome']}")
                        confirm_key = f"confirm_delete_{usuario['id']}"
                        if confirm_key not in st.session_state:
                            st.session_state[confirm_key] = False
                        if st.button("🗑️ Excluir Usuário", type="secondary", key=f"delete_btn_{usuario['id']}"):
                            st.session_state[confirm_key] = True
                            st.rerun()
                        if st.session_state.get(confirm_key):
                            st.warning(f"**Você tem certeza que deseja excluir {usuario['nome']}?**")
                            col_sim, col_nao, _ = st.columns([1, 1, 4])
                            with col_sim:
                                if st.button("SIM, EXCLUIR", type="primary", use_container_width=True, key=f"confirm_yes_{usuario['id']}"):
                                    db.excluir_voluntario(conn, usuario['id'])
                                    del st.session_state[confirm_key]
                                    st.success(f"Usuário '{usuario['nome']}' excluído. Clique em 'Atualizar Lista'.")
                            with col_nao:
                                if st.button("Cancelar", use_container_width=True, key=f"confirm_no_{usuario['id']}"):
                                    st.session_state[confirm_key] = False
                                    st.rerun()
                    else:
                        st.info("O usuário Administrador não pode ser excluído.")
        except Exception as e:
            st.error(f"Ocorreu um erro inesperado: {e}")

    with tab_adicionar:
        st.subheader("➕ Adicionar Novo Usuário")
        role = st.selectbox("Primeiro, selecione o Tipo de Usuário:", ["voluntario", "admin"], key="add_role_select")
        with st.form("form_adicionar_usuario", clear_on_submit=True):
            nome = st.text_input("Nome que irá aparecer na escala")
            usuario = st.text_input("Nome de Usuário (Login)")
            senha = st.text_input("Senha Provisória", type="password")
            atribuicoes_selecionadas = []
            disponibilidade_selecionada = []
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

    with tab_config_escala:
        st.subheader("⚙️ Configurações da Escala e Ferramentas")
        st.markdown("---")
        col_esquerda, col_direita = st.columns([2, 1])
        with col_esquerda:
            st.markdown("#### Status de Edição")
            _, mes_ref = utils.get_dias_culto_proximo_mes()
            edicao_liberada = db.get_edicao_liberada(conn, mes_ref)
            status_texto = '✅ Liberada' if edicao_liberada else '❌ Bloqueada'
            st.write(f"A edição para **{mes_ref}** está: **{status_texto}**")
            liberar = st.radio("Alterar Status:", ["Liberar Edição", "Bloquear Edição"], index=0 if edicao_liberada else 1, horizontal=True)
            if st.button("💾 Salvar Status"):
                status = liberar == "Liberar Edição"
                db.set_edicao_liberada(conn, mes_ref, status)
                st.toast("Configuração atualizada!", icon="✅")
                st.rerun()
            st.markdown("---")
            st.markdown("#### 📋 Resumo de Disponibilidades Confirmadas")
            meses_configurados_rows = db.get_all_meses_configurados(conn)
            if meses_configurados_rows:
                meses_disponiveis = [m['mes_referencia'] for m in meses_configurados_rows]
                mes_selecionado = st.selectbox("Selecione o mês para visualizar:", sorted(list(set(meses_disponiveis))))
                if st.button("🔄 Atualizar Resumo", key="update_disponibilidades"):
                    st.rerun()
                df_disponibilidades = db.listar_disponibilidades_por_mes(conn, mes_selecionado)
                if not df_disponibilidades.empty:
                    st.dataframe(df_disponibilidades.rename(columns={'voluntario_nome': 'Voluntário', 'datas_disponiveis': 'Datas Disponíveis', 'ceia_passada': 'Serviu Ceia'}).drop(columns=['voluntario_id']), use_container_width=True)
                else:
                    st.info(f"Nenhuma disponibilidade registrada para {mes_selecionado}.")
            else:
                st.info("Nenhum mês configurado ainda.")
        with col_direita:
            if st.session_state.get("dev_mode", False):
                with st.container(border=True):
                    st.markdown("#### 🗄️ Backup do Sistema")
                    st.info("É recomendado fazer o backup regularmente para garantir a segurança dos dados.", icon="ℹ️")
                    db_file_path = "voluntarios.db"
                    if os.path.exists(db_file_path):
                        with open(db_file_path, "rb") as fp:
                            db_bytes = fp.read()
                        st.download_button(
                            label="📥 Baixar Backup Completo",
                            data=db_bytes,
                            file_name=f"backup_escala_kids_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                            mime="application/octet-stream",
                            use_container_width=True,
                            type="primary"
                        )
                    else:
                        st.error("Arquivo do banco de dados não encontrado no servidor.")