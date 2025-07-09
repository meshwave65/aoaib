import requests
import pandas as pd
import json
import os
import io
from github import Github
from github import GithubException

# Configurações
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRxPVwi6kwvZIc9bsTljFADsVIwzC1BFrI9WBDiaC91LCuBR5nU5HV6Tioy7LbyPwmZ6UEDxk3t_2v6/pub?gid=1513229493&single=true&output=csv"
GITHUB_TOKEN = os.getenv("DOADORES")  # Usando o segredo DOADORES
REPO = "meshwave65/aoaib"
FILE_PATH = "dados/doador.json"  # Caminho para o novo arquivo

def format_name(name):
    parts = name.upper().split()
    return f"{parts[0]}***{parts[-1]}" if len(parts) > 1 else name.upper()

def mask_cpf(cpf):
    return f"{cpf[:3]}***{cpf[-2:]}" if len(cpf) == 11 else cpf

def format_equip(equip):
    if pd.isna(equip) or equip is None:
        return ""
    equip_str = str(equip).strip()
    if len(equip_str) > 10:
        return f"{equip_str[:5].upper()}***{equip_str[-5:].upper()}"
    return equip_str.upper()

# Baixar e processar CSV
response = requests.get(GOOGLE_SHEET_URL)
if response.status_code != 200:
    print(f"Erro ao baixar o CSV: Status {response.status_code}")
    exit(1)
df = pd.read_csv(io.StringIO(response.text))

# Depuração: Exibir as primeiras linhas do CSV
print("Conteúdo do CSV (primeiras 5 linhas):")
print(df.head().to_string())

doadores = []
for index, row in df.iterrows():
    nome = row.get('NOME', 'DESCONHECIDO')
    cpf = str(row.get('CPF', '00000000000'))
    equipamentos = [row.get('Equipamento1', ''), row.get('Equipamento2', ''), row.get('Equipamento3', '')]
    for equip in equipamentos:
        if equip and str(equip).strip():
            doadores.append({
                "formattedName": format_name(nome),
                "cpf": mask_cpf(cpf),
                "celulares": [format_equip(equip)]
            })

# Depuração: Exibir os doadores processados
print("Doadores processados:", doadores)

# Converter para JSON
if not doadores:
    json_data = json.dumps([{"message": "Nenhum doador encontrado"}], ensure_ascii=False)
    print("Aviso: Nenhum doador encontrado, usando mensagem padrão.")
else:
    json_data = json.dumps(doadores, ensure_ascii=False)

# Enviar para GitHub
if not GITHUB_TOKEN:
    print("Erro: O token 'DOADORES' não foi encontrado no ambiente.")
    exit(1)

g = Github(GITHUB_TOKEN)
try:
    repo = g.get_repo(REPO)
    try:
        contents = repo.get_contents(FILE_PATH)
        repo.update_file(FILE_PATH, "Atualização de doador", json_data, contents.sha)
    except GithubException as e:
        if e.status == 404:
            repo.create_file(FILE_PATH, "Criação inicial de doador", json_data)
        else:
            print(f"Erro ao atualizar o arquivo: {e}")
            repo.create_file(FILE_PATH, "Forçando atualização de doador", json_data)
except GithubException as e:
    print(f"Erro ao acessar o repositório: {e}")
    exit(1)

print("JSON atualizado no GitHub!")
