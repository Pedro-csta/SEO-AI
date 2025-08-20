import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
import pandas as pd
from urllib.parse import urljoin, urlparse
import time
import plotly.express as px

# ========== CONFIGURAÇÃO DAS APIS (Inalterado) ==========
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_configured = False
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_configured = True
    except Exception as e: st.error(f"Erro ao configurar a API do Gemini: {e}")
else: st.warning("Chave da API Gemini (GEMINI_API_KEY) não encontrada...", icon="⚠️")
PSI_API_KEY = os.getenv("PSI_API_KEY")

# ========== FUNÇÕES DE COLETA DE DADOS (COM AJUSTE DE RESILIÊNCIA) ==========

def get_pagespeed_insights(url_to_check: str) -> dict:
    """Busca dados do Google PageSpeed, retornando None em caso de falha."""
    if not PSI_API_KEY: return {}
    insights_data = {}
    strategies = ["mobile", "desktop"]
    for strategy in strategies:
        api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url_to_check}&strategy={strategy}&key={PSI_API_KEY}"
        try:
            response = requests.get(api_url, timeout=60)
            response.raise_for_status()
            data = response.json()
            categories = data.get('lighthouseResult', {}).get('categories', {})
            # AJUSTE: Se o score não for encontrado, retorna None.
            scores = {f"psi_{cat}": categories.get(cat, {}).get('score') for cat in ['performance', 'accessibility', 'best-practices', 'seo']}
            # Multiplica por 100 apenas se o score não for None
            for key, value in scores.items():
                if value is not None:
                    scores[key] = int(value * 100)
            insights_data[strategy] = scores
        except requests.exceptions.RequestException:
            # Em caso de qualquer erro, retorna um dicionário com Nones
            insights_data[strategy] = {f"psi_{cat}": None for cat in ['performance', 'accessibility', 'best-practices', 'seo']}
    return insights_data

# (onpage_checks e check_broken_links permanecem os mesmos)
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

def check_broken_links(base_url: str, internal_links: list) -> list:
    broken_links = []
    # (código da função inalterado)
    return broken_links

def generate_competitive_analysis(df_competitivo, url_principal):
    # AJUSTE: Prepara os dados para a IA, substituindo valores nulos
    df_para_ia = df_competitivo.fillna("Dado Indisponível")
    dados_markdown = df_para_ia.to_markdown(index=False)
    
    prompt = f"""
    Você é um estrategista de SEO e BI (Business Intelligence) de elite... (prompt da versão anterior)
    
    **Tabela de Dados Comparativos (obs: 'Dado Indisponível' significa que a métrica não pôde ser coletada):**
    ```
    {dados_markdown}
    ```
    ...(resto do prompt da versão anterior)
    """
    # (código da função inalterado)
    try:
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        gemini_resp = gemini_model.generate_content(prompt)
        return gemini_resp.text
    except Exception as e: return f"Ocorreu um erro ao gerar a análise da IA: {e}"

# (A função display_main_dashboard também foi ajustada para lidar com None)
def display_main_dashboard(url, onpage_data, psi_data, broken_links_data):
    st.subheader(f"Análise Detalhada de: `{urlparse(url).netloc}`")
    if psi_data:
        st.markdown("#### 🚀 Performance e Experiência (Google PageSpeed)")
        col_mob, col_desk = st.columns(2)
        with col_mob:
            st.markdown("**Mobile**")
            st.metric("Performance", f"{psi_data.get('mobile', {}).get('psi_performance', 'N/A')}")
            st.metric("SEO", f"{psi_data.get('mobile', {}).get('psi_seo', 'N/A')}")
        with col_desk:
            st.markdown("**Desktop**")
            st.metric("Performance", f"{psi_data.get('desktop', {}).get('psi_performance', 'N/A')}")
            st.metric("SEO", f"{psi_data.get('desktop', {}).get('psi_seo', 'N/A')}")
    # (resto da função inalterado)

