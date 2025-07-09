import requests
import pandas as pd
import json
import os
import io
from github import Github
from github import GithubException

# Configurações
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRxPVwi6kwvZIc9bsTljFADsVIwzC1BFrI9WBDiaC91LCuBR5nU5HV6Tioy7LbyPwmZ6UEDxk3t_2v6/pub?gid=1513229493&single=true&output=csv"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "meshwave65/aoaib"
FILE_PATH = "dados/doadores.json"

def format_name(name):
    parts = str(name).upper().split()
    return f"{parts[0]}***{parts[-1]}" if len(parts) > 1 else parts[0]

def mask_cpf(cpf):
    cpf = ''.join(filter(str.isdigit, str(cpf)))
    return f"{cpf[:3]}***{cpf[-2:]}" if len(cpf) == 11 else "CPF_INVALIDO"

def format_equip(equip):
    if pd.isna(equip) or equip is None:
        return ""
    equip_str = str(equip).strip()
    if len(equip_str) > 10:
        return f"{equip_str[:5].upper()}***{equip_str[-5:].upper()}"
    return equip_str.upper()

# Baixar e processar CSV
try:
    response = requests.get(GOOGLE_SHEET_URL, timeout=10)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    print(f"Erro ao baixar o CSV: {e}")
    exit(1)

df = pd.read_csv(io.StringIO(response.text))

# Verificar colunas esperadas
expected_columns = ['NOME', 'CPF', 'Equipamento1', 'Equipamento2', 'Equipamento3']
missing_columns = [col for col in expected_columns if col not in df.columns]
if missing_columns:
    print(f"Erro: Colunas ausentes no CSV: {missing_columns}")
    exit(1)

# Depuração: Exibir as primeiras linhas do CSV
print("Conteúdo do CSV (primeiras 5 linhas):")
print(df.head().to_string())

doadores = []
for index, row in df.iterrows():
    nome = row.get('NOME', 'DESCONHECIDO')
    cpf = str(row.get('CPF', '00000000000'))
    equipamentos = [row.get('Equipamento1', ''), row.get('Equipamento2', ''), row.get('Equipamento3', '')]
    print(f"Processando linha {index}: Nome={nome}, CPF={cpf}, Equipamentos={equipamentos}")
    for equip in equipamentos:
        if equip and str(equip).strip():
            print(f"Processando equipamento: {equip}")
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
    print("Erro: O token 'GITHUB_TOKEN' não foi encontrado no ambiente.")
    exit(1)

g = Github(GITHUB_TOKEN)
try:
    repo = g.get_repo(REPO)
    try:
        contents = repo.get_contents(FILE_PATH)
        repo.update_file(
            FILE_PATH,
            "Atualização de doadores",
            json_data,
            contents.sha
        )
        print(f"Arquivo {FILE_PATH} atualizado com sucesso.")
    except GithubException as e:
        if e.status == 404:
            repo.create_file(
                FILE_PATH,
                "Criação inicial de doadores",
                json_data
            )
            print(f"Arquivo {FILE_PATH} criado com sucesso.")
        else:
            print(f"Erro ao manipular o arquivo: {e}")
            exit(1)
except GithubException as e:
    print(f"Erro ao acessar o repositório: {e}")
    exit(1)
