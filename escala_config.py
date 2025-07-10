# escala_config.py

# Dicionário que define as vagas necessárias para cada tipo de culto.
# A chave é o nome do culto (deve corresponder ao que é gerado em utils.py)
# O valor é outro dicionário onde a chave é a atribuição e o valor é a quantidade de vagas.

NECESSIDADES_ESCALA = {
    "Quinta-feira": {
        "Recepção": 1,
        "Baby Historia": 1,
        "Baby Auxiliar": 1,
        "Primario/Juvenil": 1,
        "Inclusão": 1,
        "Auxiliar": 1
    },
    "Domingo Manhã": {
        "Lider da escala": 1,
        "Recepção": 1,
        "Baby Historia": 1,
        "Baby Auxiliar 1": 1,
        "Baby Auxiliar 2": 1,
        "Inclusão": 1,
        "Primario/Juvenil": 1,
        "Auxiliar": 1
    },
    "Domingo Noite": {
        "Lider da escala": 1,
        "Recepção": 1,
        "Baby Historia": 1,
        "Baby Auxiliar 1": 1,
        "Baby Auxiliar 2": 1,
        "Inclusão": 1,
        "Primario/Juvenil": 1,
        "Auxiliar": 1
    }
}