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
    csv_content = response.text
    # Tentar diferentes encodings para evitar problemas com caracteres
    df = pd.read_csv(io.StringIO(csv_content), encoding='utf-8')
    if df.empty:
        try:
            df = pd.read_csv(io.StringIO(csv_content), encoding='ISO-8859-1')
        except UnicodeDecodeError:
            print("Erro: Não foi possível decodificar o CSV com UTF-8 ou ISO-8859-1.")
            exit(1)
except requests.exceptions.RequestException as e:
    print(f"Erro ao baixar o CSV: {e}")
    exit(1)

# Verificar se o DataFrame está vazio
if df.empty:
    print("Erro: O CSV baixado está vazio. Verifique a URL ou o conteúdo da planilha.")
    exit(1)

# Verificar colunas esperadas
expected_columns = ['CARIMBO', 'NOME', 'CPF', 'CELULAR', 'ENDEREÇO', 'CIDADE', 'ESTADO', 'CEP', 'Coluna 8', 'Tamanho da camiseta', 'Equipamento1', 'Equipamento2', 'Equipamento3', 'SIGILO', 'QTD_EQUIP', 'TOTAL EQUIP', 'UNICOS_CPF']
missing_columns = [col for col in expected_columns if col not in df.columns]
if missing_columns:
    print(f"Erro: Colunas ausentes no CSV: {missing_columns}")
    exit(1)

# Depuração: Exibir as primeiras linhas do CSV
print("Conteúdo do CSV (primeiras 5 linhas):")
print(df.head().to_string())

# Calcular valores globais
total_equip = 0
for index, row in df.iterrows():
    equipamentos = [row.get('Equipamento1', ''), row.get('Equipamento2', ''), row.get('Equipamento3', '')]
    qtd_equip = sum(1 for equip in equipamentos if equip and str(equip).strip())
    total_equip += qtd_equip

unicos_cpf = len(df['CPF'].dropna().unique())

# Processar cada linha como uma entrada independente
doadores = []
for index, row in df.iterrows():
    nome = row.get('NOME', 'DESCONHECIDO')
    cpf = str(row.get('CPF', '00000000000'))
    celula = row.get('CELULAR', '')
    endereco = row.get('ENDEREÇO', '')
    equipamentos = [row.get('Equipamento1', ''), row.get('Equipamento2', ''), row.get('Equipamento3', '')]
    qtd_equip = sum(1 for equip in equipamentos if equip and str(equip).strip())
    print(f"Processando linha {index}: Nome={nome}, CPF={cpf}, Celular={celula}, Endereço={endereco}, QTD_EQUIP={qtd_equip}, Equipamentos={equipamentos}")
    for equip in equipamentos:
        if equip and str(equip).strip():
            print(f"Processando equipamento: {equip}")
            doadores.append({
                "formattedName": format_name(nome),
                "cpf": mask_cpf(cpf),
                "celular": celula,
                "endereco": endereco,
                "qtd_equip": qtd_equip,  # Contagem de equipamentos na linha
                "total_equip": total_equip,  # Total de equipamentos doados
                "unicos_cpf": unicos_cpf,  # Número total de doadores únicos
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
