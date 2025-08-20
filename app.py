import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
import pandas as pd
from urllib.parse import urljoin
import time

# ========== CONFIGURAÇÃO DAS APIS ==========

# Chave da API do Google Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_configured = False
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_configured = True
    except Exception as e:
        st.error(f"Erro ao configurar a API do Gemini: {e}")
else:
    st.warning("Chave da API Gemini (GEMINI_API_KEY) não encontrada. A análise por IA está desabilitada.", icon="⚠️")

# Chave da API do Google PageSpeed Insights
PSI_API_KEY = os.getenv("PSI_API_KEY")


# ========== FUNÇÕES DE AUDITORIA (PILAR 2) ==========

def get_pagespeed_insights(url_to_check: str) -> dict:
    """Busca dados do Google PageSpeed Insights e detecta redirecionamentos."""
    if not PSI_API_KEY:
        st.warning("Chave da API do PageSpeed (PSI_API_KEY) não configurada. Análise de performance pulada.", icon="⚠️")
        return {}

    insights_data = {"redirected": False} # Iniciamos o dicionário
    strategies = ["mobile", "desktop"]
    
    for strategy in strategies:
        api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url_to_check}&strategy={strategy}&key={PSI_API_KEY}"
        try:
            # AJUSTE: Timeout aumentado para 60 segundos.
            response = requests.get(api_url, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            # AJUSTE: Captura a URL final para detectar redirecionamentos.
            final_url = data.get('lighthouseResult', {}).get('finalUrl', url_to_check)
            insights_data['final_url'] = final_url
            
            if url_to_check != final_url:
                insights_data['redirected'] = True
            
            categories = data.get('lighthouseResult', {}).get('categories', {})
            scores = {category: int(categories.get(category, {}).get('score', 0) * 100) for category in ['performance', 'accessibility', 'best-practices', 'seo']}
            insights_data[strategy] = scores

        except requests.exceptions.ReadTimeout:
            st.error(f"A análise do PageSpeed para '{strategy}' demorou demais e excedeu 60s. Isso pode ocorrer se o site for muito lento.", icon="⏱️")
            insights_data[strategy] = {}
        except requests.exceptions.RequestException as e:
            st.error(f"Erro ao contatar a API do PageSpeed para a estratégia '{strategy}': {e}")
            insights_data[strategy] = {}
            
    return insights_data

def check_broken_links(base_url: str, internal_links: list) -> list:
    """Verifica uma lista de links internos e retorna os que estão quebrados."""
    broken_links = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    for link in internal_links:
        full_url = urljoin(base_url, link)
        try:
            response = requests.head(full_url, headers=headers, timeout=5, allow_redirects=True)
            if response.status_code >= 400:
                broken_links.append({"url": full_url, "status": response.status_code})
        except requests.RequestException:
            broken_links.append({"url": full_url, "status": "Erro de Conexão"})
        time.sleep(0.1)
    return broken_links


# ========== FUNÇÕES DE AUDITORIA (PRINCIPAL) ==========

def onpage_checks(url):
    """Executa a auditoria on-page e retorna os dados e a lista de links internos."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Não foi possível acessar a URL. Erro: {e}")
    soup = BeautifulSoup(response.text, "html.parser")
    checks = {}
    title_tag = soup.title
    checks["title"] = title_tag.string.strip() if title_tag else "❌ Ausente"
    checks["title_length"] = len(checks["title"]) if title_tag else 0
    meta_desc = soup.find("meta", attrs={"name": "description"})
    checks["meta_description"] = meta_desc["content"].strip() if meta_desc and meta_desc.get("content") else "❌ Ausente"
    checks["meta_description_length"] = len(checks["meta_description"]) if meta_desc and meta_desc.get("content") else 0
    h1s = soup.find_all("h1")
    checks["h1_count"] = len(h1s)
    checks["h1_text"] = h1s[0].get_text(strip=True) if h1s else "❌ Ausente"
    canonical = soup.find("link", rel="canonical")
    checks["canonical"] = canonical["href"] if canonical else "❌ Ausente"
    robots = soup.find("meta", attrs={"name": "robots"})
    checks["robots_tag"] = robots["content"] if robots else "❌ Ausente"
    structured_data = soup.find("script", type="application/ld+json")
    checks["dados_estruturados"] = "✅ Presente" if structured_data else "❌ Ausente"
    all_links = soup.find_all("a", href=True)
    valid_links = [a['href'] for a in all_links if a['href'] and not a['href'].startswith(('#', 'tel:', 'mailto:'))]
    internal_links = [link for link in valid_links if url in link or link.startswith('/')]
    external_links = [link for link in valid_links if link.startswith('http') and url not in link]
    checks["links_internos"] = len(internal_links)
    checks["links_externos"] = len(external_links)
    images = soup.find_all("img")
    checks["image_count"] = len(images)
    images_sem_alt = [img for img in images if not img.get("alt", "").strip()]
    checks["images_sem_alt_text"] = len(images_sem_alt)
    body_text = soup.find("body").get_text(separator=" ", strip=True) if soup.find("body") else ""
    checks["word_count"] = len(body_text.split())
    return checks, internal_links

def generate_gemini_recommendations(checks, url):
    """Gera recomendações de SEO usando Google Gemini."""
    if not gemini_configured:
        return "A análise por IA está desabilitada pois a chave da API do Gemini não foi configurada corretamente.", ""
        
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
    
    try:
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        gemini_resp = gemini_model.generate_content(prompt)
        return prompt, gemini_resp.text
    except Exception as e:
        st.error(f"Erro ao chamar a API do Gemini: {e}")
        return prompt, "Houve um erro ao gerar a análise da IA. Verifique as configurações da sua API."


# ========== INTERFACE STREAMLIT ==========
st.set_page_config(page_title="SEO AI Auditor Pro", page_icon="🚀", layout="wide")

st.title("🚀 SEO AI Auditor Pro")
st.markdown("Análise de SEO On-Page, Performance e Experiência do Usuário com a inteligência do Google Gemini e PageSpeed Insights.")

url = st.text_input("Insira a URL completa para auditoria:", key="url_input")

if st.button("🛰️ Rodar Auditoria Completa", type="primary"):
    if not url.startswith("http"):
        st.error("Por favor, insira uma URL válida (inclua http:// ou https://).")
    else:
        try:
            with st.spinner("Etapa 1/3: Realizando auditoria On-Page..."):
                onpage_results, internal_links_list = onpage_checks(url)
            st.success("Auditoria On-Page concluída!")

            with st.spinner("Etapa 2/3: Medindo performance com Google PageSpeed e verificando links..."):
                psi_results = get_pagespeed_insights(url)
                broken_links_list = check_broken_links(url, internal_links_list)
            st.success("Análises de Performance e Links concluídas!")
            
            st.divider()
            
            if psi_results:
                st.subheader("🚀 Análise de Performance e Experiência (Google PageSpeed)")
                
                # AJUSTE: Aviso inteligente de redirecionamento.
                if psi_results.get('redirected'):
                    st.info(f"""
                    **Aviso de Redirecionamento:** A URL que você inseriu foi redirecionada para: 
                    `{psi_results.get('final_url')}`. 
                    Isso é comum, mas pode ser a causa dos scores de Acessibilidade, Melhores Práticas e SEO estarem zerados, 
                    pois o Google pode não executar todas as auditorias após um redirecionamento.
                    """, icon="↪️")
                
                col_mob, col_desk = st.columns(2)
                with col_mob:
                    st.markdown("#### Mobile")
                    st.metric("Performance", f"{psi_results.get('mobile', {}).get('performance', 'N/A')}")
                    st.metric("Acessibilidade", f"{psi_results.get('mobile', {}).get('accessibility', 'N/A')}")
                    st.metric("Melhores Práticas", f"{psi_results.get('mobile', {}).get('best-practices', 'N/A')}")
                    st.metric("SEO", f"{psi_results.get('mobile', {}).get('seo', 'N/A')}")
                with col_desk:
                    st.markdown("#### Desktop")
                    st.metric("Performance", f"{psi_results.get('desktop', {}).get('performance', 'N/A')}")
                    st.metric("Acessibilidade", f"{psi_results.get('desktop', {}).get('accessibility', 'N/A')}")
                    st.metric("Melhores Práticas", f"{psi_results.get('desktop', {}).get('best-practices', 'N/A')}")
                    st.metric("SEO", f"{psi_results.get('desktop', {}).get('seo', 'N/A')}")

            st.subheader("🔗 Verificação de Links Quebrados")
            if not broken_links_list:
                st.success("Ótima notícia! Nenhum link interno quebrado foi encontrado.")
            else:
                st.warning(f"Atenção! Encontramos {len(broken_links_list)} link(s) quebrado(s):")
                df_broken = pd.DataFrame(broken_links_list)
                st.table(df_broken)

            st.subheader("📊 Painel de Auditoria On-Page")
            df = pd.DataFrame({"Elemento": ["Título", "Meta Description", "H1 (Primeiro)"],"Conteúdo": [onpage_results.get("title", ""), onpage_results.get("meta_description", ""), onpage_results.get("h1_text", "")]})
            st.table(df)
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Palavras", onpage_results.get("word_count")); st.metric("Imagens", onpage_results.get("image_count")); st.metric("Imagens sem Alt", onpage_results.get("images_sem_alt_text"))
            with col2: st.metric("Links Internos", onpage_results.get("links_internos")); st.metric("Links Externos", onpage_results.get("links_externos")); st.metric("Dados Estruturados", onpage_results.get("dados_estruturados"))
            with col3: st.metric("Contagem de H1", onpage_results.get("h1_count")); st.metric("Tamanho Título", onpage_results.get("title_length")); st.metric("Tamanho Meta Desc.", onpage_results.get("meta_description_length"))
            with st.expander("Ver todos os dados técnicos On-Page"): st.json(onpage_results)

            st.divider()
            st.subheader("🤖 Análise e Recomendações (via Gemini)")
            with st.spinner("Etapa 3/3: A IA está processando todos os dados para criar as melhores recomendações..."):
                prompt_enviado, gemini_sug = generate_gemini_recommendations(onpage_results, url)
                
                # AJUSTE: Expander para depuração do prompt.
                with st.expander("Clique para ver o prompt exato enviado para a IA"):
                    st.code(prompt_enviado, language="markdown")
                
                st.markdown(gemini_sug)

        except ConnectionError as e:
            st.error(f"Erro de Conexão: {e}")
        except Exception as e:
            st.error(f"Opa, um erro inesperado ocorreu: {e}")
            st.exception(e)
