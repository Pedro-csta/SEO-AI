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

# ========== VALIDAÇÃO DE URL ROBUSTA ==========
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

# ========== 7. ANÁLISE DE CONTEÚDO AVANÇADA ==========
def calculate_flesch_score(text):
    """Calcula o score de legibilidade Flesch (adaptado para português)"""
    if not text:
        return 0
    
    sentences = len(re.split(r'[.!?]+', text))
    words = len(text.split())
    syllables = sum([count_syllables(word) for word in text.split()])
    
    if sentences == 0 or words == 0:
        return 0
    
    # Fórmula Flesch adaptada
    score = 206.835 - (1.015 * (words / sentences)) - (84.6 * (syllables / words))
    return max(0, min(100, score))

def count_syllables(word):
    """Conta sílabas aproximadamente"""
    word = word.lower()
    vowels = 'aeiouáéíóúâêîôûàèìòùãẽĩõũ'
    syllables = 0
    prev_was_vowel = False
    
    for char in word:
        if char in vowels:
            if not prev_was_vowel:
                syllables += 1
            prev_was_vowel = True
        else:
            prev_was_vowel = False
    
    return max(1, syllables)

def analyze_content_quality(soup, text):
    """Análise avançada de qualidade do conteúdo"""
    if not text:
        return {}
    
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    paragraphs = text.split('\n\n')
    
    # Análise básica
    analysis = {
        'word_count': len(words),
        'sentence_count': len([s for s in sentences if s.strip()]),
        'paragraph_count': len([p for p in paragraphs if p.strip()]),
        'avg_words_per_sentence': len(words) / max(1, len(sentences)) if sentences else 0,
        'readability_score': calculate_flesch_score(text)
    }
    
    # Análise de densidade de palavras-chave
    word_freq = Counter([word.lower().strip('.,!?";()[]{}') for word in words if len(word) > 3])
    analysis['top_keywords'] = dict(word_freq.most_common(10))
    
    # Análise de estrutura de headings
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    analysis['heading_structure'] = {
        'total_headings': len(headings),
        'h1_count': len(soup.find_all('h1')),
        'h2_count': len(soup.find_all('h2')),
        'h3_count': len(soup.find_all('h3')),
        'has_proper_hierarchy': check_heading_hierarchy(headings)
    }
    
    # Score de qualidade do conteúdo
    quality_score = calculate_content_quality_score(analysis)
    analysis['content_quality_score'] = quality_score
    
    return analysis

def check_heading_hierarchy(headings):
    """Verifica se a hierarquia de headings está correta"""
    if not headings:
        return False
    
    levels = [int(h.name[1]) for h in headings]
    
    # Deve começar com H1
    if levels[0] != 1:
        return False
    
    # Não deve pular níveis
    for i in range(1, len(levels)):
        if levels[i] > levels[i-1] + 1:
            return False
    
    return True

def calculate_content_quality_score(analysis):
    """Calcula score de qualidade do conteúdo (0-100)"""
    score = 0
    
    # Quantidade de conteúdo (30 pontos)
    word_count = analysis.get('word_count', 0)
    if word_count >= 1000:
        score += 30
    elif word_count >= 500:
        score += 25
    elif word_count >= 300:
        score += 20
    elif word_count >= 150:
        score += 10
    
    # Legibilidade (25 pontos)
    readability = analysis.get('readability_score', 0)
    if readability >= 60:
        score += 25
    elif readability >= 40:
        score += 20
    elif readability >= 20:
        score += 15
    
    # Estrutura de headings (20 pontos)
    if analysis.get('heading_structure', {}).get('h1_count', 0) == 1:
        score += 10
    if analysis.get('heading_structure', {}).get('total_headings', 0) >= 3:
        score += 5
    if analysis.get('heading_structure', {}).get('has_proper_hierarchy', False):
        score += 5
    
    # Estrutura de parágrafos (15 pontos)
    avg_words = analysis.get('avg_words_per_sentence', 0)
    if 15 <= avg_words <= 25:
        score += 15
    elif 10 <= avg_words <= 30:
        score += 10
    elif avg_words > 0:
        score += 5
    
    # Diversidade de vocabulário (10 pontos)
    unique_words = len(analysis.get('top_keywords', {}))
    if unique_words >= 50:
        score += 10
    elif unique_words >= 30:
        score += 7
    elif unique_words >= 20:
        score += 5
    
    return min(100, score)

