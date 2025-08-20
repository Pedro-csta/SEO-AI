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

# ========== FUNÇÕES DE LEGIBILIDADE SIMPLIFICADAS ==========
def simple_sentence_tokenize(text):
    """Tokenização simples de sentenças sem NLTK"""
    # Remove quebras de linha e espaços extras
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Divide por pontos finais, exclamações e interrogações
    sentences = re.split(r'[.!?]+', text)
    
    # Remove sentenças muito curtas (menos de 3 palavras)
    sentences = [s.strip() for s in sentences if len(s.strip().split()) >= 3]
    
    return sentences

def simple_word_tokenize(text):
    """Tokenização simples de palavras sem NLTK"""
    # Remove pontuação e converte para minúsculas
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    
    # Divide por espaços e remove palavras muito curtas
    words = [word.strip() for word in text.split() if len(word.strip()) >= 2]
    
    return words

def portuguese_stopwords():
    """Lista básica de stopwords em português"""
    return {
        'a', 'o', 'e', 'é', 'de', 'do', 'da', 'em', 'um', 'uma', 'para', 'com', 'por', 
        'que', 'se', 'na', 'no', 'os', 'as', 'dos', 'das', 'ao', 'aos', 'à', 'às',
        'mas', 'ou', 'ser', 'ter', 'seu', 'sua', 'seus', 'suas', 'foi', 'são', 'não',
        'ele', 'ela', 'eles', 'elas', 'isso', 'esta', 'este', 'estas', 'estes',
        'como', 'mais', 'muito', 'ainda', 'até', 'já', 'só', 'bem', 'todo', 'toda',
        'todos', 'todas', 'outro', 'outra', 'outros', 'outras', 'mesmo', 'mesma'
    }

def calculate_flesch_reading_ease(text):
    """Calcula o Flesch Reading Ease simplificado"""
    sentences = simple_sentence_tokenize(text)
    words = simple_word_tokenize(text)
    
    if not sentences or not words:
        return 0
    
    # Conta sílabas aproximadamente (vogais)
    syllable_count = 0
    for word in words:
        syllables = len(re.findall(r'[aeiouáéíóúâêîôûàèìòùãõy]', word.lower()))
        syllable_count += max(1, syllables)  # Mínimo 1 sílaba por palavra
    
    # Fórmula Flesch simplificada
    avg_sentence_length = len(words) / len(sentences)
    avg_syllables_per_word = syllable_count / len(words)
    
    flesch_score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
    
    return max(0, min(100, flesch_score))

def calculate_reading_level(text):
    """Calcula nível de leitura baseado em comprimento de sentenças e palavras"""
    sentences = simple_sentence_tokenize(text)
    words = simple_word_tokenize(text)
    
    if not sentences or not words:
        return 0
    
    avg_sentence_length = len(words) / len(sentences)
    avg_word_length = sum(len(word) for word in words) / len(words)
    
    # Fórmula simplificada baseada em complexidade
    reading_level = (avg_sentence_length * 0.39) + (avg_word_length * 11.8) - 15.59
    
    return max(0, reading_level)

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

# ========== NOVA FUNCIONALIDADE: ANÁLISE AVANÇADA DE CONTEÚDO ==========
def analyze_content_advanced(soup, url):
    """Análise avançada de conteúdo com métricas de legibilidade e estrutura"""
    analysis = {
        "readability": {},
        "content_structure": {},
        "semantic_analysis": {},
        "content_quality": {},
        "headings_analysis": {}
    }
    
    # Extrai texto principal
    body = soup.find("body")
    if not body:
        return analysis
    
    # Remove scripts, styles e elementos não relevantes
    for script in body(["script", "style", "nav", "footer", "aside"]):
        script.decompose()
    
    text = body.get_text()
    sentences = simple_sentence_tokenize(text)
    words = simple_word_tokenize(text)
    
    # Remove stopwords
    stop_words = portuguese_stopwords()
    filtered_words = [word for word in words if word.isalnum() and word not in stop_words]
    
    # === ANÁLISE DE LEGIBILIDADE ===
    if len(text.strip()) > 50:  # Só analisa se tiver conteúdo suficiente
        try:
            flesch_score = calculate_flesch_reading_ease(text)
            reading_level = calculate_reading_level(text)
            
            analysis["readability"]["flesch_score"] = round(flesch_score, 2)
            analysis["readability"]["reading_level"] = round(reading_level, 2)
        except:
            analysis["readability"]["flesch_score"] = "N/A"
            analysis["readability"]["reading_level"] = "N/A"
        
        # Calcula métricas customizadas
        avg_sentence_length = len(words) / len(sentences) if sentences else 0
        analysis["readability"]["avg_sentence_length"] = round(avg_sentence_length, 2)
        
        # Classifica legibilidade
        flesch = analysis["readability"]["flesch_score"]
        if isinstance(flesch, (int, float)):
            if flesch >= 80:
                analysis["readability"]["level"] = "Muito Fácil"
                analysis["readability"]["level_color"] = "green"
            elif flesch >= 65:
                analysis["readability"]["level"] = "Fácil"
                analysis["readability"]["level_color"] = "lightgreen"
            elif flesch >= 50:
                analysis["readability"]["level"] = "Médio"
                analysis["readability"]["level_color"] = "orange"
            else:
                analysis["readability"]["level"] = "Difícil"
                analysis["readability"]["level_color"] = "red"
        else:
            analysis["readability"]["level"] = "N/A"
            analysis["readability"]["level_color"] = "gray"
    
    # === ANÁLISE DE ESTRUTURA DE CONTEÚDO ===
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    
    headings_structure = []
    for heading in headings:
        headings_structure.append({
            'level': heading.name,
            'text': heading.get_text(strip=True),
            'length': len(heading.get_text(strip=True))
        })
    
    analysis["headings_analysis"]["total_headings"] = len(headings)
    analysis["headings_analysis"]["structure"] = headings_structure
    
    # Analisa hierarquia de headings
    h_levels = [h['level'] for h in headings_structure]
    h1_count = h_levels.count('h1')
    h2_count = h_levels.count('h2')
    h3_count = h_levels.count('h3')
    
    analysis["headings_analysis"]["h1_count"] = h1_count
    analysis["headings_analysis"]["h2_count"] = h2_count
    analysis["headings_analysis"]["h3_count"] = h3_count
    
    # Verifica hierarquia lógica
    hierarchy_issues = []
    if h1_count == 0:
        hierarchy_issues.append("Ausência de H1")
    elif h1_count > 1:
        hierarchy_issues.append("Múltiplos H1")
    
    if h2_count == 0 and len(text.split()) > 500:
        hierarchy_issues.append("Falta de H2 em conteúdo longo")
    
    analysis["headings_analysis"]["hierarchy_issues"] = hierarchy_issues
    
    # === ANÁLISE SEMÂNTICA ===
    # Densidade de palavras-chave (top 10)
    word_freq = Counter(filtered_words)
    top_words = dict(word_freq.most_common(10))
    analysis["semantic_analysis"]["top_keywords"] = top_words
    analysis["semantic_analysis"]["vocabulary_richness"] = len(set(filtered_words)) / len(filtered_words) if filtered_words else 0
    
    # === QUALIDADE DO CONTEÚDO ===
    paragraphs = soup.find_all('p')
    paragraph_lengths = [len(p.get_text().split()) for p in paragraphs if p.get_text().strip()]
    
    analysis["content_quality"]["paragraph_count"] = len(paragraph_lengths)
    analysis["content_quality"]["avg_paragraph_length"] = round(sum(paragraph_lengths) / len(paragraph_lengths), 2) if paragraph_lengths else 0
    analysis["content_quality"]["total_words"] = len(words)
    analysis["content_quality"]["total_sentences"] = len(sentences)
    
    # Detecta conteúdo duplicado simples
    unique_sentences = set(sentences)
    duplication_ratio = 1 - (len(unique_sentences) / len(sentences)) if sentences else 0
    analysis["content_quality"]["duplication_ratio"] = round(duplication_ratio * 100, 2)
    
    # Score de qualidade geral do conteúdo
    quality_score = 0
    
    # Pontuação baseada em comprimento
    word_count = len(words)
    if word_count >= 1000:
        quality_score += 25
    elif word_count >= 500:
        quality_score += 20
    elif word_count >= 300:
        quality_score += 15
    elif word_count >= 150:
        quality_score += 10
    
    # Pontuação baseada em estrutura
    if h1_count == 1:
        quality_score += 15
    if h2_count >= 2:
        quality_score += 10
    if len(paragraph_lengths) >= 3:
        quality_score += 10
    
    # Pontuação baseada em legibilidade
    if isinstance(flesch, (int, float)):
        if flesch >= 50:
            quality_score += 20
        elif flesch >= 30:
            quality_score += 15
        else:
            quality_score += 5
    
    # Pontuação baseada em variedade vocabular
    if analysis["semantic_analysis"]["vocabulary_richness"] >= 0.7:
        quality_score += 10
    elif analysis["semantic_analysis"]["vocabulary_richness"] >= 0.5:
        quality_score += 7
    
    # Penalidade por duplicação
    if duplication_ratio > 0.3:
        quality_score -= 10
    
    analysis["content_quality"]["quality_score"] = min(quality_score, 100)
    
    return analysis

