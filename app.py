import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
import pandas as pd

# ========== CONFIGURAÇÃO DA API ==========
# Lembre-se de configurar sua GEMINI_API_KEY nos "Secrets" do Streamlit Cloud
# https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=GEMINI_API_KEY)
except AttributeError:
    st.warning("Chave da API Gemini não encontrada. Configure-a nos Secrets do Streamlit.", icon="⚠️")


# ========== FUNÇÕES DE AUDITORIA ==========

def onpage_checks(url):
    """
    Executa uma auditoria on-page aprofundada em uma URL, coletando diversas métricas de SEO.
    """
    try:
        # Usamos um User-Agent para simular um navegador e evitar bloqueios simples
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, timeout=10, headers=headers)
        # Lança um erro se a requisição falhar (ex: status 404, 500)
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        # Retornamos o erro para ser tratado na interface do Streamlit
        raise ConnectionError(f"Não foi possível acessar a URL. Erro: {e}")

    soup = BeautifulSoup(response.text, "html.parser")
    checks = {}

    # --- ANÁLISES DE CONTEÚDO E TAGS ---

    # Título
    title_tag = soup.title
    checks["title"] = title_tag.string.strip() if title_tag else "❌ Ausente"
    checks["title_length"] = len(checks["title"]) if title_tag else 0

    # Meta Description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    checks["meta_description"] = meta_desc["content"].strip() if meta_desc and meta_desc.get("content") else "❌ Ausente"
    checks["meta_description_length"] = len(checks["meta_description"]) if meta_desc and meta_desc.get("content") else 0

    # H1
    h1s = soup.find_all("h1")
    checks["h1_count"] = len(h1s)
    checks["h1_text"] = h1s[0].get_text(strip=True) if h1s else "❌ Ausente"

    # --- ANÁLISES TÉCNICAS ---

    # Canonical
    canonical = soup.find("link", rel="canonical")
    checks["canonical"] = canonical["href"] if canonical else "❌ Ausente"

    # Robots
    robots = soup.find("meta", attrs={"name": "robots"})
    checks["robots_tag"] = robots["content"] if robots else "❌ Ausente"
    
    # Dados Estruturados (JSON-LD)
    structured_data = soup.find("script", type="application/ld+json")
    checks["dados_estruturados"] = "✅ Presente" if structured_data else "❌ Ausente"


    # --- ANÁLISES DE RECURSOS E LINKS ---

    # Links
    all_links = soup.find_all("a", href=True)
    internal_links = [a["href"] for a in all_links if url in a["href"] or a["href"].startswith("/")]
    external_links = [a["href"] for a in all_links if a["href"].startswith("http") and url not in a["href"]]
    checks["links_internos"] = len(internal_links)
    checks["links_externos"] = len(external_links)
    
    # Imagens
    images = soup.find_all("img")
    checks["image_count"] = len(images)
    images_sem_alt = [img for img in images if not img.get("alt", "").strip()]
    checks["images_sem_alt_text"] = len(images_sem_alt)

    # Contagem de Palavras
    body_text = soup.find("body").get_text(separator=" ", strip=True) if soup.find("body") else ""
    checks["word_count"] = len(body_text.split())

    return checks


def generate_gemini_recommendations(checks, url):
    """
    Gera recomendações de SEO usando Google Gemini com um prompt aprimorado.
    """
    # Transforma o dicionário de checks em um texto mais legível para a IA
    report_details = "\n".join([f"- {key.replace('_', ' ').title()}: {value}" for key, value in checks.items()])

    prompt = f"""
    Você é um especialista sênior em SEO, encarregado de analisar uma página da web e fornecer um feedback claro e acionável.

    **URL Analisada:** {url}

    **Dados da Auditoria On-Page:**
    {report_details}

    **Sua Tarefa:**
    Com base nos dados fornecidos, por favor, gere a seguinte análise em português do Brasil, usando formatação Markdown:

    1.  **## SCORE DE SEO ON-PAGE (0/100)**
        Atribua uma pontuação geral de 0 a 100 para a saúde do SEO on-page desta página. Justifique brevemente a pontuação com base nos dados mais críticos (presença e qualidade do título, H1, meta description, alt text em imagens, etc.).

    2.  **## ✅ PONTOS FORTES**
        Liste de 2 a 3 elementos que estão bem implementados nesta página, explicando por que são positivos para SEO.

    3.  **## 🎯 OPORTUNIDADES DE MELHORIA**
        Liste os problemas mais críticos encontrados, em ordem de prioridade. Explique o impacto negativo de cada um.

    4.  **## 📈 Recomendações Acionáveis**
        Forneça uma lista de ações práticas e diretas que o proprietário do site pode tomar para corrigir os problemas listados. Seja específico. Por exemplo, em vez de "melhore o título", sugira "O título atual tem {checks.get('title_length', 0)} caracteres. Tente reescrevê-lo para ter entre 50 e 60 caracteres e incluir a palavra-chave principal."
    """

    gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    gemini_resp = gemini_model.generate_content(prompt)

    return gemini_resp.text


