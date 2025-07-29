# views/painel_admin.py
import streamlit as st
import pandas as pd
import database as db
import utils
from sqlalchemy.exc import IntegrityError

def show_page():
    if not st.session_state.get('logged_in') or st.session_state.user_role != 'admin':
        st.error("Acesso restrito a administradores.")
        st.rerun()
        st.stop()
    
    st.title("🛠️ Painel de Administração")

    tab_gerenciar, tab_adicionar, tab_config_escala = st.tabs(["👥 Gerenciar Usuários", "➕ Adicionar Usuário", "⚙️ Configurar Escala"])

    with tab_gerenciar:
        st.subheader("Lista de Usuários Cadastrados")
        
        try:
            df_usuarios = db.listar_voluntarios()
            if df_usuarios.empty:
                st.info("Nenhum usuário cadastrado ainda.")
            else:
                st.dataframe(df_usuarios.sort_values(by='nome').set_index('id'), use_container_width=True)
                
                st.markdown("---")
                st.subheader("Editar Dados e Disponibilidade de um Usuário")
                
                id_selecionado = st.selectbox(
                    "Selecione o usuário para editar:",
                    options=df_usuarios['id'],
                    format_func=lambda id: f"{df_usuarios.loc[df_usuarios['id'] == id, 'nome'].iloc[0]}",
                    key="selectbox_usuario_gerenciar"
                )
                
                usuario_selecionado = db.get_voluntario_by_id(id_selecionado)
                
                if usuario_selecionado:
                    # Carrega dados de disponibilidade
                    disponibilidade_geral_usuario = usuario_selecionado.get("disponibilidade") or ""
                    opcoes_agrupadas, mes_ref = utils.get_dias_culto_proximo_mes(disponibilidade_geral_usuario.split(','))
                    disponibilidade_salva = db.carregar_disponibilidade(id_selecionado, mes_ref)
                    datas_disponiveis_salvas = (disponibilidade_salva.get('datas_disponiveis') or "").split(',') if disponibilidade_salva else []
                    serviu_ceia_salvo = disponibilidade_salva.get('ceia_passada', 'Não') if disponibilidade_salva else "Não"
                    status_indisponibilidade_atual = db.get_status_indisponibilidade_mes(id_selecionado, mes_ref)

                    with st.form(key=f"form_editar_usuario_{id_selecionado}"):
                        st.write(f"**Editando:** {usuario_selecionado['nome']}")
                        
                        nome = st.text_input("Nome", value=usuario_selecionado["nome"])
                        usuario_login = st.text_input("Usuário (Login)", value=usuario_selecionado["usuario"])
                        nova_senha = st.text_input("Nova Senha", type="password", placeholder="Deixe em branco para não alterar")
                        
                        atribuicoes_selecionadas = []
                        disponibilidade_selecionada = []
                        if usuario_selecionado['role'] == 'voluntario':
                            atribuicoes_selecionadas = utils.select_from_list("Atribuições", utils.ATRIBUICOES_LISTA, usuario_selecionado.get("atribuicoes"), f"edit_atr_{id_selecionado}")
                            disponibilidade_selecionada = utils.select_from_list("Disponibilidade Geral", utils.DISPONIBILIDADE_OPCOES, usuario_selecionado.get("disponibilidade"), f"edit_disp_{id_selecionado}")

                            st.markdown("---")
                            st.write(f"**Disponibilidade para a escala de {mes_ref}**")
                            ceia_passada_radio = st.radio("Serviu na Ceia do mês anterior?", ["Não", "Sim"], index=1 if serviu_ceia_salvo == "Sim" else 0, horizontal=True, key=f"ceia_{id_selecionado}")
                            st.write("Marque os dias que este voluntário **ESTÁ DISPONÍVEL**:")
                            
                            datas_selecionadas_atuais = []
                            if opcoes_agrupadas:
                                primeiro_domingo = utils.get_primeiro_domingo_mes(opcoes_agrupadas)
                                serviu_na_ceia = (ceia_passada_radio == "Sim")
                                cols_disp_edit = st.columns(len(opcoes_agrupadas))
                                for i, (dia_turno, datas) in enumerate(opcoes_agrupadas.items()):
                                    with cols_disp_edit[i]:
                                        st.write(f"**{dia_turno}**")
                                        for data_str in datas:
                                            full_option_str = f"{data_str} - {dia_turno}"
                                            is_checked = full_option_str in datas_disponiveis_salvas
                                            is_disabled = serviu_na_ceia and (data_str == primeiro_domingo)
                                            if is_disabled: is_checked = False
                                            if st.checkbox(data_str, value=is_checked, key=f"disp_edit_{id_selecionado}_{full_option_str}", disabled=is_disabled):
                                                datas_selecionadas_atuais.append(full_option_str)
                            
                            st.markdown("---")
                            # --- PONTO DA CORREÇÃO 1: "Não escalar" movido para DENTRO do formulário ---
                            st.write("**Trava de Segurança**")
                            novo_status_indisponibilidade = st.checkbox(f"NÃO escalar em **{mes_ref.split(' de ')[0]}**", value=status_indisponibilidade_atual, key=f"lock_{id_selecionado}")
                        
                        if st.form_submit_button("💾 Salvar Alterações"):
                            db.editar_voluntario(id_selecionado, nome, usuario_login, nova_senha or None, ",".join(atribuicoes_selecionadas), ",".join(disponibilidade_selecionada), usuario_selecionado['role'])
                            if usuario_selecionado['role'] == 'voluntario':
                                # Salva a disponibilidade e o status de "não escalar" junto
                                db.salvar_disponibilidade(id_selecionado, ",".join(datas_selecionadas_atuais), ceia_passada_radio, mes_ref)
                                db.set_status_indisponibilidade_mes(id_selecionado, mes_ref, novo_status_indisponibilidade)
                            st.success(f"Dados de '{nome}' atualizados com sucesso!")
                            st.rerun()

                    # --- PONTO DA CORREÇÃO 2: Botão Excluir FORA do formulário e alinhado à direita ---
                    if usuario_selecionado['role'] != 'admin':
                        st.markdown("---")
                        col_btn_excluir, _ = st.columns([1, 4]) # Coluna vazia à esquerda para empurrar o botão
                        with col_btn_excluir:
                            if st.button("🗑️ Excluir Voluntário", use_container_width=True, type="secondary"):
                                if st.confirm(f"ATENÇÃO: Você tem certeza que deseja excluir {usuario_selecionado['nome']}?"):
                                    db.excluir_voluntario(id_selecionado)
                                    st.success(f"Usuário '{usuario_selecionado['nome']}' excluído.")
                                    st.rerun()
        except Exception as e:
            st.error(f"Ocorreu um erro ao carregar os usuários: {e}")

    # ==================================
    # ABA 2: Adicionar Novo Usuário
    # ==================================
    with tab_adicionar:
        st.subheader("➕ Adicionar Novo Usuário")
        
        with st.form("form_adicionar_usuario", clear_on_submit=True):
            nome = st.text_input("Nome que irá aparecer na escala")
            usuario = st.text_input("Nome de Usuário (Login)")
            senha = st.text_input("Senha Provisória", type="password")
            role = st.selectbox("Tipo de Usuário", ["voluntario", "admin"])
            
            atribuicoes_selecionadas = []
            disponibilidade_selecionada = []
            if role == "voluntario":
                st.markdown("---")
                atribuicoes_selecionadas = utils.select_from_list("Atribuições do Voluntário (obrigatório)", utils.ATRIBUICOES_LISTA, "", "add_atr")
                disponibilidade_selecionada = utils.select_from_list("Disponibilidade Geral (obrigatório)", utils.DISPONIBILIDADE_OPCOES, "", "add_disp")
            
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
                        db.adicionar_voluntario(nome, usuario, senha, ",".join(atribuicoes_selecionadas), ",".join(disponibilidade_selecionada), role=role)
                        st.success(f"Usuário '{nome}' cadastrado com sucesso! O formulário foi limpo.")
                    except IntegrityError:
                        st.error(f"O nome de usuário '{usuario}' já existe.")
                    except Exception as e:
                        st.error(f"Ocorreu um erro: {e}")

    # ==================================
    # ABA 3: Configurações de Escala
    # ==================================
    with tab_config_escala:
        st.subheader("⚙️ Configurações da Escala e Ferramentas")
        st.markdown("---")
        
        st.markdown("#### Status de Edição") 
        
        _, mes_ref_config = utils.get_dias_culto_proximo_mes()
        
        status_edicao = db.get_edicao_liberada(mes_ref_config)
        
        novo_status_toggle = st.toggle('Liberar edição de disponibilidade para voluntários', value=status_edicao)
        if novo_status_toggle != status_edicao:
            db.set_edicao_liberada(mes_ref_config, novo_status_toggle)
            st.toast(f"Edição para {mes_ref_config} {'liberada' if novo_status_toggle else 'bloqueada'}.", icon="✅" if novo_status_toggle else "❌")
            st.rerun()
        
        st.write(f"{'✅ LIBERADA' if novo_status_toggle else '❌ BLOQUEADA'}")

        st.markdown("---")
        st.markdown("#### 📋 Resumo de Disponibilidades Confirmadas")
        meses_configurados_rows = db.get_all_meses_configurados()
        if meses_configurados_rows:
            meses_disponiveis = [m['mes_referencia'] for m in meses_configurados_rows]
            mes_selecionado = st.selectbox("Selecione o mês para visualizar:", sorted(list(set(meses_disponiveis))))
            
            df_disponibilidades = db.listar_disponibilidades_por_mes(mes_selecionado)
            if not df_disponibilidades.empty:
                st.dataframe(df_disponibilidades.rename(columns={'nome': 'Voluntário', 'datas_disponiveis': 'Datas Disponíveis', 'ceia_passada': 'Serviu Ceia'}), use_container_width=True)
            else:
                st.info(f"Nenhuma disponibilidade registrada para {mes_selecionado}.")
        else:
            st.info("Nenhum mês configurado ainda.")

        st.markdown("---")
        if st.session_state.get("dev_mode", False):
            with st.container(border=True):
                st.markdown("#### 🗄️ Backup do Sistema")
                st.info("O backup de bancos de dados na nuvem (como Supabase) deve ser feito diretamente no painel do provedor para garantir a integridade.", icon="ℹ️")