# ========== 9. ANÁLISE DE BACKLINKS BÁSICA ==========
def analyze_basic_backlinks(soup, domain):
    """Análise básica de backlinks e links externos"""
    backlink_analysis = {
        'external_links': [],
        'referring_domains': set(),
        'anchor_patterns': {},
        'link_quality_indicators': {},
        'total_external_links': 0
    }
    
    # Encontra todos os links externos
    all_links = soup.find_all('a', href=True)
    
    for link in all_links:
        href = link.get('href', '')
        if href.startswith('http') and domain not in href:
            parsed_url = urlparse(href)
            referring_domain = parsed_url.netloc
            anchor_text = link.get_text(strip=True)
            
            backlink_analysis['external_links'].append({
                'url': href,
                'domain': referring_domain,
                'anchor_text': anchor_text,
                'rel': link.get('rel', [])
            })
            
            backlink_analysis['referring_domains'].add(referring_domain)
            
            # Analisa padrões de anchor text
            if anchor_text:
                if anchor_text in backlink_analysis['anchor_patterns']:
                    backlink_analysis['anchor_patterns'][anchor_text] += 1
                else:
                    backlink_analysis['anchor_patterns'][anchor_text] = 1
    
    backlink_analysis['total_external_links'] = len(backlink_analysis['external_links'])
    backlink_analysis['unique_referring_domains'] = len(backlink_analysis['referring_domains'])
    
    # Converte set para lista para JSON
    backlink_analysis['referring_domains'] = list(backlink_analysis['referring_domains'])
    
    # Análise de qualidade dos links
    backlink_analysis['link_quality_score'] = calculate_link_quality_score(backlink_analysis)
    
    return backlink_analysis

def calculate_link_quality_score(backlink_data):
    """Calcula score de qualidade dos links (0-100)"""
    score = 0
    
    total_links = backlink_data.get('total_external_links', 0)
    unique_domains = backlink_data.get('unique_referring_domains', 0)
    
    # Diversidade de domínios (40 pontos)
    if unique_domains >= 10:
        score += 40
    elif unique_domains >= 5:
        score += 30
    elif unique_domains >= 3:
        score += 20
    elif unique_domains >= 1:
        score += 10
    
    # Quantidade moderada de links (30 pontos)
    if 5 <= total_links <= 20:
        score += 30
    elif 3 <= total_links <= 30:
        score += 25
    elif 1 <= total_links <= 50:
        score += 15
    elif total_links > 50:
        score += 5  # Muitos links podem indicar spam
    
    # Diversidade de anchor text (30 pontos)
    anchors = backlink_data.get('anchor_patterns', {})
    if anchors:
        anchor_diversity = len(anchors) / max(1, total_links)
        if anchor_diversity >= 0.8:
            score += 30
        elif anchor_diversity >= 0.6:
            score += 25
        elif anchor_diversity >= 0.4:
            score += 15
        else:
            score += 5
    
    return min(100, score)

# ========== 10. AUDITORIA DE SCHEMA MARKUP AVANÇADA ==========
def advanced_schema_audit(soup):
    """Auditoria avançada de Schema Markup"""
    schema_audit = {
        'json_ld_schemas': [],
        'microdata_schemas': [],
        'rdfa_schemas': [],
        'validation_errors': [],
        'optimization_opportunities': [],
        'schema_coverage_score': 0,
        'recommended_schemas': []
    }
    
    # Análise JSON-LD
    json_scripts = soup.find_all('script', type='application/ld+json')
    for i, script in enumerate(json_scripts):
        try:
            data = json.loads(script.string.strip())
            schema_type = data.get('@type', 'Unknown')
            
            schema_audit['json_ld_schemas'].append({
                'type': schema_type,
                'position': i + 1,
                'valid': True,
                'properties': list(data.keys()) if isinstance(data, dict) else [],
                'completeness': calculate_schema_completeness(schema_type, data)
            })
            
        except json.JSONDecodeError as e:
            schema_audit['validation_errors'].append(f"JSON-LD inválido na posição {i + 1}: {str(e)[:100]}")
    
    # Análise Microdata
    microdata_items = soup.find_all(attrs={'itemtype': True})
    for item in microdata_items:
        itemtype = item.get('itemtype', '')
        if 'schema.org' in itemtype:
            schema_name = itemtype.split('/')[-1]
            properties = [prop.get('itemprop') for prop in item.find_all(attrs={'itemprop': True})]
            
            schema_audit['microdata_schemas'].append({
                'type': schema_name,
                'properties': [p for p in properties if p],
                'completeness': len(properties)
            })
    
    # Análise RDFa (básica)
    rdfa_items = soup.find_all(attrs={'typeof': True})
    for item in rdfa_items:
        typeof = item.get('typeof', '')
        schema_audit['rdfa_schemas'].append({
            'type': typeof,
            'properties': [prop.get('property') for prop in item.find_all(attrs={'property': True})]
        })
    
    # Detecta tipo de conteúdo e sugere schemas
    content_type = detect_content_type(soup)
    schema_audit['recommended_schemas'] = get_recommended_schemas(content_type)
    
    # Identifica oportunidades de otimização
    schema_audit['optimization_opportunities'] = identify_schema_opportunities(soup, schema_audit)
    
    # Calcula score de cobertura
    schema_audit['schema_coverage_score'] = calculate_schema_coverage_score(schema_audit, content_type)
    
    return schema_audit

