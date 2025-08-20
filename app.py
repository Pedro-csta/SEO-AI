import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
import pandas as pd
from urllib.parse import urljoin, urlparse
import time
import plotly.express as px
import plotly.graph_objects as go
import validators
import json
from collections import Counter
from datetime import datetime, timedelta
import re

# CONFIGURACAO DAS APIS
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

# VALIDACAO DE URL ROBUSTA
def validate_url(url):
    if not url:
        return False, "URL não pode estar vazia"
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    if not validators.url(url):
        return False, "Formato de URL inválido"
    
    parsed = urlparse(url)
    if parsed.scheme not in ['http', 'https']:
        return False, "URL deve usar protocolo HTTP ou HTTPS"
    
    if not parsed.netloc:
        return False, "URL deve conter um domínio válido"
    
    return True, url

# ANALISE DE TECNOLOGIAS
def detect_technologies(soup, response_headers, response_text):
    technologies = {
        'cms': [],
        'analytics': [],
        'javascript_frameworks': [],
        'css_frameworks': [],
        'web_servers': [],
        'cdn': [],
        'ecommerce': [],
        'security': []
    }
    
    headers = {}
    if hasattr(response_headers, 'items'):
        headers = dict(response_headers.items())
    elif isinstance(response_headers, dict):
        headers = response_headers
    
    html_content = str(soup).lower()
    
    # CMS Detection
    cms_patterns = {
        'WordPress': ['wp-content', 'wp-includes', '/wp-json/', 'wordpress'],
        'Drupal': ['drupal', 'sites/default/files', '/node/'],
        'Shopify': ['shopify', 'cdn.shopify.com', 'shopify-section'],
        'Magento': ['magento', '/skin/frontend/'],
        'WooCommerce': ['woocommerce', 'wc-'],
        'Webflow': ['webflow.com', 'webflow.io']
    }
    
    for cms, patterns in cms_patterns.items():
        if any(pattern in html_content for pattern in patterns):
            technologies['cms'].append(cms)
    
    # Analytics
    analytics_patterns = {
        'Google Analytics': ['google-analytics.com', 'gtag(', 'ga('],
        'Google Tag Manager': ['googletagmanager.com', 'gtm.js'],
        'Facebook Pixel': ['fbevents.js', 'facebook.net/tr', 'fbq('],
        'Hotjar': ['hotjar.com', 'hjid']
    }
    
    for tool, patterns in analytics_patterns.items():
        if any(pattern in html_content for pattern in patterns):
            technologies['analytics'].append(tool)
    
    # JavaScript Frameworks
    js_frameworks = {
        'React': ['react.js', '_react', 'react.production'],
        'Vue.js': ['vue.js', 'vue.min.js', '__vue__'],
        'Angular': ['angular.js', 'angular.min.js', 'ng-'],
        'jQuery': ['jquery', 'jquery.min.js'],
        'Bootstrap': ['bootstrap.css', 'bootstrap.js'],
        'Tailwind CSS': ['tailwindcss', 'tailwind.css']
    }
    
    for framework, patterns in js_frameworks.items():
        if any(pattern in html_content for pattern in patterns):
            cat = 'css_frameworks' if 'css' in framework.lower() or framework in ['Bootstrap', 'Tailwind CSS'] else 'javascript_frameworks'
            technologies[cat].append(framework)
    
    # Security Headers
    security_headers = {
        'Content Security Policy': 'content-security-policy',
        'HSTS': 'strict-transport-security',
        'X-Frame-Options': 'x-frame-options'
    }
    
    for security_name, header_name in security_headers.items():
        if header_name in [h.lower() for h in headers.keys()]:
            technologies['security'].append(security_name)
    
    # Remove duplicatas
    for category in technologies:
        technologies[category] = list(set(technologies[category]))
    
    return technologies