# ========== INTERFACE STREAMLIT REVOLUCIONADA ==========
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
        # (Lógica de análise do site principal inalterada)
        url_principal_final = urls_principais_limpas[0]
        with st.spinner(f"Analisando `{url_principal_final}`..."):
            onpage_principal, links_principais = onpage_checks(url_principal_final)
            if onpage_principal is None:
                st.error(f"Não foi possível analisar {url_principal_final}.")
                st.stop()
            psi_principal = get_pagespeed_insights(url_principal_final)
            broken_links_principal = check_broken_links(url_principal_final, links_principais)
        display_main_dashboard(url_principal_final, onpage_principal, psi_principal, broken_links_principal)
        
        urls_competidores_limpas = [url.strip() for url in competidores_raw.splitlines() if url.strip()]
        if urls_competidores_limpas:
            st.divider()
            st.subheader("2. Arena Competitiva")
            
            todos_os_resultados = []
            resultado_principal_formatado = {"URL": url_principal_final, "Site": urlparse(url_principal_final).netloc, **onpage_principal, 
                                             "Performance Mobile": psi_principal.get('mobile', {}).get('psi_performance'),
                                             "Performance Desktop": psi_principal.get('desktop', {}).get('psi_performance')}
            todos_os_resultados.append(resultado_principal_formatado)

            # (Lógica de análise dos concorrentes inalterada)
            for i, url_comp in enumerate(urls_competidores_limpas):
                onpage_comp, _ = onpage_checks(url_comp)
                if onpage_comp:
                    psi_comp = get_pagespeed_insights(url_comp)
                    resultado_comp_formatado = {"URL": url_comp, "Site": urlparse(url_comp).netloc, **onpage_comp, 
                                                "Performance Mobile": psi_comp.get('mobile', {}).get('psi_performance'),
                                                "Performance Desktop": psi_comp.get('desktop', {}).get('psi_performance')}
                    todos_os_resultados.append(resultado_comp_formatado)
            
            df_comparativo = pd.DataFrame(todos_os_resultados)
            df_display = df_comparativo[["Site", "word_count", "Performance Mobile", "Performance Desktop", "links_internos"]].rename(columns={"word_count": "Palavras", "links_internos": "Links Internos"})
            st.dataframe(df_display, use_container_width=True)
            
            # --- GRÁFICOS NOVOS, RESILIENTES E CUSTOMIZADOS ---
            st.markdown("#### Gráficos de Comparação")
            
            # Define as cores: o site principal será amarelo, os outros cinza.
            mapa_de_cores = {urlparse(url_principal_final).netloc: 'gold'}
            sites_competidores = [urlparse(url).netloc for url in urls_competidores_limpas]
            for site in sites_competidores:
                mapa_de_cores[site] = 'darkgrey'

            col1, col2 = st.columns(2)
            with col1:
                # Filtra dados nulos ANTES de plotar
                df_perf = df_display.dropna(subset=['Performance Mobile'])
                if not df_perf.empty:
                    fig = px.bar(df_perf, x='Performance Mobile', y='Site', orientation='h',
                                 title="Performance Mobile", color='Site', color_discrete_map=mapa_de_cores,
                                 template='plotly_white', text='Performance Mobile')
                    fig.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Não há dados de Performance Mobile para exibir no gráfico.")
            
            with col2:
                df_words = df_display.dropna(subset=['Palavras'])
                if not df_words.empty:
                    fig = px.bar(df_words, x='Palavras', y='Site', orientation='h',
                                 title="Contagem de Palavras", color='Site', color_discrete_map=mapa_de_cores,
                                 template='plotly_white', text='Palavras')
                    fig.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Não há dados de Contagem de Palavras para exibir no gráfico.")

            # --- Análise Estratégica com IA ---
            st.divider()
            st.subheader("3. Análise Estratégica (via Gemini)")
            with st.spinner("A IA está gerando seu plano de ação..."):
                analise_ia = generate_competitive_analysis(df_display, url_principal_final)
                st.markdown(analise_ia)