# ========== INTERFACE STREAMLIT ==========
st.set_page_config(page_title="SEO AI Auditor", page_icon="🔍", layout="wide")

st.title("🔍 SEO AI Auditor Turbinado com Gemini")
st.write("Uma ferramenta de auditoria de SEO que combina extração de dados e análise por IA para fornecer insights valiosos.")

url = st.text_input("Insira a URL completa para auditoria (ex: https://www.exemplo.com.br):", key="url_input")

if st.button("🚀 Rodar Auditoria Completa", type="primary"):
    if not url.startswith("http"):
        st.error("Por favor, insira uma URL válida (inclua http:// ou https://).")
    else:
        with st.spinner("Analisando cada detalhe da sua página... Isso pode levar um momento. 🤖"):
            try:
                results = onpage_checks(url)
                
                st.subheader("📊 Painel de Auditoria On-Page")

                # --- Apresentação dos Resultados ---
                
                # Tabela de Resumo com Pandas
                st.write("**Resumo do Conteúdo Principal:**")
                df = pd.DataFrame({
                    "Elemento": ["Título", "Meta Description", "H1 (Primeiro)"],
                    "Conteúdo": [results.get("title", ""), results.get("meta_description", ""), results.get("h1_text", "")]
                })
                st.table(df)

                # Métricas em Colunas
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(label="Contagem de Palavras", value=results.get("word_count", "N/A"))
                    st.metric(label="Contagem de Imagens", value=results.get("image_count", "N/A"))
                    st.metric(label="Imagens sem Alt Text", value=results.get("images_sem_alt_text"), 
                              help="O Alt Text ajuda o Google a entender suas imagens. O ideal é que este número seja 0.")

                with col2:
                    st.metric(label="Links Internos", value=results.get("links_internos", "N/A"))
                    st.metric(label="Links Externos", value=results.get("links_externos", "N/A"))
                    st.metric(label="Dados Estruturados", value=results.get("dados_estruturados", "N/A"),
                              help="Ajuda o Google a entender o contexto da sua página (ex: se é um artigo, produto, etc.).")
                
                with col3:
                    st.metric(label="Contagem de H1", value=results.get("h1_count", "N/A"), 
                              help="O ideal é ter apenas 1 tag H1 por página.")
                    st.metric(label="Comprimento do Título", value=results.get("title_length", "N/A"),
                              help="O ideal é entre 50 e 60 caracteres.")
                    st.metric(label="Comprimento da Meta Desc.", value=results.get("meta_description_length", "N/A"),
                              help="O ideal é entre 120 e 155 caracteres.")

                # Expander para detalhes técnicos
                with st.expander("Ver todos os dados técnicos coletados"):
                    st.json(results)

                # --- Geração e Exibição das Recomendações da IA ---
                st.subheader("🤖 Análise e Recomendações (via Gemini)")
                with st.spinner("A IA está pensando e gerando as melhores recomendações para você..."):
                    gemini_sug = generate_gemini_recommendations(results, url)
                    st.markdown(gemini_sug)

            except ConnectionError as e:
                st.error(f"Erro de Conexão: {e}")
            except Exception as e:
                st.error(f"Opa, um erro inesperado ocorreu: {e}")