def calculate_schema_completeness(schema_type, data):
    """Calcula completude do schema baseado em propriedades essenciais"""
    required_props = {
        'Organization': ['name', 'url'],
        'Person': ['name'],
        'Article': ['headline', 'author', 'datePublished'],
        'Product': ['name', 'description', 'offers'],
        'LocalBusiness': ['name', 'address', 'telephone'],
        'WebSite': ['name', 'url'],
        'BreadcrumbList': ['itemListElement']
    }
    
    if schema_type not in required_props:
        return 50  # Score padrão para tipos não conhecidos
    
    required = required_props[schema_type]
    present = [prop for prop in required if prop in data]
    
    return int((len(present) / len(required)) * 100)

def detect_content_type(soup):
    """Detecta o tipo de conteúdo da página"""
    # Verifica indicadores de e-commerce
    if soup.find_all(['div', 'span'], class_=re.compile(r'price|cart|buy|product')):
        return 'ecommerce'
    
    # Verifica indicadores de artigo/blog
    if soup.find_all(['article', 'div'], class_=re.compile(r'post|article|blog')):
        return 'article'
    
    # Verifica indicadores de negócio local
    if soup.find_all(['div', 'span'], class_=re.compile(r'address|phone|location')):
        return 'local_business'
    
    # Verifica indicadores de organização
    if soup.find_all(['div', 'section'], class_=re.compile(r'about|company|team')):
        return 'organization'
    
    return 'website'

def get_recommended_schemas(content_type):
    """Retorna schemas recomendados baseados no tipo de conteúdo"""
    recommendations = {
        'website': ['Organization', 'WebSite', 'BreadcrumbList'],
        'ecommerce': ['Product', 'Organization', 'WebSite', 'BreadcrumbList'],
        'article': ['Article', 'Person', 'Organization', 'WebSite'],
        'local_business': ['LocalBusiness', 'Organization', 'WebSite'],
        'organization': ['Organization', 'Person', 'WebSite']
    }
    
    return recommendations.get(content_type, ['WebSite', 'Organization'])

def identify_schema_opportunities(soup, schema_audit):
    """Identifica oportunidades de otimização de schema"""
    opportunities = []
    
    existing_schemas = [s['type'] for s in schema_audit['json_ld_schemas']]
    
    # Verifica se tem breadcrumbs visuais mas não schema
    if soup.find_all(['nav', 'ol'], class_=re.compile(r'breadcrumb')):
        if 'BreadcrumbList' not in existing_schemas:
            opportunities.append("Implementar schema BreadcrumbList para breadcrumbs existentes")
    
    # Verifica se tem informações de contato mas não schema
    if soup.find_all(text=re.compile(r'\(\d{2}\)\s*\d{4,5}-?\d{4}')):  # Telefone brasileiro
        if 'Organization' not in existing_schemas and 'LocalBusiness' not in existing_schemas:
            opportunities.append("Implementar schema Organization/LocalBusiness para informações de contato")
    
    # Verifica se tem produtos mas não schema
    if soup.find_all(['div', 'span'], class_=re.compile(r'price|product')):
        if 'Product' not in existing_schemas:
            opportunities.append("Implementar schema Product para produtos/serviços")
    
    # Verifica se tem artigos mas não schema
    if soup.find_all(['time', 'div'], class_=re.compile(r'date|publish')):
        if 'Article' not in existing_schemas:
            opportunities.append("Implementar schema Article para conteúdo editorial")
    
    return opportunities

