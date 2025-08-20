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

# ========== CONFIGURAÇÃO DAS APIS ==========
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

# ========== TÓPICO 2: VALIDAÇÃO DE URL ROBUSTA ==========
def validate_url(url):
    """Validação robusta de URLs"""
    if not url:
        return False, "URL não pode estar vazia"
    
    # Adiciona http:// se não tiver protocolo
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

def test_url_accessibility(url):
    """Testa se a URL é acessível"""
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        if response.status_code >= 400:
            return False, f"Erro HTTP {response.status_code}"
        return True, "URL acessível"
    except requests.exceptions.RequestException as e:
        return False, f"Erro de conexão: {str(e)[:100]}"

# ========== TÓPICO 3: ANÁLISE DE PALAVRAS-CHAVE ==========
def keyword_analysis(soup, target_keyword=None):
    """Análise avançada de palavras-chave e densidade"""
    body = soup.find("body")
    if not body:
        return {}
    
    text = body.get_text().lower()
    words = [word.strip('.,!?";()[]{}') for word in text.split() if len(word.strip('.,!?";()[]{}')) > 2]
    
    analysis = {
        "total_words": len(words),
        "unique_words": len(set(words))
    }
    
    if target_keyword:
        keyword_lower = target_keyword.lower()
        keyword_count = text.count(keyword_lower)
        
        # Verifica presença em elementos importantes
        title = soup.find("title")
        h1s = soup.find_all("h1")
        meta_desc = soup.find("meta", attrs={"name": "description"})
        
        analysis.update({
            "target_keyword": target_keyword,
            "keyword_count": keyword_count,
            "keyword_density": round((keyword_count / len(words)) * 100, 2) if words else 0,
            "in_title": keyword_lower in (title.get_text().lower() if title else ""),
            "in_h1": any(keyword_lower in h1.get_text().lower() for h1 in h1s),
            "in_meta_desc": keyword_lower in (meta_desc.get("content", "").lower() if meta_desc else ""),
            "keyword_prominence_score": 0
        })
        
        # Calcula score de proeminência (0-100)
        score = 0
        if analysis["in_title"]: score += 30
        if analysis["in_h1"]: score += 25
        if analysis["in_meta_desc"]: score += 20
        if 1 <= analysis["keyword_density"] <= 3: score += 25
        elif analysis["keyword_density"] > 0: score += 15
        
        analysis["keyword_prominence_score"] = score
    
    # Top 10 palavras mais frequentes
    word_freq = Counter(words)
    analysis["top_words"] = dict(word_freq.most_common(10))
    
    return analysis

# ========== TÓPICO 5: ANÁLISE DETALHADA DE DADOS ESTRUTURADOS ==========
def analyze_structured_data(soup):
    """Análise completa dos dados estruturados"""
    structured_data = {
        "json_ld_count": 0,
        "microdata_count": 0,
        "schemas_found": [],
        "errors": [],
        "recommendations": []
    }
    
    # Análise JSON-LD
    json_scripts = soup.find_all("script", type="application/ld+json")
    structured_data["json_ld_count"] = len(json_scripts)
    
    for i, script in enumerate(json_scripts):
        try:
            data = json.loads(script.string.strip())
            schema_type = data.get("@type", "Unknown")
            structured_data["schemas_found"].append({
                "type": schema_type,
                "method": "JSON-LD",
                "valid": True,
                "position": i + 1
            })
        except json.JSONDecodeError as e:
            structured_data["errors"].append(f"JSON-LD inválido na posição {i + 1}: {str(e)[:100]}")
    
    # Análise Microdata
    microdata_items = soup.find_all(attrs={"itemtype": True})
    structured_data["microdata_count"] = len(microdata_items)
    
    for item in microdata_items:
        itemtype = item.get("itemtype", "")
        if "schema.org" in itemtype:
            schema_name = itemtype.split("/")[-1]
            structured_data["schemas_found"].append({
                "type": schema_name,
                "method": "Microdata",
                "valid": True
            })
    
    # Recomendações
    if structured_data["json_ld_count"] == 0 and structured_data["microdata_count"] == 0:
        structured_data["recommendations"].append("Implementar dados estruturados para melhorar a visibilidade nos resultados de busca")
    
    if len(structured_data["schemas_found"]) == 0:
        structured_data["recommendations"].append("Adicionar Schema.org adequado ao tipo de conteúdo (Article, Product, Organization, etc.)")
    
    return structured_data