# ========== NOVA FUNCIONALIDADE: ANÁLISE DE BACKLINKS E LINKS EXTERNOS ==========
def analyze_backlinks_and_external_links(soup, url):
    """Análise de backlinks e links externos"""
    analysis = {
        "external_links": [],
        "internal_links": [],
        "link_metrics": {},
        "link_quality": {},
        "anchor_analysis": {}
    }
    
    base_domain = urlparse(url).netloc
    all_links = soup.find_all('a', href=True)
    
    external_links = []
    internal_links = []
    
    for link in all_links:
        href = link.get('href', '')
        anchor_text = link.get_text(strip=True)
        
        if not href or href.startswith(('#', 'tel:', 'mailto:', 'javascript:')):
            continue
        
        # Resolve URL completa
        full_url = urljoin(url, href)
        parsed_url = urlparse(full_url)
        
        link_data = {
            'url': full_url,
            'anchor_text': anchor_text,
            'anchor_length': len(anchor_text),
            'title': link.get('title', ''),
            'rel': link.get('rel', []),
            'target': link.get('target', ''),
            'domain': parsed_url.netloc
        }
        
        # Classifica como interno ou externo
        if parsed_url.netloc == base_domain or parsed_url.netloc == '':
            internal_links.append(link_data)
        else:
            external_links.append(link_data)
    
    analysis["external_links"] = external_links[:50]  # Limita para performance
    analysis["internal_links"] = internal_links[:50]  # Limita para performance
    
    # === MÉTRICAS GERAIS ===
    analysis["link_metrics"]["total_links"] = len(all_links)
    analysis["link_metrics"]["external_count"] = len(external_links)
    analysis["link_metrics"]["internal_count"] = len(internal_links)
    analysis["link_metrics"]["external_ratio"] = round(len(external_links) / len(all_links) * 100, 2) if all_links else 0
    
    # === ANÁLISE DE QUALIDADE DOS LINKS ===
    # Links externos com nofollow
    nofollow_external = [link for link in external_links if 'nofollow' in link.get('rel', [])]
    analysis["link_quality"]["nofollow_external_count"] = len(nofollow_external)
    analysis["link_quality"]["nofollow_ratio"] = round(len(nofollow_external) / len(external_links) * 100, 2) if external_links else 0
    
    # Links para domínios autoritários (lista básica)
    authoritative_domains = {
        'wikipedia.org', 'gov.br', 'edu.br', 'google.com', 'youtube.com',
        'facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com',
        'ibge.gov.br', 'planalto.gov.br', 'mec.gov.br'
    }
    
    authoritative_links = []
    for link in external_links:
        domain = link['domain'].lower()
        for auth_domain in authoritative_domains:
            if auth_domain in domain:
                authoritative_links.append(link)
                break
    
    analysis["link_quality"]["authoritative_links"] = len(authoritative_links)
    analysis["link_quality"]["authority_ratio"] = round(len(authoritative_links) / len(external_links) * 100, 2) if external_links else 0
    
    # === ANÁLISE DE ANCHOR TEXT ===
    all_anchors = [link['anchor_text'] for link in all_links if link.get('anchor_text')]
    anchor_lengths = [len(anchor) for anchor in all_anchors if anchor]
    
    analysis["anchor_analysis"]["total_anchors"] = len(all_anchors)
    analysis["anchor_analysis"]["avg_anchor_length"] = round(sum(anchor_lengths) / len(anchor_lengths), 2) if anchor_lengths else 0
    
    # Classifica tipos de anchor text
    exact_match_anchors = []
    branded_anchors = []
    generic_anchors = []
    empty_anchors = []
    
    brand_terms = base_domain.split('.')[0].lower()  # Termo da marca baseado no domínio
    
    for link in all_links:
        anchor = link.get('anchor_text', '').strip().lower()
        
        if not anchor:
            empty_anchors.append(link)
        elif any(generic in anchor for generic in ['clique aqui', 'saiba mais', 'leia mais', 'aqui', 'continue']):
            generic_anchors.append(link)
        elif brand_terms in anchor:
            branded_anchors.append(link)
        else:
            exact_match_anchors.append(link)
    
    analysis["anchor_analysis"]["empty_anchors"] = len(empty_anchors)
    analysis["anchor_analysis"]["generic_anchors"] = len(generic_anchors)
    analysis["anchor_analysis"]["branded_anchors"] = len(branded_anchors)
    analysis["anchor_analysis"]["exact_match_anchors"] = len(exact_match_anchors)
    
    # Top domínios linkados
    external_domains = [link['domain'] for link in external_links]
    domain_counter = Counter(external_domains)
    analysis["link_quality"]["top_external_domains"] = dict(domain_counter.most_common(10))
    
    # Score de qualidade dos links
    link_score = 0
    
    # Pontuação por proporção balanceada
    if 10 <= analysis["link_metrics"]["external_ratio"] <= 30:
        link_score += 20
    elif analysis["link_metrics"]["external_ratio"] <= 50:
        link_score += 15
    
    # Pontuação por links autoritários
    if analysis["link_quality"]["authority_ratio"] >= 20:
        link_score += 25
    elif analysis["link_quality"]["authority_ratio"] >= 10:
        link_score += 20
    elif analysis["link_quality"]["authority_ratio"] >= 5:
        link_score += 15
    
    # Pontuação por uso adequado de nofollow
    if 30 <= analysis["link_quality"]["nofollow_ratio"] <= 70:
        link_score += 20
    elif analysis["link_quality"]["nofollow_ratio"] <= 80:
        link_score += 15
    
    # Penalidade por anchor text genérico excessivo
    generic_ratio = len(generic_anchors) / len(all_anchors) * 100 if all_anchors else 0
    if generic_ratio < 20:
        link_score += 15
    elif generic_ratio < 40:
        link_score += 10
    elif generic_ratio > 60:
        link_score -= 10
    
    # Penalidade por muitos anchors vazios
    empty_ratio = len(empty_anchors) / len(all_anchors) * 100 if all_anchors else 0
    if empty_ratio < 10:
        link_score += 10
    elif empty_ratio > 25:
        link_score -= 15
    
    # Pontuação por links internos adequados
    if 20 <= analysis["link_metrics"]["internal_count"] <= 100:
        link_score += 10
    elif analysis["link_metrics"]["internal_count"] > 100:
        link_score += 5
    
    analysis["link_quality"]["link_score"] = max(min(link_score, 100), 0)
    
    return analysis

