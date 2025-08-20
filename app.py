import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
import pandas as pd
from urllib.parse import urljoin, urlparse
import time
import plotly.express as px # Importamos o Plotly

# ========== CONFIGURAÇÃO DAS APIS (Inalterado) ==========
# (O código de configuração das APIs permanece o mesmo)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_configured = False
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_configured = True
    except Exception as e: st.error(f"Erro ao configurar a API do Gemini: {e}")
else: st.warning("Chave da API Gemini (GEMINI_API_KEY) não encontrada...", icon="⚠️")
PSI_API_KEY = os.getenv("PSI_API_KEY")

# ========== FUNÇÕES DE COLETA DE DADOS (Inalteradas) ==========
# (As funções get_pagespeed_insights, onpage_checks, etc. permanecem as mesmas)
def get_pagespeed_insights(url_to_check: str) -> dict:
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
        except requests.exceptions.RequestException: insights_data[strategy] = {}
    return insights_data

def check_broken_links(base_url: str, internal_links: list) -> list:
    broken_links = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for link in internal_links:
        full_url = urljoin(base_url, link)
        try:
            response = requests.head(full_url, headers=headers, timeout=5, allow_redirects=True)
            if response.status_code >= 400: broken_links.append({"url": full_url, "status": response.status_code})
        except requests.RequestException: broken_links.append({"url": full_url, "status": "Erro de Conexão"})
        time.sleep(0.1)
    return broken_links