def calculate_schema_coverage_score(schema_audit, content_type):
    """Calcula score de cobertura de schema (0-100)"""
    score = 0
    
    total_schemas = len(schema_audit['json_ld_schemas']) + len(schema_audit['microdata_schemas'])
    recommended = get_recommended_schemas(content_type)
    existing_types = [s['type'] for s in schema_audit['json_ld_schemas']]
    
    # Pontos por schemas implementados (60 pontos)
    if total_schemas >= 3:
        score += 30
    elif total_schemas >= 2:
        score += 20
    elif total_schemas >= 1:
        score += 10
    
    # Pontos por schemas recomendados implementados (30 pontos)
    implemented_recommended = len([t for t in existing_types if t in recommended])
    score += (implemented_recommended / len(recommended)) * 30
    
    # Pontos por qualidade/completude (10 pontos)
    if schema_audit['json_ld_schemas']:
        avg_completeness = sum([s.get('completeness', 0) for s in schema_audit['json_ld_schemas']]) / len(schema_audit['json_ld_schemas'])
        score += (avg_completeness / 100) * 10
    
    return min(100, int(score))

# ========== FUNÇÕES DE AUDITORIA EXISTENTES ==========
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
        return None, []
    
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
    
    return checks, internal_links, soup, body_text

def generate_gemini_recommendations(checks, url, content_analysis=None, backlink_analysis=None, schema_analysis=None):
    if not gemini_configured:
        return "A análise por IA está desabilitada pois a chave da API do Gemini não foi configurada corretamente.", ""
        
    report_details = "\n".join([f"- {key.replace('_', ' ').title()}: {value}" for key, value in checks.items()])
    
    # Adiciona análises avançadas se disponíveis
    additional_context = ""
    if content_analysis:
        additional_context += f"\n\n**Análise de Conteúdo:**\n- Score de Qualidade: {content_analysis.get('content_quality_score', 0)}/100\n- Legibilidade: {content_analysis.get('readability_score', 0):.1f}\n- Palavras-chave principais: {', '.join(list(content_analysis.get('top_keywords', {}).keys())[:5])}"
    
    if backlink_analysis:
        additional_context += f"\n\n**Análise de Links:**\n- Links externos: {backlink_analysis.get('total_external_links', 0)}\n- Domínios únicos: {backlink_analysis.get('unique_referring_domains', 0)}\n- Score de qualidade: {backlink_analysis.get('link_quality_score', 0)}/100"
    
    if schema_analysis:
        additional_context += f"\n\n**Schema Markup:**\n- Schemas implementados: {len(schema_analysis.get('json_ld_schemas', []))}\n- Score de cobertura: {schema_analysis.get('schema_coverage_score', 0)}/100\n- Oportunidades: {len(schema_analysis.get('optimization_opportunities', []))}"
    
    prompt = f"""
    Você é um especialista sênior em SEO, encarregado de analisar uma página da web e fornecer um feedback claro e acionável.

    **URL Analisada:** {url}

    **Dados da Auditoria On-Page:**
    {report_details}
    
    {additional_context}

    **Sua Tarefa:**
    Com base nos dados fornecidos, por favor, gere a seguinte análise em português do Brasil, usando formatação Markdown:

    1. **## SCORE DE SEO ON-PAGE (0/100)**
       Atribua uma pontuação geral de 0 a 100 para a saúde do SEO on-page desta página. Justifique brevemente a pontuação.

    2. **## ✅ PONTOS FORTES**
       Liste 2-3 elementos que estão bem implementados nesta página.

    3. **## 🎯 OPORTUNIDADES DE MELHORIA**
       Liste os problemas mais críticos encontrados, em ordem de prioridade.

    4. **## 📈 Recomendações Acionáveis**
       Forneça uma lista de ações práticas e diretas que o proprietário do site pode tomar.
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
st.markdown("Análise de SEO On-Page, Performance e Experiência do Usuário com inteligência avançada.")

# Sidebar com configurações
with st.sidebar:
    st.header("⚙️ Configurações Avançadas")
    
    enable_content_analysis = st.checkbox("📝 Análise de Conteúdo Avançada", value=True,
                                         help="Inclui legibilidade, qualidade e estrutura do conteúdo")
    
    enable_backlink_analysis = st.checkbox("🔗 Análise de Backlinks Básica", value=True,
                                          help="Analisa links externos e padrões de anchor text")
    
    enable_advanced_schema = st.checkbox("🏗️ Auditoria Avançada de Schema", value=True,
                                        help="Análise detalhada de dados estruturados")
    
    st.divider()
    st.markdown("### 📊 Novas Funcionalidades")
    st.info("""
    **Análise de Conteúdo:**
    - Score de legibilidade Flesch
    - Qualidade e estrutura do texto
    - Análise de headings
    
    **Backlinks Básicos:**
    - Links externos identificados
    - Diversidade de domínios
    - Padrões de anchor text
    
    **Schema Avançado:**
    - Validação de JSON-LD
    - Sugestões personalizadas
    - Score de cobertura
    """)

url = st.text_input("Insira a URL completa para auditoria:", key="url_input")

if st.button("🛰️ Rodar Auditoria Completa", type="primary"):
    if not url.startswith("http"):
        st.error("Por favor, insira uma URL válida (inclua http:// ou https://).")
    else:
        try:
            with st.spinner("Etapa 1/4: Realizando auditoria On-Page..."):
                onpage_results, internal_links_list, soup, body_text = onpage_checks(url)
            st.success("Auditoria On-Page concluída!")

            # Análises avançadas opcionais
            content_analysis = None
            backlink_analysis = None  
            schema_analysis = None
            
            if enable_content_analysis:
                with st.spinner("Etapa 2/4: Analisando qualidade do conteúdo..."):
                    content_analysis = analyze_content_quality(soup, body_text)
                st.success("Análise de conteúdo concluída!")
            
            if enable_backlink_analysis:
                with st.spinner("Etapa 3/4: Analisando backlinks e links externos..."):
                    domain = urlparse(url).netloc
                    backlink_analysis = analyze_basic_backlinks(soup, domain)
                st.success("Análise de backlinks concluída!")
            
            if enable_advanced_schema:
                with st.spinner("Etapa 4/4: Auditando Schema Markup..."):
                    schema_analysis = advanced_schema_audit(soup)
                st.success("Auditoria de Schema concluída!")

            with st.spinner("Finalizando com PageSpeed e Links..."):
                psi_results = get_pagespeed_insights(url)
                broken_links_list = check_broken_links(url, internal_links_list)
            st.success("Análises finalizadas!")
            
            st.divider()
            
            # ========== PAINEL PRINCIPAL ==========
            if psi_results:
                st.subheader("🚀 Análise de Performance e Experiência (Google PageSpeed)")
                
                if psi_results.get('redirected'):
                    st.info(f"""
                    **Aviso de Redirecionamento:** A URL foi redirecionada para: 
                    `{psi_results.get('final_url')}`. 
                    """, icon="↪️")
                
                col_mob, col_desk = st.columns(2)
                with col_mob:
                    st.markdown("#### 📱 Mobile")
                    mobile_data = psi_results.get('mobile', {})
                    st.metric("Performance", f"{mobile_data.get('psi_performance', 'N/A')}")
                    st.metric("Acessibilidade", f"{mobile_data.get('psi_accessibility', 'N/A')}")
                    st.metric("Melhores Práticas", f"{mobile_data.get('psi_best_practices', 'N/A')}")
                    st.metric("SEO", f"{mobile_data.get('psi_seo', 'N/A')}")
                with col_desk:
                    st.markdown("#### 🖥️ Desktop")
                    desktop_data = psi_results.get('desktop', {})
                    st.metric("Performance", f"{desktop_data.get('psi_performance', 'N/A')}")
                    st.metric("Acessibilidade", f"{desktop_data.get('psi_accessibility', 'N/A')}")
                    st.metric("Melhores Práticas", f"{desktop_data.get('psi_best_practices', 'N/A')}")
                    st.metric("SEO", f"{desktop_data.get('psi_seo', 'N/A')}")

            # ========== ANÁLISES AVANÇADAS ==========
            
            # Análise de Conteúdo
            if enable_content_analysis and content_analysis:
                st.subheader("📝 Análise Avançada de Conteúdo")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Score de Qualidade", f"{content_analysis.get('content_quality_score', 0)}/100")
                with col2:
                    st.metric("Legibilidade Flesch", f"{content_analysis.get('readability_score', 0):.1f}")
                with col3:
                    st.metric("Palavras por Frase", f"{content_analysis.get('avg_words_per_sentence', 0):.1f}")
                with col4:
                    hierarchy_status = "✅ Correta" if content_analysis.get('heading_structure', {}).get('has_proper_hierarchy') else "❌ Incorreta"
                    st.metric("Hierarquia H1-H6", hierarchy_status)
                
                # Top palavras-chave
                if content_analysis.get('top_keywords'):
                    st.markdown("**🔑 Top 10 Palavras-chave:**")
                    keywords_df = pd.DataFrame(list(content_analysis['top_keywords'].items()), 
                                             columns=['Palavra', 'Frequência'])
                    st.dataframe(keywords_df, use_container_width=True)
            
            # Análise de Backlinks
            if enable_backlink_analysis and backlink_analysis:
                st.subheader("🔗 Análise de Backlinks e Links Externos")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Links Externos", backlink_analysis.get('total_external_links', 0))
                with col2:
                    st.metric("Domínios Únicos", backlink_analysis.get('unique_referring_domains', 0))
                with col3:
                    st.metric("Score de Qualidade", f"{backlink_analysis.get('link_quality_score', 0)}/100")
                with col4:
                    diversity = len(backlink_analysis.get('anchor_patterns', {}))
                    st.metric("Diversidade Anchor", diversity)
                
                # Top domínios referenciadores
                if backlink_analysis.get('referring_domains'):
                    st.markdown("**🌐 Principais Domínios Referenciados:**")
                    domains_text = ", ".join(backlink_analysis['referring_domains'][:10])
                    st.write(domains_text)
                
                # Padrões de anchor text mais comuns
                if backlink_analysis.get('anchor_patterns'):
                    with st.expander("Ver padrões de anchor text"):
                        anchor_df = pd.DataFrame(list(backlink_analysis['anchor_patterns'].items())[:10], 
                                               columns=['Anchor Text', 'Frequência'])
                        st.dataframe(anchor_df, use_container_width=True)
            
            # Auditoria Avançada de Schema
            if enable_advanced_schema and schema_analysis:
                st.subheader("🏗️ Auditoria Avançada de Schema Markup")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("JSON-LD Schemas", len(schema_analysis.get('json_ld_schemas', [])))
                with col2:
                    st.metric("Microdata Schemas", len(schema_analysis.get('microdata_schemas', [])))
                with col3:
                    st.metric("Score de Cobertura", f"{schema_analysis.get('schema_coverage_score', 0)}/100")
                with col4:
                    st.metric("Oportunidades", len(schema_analysis.get('optimization_opportunities', [])))
                
                # Schemas implementados
                if schema_analysis.get('json_ld_schemas'):
                    st.markdown("**✅ Schemas JSON-LD Detectados:**")
                    for schema in schema_analysis['json_ld_schemas']:
                        completeness = schema.get('completeness', 0)
                        status = "🟢" if completeness >= 80 else "🟡" if completeness >= 60 else "🔴"
                        st.write(f"{status} {schema['type']} - Completude: {completeness}%")
                
                # Schemas recomendados
                if schema_analysis.get('recommended_schemas'):
                    st.markdown("**💡 Schemas Recomendados para este Tipo de Conteúdo:**")
                    st.write(", ".join(schema_analysis['recommended_schemas']))
                
                # Oportunidades de otimização
                if schema_analysis.get('optimization_opportunities'):
                    st.markdown("**🎯 Oportunidades de Otimização:**")
                    for opportunity in schema_analysis['optimization_opportunities']:
                        st.write(f"• {opportunity}")
                
                # Erros de validação
                if schema_analysis.get('validation_errors'):
                    st.markdown("**⚠️ Erros de Validação:**")
                    for error in schema_analysis['validation_errors']:
                        st.error(error)

            # ========== PAINEL TRADICIONAL ==========
            st.subheader("🔗 Verificação de Links Quebrados")
            if not broken_links_list:
                st.success("Ótima notícia! Nenhum link interno quebrado foi encontrado.")
            else:
                st.warning(f"Atenção! Encontramos {len(broken_links_list)} link(s) quebrado(s):")
                df_broken = pd.DataFrame(broken_links_list)
                st.table(df_broken)

            st.subheader("📊 Painel de Auditoria On-Page")
            df = pd.DataFrame({
                "Elemento": ["Título", "Meta Description", "H1 (Primeiro)"],
                "Conteúdo": [
                    onpage_results.get("title", ""), 
                    onpage_results.get("meta_description", ""), 
                    onpage_results.get("h1_text", "")
                ]
            })
            st.table(df)
            
            col1, col2, col3 = st.columns(3)
            with col1: 
                st.metric("Palavras", onpage_results.get("word_count"))
                st.metric("Imagens", onpage_results.get("image_count"))
                st.metric("Imagens sem Alt", onpage_results.get("images_sem_alt_text"))
            with col2: 
                st.metric("Links Internos", onpage_results.get("links_internos"))
                st.metric("Links Externos", onpage_results.get("links_externos"))
                st.metric("Dados Estruturados", onpage_results.get("dados_estruturados"))
            with col3: 
                st.metric("Contagem de H1", onpage_results.get("h1_count"))
                st.metric("Tamanho Título", onpage_results.get("title_length"))
                st.metric("Tamanho Meta Desc.", onpage_results.get("meta_description_length"))
            
            with st.expander("Ver todos os dados técnicos On-Page"): 
                st.json(onpage_results)

            # ========== ANÁLISE COM IA ==========
            st.divider()
            st.subheader("🤖 Análise e Recomendações Avançadas (via Gemini)")
            with st.spinner("A IA está processando todos os dados para criar as melhores recomendações..."):
                prompt_enviado, gemini_sug = generate_gemini_recommendations(
                    onpage_results, 
                    url, 
                    content_analysis, 
                    backlink_analysis, 
                    schema_analysis
                )
                
                with st.expander("Clique para ver o prompt exato enviado para a IA"):
                    st.code(prompt_enviado, language="markdown")
                
                st.markdown(gemini_sug)

            # ========== DADOS TÉCNICOS EXPANDIDOS ==========
            if any([content_analysis, backlink_analysis, schema_analysis]):
                st.divider()
                with st.expander("🔧 Ver dados técnicos das análises avançadas"):
                    if content_analysis:
                        st.subheader("Análise de Conteúdo - Dados Técnicos")
                        st.json(content_analysis)
                    
                    if backlink_analysis:
                        st.subheader("Análise de Backlinks - Dados Técnicos")
                        st.json(backlink_analysis)
                    
                    if schema_analysis:
                        st.subheader("Schema Markup - Dados Técnicos")
                        st.json(schema_analysis)

        except ConnectionError as e:
            st.error(f"Erro de Conexão: {e}")
        except Exception as e:
            st.error(f"Opa, um erro inesperado ocorreu: {e}")
            st.exception(e)

# ========== RODAPÉ ==========
st.divider()
st.markdown("""
### 🚀 SEO AI Auditor Pro - Versão Avançada

