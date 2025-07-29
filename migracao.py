# migracao.py
import pandas as pd
from sqlalchemy import create_engine, text
import bcrypt
import streamlit as st # Usado apenas para pegar a URL do banco de dados dos secrets

# --- CONFIGURAÇÕES ---
# 1. Coloque o caminho para o seu ARQUIVO de banco de dados SQLite antigo.
SQLITE_DATABASE_PATH = r'C:\Users\BlueShift\OneDrive\Documentos\escala_kids\voluntarios.db'  # <-- ALTERE AQUI

# 2. A URL do seu banco de dados PostgreSQL (pegando dos secrets do Streamlit)
# Se você for rodar este script fora do ambiente Streamlit,
# cole a string de conexão diretamente aqui.
POSTGRES_DATABASE_URL = st.secrets["DATABASE_URL"]

# 3. Senha padrão que será atribuída a todos os voluntários migrados.
# Eles deverão trocá-la no primeiro acesso.
SENHA_PADRAO = "123"

# --- FUNÇÃO AUXILIAR PARA CRIPTOGRAFAR A SENHA ---
def hash_password(password):
    """Criptografa a senha usando bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# --- LÓGICA PRINCIPAL DA MIGRAÇÃO ---
def migrar_voluntarios():
    """
    Executa a migração da tabela 'voluntarios' do SQLite para o PostgreSQL.
    """
    print("Iniciando o script de migração...")

    try:
        # Criando as conexões com os bancos de dados
        engine_sqlite = create_engine(f'sqlite:///{SQLITE_DATABASE_PATH}')
        engine_postgres = create_engine(POSTGRES_DATABASE_URL)

        # --- PASSO 1: LER DADOS DO SQLITE ---
        print(f"Lendo dados da tabela 'voluntarios' do banco SQLite: {SQLITE_DATABASE_PATH}")
        # Usamos o 'pd.read_sql_table' para ler a tabela inteira em um DataFrame
        df_voluntarios = pd.read_sql_table('voluntarios', engine_sqlite)
        print(f"Encontrados {len(df_voluntarios)} voluntários para migrar.")
        # ---> ADICIONE ESTA LINHA PARA REMOVER O ADMIN <---
        df_voluntarios = df_voluntarios[df_voluntarios['usuario'].str.lower() != 'admin']
        print(f"Ignorando o usuário 'admin' e preparando para migrar {len(df_voluntarios)} voluntários.")

        if df_voluntarios.empty:
            print("Nenhum voluntário encontrado. Encerrando o script.")
            return

        # --- PASSO 2: PREPARAR OS DADOS PARA O POSTGRESQL ---
        print(f"Preparando os dados para a migração...")
        print(f"Todas as senhas serão redefinidas para '{SENHA_PADRAO}' e criptografadas.")
        
        # Criptografar a senha padrão para todos os usuários
        df_voluntarios['senha'] = hash_password(SENHA_PADRAO)
        
        # Garantir que o 'primeiro_acesso' seja 1 (verdadeiro) para forçar a troca de senha
        df_voluntarios['primeiro_acesso'] = 1
        
        # Renomear colunas se houver alguma diferença (ajuste se necessário)
        # Ex: df_voluntarios.rename(columns={'nome_antigo': 'nome_novo'}, inplace=True)

        # Remover a coluna 'id' para que o PostgreSQL gere novos IDs automaticamente
        if 'id' in df_voluntarios.columns:
            df_voluntarios = df_voluntarios.drop(columns=['id'])

        print("Dados preparados com sucesso.")

        # --- PASSO 3: INSERIR DADOS NO POSTGRESQL ---
        print("Conectando ao PostgreSQL e inserindo os dados...")
        
        # Usamos 'to_sql' para inserir o DataFrame inteiro na tabela do PostgreSQL
        # if_exists='append' adiciona os novos dados sem apagar os existentes
        # index=False evita que o índice do DataFrame seja salvo como uma coluna
        df_voluntarios.to_sql('voluntarios', engine_postgres, if_exists='append', index=False)
        
        print("\n🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO! 🎉")
        print(f"{len(df_voluntarios)} voluntários foram adicionados ao banco de dados PostgreSQL.")
        print("Lembre-se de avisar aos voluntários que a senha provisória deles é 'mudar123'.")

    except Exception as e:
        print(f"\n❌ Ocorreu um erro durante a migração: {e}")
        print("Nenhuma alteração foi feita no banco de dados de destino.")

# Executa a função principal
if __name__ == "__main__":
    migrar_voluntarios()