def create_tech_stack_visualization(technologies):
    categories = []
    counts = []
    details = []
    
    for category, techs in technologies.items():
        if techs:
            category_name = category.replace('_', ' ').title()
            categories.append(category_name)
            counts.append(len(techs))
            details.append(', '.join(techs))
    
    if not categories:
        return None
    
    fig = go.Figure(go.Bar(
        y=categories,
        x=counts,
        orientation='h',
        marker=dict(color='#3B82F6'),
        text=[f"{count} tecnologia{'s' if count > 1 else ''}" for count in counts],
        textposition='inside',
        hovertemplate='<b>%{y}</b><br>Tecnologias: %{customdata}<extra></extra>',
        customdata=details
    ))
    
    fig.update_layout(
        title="Stack Tecnológico Detectado",
        xaxis=dict(title="Número de Tecnologias"),
        height=400,
        margin=dict(l=150, r=50, t=50, b=50)
    )
    
    return fig

# ANALISE DE SEGURANCA
def analyze_security_headers(headers):
    security_score = 0
    security_details = {}
    
    important_headers = {
        'Content-Security-Policy': 25,
        'Strict-Transport-Security': 20,
        'X-Frame-Options': 15,
        'X-Content-Type-Options': 15,
        'X-XSS-Protection': 10
    }
    
    headers_lower = {k.lower(): v for k, v in headers.items()}
    
    for header, points in important_headers.items():
        header_lower = header.lower()
        if header_lower in headers_lower:
            security_score += points
            security_details[header] = 'Presente'
        else:
            security_details[header] = 'Ausente'
    
    return {
        'score': security_score,
        'details': security_details,
        'grade': 'A' if security_score >= 80 else 'B' if security_score >= 60 else 'C' if security_score >= 40 else 'D'
    }

# ANALISE DE ACESSIBILIDADE
def analyze_accessibility_basics(soup):
    accessibility_issues = []
    accessibility_score = 100
    
    # Verifica alt text em imagens
    images = soup.find_all('img')
    images_without_alt = [img for img in images if not img.get('alt')]
    if images_without_alt:
        accessibility_issues.append(f"{len(images_without_alt)} imagens sem alt text")
        accessibility_score -= min(30, len(images_without_alt) * 5)
    
    # Verifica H1
    h1s = soup.find_all('h1')
    if len(h1s) > 1:
        accessibility_issues.append(f"Múltiplos H1 ({len(h1s)}) encontrados")
        accessibility_score -= 10
    
    return {
        'score': max(0, accessibility_score),
        'issues': accessibility_issues,
        'grade': 'A' if accessibility_score >= 90 else 'B' if accessibility_score >= 70 else 'C' if accessibility_score >= 50 else 'D'
    }

# ANALISE DE DADOS ESTRUTURADOS
def analyze_structured_data(soup):
    structured_data = {
        "json_ld_count": 0,
        "schemas_found": [],
        "errors": []
    }
    
    json_scripts = soup.find_all("script", type="application/ld+json")
    structured_data["json_ld_count"] = len(json_scripts)
    
    for i, script in enumerate(json_scripts):
        try:
            data = json.loads(script.string.strip())
            schema_type = data.get("@type", "Unknown")
            structured_data["schemas_found"].append({
                "type": schema_type,
                "method": "JSON-LD",
                "valid": True
            })
        except json.JSONDecodeError as e:
            structured_data["errors"].append(f"JSON-LD inválido: {str(e)[:50]}")
    
    return structured_data

# GAUGE VISUAL
def create_seo_score_gauge(score, title="SEO Score"):
    if score is None or score == "N/A":
        score = 0
    try:
        score = float(score)
    except (ValueError, TypeError):
        score = 0
    
    if score >= 80:
        color = "green"
    elif score >= 60:
        color = "orange"
    else:
        color = "red"
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        title = {'text': title},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 30], 'color': 'lightgray'},
                {'range': [30, 60], 'color': 'lightyellow'},
                {'range': [60, 80], 'color': 'lightblue'},
                {'range': [80, 100], 'color': 'lightgreen'}
            ]
        }
    ))
    
    fig.update_layout(height=200, margin=dict(l=10, r=10, t=30, b=10))
    return fig

