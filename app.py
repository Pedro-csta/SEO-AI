import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
import google.generativeai as genai
import os

# ==============================
# Configuração das APIs
# ==============================
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
PSI_API_KEY = st.secrets["PSI_API_KEY"]

genai.configure(api_key=GEMINI_API_KEY)

# ==============================
# Funções de análise
# ==============================

def fetch_page_content(url: str):
    """Baixa e retorna o HTML da página"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return None

def onpage_checks(url: str):
    """Faz checagens básicas de SEO On Page"""
    html = fetch_page_content(url)
    if not html:
        return {"error": "Não foi possível acessar o site."}

    soup = BeautifulSoup(html, "html.parser")

    checks = {}
    checks["title"] = soup.title.string if soup.title else "❌ Ausente"
    meta_desc = soup.find("meta", attrs={"name": "description"})
    checks["meta_description"] = meta_desc["content"] if meta_desc else "❌ Ausente"
    checks["h1"] = soup.h1.string.strip() if soup.h1 else "❌ Ausente"
    checks["images_missing_alt"] = len([img for img in soup.find_all("img") if not img.get("alt")])
    checks["links_count"] = len(soup.find_all("a"))

    return checks

def psi_audit(url: str):
    """Consulta Google PageSpeed Insights"""
    api_url = (
        f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        f"?url={url}&strategy=mobile&key={PSI_API_KEY}"
    )
    try:
        response = requests.get(api_url, timeout=30)
        data = response.json()
        score = data["lighthouseResult"]["categories"]["performance"]["score"] * 100
        return {"performance_score": score}
    except Exception:
        return {"performance_score": "Erro ao obter"}

def gemini_analysis(checks: dict):
    """Usa Gemini para gerar recomendações de SEO/GEO"""
    prompt = f"""
    Você é um especialista em SEO e GEO On Page.
    Recebeu o seguinte relatório de auditoria:

    {checks}

    Gere:
    - Um score geral de SEO (0 a 100)
    - Pontos fortes
    - Pontos fracos
    - Recomendações práticas para otimização
    """

    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro ao gerar análise com Gemini: {e}"

# ==============================
# Interface Streamlit
# ==============================
st.set_page_config(page_title="SEO/GEO On Page Auditor", layout="wide")
st.title("🔎 SEO/GEO On Page Auditor")

url = st.text_input("Digite a URL do site para auditoria:", placeholder="https://exemplo.com")

if st.button("Rodar Auditoria"):
    if not url:
        st.warning("Por favor insira uma URL.")
    else:
        with st.spinner("🔍 Analisando site..."):
            checks = onpage_checks(url)
            psi = psi_audit(url)

            # Combina os dados
            full_report = {**checks, **psi}

            # Mostra resultados
            st.subheader("✅ Resultados da Checagem")
            df = pd.DataFrame(full_report.items(), columns=["Fator", "Resultado"])
            st.table(df)

            # Análise avançada com Gemini
            st.subheader("🤖 Análise Avançada com Gemini")
            gemini_report = gemini_analysis(full_report)
            st.markdown(gemini_report)