**Novas funcionalidades implementadas:**

#### 📝 Análise de Conteúdo Avançada
- **Score de Legibilidade Flesch** adaptado para português
- **Análise de qualidade do conteúdo** (estrutura, densidade, hierarquia)
- **Top palavras-chave** extraídas automaticamente
- **Verificação de hierarquia de headings**

#### 🔗 Análise de Backlinks Básica
- **Identificação de links externos** e domínios referenciadores
- **Análise de diversidade de anchor text**
- **Score de qualidade dos links** baseado em boas práticas
- **Detecção de padrões de linkagem**

#### 🏗️ Auditoria Avançada de Schema Markup
- **Validação de JSON-LD** com detecção de erros
- **Análise de completude** dos schemas implementados
- **Sugestões personalizadas** baseadas no tipo de conteúdo
- **Score de cobertura** e oportunidades de otimização

**Desenvolvido com:** Python, Streamlit, Google Gemini AI, PageSpeed Insights API, Beautiful Soup

---
💡 **Dica:** Use as análises avançadas para obter insights mais profundos sobre a qualidade do seu conteúdo e otimização técnica.
""")

# Rate limiting
if 'analysis_count' not in st.session_state:
    st.session_state.analysis_count = 0
    st.session_state.last_analysis_time = datetime.now()

if datetime.now() - st.session_state.last_analysis_time > timedelta(hours=1):
    st.session_state.analysis_count = 0
    st.session_state.last_analysis_time = datetime.now()