def test_external_links_status(external_links_sample):
    """Testa o status de uma amostra de links externos"""
    if not external_links_sample:
        return []
    
    # Testa apenas os primeiros 10 links para não sobrecarregar
    sample = external_links_sample[:10]
    results = []
    
    headers = {"User-Agent": "Mozilla/5.0 (compatible; SEO Checker)"}
    
    for link in sample:
        try:
            response = requests.head(link['url'], headers=headers, timeout=10, allow_redirects=True)
            status = response.status_code
            
            if status < 400:
                status_class = "✅ OK"
                color = "green"
            elif status < 500:
                status_class = "⚠️ Client Error"
                color = "orange"
            else:
                status_class = "❌ Server Error"
                color = "red"
            
            results.append({
                'url': link['url'],
                'anchor': link['anchor_text'][:50],
                'status': status,
                'status_class': status_class,
                'color': color
            })
            
        except requests.RequestException:
            results.append({
                'url': link['url'],
                'anchor': link['anchor_text'][:50],
                'status': 'Timeout/Error',
                'status_class': "❌ Error",
                'color': "red"
            })
        
        time.sleep(0.2)  # Rate limiting
    
    return results

# ========== FUNÇÕES DE VISUALIZAÇÃO PARA AS NOVAS FUNCIONALIDADES ==========
def create_content_quality_dashboard(content_analysis):
    """Cria dashboard visual para análise de conteúdo"""
    if not content_analysis or not content_analysis.get('content_quality'):
        return None
    
    quality_data = content_analysis['content_quality']
    readability_data = content_analysis.get('readability', {})
    
    # Cria subplots
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Qualidade Geral', 'Legibilidade', 'Estrutura do Conteúdo', 'Distribuição de Palavras'),
        specs=[[{"type": "indicator"}, {"type": "indicator"}],
               [{"type": "bar"}, {"type": "pie"}]]
    )
    
    # Gauge de qualidade geral
    quality_score = quality_data.get('quality_score', 0)
    color = "green" if quality_score >= 70 else "orange" if quality_score >= 50 else "red"
    
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=quality_score,
        title={'text': "Score de Qualidade"},
        gauge={'axis': {'range': [None, 100]},
               'bar': {'color': color},
               'steps': [{'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 70], 'color': "yellow"},
                        {'range': [70, 100], 'color': "lightgreen"}],
               'threshold': {'line': {'color': "red", 'width': 4},
                           'thickness': 0.75, 'value': 90}}
    ), row=1, col=1)
    
    # Gauge de legibilidade
    flesch_score = readability_data.get('flesch_score', 0)
    if isinstance(flesch_score, (int, float)):
        flesch_color = "green" if flesch_score >= 60 else "orange" if flesch_score >= 30 else "red"
        
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=flesch_score,
            title={'text': "Flesch Reading Ease"},
            gauge={'axis': {'range': [0, 100]},
                   'bar': {'color': flesch_color},
                   'steps': [{'range': [0, 30], 'color': "lightcoral"},
                            {'range': [30, 60], 'color': "yellow"},
                            {'range': [60, 100], 'color': "lightgreen"}]}
        ), row=1, col=2)
    
    # Gráfico de estrutura
    headings_data = content_analysis.get('headings_analysis', {})
    if headings_data:
        h_counts = [
            headings_data.get('h1_count', 0),
            headings_data.get('h2_count', 0),
            headings_data.get('h3_count', 0)
        ]
        h_labels = ['H1', 'H2', 'H3']
        
        fig.add_trace(go.Bar(
            x=h_labels,
            y=h_counts,
            name="Headings",
            marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1']
        ), row=2, col=1)
    
    # Gráfico de distribuição de palavras-chave
    semantic_data = content_analysis.get('semantic_analysis', {})
    top_words = semantic_data.get('top_keywords', {})
    if top_words:
        words = list(top_words.keys())[:6]  # Top 6 palavras
        counts = list(top_words.values())[:6]
        
        fig.add_trace(go.Pie(
            labels=words,
            values=counts,
            name="Top Keywords"
        ), row=2, col=2)
    
    fig.update_layout(
        height=600,
        showlegend=False,
        title_text="Dashboard de Análise de Conteúdo",
        title_x=0.5
    )
    
    return fig