def onpage_checks(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException: return None, []
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
    internal_links = [link for link in valid_links if urlparse(url).netloc in link or link.startswith('/')]
    checks["links_internos"] = len(internal_links)
    checks["image_count"] = len(soup.find_all("img"))
    body_text = soup.find("body").get_text(separator=" ", strip=True) if soup.find("body") else ""
    checks["word_count"] = len(body_text.split())
    return checks, internal_links

def generate_competitive_analysis(df_competitivo, url_principal):
    # (Função da IA inalterada)
    if not gemini_configured: return "Análise por IA desabilitada."
    dados_markdown = df_competitivo.to_markdown(index=False)
    prompt = f"""
    Você é um estrategista de SEO e BI (Business Intelligence) de elite... (prompt completo da versão anterior)
    """
    try:
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        gemini_resp = gemini_model.generate_content(prompt)
        return gemini_resp.text
    except Exception as e: return f"Ocorreu um erro ao gerar a análise da IA: {e}"

# ========== NOVA FUNÇÃO PARA EXIBIR O PAINEL PRINCIPAL ==========

def display_main_dashboard(url, onpage_data, psi_data, broken_links_data):
    """Função dedicada a exibir o painel de análise do site principal."""
    st.subheader(f"Análise Detalhada de: `{urlparse(url).netloc}`")
    
    # PAINEL DE PERFORMANCE
    if psi_data:
        st.markdown("#### 🚀 Performance e Experiência (Google PageSpeed)")
        if psi_data.get('redirected'):
            st.info(f"Aviso: A URL foi redirecionada para: `{psi_data.get('final_url')}`.", icon="↪️")
        col_mob, col_desk = st.columns(2)
        with col_mob:
            st.markdown("**Mobile**")
            st.metric("Performance", f"{psi_data.get('mobile', {}).get('psi_performance', 'N/A')}")
            st.metric("SEO", f"{psi_data.get('mobile', {}).get('psi_seo', 'N/A')}")
        with col_desk:
            st.markdown("**Desktop**")
            st.metric("Performance", f"{psi_data.get('desktop', {}).get('psi_performance', 'N/A')}")
            st.metric("SEO", f"{psi_data.get('desktop', {}).get('psi_seo', 'N/A')}")

    # PAINEL ON-PAGE
    st.markdown("#### 📊 Métricas On-Page")
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Palavras", onpage_data.get("word_count"))
    with col2: st.metric("Imagens", onpage_data.get("image_count"))
    with col3: st.metric("Links Internos", onpage_data.get("links_internos"))

    # PAINEL DE LINKS QUEBRADOS
    st.markdown("#### 🔗 Links Quebrados")
    if not broken_links_data:
        st.success("Nenhum link interno quebrado foi encontrado.")
    else:
        st.warning(f"Encontrados {len(broken_links_data)} link(s) quebrado(s):")
        st.json([link['url'] for link in broken_links_data])


# ========== INTERFACE STREAMLIT REESTRUTURADA ==========
st.set_page_config(page_title="SEO AI Strategist", page_icon="🔭", layout="wide")
st.title("🔭 SEO AI Strategist")
st.markdown("Analise seu site, compare com a concorrência e obtenha um plano de ação estratégico com IA.")

st.subheader("1. Insira as URLs para Análise")
url_principal = st.text_input("Insira a URL do SEU site:", key="url_principal")
competidores_raw = st.text_area("Opcional: Insira até 3 URLs de CONCORRENTES (uma por linha):", key="url_competidores", height=100)

if st.button("🛰️ Iniciar Análise", type="primary"):
    urls_principais_limpas = [url.strip() for url in url_principal.splitlines() if url.strip()]
    if not urls_principais_limpas:
        st.error("Por favor, insira a URL do seu site.")
    else:
        url_principal_final = urls_principais_limpas[0]
        
        # --- ETAPA 1: ANÁLISE COMPLETA DO SITE PRINCIPAL ---
        with st.spinner(f"Fazendo um raio-x completo em `{url_principal_final}`..."):
            onpage_principal, links_principais = onpage_checks(url_principal_final)
            if onpage_principal is None:
                st.error(f"Não foi possível analisar {url_principal_final}. Verifique a URL e tente novamente.")
            else:
                psi_principal = get_pagespeed_insights(url_principal_final)
                broken_links_principal = check_broken_links(url_principal_final, links_principais)
        
        # --- ETAPA 2: EXIBIR O PAINEL PRINCIPAL ---
        st.divider()
        display_main_dashboard(url_principal_final, onpage_principal, psi_principal, broken_links_principal)
        
        # --- ETAPA 3: ANÁLISE DOS CONCORRENTES (SE HOUVER) ---
        urls_competidores_limpas = [url.strip() for url in competidores_raw.splitlines() if url.strip()]
        if urls_competidores_limpas:
            st.divider()
            st.subheader("2. Arena Competitiva")
            
            todos_os_resultados = []
            
            # Adiciona os dados já coletados do site principal
            resultado_principal_formatado = {"URL": url_principal_final, "Site": urlparse(url_principal_final).netloc, **onpage_principal, "Performance Mobile": psi_principal.get('mobile', {}).get('psi_performance', 0)}
            todos_os_resultados.append(resultado_principal_formatado)

            # Loop para analisar concorrentes
            progress_bar = st.progress(0, text="Analisando concorrentes...")
            for i, url_comp in enumerate(urls_competidores_limpas):
                onpage_comp, _ = onpage_checks(url_comp)
                if onpage_comp:
                    psi_comp = get_pagespeed_insights(url_comp)
                    resultado_comp_formatado = {"URL": url_comp, "Site": urlparse(url_comp).netloc, **onpage_comp, "Performance Mobile": psi_comp.get('mobile', {}).get('psi_performance', 0)}
                    todos_os_resultados.append(resultado_comp_formatado)
                progress_bar.progress((i + 1) / len(urls_competidores_limpas))
            
            # --- Exibição da Comparação ---
            df_comparativo = pd.DataFrame(todos_os_resultados)
            df_display = df_comparativo[["Site", "word_count", "Performance Mobile", "links_internos", "image_count"]].rename(columns={"word_count": "Palavras", "links_internos": "Links Internos", "image_count": "Imagens"})
            st.dataframe(df_display, use_container_width=True)
            
            # --- NOVOS GRÁFICOS COM PLOTLY E CORES CUSTOMIZADAS ---
            st.markdown("#### Gráficos de Comparação")
            
            # Mapeamento de cores: o site principal será amarelo, os outros pretos
            cores = {urlparse(url_principal_final).netloc: 'gold'}
            cor_default = 'black'
            
            col1, col2 = st.columns(2)
            with col1:
                fig_perf = px.bar(df_display, x='Site', y='Performance Mobile', title="Performance Mobile",
                                  color='Site', color_discrete_map=cores, template='plotly_white')
                st.plotly_chart(fig_perf, use_container_width=True)
            with col2:
                fig_words = px.bar(df_display, x='Site', y='Palavras', title="Contagem de Palavras",
                                   color='Site', color_discrete_map=cores, color_discrete_sequence=[cor_default], template='plotly_white')
                st.plotly_chart(fig_words, use_container_width=True)

            # --- Análise Estratégica com IA ---
            st.divider()
            st.subheader("3. Análise Estratégica (via Gemini)")
            with st.spinner("A IA está gerando seu plano de ação..."):
                analise_ia = generate_competitive_analysis(df_display, url_principal_final)
                st.markdown(analise_ia)
