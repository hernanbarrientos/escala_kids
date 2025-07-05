# pages/painel_admin.py
import streamlit as st
import pandas as pd
import sqlite3
import database as db
import utils

# --- Configuração da Página e Sidebar Central ---
st.set_page_config(page_title="Painel Admin", layout="wide")
utils.render_sidebar() # <--- CHAMADA PARA A SIDEBAR UNIFICADA

# --- Verificação de Login e Permissão ---
if not st.session_state.get('logged_in'):
    st.error("Você precisa estar logado para acessar esta página.")
    st.switch_page("app.py")

if st.session_state.user_role != 'admin':
    st.error("Acesso restrito a administradores.")
    st.switch_page("app.py")

# --- Conexão com o Banco ---
conn = db.conectar_db()
st.title("🛠️ Painel de Administração")

# --- Abas para Organização ---
tab_gerenciar, tab_adicionar, tab_config_escala = st.tabs(["👥 Gerenciar Usuários", "➕ Adicionar Usuário", "⚙️ Configurar Escala"])

# ====================
# ABA: Gerenciar Usuários
# ====================
with tab_gerenciar:
    st.subheader("👥 Lista de Usuários")
    try:
        df_usuarios = db.listar_voluntarios(conn)
        if df_usuarios.empty:
            st.info("Nenhum usuário cadastrado.")
        else:
            st.dataframe(df_usuarios, use_container_width=True)
            st.markdown("---")

            id_selecionado = st.selectbox(
                "Selecione o usuário para editar/excluir:",
                options=df_usuarios['id'],
                format_func=lambda id: f"{df_usuarios.loc[df_usuarios['id'] == id, 'nome'].iloc[0]} (ID: {id})",
            )

            usuario = dict(db.get_voluntario_by_id(conn, id_selecionado))

            with st.form("form_editar_usuario"):
                st.write(f"✏️ Editando: **{usuario['nome']}**")
                nome = st.text_input("Nome", value=usuario["nome"])
                usuario_login = st.text_input("Usuário (Login)", value=usuario["usuario"])
                nova_senha = st.text_input("Nova Senha (opcional)", type="password", placeholder="Deixe vazio para não alterar")
                st.text_input("Papel", value=usuario["role"].capitalize(), disabled=True)

                atribuicoes_selecionadas = []
                disponibilidade_selecionada = []
                if usuario["role"] == "voluntario":
                    st.markdown("**Atribuições:**")
                    default_atribuicoes = usuario["atribuicoes"].split(",") if usuario["atribuicoes"] else []
                    for atr in utils.ATRIBUICOES_LISTA:
                        # CORREÇÃO: Adicionada uma 'key' única para o checkbox
                        if st.checkbox(atr, value=(atr in default_atribuicoes), key=f"edit_atr_{id_selecionado}_{atr}"):
                            atribuicoes_selecionadas.append(atr)

                    st.markdown("**Disponibilidade:**")
                    default_disponibilidade = usuario["disponibilidade"].split(",") if usuario["disponibilidade"] else []
                    for disp in utils.DISPONIBILIDADE_OPCOES:
                        # CORREÇÃO: Adicionada uma 'key' única para o checkbox
                        if st.checkbox(disp, value=(disp in default_disponibilidade), key=f"edit_disp_{id_selecionado}_{disp}"):
                            disponibilidade_selecionada.append(disp)

                if st.form_submit_button("💾 Salvar Alterações"):
                    senha_final = nova_senha if nova_senha else usuario["senha"]
                    db.editar_voluntario(
                        conn, id_selecionado, nome, usuario_login, senha_final,
                        ",".join(atribuicoes_selecionadas), ",".join(disponibilidade_selecionada), role=usuario["role"]
                    )
                    st.success(f"Usuário '{nome}' atualizado com sucesso!")
                    st.rerun()

            # Exclusão de Usuário
            if usuario["role"] != "admin":
                if st.button(f"🗑️ Excluir {usuario['nome']}", type="secondary"):
                    db.excluir_voluntario(conn, id_selecionado)
                    st.warning(f"Usuário '{usuario['nome']}' excluído.")
                    st.rerun()
            else:
                st.info("O usuário Administrador principal não pode ser excluído.")

    except Exception as e:
        st.error(f"Erro ao carregar usuários: {e}")

# ====================
# ABA: Adicionar Novo Usuário
# ====================
with tab_adicionar:
    st.subheader("➕ Adicionar Usuário")
    with st.form("form_add_usuario", clear_on_submit=True):
        nome = st.text_input("Nome Completo")
        usuario_login = st.text_input("Usuário (Login)")
        senha = st.text_input("Senha Provisória", type="password")
        role = st.selectbox("Tipo de Usuário", ["voluntario", "admin"])
        
        atribuicoes = []
        disponibilidade = []
        if role == "voluntario":
            st.markdown("**Atribuições:**")
            for atr in utils.ATRIBUICOES_LISTA:
                if st.checkbox(atr, key=f"add_atr_{atr}"):
                    atribuicoes.append(atr)

            st.markdown("**Disponibilidade:**")
            for disp in utils.DISPONIBILIDADE_OPCOES:
                if st.checkbox(disp, key=f"add_disp_{disp}"):
                    disponibilidade.append(disp)

        if st.form_submit_button("➕ Cadastrar"):
            if nome and usuario_login and senha:
                try:
                    db.adicionar_voluntario(
                        conn, nome, usuario_login, senha,
                        ",".join(atribuicoes), ",".join(disponibilidade), role
                    )
                    st.success(f"Usuário '{nome}' cadastrado com sucesso!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error(f"O nome de usuário '{usuario_login}' já existe.")
                except Exception as e:
                    st.error(f"Erro ao cadastrar: {e}")
            else:
                st.error("Nome, Usuário e Senha são campos obrigatórios.")


# ====================
# ABA: Configurações de Escala (Mantida da sua versão)
# ====================
with tab_config_escala:
    st.subheader("⚙️ Configurações da Escala")
    _, mes_ref = utils.get_dias_culto_proximo_mes()
    edicao_liberada = db.get_edicao_liberada(conn, mes_ref)
    
    status_texto = '✅ Liberada' if edicao_liberada else '❌ Bloqueada'
    st.write(f"**Edição para {mes_ref}:** {status_texto}")

    liberar = st.radio("Alterar Status:", ["Liberar Edição", "Bloquear Edição"], index=0 if edicao_liberada else 1)

    if st.button("Salvar Configuração"):
        status = liberar == "Liberar Edição"
        db.set_edicao_liberada(conn, mes_ref, status)
        st.success("Configuração atualizada!")
        st.rerun()

    st.markdown("---")
    st.subheader("📋 Resumo de Indisponibilidades")
    meses = [m["mes_referencia"] for m in db.get_all_meses_configurados(conn)]
    
    if meses:
        mes_selecionado = st.selectbox("Selecione o mês:", sorted(list(set(meses))))
        df_indisponibilidades = db.listar_indisponibilidades_por_mes(conn, mes_selecionado)
        
        if not df_indisponibilidades.empty:
            df_indisponibilidades.columns = ['ID Voluntário', 'Voluntário', 'Datas de Restrição', 'Serviu Ceia']
            st.dataframe(df_indisponibilidades[['Voluntário', 'Datas de Restrição', 'Serviu Ceia']], use_container_width=True)
        else:
            st.info(f"Nenhuma indisponibilidade registrada para {mes_selecionado}.")
    else:
        st.info("Nenhum mês configurado ainda.")