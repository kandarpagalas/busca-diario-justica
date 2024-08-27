import os
import streamlit as st
from streamlit import session_state as ss
import pendulum
from src.diario_justica import download_caderno_judiciario, extract_processos_from_pdf

from duckduckgo_search import DDGS


@st.cache_data(ttl="4h")
def find_cnpj_data(empresa):
    results = DDGS().text(empresa, max_results=10)
    results = list(filter(lambda x: "econodata.com.br" in x["href"], results))
    results = list(map(lambda x: x["href"], results))
    return results


ss.download_dir = f"{os.getcwd()}/src/data/downloads"

img_logo = "https://seeklogo.com/images/G/google-search-ads-360-logo-A7DEAFC777-seeklogo.com.png"
st.set_page_config(
    page_title="Exec. Fiscal",
    page_icon=img_logo,
    layout="centered",
    initial_sidebar_state="auto",
)
st.logo(img_logo)
# Oculta o menu a direita
# hide_streamlit_style = """
#             <style>
#             #MainMenu {visibility: hidden;}
#             footer {visibility: hidden;}
#             </style>
#             """
# st.markdown(hide_streamlit_style, unsafe_allow_html=True)


today = pendulum.now()
if "" not in ss:
    ss.execucoes = None

with st.sidebar:
    st.title("EXECUÇÕES FISCAIS")
    st.subheader("Data")
    dt = pendulum.instance(
        st.date_input(
            label="Data",
            label_visibility="collapsed",
            value=today,
            max_value=today,
            format="DD/MM/YYYY",
        )
    )
    if ss.execucoes is not None:
        st.download_button(
            label="Download resultado em csv",
            data="",
            file_name="large_df.csv",
            mime="text/csv",
            use_container_width=True,
        )
    st.subheader("Filtros")
    ss.only_cnpj = st.checkbox("Somente CNPJ")
    ss.only_with_value = st.checkbox("Somente com Valor da Causa")
    ss.prazo = st.slider(
        label="Prazo", min_value=1, max_value=90, value=90, step=1, format="%i dias"
    )

    st.divider()
    st.subheader("Sobre")
    linkedin = "https://www.linkedin.com/in/kandarpagalas/"
    st.link_button("Sobre", linkedin, type="secondary", use_container_width=True)
    st.link_button("Autor", linkedin, type="secondary", use_container_width=True)
    st.link_button("GitHub", linkedin, type="secondary", use_container_width=True)

dt_str = dt.format("DD/MM/YYYY")

caderno = download_caderno_judiciario(dt, download_dir=ss.download_dir)
print("Arquivo:", caderno)
error_message = """Não foi possível fazer o download do caderno.
\nVocê pode verificar se está disponível através desse link\n
[Diário da Justiça Eletrônico](https://esaj.tjce.jus.br/cdje/consultaAvancada.do#buscaavancada)
"""


# Função para verificar se a string contém alguma das siglas
def contem_siglas(s):
    siglas = [
        "LTDA",  # Limitada
        "S/A",  # Sociedade Anônima
        "EIRELI",  # Empresa Individual de Responsabilidade Limitada
        "MEI",  # Microempreendedor Individual
        "S/S",  # Sociedade Simples
        "EPP",  # Empresa de Pequeno Porte
        "SCC",  # Sociedade de Capital Coletivo
        "SCS",  # Sociedade em Conta de Participação
        "SCS",  # Sociedade Cooperativa de Socorros Mutuos
    ]
    try:
        for sigla in siglas:
            if sigla in s:
                return True
        return False
    except:
        return False


st.title(f"Diário da Justiça - {dt_str}")
if caderno is None:
    st.error(error_message)


else:
    print("\n")
    dt_str = dt.format("DD/MM/YYYY")
    print(f"Caderno Judiciario - Execuções Fiscais - {dt_str}")
    ss.execucoes = extract_processos_from_pdf(caderno)

    # execucoes = list(map(add_date, execucoes))
    print("TOTAL:", len(ss.execucoes))

    if len(ss.execucoes) == 0:
        st.success("Não encontramos Execuções Fiscais")

    ss.execucoes = list(filter(lambda x: int(x["prazo"]) <= ss.prazo, ss.execucoes))
    if ss.only_cnpj:
        ss.execucoes = list(
            filter(lambda x: contem_siglas(x["executado"]), ss.execucoes)
        )
    if ss.only_with_value:
        ss.execucoes = list(
            filter(lambda x: x["valor_causa"] is not None, ss.execucoes)
        )

    for ex in ss.execucoes:
        if contem_siglas(ex["executado"]):
            ex_icon = ":material/campaign:"
        else:
            ex_icon = None

        with st.expander("### **PROCESSO NO.** " + ex["numero_processo"], icon=ex_icon):

            st.write("#### " + str(ex["classe"]))
            st.write("**No:** " + str(ex["numero_processo"]))

            st.write("**Data:** " + str(ex["data"]))
            st.write("**Página:** " + str(ex["pagina"]))
            st.write("**Executado:** " + str(ex["executado"]))
            if ex["valor_causa"] is not None:
                st.write("**Valor Causa:** R$" + str(ex["valor_causa"]))
            st.write("**Prazo:** " + str(ex["prazo"]) + " dias")

            st.markdown("**Possíveis dados de contato**")
            if ex_icon is not None:
                links = find_cnpj_data(str(ex["executado"]))
                links = list(map(lambda x: f"[ - {x.split('/')[-1]}]({x})\n", links))

                st.markdown("\n".join(links))
                # for i, link in enumerate(links):
                #     last_part_of_link = link.split("/")[-1]
                #     st.markdown(f"[{last_part_of_link}]({link})")

            st.markdown("**Decisção**")
            st.write(ex["sentenca"])

            st.markdown("**Conteúdo completo**")
            st.write(ex["texto"])
