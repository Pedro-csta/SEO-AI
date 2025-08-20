import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
import pandas as pd
from urllib.parse import urljoin, urlparse
import time

# ========== CONFIGURAÇÃO DAS APIS (Inalterado) ==========
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_configured = False
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_configured = True
    except Exception as e:
        st.error(f"Erro ao configurar a API do Gemini: {e}")
else:
    st.warning("Chave da API Gemini (GEMINI_API_KEY) não encontrada...", icon="⚠️")

PSI_API_KEY = os.getenv("PSI_API_KEY")


# ========== FUNÇÕES DE COLETA DE DADOS (Inalteradas) ==========
# As funções get_pagespeed_insights, check_broken_links e onpage_checks
# continuam as mesmas da versão anterior.

def get_pagespeed_insights(url_to_check: str) -> dict:
    # (Código da função inalterado)
    if not PSI_API_KEY: return {}
    insights_data = {"redirected": False}
    strategies = ["mobile", "desktop"]
    for strategy in strategies:
        api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url_to_check}&strategy={strategy}&key={PSI_API_KEY}"
        try:
            response = requests.get(api_url, timeout=60)
            response.raise_for_status()
            data = response.json()
            final_url = data.get('lighthouseResult', {}).get('finalUrl', url_to_check)
            insights_data['final_url'] = final_url
            if url_to_check != final_url: insights_data['redirected'] = True
            categories = data.get('lighthouseResult', {}).get('categories', {})
            scores = {f"psi_{category.replace('-', '_')}": int(categories.get(category, {}).get('score', 0) * 100) for category in ['performance', 'accessibility', 'best-practices', 'seo']}
            insights_data[strategy] = scores
        except requests.exceptions.RequestException:
            insights_data[strategy] = {}
    return insights_data

def onpage_checks(url):
    # (Código da função inalterado, apenas o retorno foi simplificado)
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException: return None # Retorna None em caso de erro
    soup = BeautifulSoup(response.text, "html.parser")
    checks = {}
    title_tag = soup.title
    checks["title"] = title_tag.string.strip() if title_tag else "N/A"
    checks["title_length"] = len(checks["title"])
    meta_desc = soup.find("meta", attrs={"name": "description"})
    checks["meta_description"] = meta_desc["content"].strip() if meta_desc and meta_desc.get("content") else "N/A"
    checks["h1_count"] = len(soup.find_all("h1"))
    all_links = soup.find_all("a", href=True)
    valid_links = [a['href'] for a in all_links if a['href'] and not a['href'].startswith(('#', 'tel:', 'mailto:'))]
    internal_links = [link for link in valid_links if url in link or link.startswith('/')]
    checks["links_internos"] = len(internal_links)
    checks["image_count"] = len(soup.find_all("img"))
    body_text = soup.find("body").get_text(separator=" ", strip=True) if soup.find("body") else ""
    checks["word_count"] = len(body_text.split())
    return checks

# ========== NOVA FUNÇÃO DE IA ESTRATEGISTA ==========

def generate_competitive_analysis(df_competitivo, url_principal):
    """Gera uma análise competitiva estratégica usando Gemini."""
    if not gemini_configured:
        return "Análise por IA desabilitada. Chave da API Gemini não configurada."
    
    # Converte o DataFrame para Markdown, um formato que a IA lê muito bem
    dados_markdown = df_competitivo.to_markdown(index=False)
    
    prompt = f"""
    Você é um estrategista de SEO e BI (Business Intelligence) de elite. Sua missão é analisar os dados da tabela abaixo, que compara o site principal com seus concorrentes, e gerar um relatório estratégico.

    **Site Principal para Análise:** {url_principal}

    **Tabela de Dados Comparativos:**
    ```
    {dados_markdown}
    ```

    **Seu Relatório Estratégico:**
    Com base exclusivamente nos dados da tabela, forneça a seguinte análise em português do Brasil, usando formatação Markdown:

    1.  **## 📊 Resumo Executivo**
        Forneça um parágrafo conciso destacando quem está na liderança geral (considerando performance e conteúdo) e qual o principal desafio para o site principal.

    2.  **## ✅ Vantagens Competitivas (Seu Site)**
        Aponte 2 a 3 áreas onde o site principal (`{url_principal}`) está objetivamente melhor que os concorrentes, de acordo com os dados.

    3.  **## 🎯 Oportunidades Críticas (Seu Site)**
        Aponte as 2 ou 3 maiores fraquezas ou lacunas do site principal em relação aos concorrentes, baseando-se nos maiores diferenciais negativos da tabela.

    4.  **## 📈 Plano de Ação Estratégico**
        Forneça uma lista de 3 ações concretas e priorizadas que o proprietário do site principal deve tomar para diminuir as fraquezas e superar a concorrência. As ações devem ser diretamente relacionadas aos dados (ex: "Aumentar o conteúdo da página X para perto de Y palavras, como os concorrentes A e B", ou "Focar em otimização de performance mobile, pois o score de Z é muito inferior à média de W").
    """
    
    try:
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        gemini_resp = gemini_model.generate_content(prompt)
        return gemini_resp.text
    except Exception as e:
        return f"Ocorreu um erro ao gerar a análise da IA: {e}"