def create_links_analysis_dashboard(links_analysis):
    """Cria dashboard visual para análise de links"""
    if not links_analysis or not links_analysis.get('link_metrics'):
        return None
    
    metrics = links_analysis['link_metrics']
    quality = links_analysis['link_quality']
    anchor = links_analysis['anchor_analysis']
    
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Score de Links', 'Distribuição de Links', 'Tipos de Anchor Text', 'Qualidade dos Links'),
        specs=[[{"type": "indicator"}, {"type": "pie"}],
               [{"type": "bar"}, {"type": "bar"}]]
    )
    
    # Gauge do score de links
    link_score = quality.get('link_score', 0)
    score_color = "green" if link_score >= 70 else "orange" if link_score >= 50 else "red"
    
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=link_score,
        title={'text': "Score de Links"},
        gauge={'axis': {'range': [None, 100]},
               'bar': {'color': score_color},
               'steps': [{'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 70], 'color': "yellow"},
                        {'range': [70, 100], 'color': "lightgreen"}]}
    ), row=1, col=1)
    
    # Distribuição interno vs externo
    internal_count = metrics.get('internal_count', 0)
    external_count = metrics.get('external_count', 0)
    
    fig.add_trace(go.Pie(
        labels=['Links Internos', 'Links Externos'],
        values=[internal_count, external_count],
        marker_colors=['#4ECDC4', '#FF6B6B']
    ), row=1, col=2)
    
    # Tipos de anchor text
    anchor_types = ['Genérico', 'Marca', 'Exato', 'Vazio']
    anchor_counts = [
        anchor.get('generic_anchors', 0),
        anchor.get('branded_anchors', 0),
        anchor.get('exact_match_anchors', 0),
        anchor.get('empty_anchors', 0)
    ]
    
    fig.add_trace(go.Bar(
        x=anchor_types,
        y=anchor_counts,
        name="Anchor Types",
        marker_color=['#FF9F43', '#10AC84', '#5F27CD', '#EE5A24']
    ), row=2, col=1)
    
    # Métricas de qualidade
    quality_labels = ['Autoritários', 'Nofollow', 'Status OK']
    quality_values = [
        quality.get('authoritative_links', 0),
        quality.get('nofollow_external_count', 0),
        external_count - quality.get('nofollow_external_count', 0)  # Aproximação
    ]
    
    fig.add_trace(go.Bar(
        x=quality_labels,
        y=quality_values,
        name="Link Quality",
        marker_color=['#00D2D3', '#FF6B6B', '#4ECDC4']
    ), row=2, col=2)
    
    fig.update_layout(
        height=600,
        showlegend=False,
        title_text="Dashboard de Análise de Links",
        title_x=0.5
    )
    
    return fig

