# views/painel_admin.py
import streamlit as st
import pandas as pd
from sqlalchemy.exc import IntegrityError
import database as db
import utils
import os
from datetime import datetime

# --- NOVA FUNÇÃO DE CALLBACK ---
# Esta função será executada de forma segura quando o botão do formulário de vínculo for clicado.
def callback_criar_vinculo():
    # Pega o mapa de nome para id que foi previamente armazenado no session_state
    mapa_nome_id = st.session_state.get('mapa_nome_id', {})
    
    # Pega os nomes selecionados diretamente do estado dos widgets
    nome_a = st.session_state.vinc_a
    nome_b = st.session_state.vinc_b

    if nome_a and nome_b and nome_a != nome_b:
        id_a = mapa_nome_id.get(nome_a)
        id_b = mapa_nome_id.get(nome_b)
        if id_a and id_b:
            db.criar_vinculo(id_a, id_b)
            st.toast(f"Vínculo entre {nome_a} e {nome_b} criado com sucesso!", icon="✅")
        else:
            st.toast("Erro: Não foi possível encontrar os IDs dos voluntários.", icon="❌")
    else:
        st.toast("Aviso: Selecione dois voluntários diferentes para criar o vínculo.", icon="⚠️")

def show_page():
    if not st.session_state.get('logged_in') or st.session_state.user_role != 'admin':
        st.error("Acesso restrito a administradores.")
        if st.button("Ir para Login"):
            st.session_state.page = 'login'
            st.rerun()
        st.stop()
    
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
            df_usuarios = db.listar_voluntarios()
            if df_usuarios.empty:
                st.info("Nenhum usuário cadastrado ainda.")
            else:
                df_usuarios_sorted = df_usuarios.sort_values(by='nome', key=lambda col: col.str.lower())
                st.dataframe(df_usuarios_sorted.set_index('id'), use_container_width=True)
                
                st.markdown("---")
                st.subheader("🔗 Gerenciar Vínculos de Voluntários")
                st.info("Vincule voluntários que precisam ser escalados juntos no mesmo dia e horário (ex: carona).", icon="ℹ️")

                df_vinculos = db.listar_vinculos()

                if not df_vinculos.empty:
                    st.write("Vínculos existentes:")
                    for index, row in df_vinculos.iterrows():
                        col_nome1, col_nome2, col_excluir = st.columns([2, 2, 1])
                        col_nome1.write(f"**{row['nome_a']}** está vinculado(a) com")
                        col_nome2.write(f"**{row['nome_b']}**")
                        if col_excluir.button("Excluir", key=f"del_vinculo_{row['vinculo_id']}", use_container_width=True):
                            db.excluir_vinculo(row['vinculo_id'])
                            st.toast("Vínculo removido!")
                            st.rerun()
                
                with st.form("form_criar_vinculo"):
                    st.write("**Criar novo vínculo:**")
                    
                    opcoes_nomes = df_usuarios_sorted['nome'].tolist()
                    # Armazena o mapa de nomes no session_state para que a callback possa acessá-lo
                    st.session_state.mapa_nome_id = pd.Series(df_usuarios_sorted.id.values, index=df_usuarios_sorted.nome).to_dict()

                    col_v1, col_v2 = st.columns(2)
                    with col_v1:
                        nome_a_selecionado = st.selectbox("Selecione o primeiro voluntário:", opcoes_nomes, key="vinc_a")
                    with col_v2:
                        opcoes_b = [nome for nome in opcoes_nomes if nome != nome_a_selecionado]
                        st.selectbox("Selecione o segundo voluntário:", opcoes_b, key="vinc_b")

                    # O botão agora chama a função de callback, que é a forma mais segura
                    st.form_submit_button("➕ Criar Vínculo", type="primary", on_click=callback_criar_vinculo)

                st.markdown("---")
                st.subheader("Ações Individuais para um Usuário Específico")
                
                id_selecionado = st.selectbox(
                    "Selecione o usuário para editar:",
                    options=df_usuarios_sorted['id'],
                    format_func=lambda id: f"{df_usuarios_sorted.loc[df_usuarios_sorted['id'] == id, 'nome'].iloc[0]})",
                    key="selectbox_usuario_gerenciar"
                )
                
                usuario_selecionado_row = db.get_voluntario_by_id(id_selecionado)
                
                if usuario_selecionado_row:
                    usuario = dict(usuario_selecionado_row)

                    with st.container(border=True):
                        st.markdown(f"#### 🔒 Trava de Segurança para **{usuario['nome']}**")
                        _, mes_ref_proximo = utils.get_dias_culto_proximo_mes()
                        status_atual = db.get_status_indisponibilidade_mes(id_selecionado, mes_ref_proximo)
                        novo_status = st.checkbox(
                            f"NÃO escalar durante todo o mês de **{mes_ref_proximo.split(' de ')[0]}**",
                            value=status_atual,
                            key=f"lock_{id_selecionado}"
                        )
                        if novo_status != status_atual:
                            db.set_status_indisponibilidade_mes(id_selecionado, mes_ref_proximo, novo_status)
                            st.toast(f"Status de indisponibilidade de {usuario['nome']} atualizado!", icon="🔒")
                            st.rerun()
                    

                    with st.container(border=True):
                        st.markdown(f"#### 🗓️ Definir Disponibilidade para **{usuario['nome']}**")
                        disponibilidade_geral = [d.strip() for d in (usuario.get('disponibilidade') or "").split(',') if d.strip()]
                        
                        if not disponibilidade_geral:
                            st.warning(f"Este voluntário não possui uma 'Disponibilidade Geral' cadastrada. Edite o perfil abaixo para definir uma.", icon="⚠️")
                        else:
                            opcoes_culto, mes_ref = utils.get_dias_culto_proximo_mes(disponibilidade_geral)
                            disponibilidade_salva = db.carregar_disponibilidade(id_selecionado, mes_ref)
                            datas_salvas = []
                            ceia_salva = "Não"
                            if disponibilidade_salva:
                                datas_salvas = [d.strip() for d in (disponibilidade_salva.get('datas_disponiveis') or "").split(',') if d.strip()]
                                ceia_salva = disponibilidade_salva.get('ceia_passada', "Não")

                            with st.form(key=f"disp_form_{id_selecionado}"):
                                st.write(f"**Disponibilidade para a escala de {mes_ref.split(' de ')[0]}**")
                                ceia_passada = st.radio("Serviu na Ceia do mês anterior?", ["Não", "Sim"], index=["Não", "Sim"].index(ceia_salva), horizontal=True)
                                st.write("Marque os dias que este voluntário **ESTÁ DISPONÍVEL**:")

                                cols = st.columns(len(opcoes_culto))
                                datas_selecionadas = []
                                for i, (tipo_culto, datas) in enumerate(opcoes_culto.items()):
                                    with cols[i]:
                                        st.markdown(f"**{tipo_culto}**")
                                        for data in datas:
                                            data_completa = f"{data} - {tipo_culto}"
                                            if st.checkbox(data, value=(data_completa in datas_salvas), key=f"disp_{id_selecionado}_{data_completa}"):
                                                datas_selecionadas.append(data_completa)
                                
                                if st.form_submit_button("💾 Salvar Disponibilidade", type="primary"):
                                    if db.salvar_disponibilidade(id_selecionado, ",".join(datas_selecionadas), ceia_passada, mes_ref):
                                        st.success("Disponibilidade salva com sucesso!")
                                        st.rerun()
                                    else:
                                        st.error("Erro ao salvar a disponibilidade.")
                    


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
                        if st.form_submit_button("💾 Salvar Alterações"):
                            is_valid = True
                            if usuario["role"] == "voluntario" and (not atribuicoes_selecionadas or not disponibilidade_selecionada):
                                is_valid = False
                                st.error("Para voluntários, é obrigatório selecionar pelo menos uma Atribuição e uma Disponibilidade.")
                            if is_valid:
                                senha_para_salvar = nova_senha if nova_senha else None
                                db.editar_voluntario(id_selecionado, nome, usuario_login, senha_para_salvar, ",".join(atribuicoes_selecionadas), ",".join(disponibilidade_selecionada), role=usuario['role'])
                                st.toast(f"Dados de '{nome}' atualizados!", icon="✅")
                    
           
                    if usuario['role'] != 'admin':
                        st.write(f"**Excluir:** {usuario['nome']}")
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
                                    db.excluir_voluntario(usuario['id'])
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
                        db.adicionar_voluntario(nome, usuario, senha, ",".join(atribuicoes_selecionadas), ",".join(disponibilidade_selecionada), role=role)
                        st.success(f"Usuário '{nome}' cadastrado com sucesso!")
                    except IntegrityError:
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
            status_edicao = db.get_edicao_liberada(mes_ref)
            
            status_texto = '✅ Liberada' if status_edicao else '❌ Bloqueada'
            st.write(f"A edição para **{mes_ref}** está: **{status_texto}**")
            liberar = st.radio("Alterar Status:", ["Liberar Edição", "Bloquear Edição"], index=0 if status_edicao else 1, horizontal=True)
            if st.button("💾 Salvar Status"):
                novo_status = (liberar == "Liberar Edição")
                db.set_edicao_liberada(mes_ref, novo_status)
                st.toast("Configuração atualizada!", icon="✅")
                st.rerun()

            st.markdown("---")
            st.markdown("#### 📋 Resumo de Disponibilidades Confirmadas")
            meses_configurados_rows = db.get_all_meses_configurados()
            if meses_configurados_rows:
                meses_disponiveis = [m['mes_referencia'] for m in meses_configurados_rows]
                mes_selecionado = st.selectbox("Selecione o mês para visualizar:", sorted(list(set(meses_disponiveis))))
                if st.button("🔄 Atualizar Resumo", key="update_disponibilidades"):
                    st.rerun()
                df_disponibilidades = db.listar_disponibilidades_por_mes(mes_selecionado)
                if not df_disponibilidades.empty:
                    st.dataframe(df_disponibilidades.rename(columns={'voluntario_nome': 'Voluntário', 'datas_disponiveis': 'Datas Disponíveis', 'ceia_passada': 'Serviu Ceia'}).drop(columns=['voluntario_id']), use_container_width=True)
                else:
                    st.info(f"Nenhuma disponibilidade registrada para {mes_selecionado}.")
            else:
                st.info("Nenhum mês configurado ainda.")
        
        with col_direita:
            if st.session_state.get("dev_mode", False):
                with st.container(border=True):
                    st.markdown("#### 🗄️ Backup (SQLite - Legado)")
                    st.warning("Esta funcionalidade de backup se refere ao banco de dados SQLite local e não tem efeito no banco de dados PostgreSQL na nuvem.", icon="⚠️")