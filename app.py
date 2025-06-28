# Aplicativo básico com Streamlit para gerar escala mensal de ministério infantil

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import random

# --- CONFIGURACOES INICIAIS ---
FUNCOES_DOMINGO = [
    "Recepção", "Baby Historia", "Baby auxiliar 1", "Baby auxiliar 2",
    "Apoio", "Inclusão", "Primario/Juvenil", "Auxiliar"
]
FUNCOES_QUINTA = [
    "Recepção", "Baby Historia", "Baby auxiliar 1",
    "Apoio", "Inclusão", "Primario/Juvenil"
]

TURNOS = ["Domingo manhã", "Domingo tarde", "Quinta-feira"]

# --- INTERFACE ---
st.title("Gerador de Escala - Ministério Infantil")

# Upload dos dados
vol_data = st.file_uploader("Envie a planilha de voluntários (.xlsx)", type="xlsx")
restricoes_data = st.file_uploader("Envie a planilha de restrições mensais (.xlsx)", type="xlsx")

if vol_data and restricoes_data:
    voluntarios_df = pd.read_excel(vol_data)
    restricoes_df = pd.read_excel(restricoes_data)

    ano = st.number_input("Ano da escala", value=datetime.now().year)
    mes = st.number_input("Mês da escala", min_value=1, max_value=12, value=datetime.now().month)

    if st.button("Gerar Escala"):
        # Criação da escala
        escala = []
        num_dias = calendar.monthrange(ano, mes)[1]
        datas_do_mes = [datetime(ano, mes, dia) for dia in range(1, num_dias + 1)]

        # Filtrar datas por dias corretos
        domingos = [d for d in datas_do_mes if d.weekday() == 6]  # Domingo
        quintas = [d for d in datas_do_mes if d.weekday() == 3]   # Quinta

        rodada = {nome: 0 for nome in voluntarios_df["Nome"]}

        def escolher_voluntario(funcao, turno, data):
            disponiveis = []
            for _, row in voluntarios_df.iterrows():
                if funcao in row["Atribuições"].split(",") and turno in row["Disponibilidade"]:
                    nome = row["Nome"]
                    if not restricoes_df[(restricoes_df["Nome"] == nome) &
                                         (restricoes_df["Tipo de Restrição"] == "1o domingo") &
                                         (data.day <= 7 and data.weekday() == 6 and data.isocalendar()[1] == 1) &
                                         (restricoes_df["Mês"] == calendar.month_name[mes])].any().any():
                        disponiveis.append((nome, rodada[nome]))

            if not disponiveis:
                return "--FALTOU--"

            # Rodízio: menor número de participações primeiro
            disponiveis.sort(key=lambda x: x[1])
            escolhido = disponiveis[0][0]
            rodada[escolhido] += 1
            return escolhido

        for dia in domingos:
            for turno in ["Domingo manhã", "Domingo tarde"]:
                for funcao in FUNCOES_DOMINGO:
                    escala.append({
                        "Data": dia.strftime("%Y-%m-%d"),
                        "Turno": turno,
                        "Função": funcao,
                        "Voluntário": escolher_voluntario(funcao, turno, dia)
                    })

        for dia in quintas:
            for funcao in FUNCOES_QUINTA:
                escala.append({
                    "Data": dia.strftime("%Y-%m-%d"),
                    "Turno": "Quinta-feira",
                    "Função": funcao,
                    "Voluntário": escolher_voluntario(funcao, "Quinta-feira", dia)
                })

        df_escala = pd.DataFrame(escala)
        st.success("Escala gerada com sucesso!")
        st.dataframe(df_escala)

        # Download
        csv = df_escala.to_csv(index=False).encode("utf-8")
        st.download_button("Baixar Escala em CSV", csv, "escala_ministerio.csv", "text/csv")

else:
    st.info("Aguardando upload dos arquivos...")