# ========== CONTINUA COM TODAS AS FUNÇÕES EXISTENTES ==========
# [Todo o código existente permanece igual - apenas adiciono as importações no topo]

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
    """Cria visualização profissional e legível do sitemap"""
    if not site_structure.get('structure'):
        return None
    
    pages = site_structure['structure']
    
    # Agrupa e organiza por profundidade
    depth_groups = {}
    for page in pages:
        depth = page['depth']
        if depth not in depth_groups:
            depth_groups[depth] = []
        depth_groups[depth].append(page)
    
    # Limita páginas por nível para melhor visualização
    max_per_level = 12
    for depth in depth_groups:
        if len(depth_groups[depth]) > max_per_level:
            depth_groups[depth] = depth_groups[depth][:max_per_level]
    
    # Cria um layout mais profissional tipo organograma
    fig = go.Figure()
    
    # Paleta de cores profissional
    colors = ['#1E3A8A', '#7C3AED', '#059669', '#DC2626', '#EA580C', '#0891B2']
    
    # Configurações de layout
    level_height = 150  # Espaçamento vertical entre níveis
    max_width = 1200   # Largura máxima do gráfico
    
    for depth in sorted(depth_groups.keys()):
        pages_at_depth = depth_groups[depth]
        color = colors[depth % len(colors)]
        
        # Calcula posicionamento horizontal
        num_pages = len(pages_at_depth)
        if num_pages == 1:
            x_positions = [0]
        else:
            spacing = max_width / (num_pages + 1)
            x_positions = [spacing * (i + 1) - max_width/2 for i in range(num_pages)]
        
        y_position = -depth * level_height
        
        # Prepara textos mais limpos
        clean_texts = []
        hover_texts = []
        
        for i, page in enumerate(pages_at_depth):
            # Extrai texto limpo
            page_text = page['text'].strip()
            
            if not page_text or len(page_text) < 3:
                # Extrai da URL
                path_parts = page['path'].strip('/').split('/')
                if path_parts and path_parts[-1]:
                    page_text = path_parts[-1].replace('-', ' ').replace('_', ' ')
                    page_text = ' '.join(word.capitalize() for word in page_text.split())
                else:
                    page_text = "Home" if depth == 0 else f"Página {i+1}"
            
            # Limita e formata o texto
            if len(page_text) > 15:
                display_text = page_text[:12] + "..."
            else:
                display_text = page_text
            
            clean_texts.append(display_text)
            
            # Texto do hover mais informativo
            hover_text = f"<b>{page_text}</b><br>"
            hover_text += f"URL: {page['url']}<br>"
            hover_text += f"Nível: {depth}<br>"
            hover_text += f"Profundidade: {len(page['path'].strip('/').split('/')) if page['path'] != '/' else 0}"
            hover_texts.append(hover_text)
        
        # Adiciona os nós com estilo profissional
        fig.add_trace(go.Scatter(
            x=x_positions,
            y=[y_position] * len(x_positions),
            mode='markers+text',
            marker=dict(
                size=45,
                color=color,
                line=dict(width=3, color='white'),
                symbol='circle'
            ),
            text=clean_texts,
            textposition="middle center",
            textfont=dict(
                size=11, 
                color='white',
                family="Arial Black"
            ),
            hovertemplate='%{customdata}<extra></extra>',
            customdata=hover_texts,
            name=f'Nível {depth}',
            showlegend=True
        ))
        
        # Adiciona labels de nível
        fig.add_annotation(
            x=-max_width/2 - 100,
            y=y_position,
            text=f"<b>Nível {depth}</b>",
            showarrow=False,
            font=dict(size=14, color=color, family="Arial"),
            xanchor="right"
        )
    
    # Adiciona conexões mais elegantes
    for depth in sorted(depth_groups.keys())[:-1]:
        next_depth = depth + 1
        if next_depth in depth_groups:
            current_level = depth_groups[depth]
            next_level = depth_groups[next_depth]
            
            current_y = -depth * level_height
            next_y = -next_depth * level_height
            
            # Conecta home page com páginas principais
            if depth == 0 and len(current_level) == 1:
                home_x = 0
                next_spacing = max_width / (len(next_level) + 1)
                
                for i, _ in enumerate(next_level):
                    next_x = next_spacing * (i + 1) - max_width/2
                    
                    fig.add_trace(go.Scatter(
                        x=[home_x, next_x],
                        y=[current_y, next_y],
                        mode='lines',
                        line=dict(
                            color='rgba(100,100,100,0.4)', 
                            width=2,
                            dash='dot'
                        ),
                        showlegend=False,
                        hoverinfo='skip'
                    ))
            else:
                # Conecta níveis subsequentes de forma mais sutil
                max_connections = min(len(current_level), len(next_level), 6)
                for i in range(max_connections):
                    if i < len(current_level) and i < len(next_level):
                        current_spacing = max_width / (len(current_level) + 1)
                        next_spacing = max_width / (len(next_level) + 1)
                        
                        current_x = current_spacing * (i + 1) - max_width/2
                        next_x = next_spacing * (i + 1) - max_width/2
                        
                        fig.add_trace(go.Scatter(
                            x=[current_x, next_x],
                            y=[current_y, next_y],
                            mode='lines',
                            line=dict(
                                color='rgba(150,150,150,0.3)', 
                                width=1
                            ),
                            showlegend=False,
                            hoverinfo='skip'
                        ))
    
    # Layout profissional
    fig.update_layout(
        title=dict(
            text=f"🏗️ Arquitetura do Site: {site_structure.get('domain', 'Site')}",
            font=dict(size=18, family="Arial", color="#1F2937"),
            x=0.5,
            xanchor="center"
        ),
        xaxis=dict(
            showgrid=False, 
            zeroline=False, 
            showticklabels=False,
            range=[-max_width/2 - 150, max_width/2 + 50]
        ),
        yaxis=dict(
            showgrid=False, 
            zeroline=False, 
            showticklabels=False,
            scaleanchor="x",
            scaleratio=1
        ),
        height=600,
        plot_bgcolor='#FAFAFA',
        paper_bgcolor='white',
        margin=dict(l=50, r=50, t=80, b=50),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.05,
            xanchor="center",
            x=0.5,
            font=dict(size=12, family="Arial")
        ),
        hovermode='closest'
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
    
    deep_analysis = st.checkbox("🔍 Análise profunda", value=True,
                               help="Inclui análise de dados estruturados")
    
    extract_structure = st.checkbox("🗺️ Mapear estrutura do site", value=True,
                                   help="Cria mapa visual da arquitetura do site")
    
    content_analysis_enabled = st.checkbox("📝 Análise avançada de conteúdo", value=True,
                                          help="Análise de legibilidade, estrutura e qualidade do conteúdo")
    
    links_analysis_enabled = st.checkbox("🔗 Análise de links e backlinks", value=True,
                                        help="Análise detalhada de links internos e externos")
    
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
    **Legibilidade:** Score Flesch > 60  
    **Links:** 20-100 links internos
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
                structured_data = {}
                site_structure = {}
                content_analysis = {}
                links_analysis = {}
                
                if deep_analysis:
                    structured_data = analyze_structured_data(soup_principal)
                
                if extract_structure:
                    with st.spinner("🗺️ Mapeando estrutura do site..."):
                        site_structure = extract_site_structure(url_principal, max_pages=max_pages_sitemap)
                
                if content_analysis_enabled:
                    with st.spinner("📝 Analisando qualidade do conteúdo..."):
                        content_analysis = analyze_content_advanced(soup_principal, url_principal)
                
                if links_analysis_enabled:
                    with st.spinner("🔗 Analisando links e backlinks..."):
                        links_analysis = analyze_backlinks_and_external_links(soup_principal, url_principal)
                
                psi_principal = get_pagespeed_insights(url_principal)
                broken_links_principal = check_broken_links(url_principal, links_principais)
                
            except Exception as e:
                st.error(f"Erro na análise: {str(e)}")
                st.stop()
        
        st.success("✅ Análise principal concluída!")
        
        # --- DASHBOARD PRINCIPAL ---
        st.divider()
        st.subheader(f"📊 Dashboard: {urlparse(url_principal).netloc}")
        
        # Calcula score geral (sem palavra-chave)
        overall_score = calculate_overall_seo_score(onpage_principal, psi_principal, {}, structured_data)
        
        # === SEÇÃO DE ANÁLISE DE CONTEÚDO ===
        if content_analysis_enabled and content_analysis:
            st.markdown("#### 📝 Análise Avançada de Conteúdo")
            
            # Dashboard de conteúdo
            content_dashboard = create_content_quality_dashboard(content_analysis)
            if content_dashboard:
                st.plotly_chart(content_dashboard, use_container_width=True)
            
            # Métricas detalhadas de conteúdo
            col1, col2, col3, col4 = st.columns(4)
            
            quality_data = content_analysis.get('content_quality', {})
            readability_data = content_analysis.get('readability', {})
            headings_data = content_analysis.get('headings_analysis', {})
            
            with col1:
                quality_score = quality_data.get('quality_score', 0)
                st.metric("🎯 Score de Qualidade", f"{quality_score}/100")
                
                word_count = quality_data.get('total_words', 0)
                st.metric("📝 Total de Palavras", word_count)
            
            with col2:
                flesch_score = readability_data.get('flesch_score', 'N/A')
                if isinstance(flesch_score, (int, float)):
                    st.metric("📖 Legibilidade (Flesch)", f"{flesch_score:.1f}")
                else:
                    st.metric("📖 Legibilidade", "N/A")
                
                level = readability_data.get('level', 'N/A')
                level_color = readability_data.get('level_color', 'gray')
                st.markdown(f"<span style='color: {level_color}'>**{level}**</span>", unsafe_allow_html=True)
            
            with col3:
                total_headings = headings_data.get('total_headings', 0)
                st.metric("🏷️ Total de Headings", total_headings)
                
                h1_count = headings_data.get('h1_count', 0)
                h1_status = "✅" if h1_count == 1 else "⚠️" if h1_count > 1 else "❌"
                st.metric("H1 Count", f"{h1_count} {h1_status}")
            
            with col4:
                paragraph_count = quality_data.get('paragraph_count', 0)
                st.metric("📄 Parágrafos", paragraph_count)
                
                avg_paragraph = quality_data.get('avg_paragraph_length', 0)
                st.metric("📏 Média Palavras/Parágrafo", f"{avg_paragraph:.1f}")
            
            # Insights de conteúdo
            content_insights = []
            
            if quality_score >= 80:
                content_insights.append("🏆 **Excelente qualidade de conteúdo!**")
            elif quality_score >= 60:
                content_insights.append("👍 **Boa qualidade, com espaço para melhorias**")
            else:
                content_insights.append("⚠️ **Conteúdo precisa de otimização**")
            
            if isinstance(flesch_score, (int, float)):
                if flesch_score < 30:
                    content_insights.append("📚 **Texto muito complexo** - Simplifique frases")
                elif flesch_score > 80:
                    content_insights.append("📖 **Texto muito simples** - Considere mais profundidade")
            
            hierarchy_issues = headings_data.get('hierarchy_issues', [])
            if hierarchy_issues:
                for issue in hierarchy_issues:
                    content_insights.append(f"🏷️ **Estrutura:** {issue}")
            
            if content_insights:
                with st.expander("💡 Insights de Conteúdo"):
                    for insight in content_insights:
                        st.markdown(f"- {insight}")
            
            st.divider()
        
        # === SEÇÃO DE ANÁLISE DE LINKS ===
        if links_analysis_enabled and links_analysis:
            st.markdown("#### 🔗 Análise de Links e Backlinks")
            
            # Dashboard de links
            links_dashboard = create_links_analysis_dashboard(links_analysis)
            if links_dashboard:
                st.plotly_chart(links_dashboard, use_container_width=True)
            
            # Métricas detalhadas de links
            col1, col2, col3, col4 = st.columns(4)
            
            link_metrics = links_analysis.get('link_metrics', {})
            link_quality = links_analysis.get('link_quality', {})
            anchor_analysis = links_analysis.get('anchor_analysis', {})
            
            with col1:
                link_score = link_quality.get('link_score', 0)
                st.metric("🎯 Score de Links", f"{link_score}/100")
                
                total_links = link_metrics.get('total_links', 0)
                st.metric("🔗 Total de Links", total_links)
            
            with col2:
                external_count = link_metrics.get('external_count', 0)
                st.metric("🌐 Links Externos", external_count)
                
                internal_count = link_metrics.get('internal_count', 0)
                st.metric("🏠 Links Internos", internal_count)
            
            with col3:
                authority_ratio = link_quality.get('authority_ratio', 0)
                st.metric("⭐ % Links Autoritários", f"{authority_ratio:.1f}%")
                
                nofollow_ratio = link_quality.get('nofollow_ratio', 0)
                st.metric("🚫 % Nofollow", f"{nofollow_ratio:.1f}%")
            
            with col4:
                generic_anchors = anchor_analysis.get('generic_anchors', 0)
                st.metric("⚠️ Anchors Genéricos", generic_anchors)
                
                empty_anchors = anchor_analysis.get('empty_anchors', 0)
                st.metric("❌ Anchors Vazios", empty_anchors)
            
            # Teste de status dos links externos (amostra)
            external_links_sample = links_analysis.get('external_links', [])
            if external_links_sample:
                with st.expander("🔍 Status dos Links Externos (Amostra)"):
                    with st.spinner("Testando status dos links..."):
                        link_status_results = test_external_links_status(external_links_sample[:5])
                    
                    if link_status_results:
                        for result in link_status_results:
                            col_url, col_anchor, col_status = st.columns([3, 2, 1])
                            with col_url:
                                st.text(result['url'][:60] + "..." if len(result['url']) > 60 else result['url'])
                            with col_anchor:
                                st.text(result['anchor'][:30] + "..." if len(result['anchor']) > 30 else result['anchor'])
                            with col_status:
                                st.markdown(f"<span style='color: {result['color']}'>{result['status_class']}</span>", unsafe_allow_html=True)
            
            # Top domínios linkados
            top_domains = link_quality.get('top_external_domains', {})
            if top_domains:
                with st.expander("🌐 Top Domínios Linkados"):
                    df_domains = pd.DataFrame(list(top_domains.items()), columns=['Domínio', 'Quantidade'])
                    df_domains = df_domains.head(10)  # Top 10
                    
                    fig_domains = px.bar(df_domains, x='Quantidade', y='Domínio', orientation='h',
                                       title="Domínios Mais Linkados", 
                                       color='Quantidade', color_continuous_scale='viridis')
                    fig_domains.update_layout(height=400)
                    st.plotly_chart(fig_domains, use_container_width=True)
            
            # Insights de links
            link_insights = []
            
            if link_score >= 80:
                link_insights.append("🏆 **Excelente estratégia de links!**")
            elif link_score >= 60:
                link_insights.append("👍 **Boa estratégia, pode ser aprimorada**")
            else:
                link_insights.append("⚠️ **Estratégia de links precisa de atenção**")
            
            external_ratio = link_metrics.get('external_ratio', 0)
            if external_ratio > 50:
                link_insights.append("⚠️ **Muitos links externos** - Pode diluir autoridade")
            elif external_ratio < 10:
                link_insights.append("📈 **Poucos links externos** - Considere mais referências")
            
            if authority_ratio < 10:
                link_insights.append("⭐ **Adicione links para sites autoritários** - Melhora credibilidade")
            
            generic_ratio = (generic_anchors / total_links * 100) if total_links > 0 else 0
            if generic_ratio > 30:
                link_insights.append("🎯 **Otimize anchor texts** - Evite textos genéricos")
            
            if link_insights:
                with st.expander("💡 Insights de Links"):
                    for insight in link_insights:
                        st.markdown(f"- {insight}")
            
            st.divider()
        
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
        
        # Segunda linha: Performance detalhada
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
        
        # Performance detalhada
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
            
            # Adiciona métricas das novas análises
            if content_analysis:
                resultado_principal["Content Score"] = content_analysis.get('content_quality', {}).get('quality_score', 0)
                resultado_principal["Flesch Score"] = content_analysis.get('readability', {}).get('flesch_score', 0)
            
            if links_analysis:
                resultado_principal["Links Score"] = links_analysis.get('link_quality', {}).get('link_score', 0)
                resultado_principal["External Links"] = links_analysis.get('link_metrics', {}).get('external_count', 0)
            
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
                                structured_comp = analyze_structured_data(soup_comp) if deep_analysis else {}
                                site_structure_comp = extract_site_structure(url_comp, max_pages=max_pages_sitemap//2) if extract_structure else {}
                                content_comp = analyze_content_advanced(soup_comp, url_comp) if content_analysis_enabled else {}
                                links_comp = analyze_backlinks_and_external_links(soup_comp, url_comp) if links_analysis_enabled else {}
                                
                                comp_score = calculate_overall_seo_score(onpage_comp, psi_comp, {}, structured_comp)
                                
                                # Armazena dados do concorrente para dashboard individual
                                competitor_dashboards.append({
                                    'url': url_comp,
                                    'domain': urlparse(url_comp).netloc,
                                    'onpage': onpage_comp,
                                    'psi': psi_comp,
                                    'structured': structured_comp,
                                    'site_structure': site_structure_comp,
                                    'content': content_comp,
                                    'links': links_comp,
                                    'score': comp_score
                                })
                                
                                resultado_comp = {
                                    "URL": url_comp, 
                                    "Site": urlparse(url_comp).netloc, 
                                    **onpage_comp,
                                    "Performance Mobile": psi_comp.get('mobile', {}).get('psi_performance', 0),
                                    "SEO Score": comp_score
                                }
                                
                                # Adiciona métricas das novas análises
                                if content_comp:
                                    resultado_comp["Content Score"] = content_comp.get('content_quality', {}).get('quality_score', 0)
                                    resultado_comp["Flesch Score"] = content_comp.get('readability', {}).get('flesch_score', 0)
                                
                                if links_comp:
                                    resultado_comp["Links Score"] = links_comp.get('link_quality', {}).get('link_score', 0)
                                    resultado_comp["External Links"] = links_comp.get('link_metrics', {}).get('external_count', 0)
                                
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
                            st.metric("🏷️ Title Length", comp_data['onpage'].get('title_length', 0))
                            h1_count = comp_data['onpage'].get('h1_count', 0)
                            st.metric("📋 H1 Count", h1_count)
                        
                        # Análises adicionais do concorrente
                        if comp_data.get('content'):
                            with st.expander("📝 Análise de Conteúdo"):
                                content_score = comp_data['content'].get('content_quality', {}).get('quality_score', 0)
                                flesch_score = comp_data['content'].get('readability', {}).get('flesch_score', 'N/A')
                                st.metric("Qualidade do Conteúdo", f"{content_score}/100")
                                if isinstance(flesch_score, (int, float)):
                                    st.metric("Legibilidade Flesch", f"{flesch_score:.1f}")
                        
                        if comp_data.get('links'):
                            with st.expander("🔗 Análise de Links"):
                                links_score = comp_data['links'].get('link_quality', {}).get('link_score', 0)
                                external_count = comp_data['links'].get('link_metrics', {}).get('external_count', 0)
                                authority_ratio = comp_data['links'].get('link_quality', {}).get('authority_ratio', 0)
                                st.metric("Score de Links", f"{links_score}/100")
                                st.metric("Links Externos", external_count)
                                st.metric("% Autoritários", f"{authority_ratio:.1f}%")
                        
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
                
                # Colunas para exibição da comparação
                display_columns = [
                    "Site", "SEO Score", "word_count", "Performance Mobile", 
                    "links_internos", "image_count", "title_length"
                ]
                
                # Adiciona novas métricas se disponíveis
                if "Content Score" in df_comparativo.columns:
                    display_columns.insert(-2, "Content Score")
                if "Links Score" in df_comparativo.columns:
                    display_columns.insert(-2, "Links Score")
                if "External Links" in df_comparativo.columns:
                    display_columns.append("External Links")
                
                df_display = df_comparativo[display_columns].rename(columns={
                    "word_count": "Palavras", 
                    "links_internos": "Links Internos", 
                    "image_count": "Imagens",
                    "title_length": "Tam. Título",
                    "Content Score": "Score Conteúdo",
                    "Links Score": "Score Links",
                    "External Links": "Links Externos"
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
                
                # Gráficos adicionais se há dados de conteúdo e links
                if "Score Conteúdo" in df_display.columns or "Score Links" in df_display.columns:
                    col3, col4 = st.columns(2)
                    
                    if "Score Conteúdo" in df_display.columns:
                        with col3:
                            fig_content = px.bar(df_display, x='Site', y='Score Conteúdo',
                                               title="Qualidade do Conteúdo",
                                               color='Site', color_discrete_map=cores)
                            st.plotly_chart(fig_content, use_container_width=True)
                    
                    if "Score Links" in df_display.columns:
                        with col4:
                            fig_links = px.bar(df_display, x='Site', y='Score Links',
                                             title="Qualidade dos Links",
                                             color='Site', color_discrete_map=cores)
                            st.plotly_chart(fig_links, use_container_width=True)
        
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
        
        if deep_analysis and structured_data and len(structured_data.get('schemas_found', [])) == 0:
            issues.append("⚠️ **Dados estruturados ausentes** - Oportunidade perdida para rich snippets")
        
        # Problemas de conteúdo
        if content_analysis:
            content_score = content_analysis.get('content_quality', {}).get('quality_score', 0)
            if content_score < 50:
                issues.append("📝 **Qualidade do conteúdo baixa** - Revise estrutura e legibilidade")
            
            flesch_score = content_analysis.get('readability', {}).get('flesch_score', 0)
            if isinstance(flesch_score, (int, float)) and flesch_score < 30:
                issues.append("📚 **Texto muito complexo** - Simplifique para melhor compreensão")
        
        # Problemas de links
        if links_analysis:
            link_score = links_analysis.get('link_quality', {}).get('link_score', 0)
            if link_score < 50:
                issues.append("🔗 **Estratégia de links precisa melhorar** - Otimize anchor texts e adicione links autoritários")
            
            empty_anchors = links_analysis.get('anchor_analysis', {}).get('empty_anchors', 0)
            if empty_anchors > 5:
                issues.append("🎯 **Muitos links sem texto âncora** - Adicione textos descritivos")
        
        # Exibe problemas encontrados
        if issues:
            st.markdown("#### 🚨 Problemas Identificados")
            for issue in issues[:8]:  # Mostra no máximo 8 problemas principais
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
                "🔗 Estratégia de link building avançada",
                "📊 Análise de comportamento de usuários",
                "🎯 Otimização para featured snippets"
            ]
        elif overall_score >= 60:
            st.warning("🚀 **Bom potencial!** Otimize:")
            recommendations = [
                "📱 Performance mobile (Core Web Vitals)",
                "🎯 Qualidade e estrutura do conteúdo",
                "🖼️ Alt text em todas as imagens",
                "🏗️ Implementação de dados estruturados",
                "🔗 Melhoria da estratégia de links"
            ]
        else:
            st.error("⚠️ **Necessita atenção urgente!** Priorize:")
            recommendations = [
                "📝 Title e meta description adequados",
                "🏷️ Estrutura H1 correta",
                "📄 Conteúdo mais robusto (mín. 300 palavras)",
                "🔧 Correção de problemas técnicos básicos",
                "📚 Melhoria da legibilidade do texto"
            ]
        
        for rec in recommendations:
            st.markdown(f"- {rec}")
        
        # Dados técnicos completos (expansível)
        with st.expander("🔧 Ver todos os dados técnicos"):
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 On-Page", "🚀 Performance", "📝 Conteúdo", "🔗 Links", "🏗️ Estruturados"])
            
            with tab1:
                st.json(onpage_principal)
            
            with tab2:
                if psi_principal:
                    st.json(psi_principal)
                else:
                    st.info("Dados de performance não disponíveis")
            
            with tab3:
                if content_analysis:
                    st.json(content_analysis)
                else:
                    st.info("Análise de conteúdo não realizada")
            
            with tab4:
                if links_analysis:
                    # Mostra apenas métricas principais para evitar sobrecarga
                    links_summary = {
                        "link_metrics": links_analysis.get('link_metrics', {}),
                        "link_quality": links_analysis.get('link_quality', {}),
                        "anchor_analysis": links_analysis.get('anchor_analysis', {}),
                        "external_links_sample": links_analysis.get('external_links', [])[:10]  # Apenas primeiros 10
                    }
                    st.json(links_summary)
                else:
                    st.info("Análise de links não realizada")
            
            with tab5:
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
- ✅ **NOVO:** Análise avançada de conteúdo e legibilidade
- ✅ **NOVO:** Análise de backlinks e links externos
- ✅ Comparação competitiva
- ✅ Score geral de SEO (algoritmo proprietário)

**Tecnologias:** Python, Streamlit, Google Gemini AI, PageSpeed Insights API, Plotly, NLTK

**Novas funcionalidades:**
- 📝 **Análise de Conteúdo:** Score de qualidade, legibilidade Flesch, estrutura de headings
- 🔗 **Análise de Links:** Qualidade de backlinks, anchor texts, links autoritários
- 🎯 **Dashboards Visuais:** Gauges interativos e gráficos detalhados
- 📊 **Comparação Competitiva:** Análise lado a lado com concorrentes

---
💡 **Dica:** Para melhores resultados, execute análises regularmente e monitore as melhorias ao longo do tempo.

**Dependencies necessárias para execução:**
```
streamlit
requests
beautifulsoup4
google-generativeai
pandas
plotly
validators
```

**Nota:** As funcionalidades de análise de legibilidade foram implementadas com algoritmos próprios, 
não necessitando de bibliotecas externas como NLTK ou textstat.
""")

# Rate limiting simples para evitar abuso
if 'analysis_count' not in st.session_state:
    st.session_state.analysis_count = 0
    st.session_state.last_analysis_time = datetime.now()

# Reset contador a cada hora
if datetime.now() - st.session_state.last_analysis_time > timedelta(hours=1):
    st.session_state.analysis_count = 0
    st.session_state.last_analysis_time = datetime.now()

# ========== FOOTER COM INFORMAÇÕES TÉCNICAS ==========
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.8em;'>
<b>SEO AI Strategist Pro v2.0</b> | Desenvolvido com ❤️ para otimização de SEO<br>
🔧 Análise Técnica | 📊 Visualização de Dados | 🤖 Inteligência Artificial | 🏆 Insights Competitivos
</div>
""", unsafe_allow_html=True)
