import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os

# ========== CONFIGURAÇÃO DA API ==========
# Defina sua chave Gemini no Streamlit Cloud (Secrets)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)


# ========== FUNÇÕES DE AUDITORIA ==========
def onpage_checks(url):
    """Executa auditoria on-page em uma URL"""
    response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(response.text, "html.parser")

    checks = {}

    # Título
    checks["title"] = soup.title.string.strip() if soup.title else "❌ Ausente"

    # Meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    checks["meta_description"] = meta_desc["content"].strip() if meta_desc else "❌ Ausente"

    # H1
    h1 = soup.find("h1")
    checks["h1"] = h1.get_text(strip=True) if h1 else "❌ Ausente"

    # Canonical
    canonical = soup.find("link", rel="canonical")
    checks["canonical"] = canonical["href"] if canonical else "❌ Ausente"

    # Robots
    robots = soup.find("meta", attrs={"name": "robots"})
    checks["robots"] = robots["content"] if robots else "❌ Ausente"

    # Links internos e externos
    links = soup.find_all("a", href=True)
    internal_links = [a["href"] for a in links if a["href"].startswith("/")]
    external_links = [a["href"] for a in links if a["href"].startswith("http")]
    checks["links_internos"] = len(internal_links)
    checks["links_externos"] = len(external_links)

    return checks


def generate_gemini_recommendations(checks):
    """Gera recomendações de SEO usando Google Gemini"""
    prompt = f"""
    Você é um consultor de SEO. Aqui estão os resultados de uma auditoria on-page:

    {checks}

    Gere:
    - Um score de 0 a 100 baseado na qualidade da página.
    - Lista de pontos positivos.
    - Lista de pontos negativos.
    - Recomendações práticas para melhorar SEO on-page.
    """

    gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    gemini_resp = gemini_model.generate_content(prompt)

    return gemini_resp.text


# ========== INTERFACE STREAMLIT ==========
st.set_page_config(page_title="SEO AI Auditor", page_icon="🔍", layout="wide")

st.title("🔍 SEO AI Auditor (Gemini)")
st.write("Ferramenta de auditoria SEO usando **Google Gemini**")

url = st.text_input("Insira a URL para auditoria:")

if st.button("Rodar Auditoria"):
    if not url.startswith("http"):
        st.error("Por favor, insira uma URL válida (inclua http ou https).")
    else:
        with st.spinner("Rodando auditoria..."):
            try:
                results = onpage_checks(url)
                st.subheader("📊 Resultados On-page")
                st.json(results)

                st.subheader("🤖 Recomendações de SEO (Gemini)")
                gemini_sug = generate_gemini_recommendations(results)
                st.write(gemini_sug)

            except Exception as e:
                st.error(f"Erro ao processar: {e}")