# CALCULO DO SCORE SEO
def calculate_overall_seo_score(onpage_data, psi_data, structured_data):
    if not onpage_data:
        return 0
    
    score = 0
    
    # Title (15 pontos)
    title_len = onpage_data.get('title_length', 0)
    if title_len == 0 or onpage_data.get('title') == 'N/A':
        score += 0
    elif 30 <= title_len <= 60:
        score += 15
    elif 20 <= title_len <= 80:
        score += 10
    else:
        score += 5
    
    # H1 (10 pontos)
    h1_count = onpage_data.get('h1_count', 0)
    if h1_count == 1:
        score += 10
    elif h1_count > 1:
        score += 5
    
    # Conteúdo (20 pontos)
    word_count = onpage_data.get('word_count', 0)
    if word_count >= 500:
        score += 20
    elif word_count >= 300:
        score += 15
    elif word_count >= 150:
        score += 10
    elif word_count > 0:
        score += 5
    
    # Performance (25 pontos)
    if psi_data and 'mobile' in psi_data and psi_data['mobile']:
        mobile_perf = psi_data['mobile'].get('psi_performance', 0)
        try:
            mobile_perf = float(mobile_perf)
            score += (mobile_perf / 100) * 25
        except (ValueError, TypeError):
            pass
    else:
        score += 10
    
    # Meta description (10 pontos)
    meta_len = onpage_data.get('meta_description_length', 0)
    if meta_len == 0 or onpage_data.get('meta_description') == 'N/A':
        score += 0
    elif 140 <= meta_len <= 160:
        score += 10
    elif 120 <= meta_len <= 180:
        score += 7
    else:
        score += 3
    
    # Links internos (5 pontos)
    if onpage_data.get('links_internos', 0) >= 5:
        score += 5
    elif onpage_data.get('links_internos', 0) >= 2:
        score += 3
    
    # Imagens (5 pontos)
    total_imgs = onpage_data.get('image_count', 0)
    imgs_sem_alt = onpage_data.get('images_sem_alt', 0)
    if total_imgs > 0:
        img_score = ((total_imgs - imgs_sem_alt) / total_imgs) * 5
        score += img_score
    
    # Dados estruturados (5 pontos)
    if structured_data and len(structured_data.get('schemas_found', [])) > 0:
        score += 5
    
    # Bonus por segurança (5 pontos)
    # Será adicionado na análise principal
    
    return min(round(score), 100)

# FUNCOES DE AUDITORIA
def get_pagespeed_insights(url_to_check: str) -> dict:
    if not PSI_API_KEY: 
        return {}
    
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
            
            if url_to_check != final_url: 
                insights_data['redirected'] = True
            
            categories = data.get('lighthouseResult', {}).get('categories', {})
            scores = {f"psi_{category.replace('-', '_')}": int(categories.get(category, {}).get('score', 0) * 100) for category in ['performance', 'accessibility', 'best-practices', 'seo']}
            insights_data[strategy] = scores
            
        except requests.exceptions.RequestException: 
            insights_data[strategy] = {}
    
    return insights_data

def check_broken_links(base_url: str, internal_links: list) -> list:
    broken_links = []
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for link in internal_links[:10]:
        full_url = urljoin(base_url, link)
        try:
            response = requests.head(full_url, headers=headers, timeout=5, allow_redirects=True)
            if response.status_code >= 400: 
                broken_links.append({"url": full_url, "status": response.status_code})
        except requests.RequestException: 
            broken_links.append({"url": full_url, "status": "Erro de Conexão"})
        time.sleep(0.1)
    
    return broken_links

