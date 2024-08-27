import os
import re
from time import sleep
import fitz  # PyMuPDF
import pendulum
import streamlit as st
from selenium import webdriver
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile


def extrair_informacoes(texto):

    # Expressões regulares para encontrar o número do processo e a classe
    processo_pattern = r"PROCESSO:\s*(\S+)"
    classe_pattern = r"CLASSE:\s*([^(]+)"
    executado_pattern = r"EXECUTADO:\s*(.*?)\s*(?:VALOR DA CAUSA|EDITAL DE INTIMAÇÃO)"
    valor_causa_pattern = r"VALOR DA CAUSA:\s*R\$ ([\d\.,]+)"
    prazo_pattern = r"PRAZO\s*-\s*(\d+)\s*\(.*?\)\s*DIAS"
    sentenca_pattern = r"\) DIAS\s*(.*)"

    # Encontrar o número do processo
    processo_match = re.search(processo_pattern, texto)
    numero_processo = processo_match.group(1) if processo_match else None

    # Encontrar a classe
    classe_match = re.search(classe_pattern, texto)
    classe = classe_match.group(1).strip() if classe_match else None

    # Encontrar a executado
    executado_match = re.search(executado_pattern, texto)
    executado = executado_match.group(1).strip() if executado_match else None

    # Encontrar o prazo
    prazo_match = re.search(prazo_pattern, texto.replace("\n", " "))
    prazo = prazo_match.group(1).strip() if prazo_match else None

    # Encontrar a sentença
    sentenca_match = re.search(sentenca_pattern, texto.replace("\n", " "))
    sentenca = sentenca_match.group(1).strip() if sentenca_match else None

    # Encontrar a sentença
    valor_causa_match = re.search(valor_causa_pattern, texto.replace("\n", " "))
    valor_causa = valor_causa_match.group(1).strip() if valor_causa_match else None

    # Criar o dicionário com os dados extraídos
    resultado = {
        "numero_processo": numero_processo,
        "classe": classe,
        "executado": executado,
        "valor_causa": valor_causa,
        "prazo": prazo,
        "sentenca": sentenca,
        "texto": texto.replace("\n", " "),
    }

    return resultado


def extrair_processos(page):
    text = page.get_text()

    document = text.replace("\n", "{||}")

    # Find matches between text
    # Regular expression pattern to find text between "PROCESSO:" and "PROCESSO:"
    matches = re.findall(r"PROCESSO:\s*(.*?)\s*(PROCESSO:|__)", document)

    # Find matches ending in **
    # Regular expression pattern to find text between "PROCESSO:" and "**"
    matches2 = re.findall(r"PROCESSO:\s*(.*?)\*\*", document)

    # Merge all matches
    matches.extend(matches2)

    if len(matches) > 0:

        # Transforma a tupla em string e substitui a quebra de linha
        matches = list(
            map(lambda x: "PROCESSO:" + x[0].strip().replace("{||}", "\n"), matches)
        )

        # Extrai informações e transforma em json
        processos = list(map(extrair_informacoes, matches))

        def add_page_num(x):
            x["pagina"] = page.number + 1
            return x

        # Adiciona o número da página ao documento
        processos = list(map(add_page_num, processos))

        return processos
    return []


@st.cache_data()
def extract_processos_from_pdf(pdf_path):
    execucoes_fiscais = []
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)

    # for page_num in range(600, 640):
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        # break

        processos = extrair_processos(page)

        if len(processos) > 0:
            execucoes_fiscais.extend(processos)
            # print("\nPágina", page.number + 1)
            # for processo in processos:
            #     print(" -", processo)

    # Close the PDF file
    pdf_document.close()
    dt_str = pdf_path.split("/")[-1].split(".")[0]

    def add_date(x):
        x["data"] = dt_str
        return x

    execucoes_fiscais = list(map(add_date, execucoes_fiscais))
    execucoes_fiscais = list(
        filter(lambda x: x["classe"] is not None, execucoes_fiscais)
    )

    return execucoes_fiscais


@st.cache_data()
def download_caderno_judiciario(dt, download_dir="/Users/kandarpagalas/Downloads/lpl"):
    output_filename = dt.format("YYYY-MM-DD") + ".pdf"
    dt_str = dt.format("DD/MM/YYYY")

    if output_filename in os.listdir(download_dir):
        # print(f"Arquivo {output_filename} já existe")
        return f"{download_dir}/{output_filename}"

    # Cria a pasta se necessário
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    # Create a Firefox profile and set download preferences
    firefox_profile = FirefoxProfile()
    firefox_profile.set_preference(
        "browser.download.folderList", 2
    )  # Use custom download directory
    firefox_profile.set_preference("browser.download.dir", download_dir)
    firefox_profile.set_preference(
        "browser.helperApps.neverAsk.saveToDisk", "application/octet-stream"
    )  # MIME type for the file to download
    firefox_profile.set_preference("browser.download.panel.shown", False)
    firefox_profile.set_preference("browser.download.manager.showWhenStarting", False)

    # Set up Firefox options
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")  # Run in headless mode for no GUI
    options.profile = firefox_profile

    # Start Firefox Driver
    driver = webdriver.Firefox(options=options)
    try:
        # Set the page load timeout
        driver.set_page_load_timeout(10)  # Timeout in seconds

        url = f"https://esaj.tjce.jus.br/cdje/downloadCaderno.do?dtDiario={dt_str}&cdCaderno=2&tpDownload=D"

        # print("URL:", url)
        # Navigate to the URL
        driver.get(url)

    except Exception as e:
        print("Exception - Fechando navegador -", e.__class__.__name__)

    finally:

        def check_for_pdf_part_files(directory):
            # List all files in the given directory
            files = os.listdir(directory)
            # Check for any file ending with .pdf.part
            for file in files:
                if file.endswith(".pdf.part"):
                    return True
            return False

        while check_for_pdf_part_files(download_dir):
            print(".", end="")
            sleep(2)

        driver.quit()

    current_name = f"{download_dir}/caderno2-Judiciario.pdf"
    new_name = f"{download_dir}/{output_filename}"

    if "caderno2-Judiciario.pdf" in os.listdir(download_dir):
        # Rename the file
        os.rename(current_name, new_name)
        return new_name

    else:
        return None


if __name__ == "__main__":
    dt = pendulum.today()
    # dt = dt.add(days=-1)
    dt = dt.add(days=-4)
    caderno = download_caderno_judiciario(dt)
    print("Arquivo:", caderno)

    if caderno is not None:
        print("\n")
        dt_str = dt.format("DD/MM/YYYY")
        print(f"Caderno Judiciario - Execuções Fiscais - {dt_str}")
        execucoes = extract_processos_from_pdf(caderno)
        print("TOTAL:", len(execucoes))