# ========== NOVA INTERFACE STREAMLIT COM ANÁLISE COMPETITIVA ==========
st.set_page_config(page_title="SEO AI Strategist", page_icon="🔭", layout="wide")

st.title("🔭 SEO AI Strategist")
st.markdown("Deixe de auditar. Comece a competir. Analise seu site contra seus concorrentes e obtenha um plano de ação estratégico com IA.")

# --- Nova UI para Múltiplas URLs ---
st.subheader("1. Insira os Competidores")
url_principal = st.text_input("Insira a URL do SEU site:", key="url_principal")
competidores_raw = st.text_area("Insira até 3 URLs de CONCORRENTES (uma por linha):", key="url_competidores", height=100)

# --- Lógica Principal ---
if st.button("🛰️ Gerar Análise Competitiva", type="primary"):
    # Limpa e valida as URLs
    urls_principais_limpas = [url.strip() for url in url_principal.splitlines() if url.strip()]
    urls_competidores_limpas = [url.strip() for url in competidores_raw.splitlines() if url.strip()]
    
    if not urls_principais_limpas:
        st.error("Por favor, insira a URL do seu site.")
    else:
        url_principal_final = urls_principais_limpas[0]
        todas_as_urls = [url_principal_final] + urls_competidores_limpas
        
        todos_os_resultados = []
        
        # --- Motor de Análise Múltipla ---
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, url in enumerate(todas_as_urls):
            status_text.info(f"Analisando {i+1}/{len(todas_as_urls)}: {url}...")
            
            onpage_data = onpage_checks(url)
            if onpage_data is None:
                st.warning(f"Não foi possível analisar {url}. Pulando para o próximo.", icon="⚠️")
                continue

            psi_data = get_pagespeed_insights(url)
            
            # Combina todos os resultados em um único dicionário
            resultado_final = {
                "Site": urlparse(url).netloc, # Nome mais amigável
                "URL": url,
                **onpage_data,
                "Performance Mobile": psi_data.get('mobile', {}).get('psi_performance', 0),
                "SEO Mobile": psi_data.get('mobile', {}).get('psi_seo', 0),
                "Performance Desktop": psi_data.get('desktop', {}).get('psi_performance', 0),
            }
            todos_os_resultados.append(resultado_final)
            progress_bar.progress((i + 1) / len(todas_as_urls))

        status_text.success("Todas as análises foram concluídas!")
        
        if todos_os_resultados:
            # --- Painel Comparativo ---
            st.divider()
            st.subheader("2. Painel Comparativo de Métricas")
            
            df_comparativo = pd.DataFrame(todos_os_resultados)
            
            # Seleciona as colunas mais importantes para a tabela
            colunas_display = [
                "Site", "word_count", "Performance Mobile", "Performance Desktop", 
                "links_internos", "image_count", "title_length", "h1_count"
            ]
            # Renomeia para melhor leitura
            df_display = df_comparativo[colunas_display].rename(columns={
                "word_count": "Palavras", "links_internos": "Links Internos", "image_count": "Imagens",
                "title_length": "Tam. Título", "h1_count": "Nº de H1s"
            })
            
            st.dataframe(df_display, use_container_width=True)
            
            # --- Gráficos Comparativos ---
            st.write("#### Gráficos de Comparação")
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Performance Mobile**")
                st.bar_chart(df_display.set_index("Site")["Performance Mobile"])
            with col2:
                st.write("**Contagem de Palavras**")
                st.bar_chart(df_display.set_index("Site")["Palavras"])

            # --- Análise Estratégica com IA ---
            st.divider()
            st.subheader("3. Análise Estratégica (via Gemini)")
            with st.spinner("A IA está analisando o cenário competitivo e gerando seu plano de ação..."):
                analise_ia = generate_competitive_analysis(df_display, url_principal_final)
                st.markdown(analise_ia)