# ========== TÓPICO 6: DASHBOARD COM GAUGES VISUAIS (CORRIGIDO) ==========
def create_seo_score_gauge(score, title="SEO Score"):
    """Cria um gauge visual para scores de SEO"""
    # Garantir que score é numérico
    if score is None or score == "N/A":
        score = 0
    try:
        score = float(score)
    except (ValueError, TypeError):
        score = 0
    
    # Determina cor baseada no score
    if score >= 80:
        color = "green"
    elif score >= 60:
        color = "orange"
    else:
        color = "red"
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title, 'font': {'size': 14}},
        delta = {'reference': 80, 'suffix': " pts"},
        gauge = {
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 30], 'color': 'lightgray'},
                {'range': [30, 60], 'color': 'lightyellow'},
                {'range': [60, 80], 'color': 'lightblue'},
                {'range': [80, 100], 'color': 'lightgreen'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(height=200, margin=dict(l=10, r=10, t=30, b=10))
    return fig

def calculate_overall_seo_score(onpage_data, psi_data, keyword_data, structured_data):
    """Calcula um score geral de SEO baseado em múltiplos fatores - VERSÃO CORRIGIDA"""
    if not onpage_data:
        return 0
    
    score = 0
    
    # CRITÉRIOS BÁSICOS (40 pontos) - Sempre disponíveis
    # Title (15 pontos)
    title_len = onpage_data.get('title_length', 0)
    if title_len == 0 or onpage_data.get('title') == 'N/A':
        score += 0  # Sem title
    elif 30 <= title_len <= 60:
        score += 15  # Title ideal
    elif 20 <= title_len <= 80:
        score += 10  # Title OK
    else:
        score += 5   # Title existe mas não ideal
    
    # H1 (10 pontos)
    h1_count = onpage_data.get('h1_count', 0)
    if h1_count == 1:
        score += 10  # H1 perfeito
    elif h1_count > 1:
        score += 5   # Tem H1 mas múltiplos
    # Se 0, não soma nada
    
    # Conteúdo (15 pontos)
    word_count = onpage_data.get('word_count', 0)
    if word_count >= 500:
        score += 15
    elif word_count >= 300:
        score += 12
    elif word_count >= 150:
        score += 8
    elif word_count > 0:
        score += 3
    
    # PERFORMANCE (25 pontos) - Se disponível
    if psi_data and 'mobile' in psi_data and psi_data['mobile']:
        mobile_perf = psi_data['mobile'].get('psi_performance', 0)
        try:
            mobile_perf = float(mobile_perf)
            score += (mobile_perf / 100) * 25
        except (ValueError, TypeError):
            pass
    else:
        # Se não tiver dados de performance, distribuir pontos nos outros critérios
        score += 10  # Pontos base
    
    # META DESCRIPTION (10 pontos)
    meta_len = onpage_data.get('meta_description_length', 0)
    if meta_len == 0 or onpage_data.get('meta_description') == 'N/A':
        score += 0
    elif 140 <= meta_len <= 160:
        score += 10
    elif 120 <= meta_len <= 180:
        score += 7
    else:
        score += 3
    
    # ELEMENTOS TÉCNICOS (25 pontos)
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
    
    # Palavra-chave (10 pontos)
    if keyword_data and 'keyword_prominence_score' in keyword_data:
        kw_score = keyword_data.get('keyword_prominence_score', 0)
        try:
            score += (float(kw_score) / 100) * 10
        except (ValueError, TypeError):
            pass
    
    # Dados estruturados (5 pontos)
    if structured_data and len(structured_data.get('schemas_found', [])) > 0:
        score += 5
    
    return min(round(score), 100)

# ========== NOVA FUNCIONALIDADE: SITEMAP E MAPEAMENTO (SEM NETWORKX) ==========
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def extract_site_structure(url, max_depth=2, max_pages=20):
    """Extrai a estrutura do site para criar sitemap"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        base_domain = urlparse(url).netloc
        
        # Encontra todos os links internos
        links = soup.find_all("a", href=True)
        internal_links = []
        
        for link in links:
            href = link.get('href')
            if href:
                # Resolve URL relativa
                full_url = urljoin(url, href)
                parsed = urlparse(full_url)
                
                # Verifica se é link interno
                if parsed.netloc == base_domain and not href.startswith('#'):
                    # Extrai informações do link
                    link_info = {
                        'url': full_url,
                        'path': parsed.path,
                        'text': link.get_text(strip=True)[:50],  # Primeiros 50 chars
                        'depth': len(parsed.path.strip('/').split('/')) if parsed.path != '/' else 0
                    }
                    internal_links.append(link_info)
        
        # Remove duplicatas e limita
        seen_urls = set()
        unique_links = []
        for link in internal_links:
            if link['url'] not in seen_urls and len(unique_links) < max_pages:
                seen_urls.add(link['url'])
                unique_links.append(link)
        
        return {
            'base_url': url,
            'domain': base_domain,
            'total_links_found': len(internal_links),
            'unique_pages': len(unique_links),
            'structure': unique_links
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'base_url': url,
            'structure': []
        }

def create_sitemap_visualization(site_structure):
    """Cria visualização interativa do sitemap"""
    if not site_structure.get('structure'):
        return None
    
    # Prepara dados para o gráfico
    pages = site_structure['structure']
    
    # Agrupa por profundidade
    depth_groups = {}
    for page in pages:
        depth = page['depth']
        if depth not in depth_groups:
            depth_groups[depth] = []
        depth_groups[depth].append(page)
    
    # Cria o gráfico hierárquico
    fig = go.Figure()
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    y_positions = {}
    current_y = 0
    
    for depth in sorted(depth_groups.keys()):
        pages_at_depth = depth_groups[depth]
        color = colors[depth % len(colors)]
        
        x_positions = list(range(len(pages_at_depth)))
        y_positions[depth] = [current_y] * len(pages_at_depth)
        
        # Adiciona nós
        fig.add_trace(go.Scatter(
            x=x_positions,
            y=y_positions[depth],
            mode='markers+text',
            marker=dict(
                size=15,
                color=color,
                symbol='circle'
            ),
            text=[page['text'][:20] + '...' if len(page['text']) > 20 else page['text'] 
                  for page in pages_at_depth],
            textposition="middle center",
            hovertemplate='<b>%{text}</b><br>URL: %{customdata}<br>Profundidade: ' + str(depth),
            customdata=[page['url'] for page in pages_at_depth],
            name=f'Nível {depth}',
            showlegend=True
        ))
        
        current_y -= 1
    
    # Conecta os nós (linhas entre níveis)
    for depth in sorted(depth_groups.keys())[:-1]:
        next_depth = depth + 1
        if next_depth in depth_groups:
            # Linhas conectando níveis
            for i in range(len(depth_groups[depth])):
                for j in range(min(3, len(depth_groups[next_depth]))):  # Máximo 3 conexões
                    fig.add_trace(go.Scatter(
                        x=[i, j],
                        y=[y_positions[depth][0], y_positions[next_depth][0]],
                        mode='lines',
                        line=dict(color='gray', width=1),
                        showlegend=False,
                        hoverinfo='skip'
                    ))
    
    fig.update_layout(
        title=f"Mapa da Estrutura: {site_structure.get('domain', 'Site')}",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=400,
        plot_bgcolor='white',
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

def analyze_site_strategy(site_structure):
    """Analisa a estratégia de estrutura do site"""
    if not site_structure.get('structure'):
        return "Não foi possível analisar a estrutura do site."
    
    pages = site_structure['structure']
    depth_analysis = {}
    
    for page in pages:
        depth = page['depth']
        if depth not in depth_analysis:
            depth_analysis[depth] = []
        depth_analysis[depth].append(page)
    
    insights = []
    
    # Análise de profundidade
    max_depth = max(depth_analysis.keys()) if depth_analysis else 0
    if max_depth <= 2:
        insights.append("✅ **Estrutura rasa**: Boa para SEO, fácil navegação")
    elif max_depth <= 4:
        insights.append("⚠️ **Estrutura média**: Adequada, mas pode ser otimizada")
    else:
        insights.append("❌ **Estrutura muito profunda**: Pode dificultar indexação")
    
    # Análise de distribuição
    pages_per_level = [len(depth_analysis.get(i, [])) for i in range(max_depth + 1)]
    if len(pages_per_level) > 1 and pages_per_level[1] > pages_per_level[0] * 3:
        insights.append("⚠️ **Muitas páginas no segundo nível**: Considere subcategorias")
    
    # Análise de navegação
    home_links = len(depth_analysis.get(0, []))
    if home_links > 10:
        insights.append("⚠️ **Muitos links na home**: Pode diluir autoridade")
    elif home_links < 3:
        insights.append("❌ **Poucos links na home**: Pode prejudicar descoberta de conteúdo")
    
    return "\n".join(insights)

# ========== FUNÇÕES EXISTENTES (ATUALIZADAS) ==========
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
    for link in internal_links[:10]:  # Limita a 10 links para não sobrecarregar
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
    
    # Conta imagens sem alt text
    images = soup.find_all("img")
    images_sem_alt = [img for img in images if not img.get("alt", "").strip()]
    checks["images_sem_alt"] = len(images_sem_alt)
    
    body_text = soup.find("body").get_text(separator=" ", strip=True) if soup.find("body") else ""
    checks["word_count"] = len(body_text.split())
    
    return checks, internal_links, soup

# ========== INTERFACE STREAMLIT MELHORADA ==========
st.set_page_config(page_title="SEO AI Strategist Pro", page_icon="🔭", layout="wide")

# Sidebar com configurações
with st.sidebar:
    st.header("⚙️ Configurações de Análise")
    
    target_keyword = st.text_input("🎯 Palavra-chave principal (opcional)", 
                                   help="Digite a palavra-chave que você quer otimizar")
    
    deep_analysis = st.checkbox("🔍 Análise profunda", value=True,
                               help="Inclui análise de dados estruturados e palavras-chave")
    
    extract_structure = st.checkbox("🗺️ Mapear estrutura do site", value=True,
                                   help="Cria mapa visual da arquitetura do site")
    
    max_pages_sitemap = st.slider("Máx. páginas para sitemap", 10, 50, 20,
                                 help="Limite de páginas para análise de estrutura")
    
    st.divider()
    st.markdown("### 📊 Métricas Ideais")
    st.info("""
    **Title:** 30-60 caracteres  
    **Meta Description:** 150-160 caracteres  
    **H1:** Apenas 1 por página  
    **Conteúdo:** Mínimo 300 palavras  
    **Performance:** Acima de 80
    """)

st.title("🔭 SEO AI Strategist Pro")
st.markdown("Análise avançada de SEO com IA, comparação competitiva e insights estratégicos.")

st.subheader("🚀 Análise Principal")
url_principal = st.text_input("Insira a URL do seu site:", key="url_principal",
                             placeholder="https://seusite.com.br")

# Validação em tempo real
if url_principal:
    is_valid, validation_result = validate_url(url_principal)
    if not is_valid:
        st.error(f"❌ {validation_result}")
    else:
        if validation_result != url_principal:
            st.info(f"✅ URL corrigida para: {validation_result}")
            url_principal = validation_result

st.subheader("🏆 Análise Competitiva (Opcional)")
competidores_raw = st.text_area("URLs dos concorrentes (uma por linha):", 
                                key="url_competidores", height=100,
                                placeholder="https://concorrente1.com\nhttps://concorrente2.com")

if st.button("🛰️ Iniciar Análise Completa", type="primary"):
    if not url_principal:
        st.error("Por favor, insira a URL do seu site.")
    else:
        # Validação final
        is_valid, url_principal = validate_url(url_principal)
        if not is_valid:
            st.error(f"URL inválida: {url_principal}")
            st.stop()
        
        # --- ANÁLISE PRINCIPAL ---
        with st.spinner(f"🔍 Analisando {urlparse(url_principal).netloc}..."):
            try:
                onpage_principal, links_principais, soup_principal = onpage_checks(url_principal)
                if onpage_principal is None:
                    st.error(f"Não foi possível analisar {url_principal}")
                    st.stop()
                
                # Análises adicionais se ativadas
                keyword_data = {}
                structured_data = {}
                site_structure = {}
                
                if deep_analysis:
                    if target_keyword:
                        keyword_data = keyword_analysis(soup_principal, target_keyword)
                    structured_data = analyze_structured_data(soup_principal)
                
                if extract_structure:
                    with st.spinner("🗺️ Mapeando estrutura do site..."):
                        site_structure = extract_site_structure(url_principal, max_pages=max_pages_sitemap)
                
                psi_principal = get_pagespeed_insights(url_principal)
                broken_links_principal = check_broken_links(url_principal, links_principais)
                
            except Exception as e:
                st.error(f"Erro na análise: {str(e)}")
                st.stop()
        
        st.success("✅ Análise principal concluída!")
        
        # --- DASHBOARD PRINCIPAL ---
        st.divider()
        st.subheader(f"📊 Dashboard: {urlparse(url_principal).netloc}")
        
        # Calcula score geral
        overall_score = calculate_overall_seo_score(onpage_principal, psi_principal, keyword_data, structured_data)
        
        # === SEÇÃO DE SITEMAP ===
        if site_structure and site_structure.get('structure'):
            st.markdown("#### 🗺️ Mapa da Estrutura do Site")
            
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.metric("📄 Páginas Encontradas", site_structure.get('unique_pages', 0))
            with col_info2:
                st.metric("🔗 Total de Links", site_structure.get('total_links_found', 0))
            with col_info3:
                max_depth = max([page['depth'] for page in site_structure['structure']]) if site_structure['structure'] else 0
                st.metric("📏 Profundidade Máxima", max_depth)
            
            # Visualização do sitemap
            sitemap_fig = create_sitemap_visualization(site_structure)
            if sitemap_fig:
                st.plotly_chart(sitemap_fig, use_container_width=True)
            
            # Análise estratégica da estrutura
            strategy_insights = analyze_site_strategy(site_structure)
            if strategy_insights:
                st.markdown("**💡 Insights da Estrutura:**")
                st.markdown(strategy_insights)
            
            st.divider()
        
        # Primeira linha: Score geral e métricas principais
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            fig_score = create_seo_score_gauge(overall_score, "Score Geral de SEO")
            st.plotly_chart(fig_score, use_container_width=True)
        
        with col2:
            st.metric("📝 Palavras", onpage_principal.get("word_count", 0))
            st.metric("🖼️ Imagens", onpage_principal.get("image_count", 0))
        
        with col3:
            st.metric("🔗 Links Internos", onpage_principal.get("links_internos", 0))
            st.metric("❌ Imgs sem Alt", onpage_principal.get("images_sem_alt", 0))
        
        with col4:
            if psi_principal and 'mobile' in psi_principal:
                perf_mobile = psi_principal['mobile'].get('psi_performance', 0)
                st.metric("📱 Performance", f"{perf_mobile}/100")
            else:
                st.metric("📱 Performance", "N/A")
            
            if broken_links_principal:
                st.metric("🔗 Links Quebrados", len(broken_links_principal), delta_color="inverse")
            else:
                st.metric("🔗 Links Quebrados", "0 ✅")
        
        # Segunda linha: Análise de palavra-chave (se disponível)
        if keyword_data:
            st.markdown("#### 🎯 Análise da Palavra-chave")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                fig_keyword = create_seo_score_gauge(
                    keyword_data.get('keyword_prominence_score', 0), 
                    f"Otimização: {target_keyword}"
                )
                st.plotly_chart(fig_keyword, use_container_width=True)
            
            with col2:
                st.metric("🔍 Ocorrências", keyword_data.get('keyword_count', 0))
                st.metric("📊 Densidade", f"{keyword_data.get('keyword_density', 0)}%")
            
            with col3:
                presence_score = 0
                if keyword_data.get('in_title'): presence_score += 1
                if keyword_data.get('in_h1'): presence_score += 1
                if keyword_data.get('in_meta_desc'): presence_score += 1
                
                st.metric("✅ Presença em Elementos", f"{presence_score}/3")
                
                presence_details = []
                if keyword_data.get('in_title'): presence_details.append("Title ✅")
                else: presence_details.append("Title ❌")
                if keyword_data.get('in_h1'): presence_details.append("H1 ✅")  
                else: presence_details.append("H1 ❌")
                if keyword_data.get('in_meta_desc'): presence_details.append("Meta Desc ✅")
                else: presence_details.append("Meta Desc ❌")
                
                st.write(" | ".join(presence_details))
        
        # Terceira linha: Dados estruturados (se análise profunda ativada)
        if deep_analysis and structured_data:
            st.markdown("#### 🏗️ Dados Estruturados")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("📋 Schemas JSON-LD", structured_data.get('json_ld_count', 0))
            with col2:
                st.metric("🏷️ Microdata", structured_data.get('microdata_count', 0))
            with col3:
                total_schemas = len(structured_data.get('schemas_found', []))
                st.metric("✅ Total de Schemas", total_schemas)
            
            if structured_data.get('schemas_found'):
                st.write("**Schemas detectados:**")
                for schema in structured_data['schemas_found']:
                    st.write(f"- {schema['type']} ({schema['method']})")
        
        # Quarta linha: Performance detalhada
        if psi_principal:
            st.markdown("#### 🚀 Performance Detalhada")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📱 Mobile**")
                mobile_data = psi_principal.get('mobile', {})
                perf = mobile_data.get('psi_performance', 0)
                seo = mobile_data.get('psi_seo', 0)
                
                fig_mobile = create_seo_score_gauge(perf, "Performance Mobile")
                st.plotly_chart(fig_mobile, use_container_width=True)
                st.metric("SEO Score", f"{seo}/100")
            
            with col2:
                st.markdown("**🖥️ Desktop**")
                desktop_data = psi_principal.get('desktop', {})
                perf_desk = desktop_data.get('psi_performance', 0)
                seo_desk = desktop_data.get('psi_seo', 0)
                
                fig_desktop = create_seo_score_gauge(perf_desk, "Performance Desktop")
                st.plotly_chart(fig_desktop, use_container_width=True)
                st.metric("SEO Score", f"{seo_desk}/100")
        
        # --- ANÁLISE COMPETITIVA (SE HOUVER) ---
        urls_competidores_limpas = [url.strip() for url in competidores_raw.splitlines() if url.strip()][:3]  # Máximo 3
        
        if urls_competidores_limpas:
            st.divider()
            st.subheader("🏆 Comparação Competitiva")
            
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
            competitor_dashboards = []  # Lista para armazenar dashboards dos concorrentes
            
            for i, url_comp in enumerate(urls_competidores_limpas):
                is_valid, url_comp = validate_url(url_comp)
                if is_valid:
                    try:
                        with st.spinner(f"Analisando {urlparse(url_comp).netloc}..."):
                            onpage_comp, _, soup_comp = onpage_checks(url_comp)
                            if onpage_comp:
                                psi_comp = get_pagespeed_insights(url_comp)
                                keyword_comp = keyword_analysis(soup_comp, target_keyword) if target_keyword else {}
                                structured_comp = analyze_structured_data(soup_comp)
                                site_structure_comp = extract_site_structure(url_comp, max_pages=max_pages_sitemap//2) if extract_structure else {}
                                comp_score = calculate_overall_seo_score(onpage_comp, psi_comp, keyword_comp, structured_comp)
                                
                                # Armazena dados do concorrente para dashboard individual
                                competitor_dashboards.append({
                                    'url': url_comp,
                                    'domain': urlparse(url_comp).netloc,
                                    'onpage': onpage_comp,
                                    'psi': psi_comp,
                                    'keyword': keyword_comp,
                                    'structured': structured_comp,
                                    'site_structure': site_structure_comp,
                                    'score': comp_score
                                })
                                
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
            
            # === DASHBOARDS INDIVIDUAIS DOS CONCORRENTES ===
            if competitor_dashboards:
                st.markdown("#### 🏢 Análise Individual dos Concorrentes")
                
                # Tabs para cada concorrente
                tab_names = [f"🏢 {comp['domain']}" for comp in competitor_dashboards]
                if len(tab_names) == 1:
                    tabs = [st.container()]
                else:
                    tabs = st.tabs(tab_names)
                
                for i, (tab, comp_data) in enumerate(zip(tabs, competitor_dashboards)):
                    with tab:
                        st.markdown(f"**Análise de: {comp_data['domain']}**")
                        
                        # Mini dashboard para cada concorrente
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            mini_gauge = create_seo_score_gauge(comp_data['score'], f"Score: {comp_data['domain']}")
                            st.plotly_chart(mini_gauge, use_container_width=True)
                        
                        with col2:
                            st.metric("📝 Palavras", comp_data['onpage'].get("word_count", 0))
                            st.metric("🔗 Links Internos", comp_data['onpage'].get("links_internos", 0))
                        
                        with col3:
                            st.metric("🖼️ Imagens", comp_data['onpage'].get("image_count", 0))
                            perf_mobile = comp_data['psi'].get('mobile', {}).get('psi_performance', 0)
                            st.metric("📱 Performance", f"{perf_mobile}/100")
                        
                        with col4:
                            # Análise de palavra-chave se disponível
                            if comp_data['keyword'] and target_keyword:
                                kw_score = comp_data['keyword'].get('keyword_prominence_score', 0)
                                st.metric(f"🎯 {target_keyword}", f"{kw_score}/100")
                                st.metric("📊 Densidade", f"{comp_data['keyword'].get('keyword_density', 0)}%")
                            else:
                                st.metric("🏷️ Title Length", comp_data['onpage'].get('title_length', 0))
                                h1_count = comp_data['onpage'].get('h1_count', 0)
                                st.metric("📋 H1 Count", h1_count)
                        
                        # Sitemap do concorrente (se disponível)
                        if comp_data.get('site_structure') and comp_data['site_structure'].get('structure'):
                            with st.expander(f"🗺️ Ver estrutura de {comp_data['domain']}"):
                                sitemap_comp = create_sitemap_visualization(comp_data['site_structure'])
                                if sitemap_comp:
                                    st.plotly_chart(sitemap_comp, use_container_width=True)
                                
                                strategy_comp = analyze_site_strategy(comp_data['site_structure'])
                                if strategy_comp:
                                    st.markdown("**Estratégia de Estrutura:**")
                                    st.markdown(strategy_comp)
            
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
                st.markdown("#### 📈 Comparação Visual")
                
                site_principal = urlparse(url_principal).netloc
                cores = {site_principal: 'gold'}
                
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
        
        # --- RECOMENDAÇÕES FINAIS ---
        st.divider()
        st.subheader("💡 Resumo e Próximos Passos")
        
        # Identifica principais problemas
        issues = []
        if onpage_principal.get('title_length', 0) == 0:
            issues.append("❌ **Title ausente** - Crítico para SEO")
        elif onpage_principal.get('title_length', 0) > 60:
            issues.append("⚠️ **Title muito longo** - Pode ser cortado nos resultados")
        
        if onpage_principal.get('h1_count', 0) == 0:
            issues.append("❌ **H1 ausente** - Importante para estrutura")
        elif onpage_principal.get('h1_count', 0) > 1:
            issues.append("⚠️ **Múltiplos H1** - Use apenas um H1 por página")
        
        if onpage_principal.get('word_count', 0) < 300:
            issues.append("⚠️ **Conteúdo insuficiente** - Mínimo recomendado: 300 palavras")
        
        if onpage_principal.get('images_sem_alt', 0) > 0:
            issues.append(f"⚠️ **{onpage_principal.get('images_sem_alt', 0)} imagens sem alt text** - Prejudica acessibilidade")
        
        if broken_links_principal:
            issues.append(f"❌ **{len(broken_links_principal)} links quebrados** - Prejudica experiência do usuário")
        
        if psi_principal and psi_principal.get('mobile', {}).get('psi_performance', 0) < 60:
            issues.append("⚠️ **Performance baixa** - Afeta ranking e experiência")
        
        if target_keyword and keyword_data:
            if keyword_data.get('keyword_prominence_score', 0) < 50:
                issues.append(f"⚠️ **Palavra-chave '{target_keyword}' mal otimizada** - Baixa proeminência")
        
        if deep_analysis and structured_data and len(structured_data.get('schemas_found', [])) == 0:
            issues.append("⚠️ **Dados estruturados ausentes** - Oportunidade perdida para rich snippets")
        
        # Exibe problemas encontrados
        if issues:
            st.markdown("#### 🚨 Problemas Identificados")
            for issue in issues[:5]:  # Mostra no máximo 5 problemas principais
                st.markdown(issue)
        else:
            st.success("🎉 **Excelente!** Nenhum problema crítico encontrado!")
        
        # Recomendações baseadas no score
        st.markdown("#### 🎯 Prioridades de Otimização")
        
        if overall_score >= 80:
            st.success("🏆 **Site bem otimizado!** Foque em:")
            recommendations = [
                "🔍 Monitoramento contínuo de performance",
                "📝 Criação de conteúdo de qualidade regular",
                "🔗 Estratégia de link building",
                "📊 Análise de comportamento de usuários"
            ]
        elif overall_score >= 60:
            st.warning("🚀 **Bom potencial!** Otimize:")
            recommendations = [
                "📱 Performance mobile (Core Web Vitals)",
                "🎯 Otimização de palavra-chave principal",
                "🖼️ Alt text em todas as imagens",
                "🏗️ Implementação de dados estruturados"
            ]
        else:
            st.error("⚠️ **Necessita atenção urgente!** Priorize:")
            recommendations = [
                "📝 Title e meta description adequados",
                "🏷️ Estrutura H1 correta",
                "📄 Conteúdo mais robusto (mín. 300 palavras)",
                "🔧 Correção de problemas técnicos básicos"
            ]
        
        for rec in recommendations:
            st.markdown(f"- {rec}")
        
        # Dados técnicos completos (expansível)
        with st.expander("🔧 Ver todos os dados técnicos"):
            tab1, tab2, tab3, tab4 = st.tabs(["📊 On-Page", "🚀 Performance", "🎯 Palavra-chave", "🏗️ Estruturados"])
            
            with tab1:
                st.json(onpage_principal)
            
            with tab2:
                if psi_principal:
                    st.json(psi_principal)
                else:
                    st.info("Dados de performance não disponíveis")
            
            with tab3:
                if keyword_data:
                    st.json(keyword_data)
                else:
                    st.info("Análise de palavra-chave não realizada")
            
            with tab4:
                if structured_data:
                    st.json(structured_data)
                else:
                    st.info("Análise de dados estruturados não realizada")

# ========== FUNÇÃO EXISTENTE PARA ANÁLISE COMPETITIVA COM IA ==========
def generate_competitive_analysis(df_competitivo, url_principal):
    """Gera análise competitiva com IA"""
    if not gemini_configured: 
        return "Análise por IA desabilitada. Configure a API do Gemini para obter insights estratégicos."
    
    dados_markdown = df_competitivo.to_markdown(index=False)
    site_principal = urlparse(url_principal).netloc
    
    prompt = f"""
    Você é um estrategista de SEO sênior analisando a posição competitiva de um site.

    **Site Principal:** {site_principal}

    **Dados Comparativos:**
    {dados_markdown}

    **Sua Missão:**
    Analise os dados e forneça insights estratégicos em português do Brasil usando formatação Markdown:

    ## 🎯 POSIÇÃO COMPETITIVA
    Avalie a posição do site principal em relação aos concorrentes. Identifique se está liderando, competindo ou perdendo em cada métrica.

    ## 💪 VANTAGENS COMPETITIVAS
    Liste 2-3 pontos onde o site principal supera a concorrência e como capitalizar essas vantagens.

    ## ⚠️ GAPS IDENTIFICADOS
    Identifique as principais lacunas onde os concorrentes estão à frente e o impacto dessas diferenças.

    ## 🚀 ESTRATÉGIA DE AÇÃO
    Forneça um plano de ação priorizado com 4-5 iniciativas específicas para superar a concorrência.

    ## 📊 BENCHMARKS RECOMENDADOS
    Sugira métricas-alvo baseadas no melhor desempenho observado na comparação.

    Seja específico, acionável e focado em resultados mensuráveis.
    """
    
    try:
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        gemini_resp = gemini_model.generate_content(prompt)
        return gemini_resp.text
    except Exception as e:
        return f"Erro ao gerar análise estratégica: {str(e)}"

# ========== VERSÃO SIMPLIFICADA DO REQUIREMENTS.TXT ==========
# Removido networkx para evitar conflitos no Streamlit Cloud
st.divider()
st.markdown("""
### 📚 Sobre esta Ferramenta

**SEO AI Strategist Pro** combina análise técnica avançada com inteligência artificial para fornecer 
insights estratégicos de SEO. 

**Métricas analisadas:**
- ✅ Performance e Core Web Vitals (Google PageSpeed)
- ✅ Otimização on-page completa
- ✅ Análise de palavra-chave e densidade
- ✅ Dados estruturados (Schema.org)
- ✅ Comparação competitiva
- ✅ Score geral de SEO (algoritmo proprietário)

**Tecnologias:** Python, Streamlit, Google Gemini AI, PageSpeed Insights API, Plotly

---
💡 **Dica:** Para melhores resultados, execute análises regularmente e monitore as melhorias ao longo do tempo.
""")

# Rate limiting simples para evitar abuso
if 'analysis_count' not in st.session_state:
    st.session_state.analysis_count = 0
    st.session_state.last_analysis_time = datetime.now()

# Reset contador a cada hora
if datetime.now() - st.session_state.last_analysis_time > timedelta(hours=1):
    st.session_state.analysis_count = 0
    st.session_state.last_analysis_time = datetime.now()