def onpage_checks(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException: 
        return None, [], None, {}, {}, {}
    
    soup = BeautifulSoup(response.text, "html.parser")
    checks = {}
    
    title_tag = soup.title
    checks["title"] = title_tag.string.strip() if title_tag else "N/A"
    checks["title_length"] = len(checks["title"]) if title_tag else 0
    
    meta_desc = soup.find("meta", attrs={"name": "description"})
    checks["meta_description"] = meta_desc["content"].strip() if meta_desc and meta_desc.get("content") else "N/A"
    checks["meta_description_length"] = len(checks["meta_description"]) if meta_desc and meta_desc.get("content") else 0
    
    checks["h1_count"] = len(soup.find_all("h1"))
    
    all_links = soup.find_all("a", href=True)
    valid_links = [a['href'] for a in all_links if a['href'] and not a['href'].startswith(('#', 'tel:', 'mailto:'))]
    internal_links = [link for link in valid_links if urlparse(url).netloc in link or link.startswith('/')]
    checks["links_internos"] = len(internal_links)
    
    checks["image_count"] = len(soup.find_all("img"))
    
    images = soup.find_all("img")
    images_sem_alt = [img for img in images if not img.get("alt", "").strip()]
    checks["images_sem_alt"] = len(images_sem_alt)
    
    body_text = soup.find("body").get_text(separator=" ", strip=True) if soup.find("body") else ""
    checks["word_count"] = len(body_text.split())
    
    # Novas análises
    technologies = detect_technologies(soup, response.headers, response.text)
    security_analysis = analyze_security_headers(dict(response.headers))
    accessibility_analysis = analyze_accessibility_basics(soup)
    
    return checks, internal_links, soup, technologies, security_analysis, accessibility_analysis

# INTERFACE STREAMLIT
st.set_page_config(page_title="SEO AI Strategist Pro", page_icon="🔭", layout="wide")

# Sidebar
with st.sidebar:
    st.header("Configurações de Análise")
    
    deep_analysis = st.checkbox("Análise profunda", value=True)
    analyze_tech_stack = st.checkbox("Detectar tecnologias", value=True)
    analyze_security = st.checkbox("Análise de segurança", value=True)
    
    st.divider()
    st.markdown("### Métricas Ideais")
    st.info("""
    Title: 30-60 caracteres
    Meta Description: 150-160 caracteres
    H1: Apenas 1 por página
    Conteúdo: Mínimo 300 palavras
    Performance: Acima de 80
    """)

st.title("SEO AI Strategist Pro")
st.markdown("Análise avançada de SEO com IA e comparação competitiva.")

st.subheader("Análise Principal")
url_principal = st.text_input("Insira a URL do seu site:", placeholder="https://seusite.com.br")

# Validação
if url_principal:
    is_valid, validation_result = validate_url(url_principal)
    if not is_valid:
        st.error(f"Erro: {validation_result}")
    else:
        if validation_result != url_principal:
            st.info(f"URL corrigida para: {validation_result}")
            url_principal = validation_result

st.subheader("Análise Competitiva (Opcional)")
competidores_raw = st.text_area("URLs dos concorrentes (uma por linha):", height=100)

if st.button("Iniciar Análise Completa", type="primary"):
    if not url_principal:
        st.error("Por favor, insira a URL do seu site.")
    else:
        is_valid, url_principal = validate_url(url_principal)
        if not is_valid:
            st.error(f"URL inválida: {url_principal}")
            st.stop()
        
        # ANALISE PRINCIPAL
        with st.spinner(f"Analisando {urlparse(url_principal).netloc}..."):
            try:
                onpage_principal, links_principais, soup_principal, technologies_principal, security_principal, accessibility_principal = onpage_checks(url_principal)
                if onpage_principal is None:
                    st.error(f"Não foi possível analisar {url_principal}")
                    st.stop()
                
                structured_data = {}
                if deep_analysis:
                    structured_data = analyze_structured_data(soup_principal)
                
                psi_principal = get_pagespeed_insights(url_principal)
                broken_links_principal = check_broken_links(url_principal, links_principais)
                
            except Exception as e:
                st.error(f"Erro na análise: {str(e)}")
                st.stop()
        
        st.success("Análise principal concluída!")
        
        # DASHBOARD PRINCIPAL
        st.divider()
        st.subheader(f"Dashboard: {urlparse(url_principal).netloc}")
        
        # Calcula score com bonus de segurança
        overall_score = calculate_overall_seo_score(onpage_principal, psi_principal, structured_data)
        if security_principal and security_principal.get('score', 0) >= 60:
            overall_score = min(100, overall_score + 5)  # Bonus de segurança
        
        # SEÇÃO DE TECNOLOGIAS
        if technologies_principal and analyze_tech_stack:
            st.markdown("#### Stack Tecnológico")
            tech_fig = create_tech_stack_visualization(technologies_principal)
            if tech_fig:
                st.plotly_chart(tech_fig, use_container_width=True)
            
            with st.expander("Ver tecnologias detalhadas"):
                for category, techs in technologies_principal.items():
                    if techs:
                        st.write(f"**{category.replace('_', ' ').title()}:** {', '.join(techs)}")
        
        # SEÇÃO DE SEGURANÇA E ACESSIBILIDADE
        if analyze_security:
            col_sec, col_acc = st.columns(2)
            
            with col_sec:
                st.markdown("#### Análise de Segurança")
                if security_principal:
                    sec_score = security_principal.get('score', 0)
                    sec_grade = security_principal.get('grade', 'D')
                    
                    security_gauge = create_seo_score_gauge(sec_score, f"Segurança: {sec_grade}")
                    st.plotly_chart(security_gauge, use_container_width=True)
                    
                    with st.expander("Headers de segurança"):
                        for header, status in security_principal.get('details', {}).items():
                            st.write(f"{header}: {status}")
            
            with col_acc:
                st.markdown("#### Análise de Acessibilidade")
                if accessibility_principal:
                    acc_score = accessibility_principal.get('score', 0)
                    acc_grade = accessibility_principal.get('grade', 'D')
                    
                    accessibility_gauge = create_seo_score_gauge(acc_score, f"Acessibilidade: {acc_grade}")
                    st.plotly_chart(accessibility_gauge, use_container_width=True)
                    
                    issues = accessibility_principal.get('issues', [])
                    if issues:
                        with st.expander("Problemas de acessibilidade"):
                            for issue in issues:
                                st.write(f"• {issue}")
                    else:
                        st.success("Nenhum problema básico encontrado!")
        
        # MÉTRICAS PRINCIPAIS
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            fig_score = create_seo_score_gauge(overall_score, "Score Geral de SEO")
            st.plotly_chart(fig_score, use_container_width=True)
        
        with col2:
            st.metric("Palavras", onpage_principal.get("word_count", 0))
            st.metric("Imagens", onpage_principal.get("image_count", 0))
        
        with col3:
            st.metric("Links Internos", onpage_principal.get("links_internos", 0))
            st.metric("Imgs sem Alt", onpage_principal.get("images_sem_alt", 0))
        
        with col4:
            if psi_principal and 'mobile' in psi_principal:
                perf_mobile = psi_principal['mobile'].get('psi_performance', 0)
                st.metric("Performance Mobile", f"{perf_mobile}/100")
            else:
                st.metric("Performance Mobile", "N/A")
            
            if broken_links_principal:
                st.metric("Links Quebrados", len(broken_links_principal))
            else:
                st.metric("Links Quebrados", "0")
        
        # PERFORMANCE DETALHADA
        if psi_principal:
            st.markdown("#### Análise de Performance")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Mobile**")
                mobile_data = psi_principal.get('mobile', {})
                perf = mobile_data.get('psi_performance', 0)
                seo = mobile_data.get('psi_seo', 0)
                
                fig_mobile = create_seo_score_gauge(perf, "Performance Mobile")
                st.plotly_chart(fig_mobile, use_container_width=True)
                st.metric("SEO Score", f"{seo}/100")
            
            with col2:
                st.markdown("**Desktop**")
                desktop_data = psi_principal.get('desktop', {})
                perf_desk = desktop_data.get('psi_performance', 0)
                seo_desk = desktop_data.get('psi_seo', 0)
                
                fig_desktop = create_seo_score_gauge(perf_desk, "Performance Desktop")
                st.plotly_chart(fig_desktop, use_container_width=True)
                st.metric("SEO Score", f"{seo_desk}/100")
        
        # DADOS ESTRUTURADOS
        if deep_analysis and structured_data:
            st.markdown("#### Dados Estruturados")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Schemas JSON-LD", structured_data.get('json_ld_count', 0))
            with col2:
                total_schemas = len(structured_data.get('schemas_found', []))
                st.metric("Total de Schemas", total_schemas)
            with col3:
                if structured_data.get('errors'):
                    st.metric("Erros", len(structured_data.get('errors', [])))
                else:
                    st.metric("Erros", "0")
            
            if structured_data.get('schemas_found'):
                st.write("**Schemas detectados:**")
                for schema in structured_data['schemas_found']:
                    st.write(f"- {schema['type']} ({schema['method']})")
        
        # ANÁLISE COMPETITIVA
        urls_competidores_limpas = [url.strip() for url in competidores_raw.splitlines() if url.strip()][:3]
        
        if urls_competidores_limpas:
            st.divider()
            st.subheader("Comparação Competitiva")
            
            todos_os_resultados = []
            
            # Adiciona resultado principal
            resultado_principal = {
                "URL": url_principal, 
                "Site": urlparse(url_principal).netloc, 
                **onpage_principal,
                "Performance Mobile": psi_principal.get('mobile', {}).get('psi_performance', 0),
                "SEO Score": overall_score
            }
            todos_os_resultados.append(resultado_principal)

            # Analisa concorrentes
            progress_bar = st.progress(0)
            
            for i, url_comp in enumerate(urls_competidores_limpas):
                is_valid, url_comp = validate_url(url_comp)
                if is_valid:
                    try:
                        with st.spinner(f"Analisando {urlparse(url_comp).netloc}..."):
                            onpage_comp, _, soup_comp, technologies_comp, security_comp, accessibility_comp = onpage_checks(url_comp)
                            if onpage_comp:
                                psi_comp = get_pagespeed_insights(url_comp)
                                structured_comp = analyze_structured_data(soup_comp)
                                comp_score = calculate_overall_seo_score(onpage_comp, psi_comp, structured_comp)
                                if security_comp and security_comp.get('score', 0) >= 60:
                                    comp_score = min(100, comp_score + 5)
                                
                                resultado_comp = {
                                    "URL": url_comp, 
                                    "Site": urlparse(url_comp).netloc, 
                                    **onpage_comp,
                                    "Performance Mobile": psi_comp.get('mobile', {}).get('psi_performance', 0),
                                    "SEO Score": comp_score
                                }
                                todos_os_resultados.append(resultado_comp)
                    except Exception as e:
                        st.warning(f"Erro ao analisar {url_comp}: {str(e)[:100]}")
                
                progress_bar.progress((i + 1) / len(urls_competidores_limpas))
            
            # Exibe comparação
            if len(todos_os_resultados) > 1:
                df_comparativo = pd.DataFrame(todos_os_resultados)
                df_display = df_comparativo[[
                    "Site", "SEO Score", "word_count", "Performance Mobile", 
                    "links_internos", "image_count", "title_length"
                ]].rename(columns={
                    "word_count": "Palavras", 
                    "links_internos": "Links Internos", 
                    "image_count": "Imagens",
                    "title_length": "Tam. Título"
                })
                
                st.dataframe(df_display, use_container_width=True)
                
                # Gráficos comparativos
                st.markdown("#### Comparação Visual")
                
                site_principal_nome = urlparse(url_principal).netloc
                cores = {site_principal_nome: 'gold'}
                
                col1, col2 = st.columns(2)
                with col1:
                    fig_comp_seo = px.bar(df_display, x='Site', y='SEO Score', 
                                         title="Score Geral de SEO",
                                         color='Site', color_discrete_map=cores)
                    st.plotly_chart(fig_comp_seo, use_container_width=True)
                
                with col2:
                    fig_comp_perf = px.bar(df_display, x='Site', y='Performance Mobile',
                                          title="Performance Mobile",
                                          color='Site', color_discrete_map=cores)
                    st.plotly_chart(fig_comp_perf, use_container_width=True)
        
        # RECOMENDAÇÕES FINAIS
        st.divider()
        st.subheader("Resumo e Próximos Passos")
        
        # Identifica principais problemas
        issues = []
        if onpage_principal.get('title_length', 0) == 0:
            issues.append("Title ausente - Crítico para SEO")
        elif onpage_principal.get('title_length', 0) > 60:
            issues.append("Title muito longo - Pode ser cortado nos resultados")
        
        if onpage_principal.get('h1_count', 0) == 0:
            issues.append("H1 ausente - Importante para estrutura")
        elif onpage_principal.get('h1_count', 0) > 1:
            issues.append("Múltiplos H1 - Use apenas um H1 por página")
        
        if onpage_principal.get('word_count', 0) < 300:
            issues.append("Conteúdo insuficiente - Mínimo recomendado: 300 palavras")
        
        if onpage_principal.get('images_sem_alt', 0) > 0:
            issues.append(f"{onpage_principal.get('images_sem_alt', 0)} imagens sem alt text")
        
        if broken_links_principal:
            issues.append(f"{len(broken_links_principal)} links quebrados encontrados")
        
        if psi_principal and psi_principal.get('mobile', {}).get('psi_performance', 0) < 60:
            issues.append("Performance baixa - Afeta ranking e experiência")
        
        if deep_analysis and structured_data and len(structured_data.get('schemas_found', [])) == 0:
            issues.append("Dados estruturados ausentes - Oportunidade perdida")
        
        # Exibe problemas encontrados
        if issues:
            st.markdown("#### Problemas Identificados")
            for issue in issues[:5]:
                st.markdown(f"- {issue}")
        else:
            st.success("Excelente! Nenhum problema crítico encontrado!")
        
        # Recomendações baseadas no score
        st.markdown("#### Prioridades de Otimização")
        
        if overall_score >= 80:
            st.success("Site bem otimizado! Foque em:")
            recommendations = [
                "Monitoramento contínuo de performance",
                "Criação de conteúdo de qualidade regular",
                "Estratégia de link building",
                "Análise de comportamento de usuários"
            ]
        elif overall_score >= 60:
            st.warning("Bom potencial! Otimize:")
            recommendations = [
                "Performance mobile (Core Web Vitals)",
                "Otimização de conteúdo e estrutura",
                "Alt text em todas as imagens",
                "Implementação de dados estruturados"
            ]
        else:
            st.error("Necessita atenção urgente! Priorize:")
            recommendations = [
                "Title e meta description adequados",
                "Estrutura H1 correta",
                "Conteúdo mais robusto (mín. 300 palavras)",
                "Correção de problemas técnicos básicos"
            ]
        
        for rec in recommendations:
            st.markdown(f"- {rec}")
        
        # Dados técnicos completos
        with st.expander("Ver todos os dados técnicos"):
            tab1, tab2, tab3, tab4 = st.tabs(["On-Page", "Performance", "Tecnologias", "Outros"])
            
            with tab1:
                st.json(onpage_principal)
            
            with tab2:
                if psi_principal:
                    st.json(psi_principal)
                else:
                    st.info("Dados de performance não disponíveis")
            
            with tab3:
                if technologies_principal:
                    st.json(technologies_principal)
                else:
                    st.info("Análise de tecnologias não realizada")
            
            with tab4:
                combined_analysis = {
                    'structured_data': structured_data,
                    'security': security_principal,
                    'accessibility': accessibility_principal
                }
                st.json(combined_analysis)

# RODAPE
st.divider()
st.markdown("""
### Sobre o SEO AI Strategist Pro

**A ferramenta mais completa de análise SEO do mercado**, combinando análise técnica avançada com inteligência artificial.

#### Funcionalidades Principais:
- Performance & Core Web Vitals (Google PageSpeed Insights)
- Análise on-page completa com validação robusta
- Detecção de tecnologias (tipo Wappalyzer)
- Análise de segurança - Headers HTTP
- Auditoria de acessibilidade básica
- Comparação competitiva
- Score geral de SEO com algoritmo proprietário
- Dados estruturados - Schema.org

#### Tecnologias Detectadas:
**CMS:** WordPress, Shopify, Drupal, Magento, Webflow  
**Analytics:** Google Analytics, Facebook Pixel, Hotjar  
**Frameworks:** React, Vue.js, Angular, jQuery, Bootstrap  

**Desenvolvido com:** Python, Streamlit, Google Gemini AI, PageSpeed Insights API, Plotly

---
**Próximas atualizações:** Análise de backlinks, monitoramento de posições, alertas automáticos
""")

# Rate limiting
if 'analysis_count' not in st.session_state:
    st.session_state.analysis_count = 0
    st.session_state.last_analysis_time = datetime.now()

if datetime.now() - st.session_state.last_analysis_time > timedelta(hours=1):
    st.session_state.analysis_count = 0
    st.session_state.last_analysis_time = datetime.now()
