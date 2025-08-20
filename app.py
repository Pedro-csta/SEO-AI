geo_seo_enabled = st.checkbox("🤖 Análise de GEO (Generative Engine Optimization)", value=True,
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
from textstat import flesch_reading_ease, automated_readability_index
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords

# Download necessário para NLTK (executar apenas uma vez)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    try:
        nltk.download('punkt', quiet=True)
    except:
        nltk.download('punkt_tab', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

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

# ========== NOVA FUNCIONALIDADE: ANÁLISE DE GEO (GENERATIVE ENGINE OPTIMIZATION) ==========
def analyze_geo_ai_optimization(soup, url):
    """Análise de GEO - Generative Engine Optimization para IAs"""
    geo_analysis = {
        "content_structure": {},
        "factual_content": {},
        "ai_friendly_format": {},
        "authority_signals": {},
        "geo_score": 0
    }
    
    text_content = soup.get_text()
    text_lower = text_content.lower()
    
    # === ANÁLISE DE ESTRUTURA DE CONTEÚDO PARA IAs ===
    # Perguntas e respostas (formato FAQ)
    faq_indicators = [
        'o que é', 'como fazer', 'por que', 'quando', 'onde', 'quem',
        'qual a diferença', 'como funciona', 'qual o melhor', 'pergunta',
        'resposta', 'dúvida', 'questão'
    ]
    
    faq_mentions = sum(1 for indicator in faq_indicators if indicator in text_lower)
    geo_analysis["content_structure"]["faq_indicators"] = faq_mentions
    
    # Listas e estruturas organizadas
    lists = soup.find_all(['ul', 'ol'])
    geo_analysis["content_structure"]["lists_count"] = len(lists)
    
    # Tabelas (dados estruturados)
    tables = soup.find_all('table')
    geo_analysis["content_structure"]["tables_count"] = len(tables)
    
    # Headings bem estruturados
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    geo_analysis["content_structure"]["headings_count"] = len(headings)
    
    # Verifica hierarquia lógica de headings
    h_levels = [int(h.name[1]) for h in headings]
    hierarchy_score = 0
    if h_levels:
        # Pontos por ordem lógica (H1 -> H2 -> H3...)
        for i in range(len(h_levels) - 1):
            if h_levels[i+1] <= h_levels[i] + 1:  # Não pula níveis
                hierarchy_score += 1
        hierarchy_score = (hierarchy_score / max(len(h_levels) - 1, 1)) * 100
    
    geo_analysis["content_structure"]["hierarchy_score"] = round(hierarchy_score, 1)
    
    # === ANÁLISE DE CONTEÚDO FACTUAL ===
    # Indicadores de conteúdo factual e autoritativo
    factual_indicators = [
        'segundo', 'de acordo com', 'estudos mostram', 'pesquisa indica',
        'dados revelam', 'estatística', 'porcentagem', '%', 'número',
        'ano', 'em 2023', 'em 2024', 'recente', 'atual'
    ]
    
    factual_mentions = sum(1 for indicator in factual_indicators if indicator in text_lower)
    geo_analysis["factual_content"]["factual_indicators"] = factual_mentions
    
    # Citations e referências
    citations = soup.find_all('cite') + soup.find_all('blockquote')
    geo_analysis["factual_content"]["citations"] = len(citations)
    
    # Links externos para fontes autoritárias
    external_links = soup.find_all('a', href=True)
    authoritative_domains = [
        'wikipedia.org', 'edu.br', 'gov.br', 'ibge.gov.br',
        'nature.com', 'pubmed.gov', 'scholar.google',
        'researchgate.net', 'scielo.org'
    ]
    
    authoritative_links = 0
    for link in external_links:
        href = link.get('href', '').lower()
        if any(domain in href for domain in authoritative_domains):
            authoritative_links += 1
    
    geo_analysis["factual_content"]["authoritative_links"] = authoritative_links
    
    # === ANÁLISE DE FORMATO AMIGÁVEL PARA IA ===
    # Definições claras (importante para IAs)
    definition_patterns = [
        r'\b\w+\s+é\s+', r'\b\w+\s+são\s+', r'definição\s+de',
        r'significa', r'conceito\s+de', r'refere-se\s+a'
    ]
    
    definition_count = 0
    for pattern in definition_patterns:
        definition_count += len(re.findall(pattern, text_lower))
    
    geo_analysis["ai_friendly_format"]["definitions"] = definition_count
    
    # Exemplos práticos
    example_indicators = [
        'por exemplo', 'exemplo', 'como:', 'veja:', 'observe:',
        'considere', 'imagine', 'suponha', 'caso'
    ]
    
    example_mentions = sum(1 for indicator in example_indicators if indicator in text_lower)
    geo_analysis["ai_friendly_format"]["examples"] = example_mentions
    
    # Comparações (úteis para IAs entenderem contexto)
    comparison_indicators = [
        'diferença entre', 'comparado com', 'versus', 'vs',
        'melhor que', 'pior que', 'similar a', 'ao contrário'
    ]
    
    comparison_mentions = sum(1 for indicator in comparison_indicators if indicator in text_lower)
    geo_analysis["ai_friendly_format"]["comparisons"] = comparison_mentions
    
    # Instruções passo a passo
    step_indicators = [
        'passo', 'etapa', 'primeiro', 'segundo', 'terceiro',
        'em seguida', 'depois', 'finalmente', 'para começar'
    ]
    
    step_mentions = sum(1 for indicator in step_indicators if indicator in text_lower)
    geo_analysis["ai_friendly_format"]["step_by_step"] = step_mentions
    
    # === ANÁLISE DE SINAIS DE AUTORIDADE ===
    # Dados do autor
    author_tags = soup.find_all(['meta'], attrs={'name': ['author', 'article:author']})
    author_elements = soup.find_all(['span', 'div', 'p'], class_=lambda x: x and 'author' in x.lower() if x else False)
    
    geo_analysis["authority_signals"]["author_mentioned"] = len(author_tags) + len(author_elements) > 0
    
    # Data de publicação/atualização
    date_tags = soup.find_all(['meta'], attrs={'name': ['publish_date', 'article:published_time', 'article:modified_time']})
    time_elements = soup.find_all(['time'])
    
    geo_analysis["authority_signals"]["date_mentioned"] = len(date_tags) + len(time_elements) > 0
    
    # Schema Article
    has_article_schema = False
    json_scripts = soup.find_all("script", type="application/ld+json")
    for script in json_scripts:
        try:
            data = json.loads(script.string.strip())
            if isinstance(data, dict) and 'Article' in str(data.get('@type', '')):
                has_article_schema = True
                break
        except:
            continue
    
    geo_analysis["authority_signals"]["article_schema"] = has_article_schema
    
    # Comprimento do conteúdo (IAs preferem conteúdo substancial)
    word_count = len(text_content.split())
    geo_analysis["authority_signals"]["word_count"] = word_count
    
    # === CÁLCULO DO SCORE GEO ===
    score = 0
    
    # Estrutura de conteúdo (25 pontos)
    if faq_mentions >= 3: score += 8
    elif faq_mentions >= 1: score += 5
    
    if len(lists) >= 2: score += 5
    elif len(lists) >= 1: score += 3
    
    if len(headings) >= 3: score += 7
    elif len(headings) >= 1: score += 4
    
    if hierarchy_score >= 80: score += 5
    elif hierarchy_score >= 50: score += 3
    
    # Conteúdo factual (25 pontos)
    if factual_mentions >= 5: score += 10
    elif factual_mentions >= 2: score += 6
    
    if authoritative_links >= 2: score += 10
    elif authoritative_links >= 1: score += 6
    
    if len(citations) >= 1: score += 5
    
    # Formato amigável para IA (25 pontos)
    if definition_count >= 3: score += 8
    elif definition_count >= 1: score += 5
    
    if example_mentions >= 2: score += 6
    elif example_mentions >= 1: score += 3
    
    if comparison_mentions >= 1: score += 6
    if step_mentions >= 2: score += 5
    
    # Sinais de autoridade (25 pontos)
    if geo_analysis["authority_signals"]["author_mentioned"]: score += 6
    if geo_analysis["authority_signals"]["date_mentioned"]: score += 6
    if has_article_schema: score += 8
    
    if word_count >= 1000: score += 5
    elif word_count >= 500: score += 3
    
    geo_analysis["geo_score"] = min(score, 100)
    
    return geo_analysis

def create_geo_ai_dashboard(geo_analysis):
    """Cria dashboard visual para análise de GEO (IA)"""
    if not geo_analysis:
        return None
    
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Score GEO (IA)', 'Estrutura para IA', 'Conteúdo Factual', 'Sinais de Autoridade'),
        specs=[[{"type": "indicator"}, {"type": "bar"}],
               [{"type": "bar"}, {"type": "bar"}]]
    )
    
    # Gauge do score GEO
    geo_score = geo_analysis.get('geo_score', 0)
    if geo_score == 0:
        return None
    
    color = "#2F4F4F" if geo_score >= 70 else "#708090" if geo_score >= 50 else "#A9A9A9"
    
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=geo_score,
        title={'text': "Score GEO (IA)", 'font': {'color': '#2F4F4F'}},
        gauge={'axis': {'range': [None, 100], 'tickcolor': '#696969'},
               'bar': {'color': color},
               'bgcolor': "white",
               'borderwidth': 2,
               'bordercolor': "#D3D3D3",
               'steps': [{'range': [0, 50], 'color': "#F5F5F5"},
                        {'range': [50, 70], 'color': "#E8E8E8"},
                        {'range': [70, 100], 'color': "#DCDCDC"}]}
    ), row=1, col=1)
    
    # Estrutura para IA
    content_structure = geo_analysis.get('content_structure', {})
    structure_labels = ['FAQ', 'Listas', 'Tabelas', 'Headings']
    structure_values = [
        content_structure.get('faq_indicators', 0),
        content_structure.get('lists_count', 0),
        content_structure.get('tables_count', 0),
        min(content_structure.get('headings_count', 0), 10)  # Máximo 10 para visualização
    ]
    
    fig.add_trace(go.Bar(
        x=structure_labels,
        y=structure_values,
        name="Estrutura",
        marker_color=['#2F4F4F', '#708090', '#A9A9A9', '#C0C0C0'],
        showlegend=False
    ), row=1, col=2)
    
    # Conteúdo factual
    factual_content = geo_analysis.get('factual_content', {})
    factual_labels = ['Indicadores', 'Citações', 'Links Autoritários']
    factual_values = [
        factual_content.get('factual_indicators', 0),
        factual_content.get('citations', 0),
        factual_content.get('authoritative_links', 0)
    ]
    
    fig.add_trace(go.Bar(
        x=factual_labels,
        y=factual_values,
        name="Factual",
        marker_color=['#2F4F4F', '#708090', '#A9A9A9'],
        showlegend=False
    ), row=2, col=1)
    
    # Sinais de autoridade
    authority_signals = geo_analysis.get('authority_signals', {})
    ai_format = geo_analysis.get('ai_friendly_format', {})
    
    authority_labels = ['Definições', 'Exemplos', 'Comparações', 'Passos']
    authority_values = [
        ai_format.get('definitions', 0),
        ai_format.get('examples', 0),
        ai_format.get('comparisons', 0),
        ai_format.get('step_by_step', 0)
    ]
    
    fig.add_trace(go.Bar(
        x=authority_labels,
        y=authority_values,
        name="IA Format",
        marker_color=['#2F4F4F', '#708090', '#A9A9A9', '#C0C0C0'],
        showlegend=False
    ), row=2, col=2)
    
    fig.update_layout(
        height=500,
        showlegend=False,
        title_text="Dashboard de GEO - Generative Engine Optimization",
        title_x=0.5,
        title_font_color='#2F4F4F',
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return fig
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
    
    # Tokenização com fallback
    try:
        sentences = sent_tokenize(text)
        words = word_tokenize(text.lower())
    except:
        # Fallback simples se NLTK não funcionar
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        words = re.findall(r'\b[a-záàâãéêíóôõúç]+\b', text.lower())
    
    # Remove stopwords
    try:
        stop_words = set(stopwords.words('portuguese'))
        filtered_words = [word for word in words if word.isalnum() and word not in stop_words]
    except:
        # Fallback para lista básica se não conseguir carregar stopwords
        basic_stopwords = {
            'a', 'o', 'e', 'é', 'de', 'do', 'da', 'em', 'um', 'uma', 'para', 'com', 'por', 
            'que', 'se', 'na', 'no', 'os', 'as', 'dos', 'das', 'ao', 'aos', 'à', 'às',
            'mas', 'ou', 'ser', 'ter', 'seu', 'sua', 'seus', 'suas', 'foi', 'são', 'não'
        }
        filtered_words = [word for word in words if word.isalnum() and word not in basic_stopwords]
    
    # === ANÁLISE DE LEGIBILIDADE ===
    if len(text.strip()) > 50:  # Só analisa se tiver conteúdo suficiente
        try:
            analysis["readability"]["flesch_score"] = round(flesch_reading_ease(text), 2)
            analysis["readability"]["ari_score"] = round(automated_readability_index(text), 2)
        except:
            analysis["readability"]["flesch_score"] = "N/A"
            analysis["readability"]["ari_score"] = "N/A"
        
        # Calcula métricas customizadas
        avg_sentence_length = len(words) / len(sentences) if sentences else 0
        analysis["readability"]["avg_sentence_length"] = round(avg_sentence_length, 2)
        
        # Classifica legibilidade
        flesch = analysis["readability"]["flesch_score"]
        if isinstance(flesch, (int, float)):
            if flesch >= 80:
                analysis["readability"]["level"] = "Muito Fácil"
                analysis["readability"]["level_color"] = "#2E8B57"
            elif flesch >= 65:
                analysis["readability"]["level"] = "Fácil"
                analysis["readability"]["level_color"] = "#32CD32"
            elif flesch >= 50:
                analysis["readability"]["level"] = "Médio"
                analysis["readability"]["level_color"] = "#FF8C00"
            else:
                analysis["readability"]["level"] = "Difícil"
                analysis["readability"]["level_color"] = "#DC143C"
        else:
            analysis["readability"]["level"] = "N/A"
            analysis["readability"]["level_color"] = "#696969"
    
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

# ========== FUNÇÕES DE VISUALIZAÇÃO OTIMIZADAS (MONOCROMÁTICAS) ==========
def create_content_quality_dashboard(content_analysis):
    """Cria dashboard visual minimalista para análise de conteúdo"""
    if not content_analysis or not content_analysis.get('content_quality'):
        return None
    
    quality_data = content_analysis['content_quality']
    readability_data = content_analysis.get('readability', {})
    headings_data = content_analysis.get('headings_analysis', {})
    
    # Cria subplots com design limpo
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Score de Qualidade', 'Legibilidade Flesch', 'Estrutura de Headings', 'Top Palavras-chave'),
        specs=[[{"type": "indicator"}, {"type": "indicator"}],
               [{"type": "bar"}, {"type": "pie"}]]
    )
    
    # Gauge de qualidade geral (tons de cinza)
    quality_score = quality_data.get('quality_score', 0)
    if quality_score == 0:
        return None  # Não exibe se zerado
    
    color = "#2F4F4F" if quality_score >= 70 else "#708090" if quality_score >= 50 else "#A9A9A9"
    
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=quality_score,
        title={'text': "Score de Qualidade", 'font': {'color': '#2F4F4F'}},
        gauge={'axis': {'range': [None, 100], 'tickcolor': '#696969'},
               'bar': {'color': color},
               'bgcolor': "white",
               'borderwidth': 2,
               'bordercolor': "#D3D3D3",
               'steps': [{'range': [0, 50], 'color': "#F5F5F5"},
                        {'range': [50, 70], 'color': "#E8E8E8"},
                        {'range': [70, 100], 'color': "#DCDCDC"}]}
    ), row=1, col=1)
    
    # Gauge de legibilidade (tons de cinza)
    flesch_score = readability_data.get('flesch_score', 0)
    if isinstance(flesch_score, (int, float)) and flesch_score > 0:
        flesch_color = "#2F4F4F" if flesch_score >= 60 else "#708090" if flesch_score >= 30 else "#A9A9A9"
        
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=flesch_score,
            title={'text': "Flesch Reading Ease", 'font': {'color': '#2F4F4F'}},
            gauge={'axis': {'range': [0, 100], 'tickcolor': '#696969'},
                   'bar': {'color': flesch_color},
                   'bgcolor': "white",
                   'borderwidth': 2,
                   'bordercolor': "#D3D3D3",
                   'steps': [{'range': [0, 30], 'color': "#F5F5F5"},
                            {'range': [30, 60], 'color': "#E8E8E8"},
                            {'range': [60, 100], 'color': "#DCDCDC"}]}
        ), row=1, col=2)
    
    # Gráfico de estrutura (tons de cinza)
    if headings_data and headings_data.get('total_headings', 0) > 0:
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
            marker_color=['#2F4F4F', '#708090', '#A9A9A9'],
            showlegend=False
        ), row=2, col=1)
    
    # Gráfico de distribuição de palavras-chave (tons de cinza)
    semantic_data = content_analysis.get('semantic_analysis', {})
    top_words = semantic_data.get('top_keywords', {})
    if top_words:
        words = list(top_words.keys())[:5]  # Top 5 palavras
        counts = list(top_words.values())[:5]
        
        # Paleta de cinzas
        gray_colors = ['#2F4F4F', '#708090', '#778899', '#A9A9A9', '#C0C0C0']
        
        fig.add_trace(go.Pie(
            labels=words,
            values=counts,
            name="Top Keywords",
            marker=dict(colors=gray_colors),
            showlegend=False
        ), row=2, col=2)
    
    fig.update_layout(
        height=500,
        showlegend=False,
        title_text="Dashboard de Análise de Conteúdo",
        title_x=0.5,
        title_font_color='#2F4F4F',
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return fig

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

# ========== TÓPICO 6: DASHBOARD COM GAUGES VISUAIS MINIMALISTAS ==========
def create_seo_score_gauge(score, title="SEO Score"):
    """Cria um gauge visual minimalista para scores de SEO"""
    # Garantir que score é numérico
    if score is None or score == "N/A" or score == 0:
        return None  # Não exibe se zerado
    try:
        score = float(score)
    except (ValueError, TypeError):
        return None
    
    # Determina cor em tons de cinza
    if score >= 80:
        color = "#2F4F4F"  # Cinza escuro
    elif score >= 60:
        color = "#708090"  # Cinza médio
    else:
        color = "#A9A9A9"  # Cinza claro
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 14, 'color': '#2F4F4F'}},
        delta={'reference': 80, 'suffix': " pts"},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#696969"},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#D3D3D3",
            'steps': [
                {'range': [0, 30], 'color': '#F8F8F8'},
                {'range': [30, 60], 'color': '#F0F0F0'},
                {'range': [60, 80], 'color': '#E8E8E8'},
                {'range': [80, 100], 'color': '#E0E0E0'}
            ],
            'threshold': {
                'line': {'color': "#696969", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(
        height=200, 
        margin=dict(l=10, r=10, t=30, b=10),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    return fig

def calculate_overall_seo_score(onpage_data, psi_data, keyword_data, structured_data):
    """Calcula um score geral de SEO baseado em múltiplos fatores"""
    if not onpage_data:
        return 0
    
    score = 0
    
    # CRITÉRIOS BÁSICOS (40 pontos)
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
    
    # PERFORMANCE (25 pontos)
    if psi_data and 'mobile' in psi_data and psi_data['mobile']:
        mobile_perf = psi_data['mobile'].get('psi_performance', 0)
        try:
            mobile_perf = float(mobile_perf)
            score += (mobile_perf / 100) * 25
        except (ValueError, TypeError):
            pass
    else:
        score += 10
    
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
    if onpage_data.get('links_internos', 0) >= 5:
        score += 5
    elif onpage_data.get('links_internos', 0) >= 2:
        score += 3
    
    # Imagens
    total_imgs = onpage_data.get('image_count', 0)
    imgs_sem_alt = onpage_data.get('images_sem_alt', 0)
    if total_imgs > 0:
        img_score = ((total_imgs - imgs_sem_alt) / total_imgs) * 5
        score += img_score
    
    # Palavra-chave
    if keyword_data and 'keyword_prominence_score' in keyword_data:
        kw_score = keyword_data.get('keyword_prominence_score', 0)
        try:
            score += (float(kw_score) / 100) * 10
        except (ValueError, TypeError):
            pass
    
    # Dados estruturados
    if structured_data and len(structured_data.get('schemas_found', [])) > 0:
        score += 5
    
    return min(round(score), 100)

# ========== NOVA FUNCIONALIDADE: SITEMAP E MAPEAMENTO ==========
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
                        'text': link.get_text(strip=True)[:50],
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
    """Cria visualização profissional do sitemap em tons de cinza"""
    if not site_structure.get('structure'):
        return None
    
    pages = site_structure['structure']
    
    # Agrupa por profundidade
    depth_groups = {}
    for page in pages:
        depth = page['depth']
        if depth not in depth_groups:
            depth_groups[depth] = []
        depth_groups[depth].append(page)
    
    # Limita páginas por nível
    max_per_level = 12
    for depth in depth_groups:
        if len(depth_groups[depth]) > max_per_level:
            depth_groups[depth] = depth_groups[depth][:max_per_level]
    
    # Cria layout organograma
    fig = go.Figure()
    
    # Paleta de cinzas
    gray_colors = ['#2F4F4F', '#696969', '#708090', '#778899', '#A9A9A9', '#C0C0C0']
    
    level_height = 150
    max_width = 1200
    
    for depth in sorted(depth_groups.keys()):
        pages_at_depth = depth_groups[depth]
        color = gray_colors[depth % len(gray_colors)]
        
        # Posicionamento horizontal
        num_pages = len(pages_at_depth)
        if num_pages == 1:
            x_positions = [0]
        else:
            spacing = max_width / (num_pages + 1)
            x_positions = [spacing * (i + 1) - max_width/2 for i in range(num_pages)]
        
        y_position = -depth * level_height
        
        # Textos limpos
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
            
            # Limita texto
            if len(page_text) > 15:
                display_text = page_text[:12] + "..."
            else:
                display_text = page_text
            
            clean_texts.append(display_text)
            
            # Hover informativo
            hover_text = f"<b>{page_text}</b><br>"
            hover_text += f"URL: {page['url']}<br>"
            hover_text += f"Nível: {depth}<br>"
            hover_text += f"Profundidade: {len(page['path'].strip('/').split('/')) if page['path'] != '/' else 0}"
            hover_texts.append(hover_text)
        
        # Adiciona nós
        fig.add_trace(go.Scatter(
            x=x_positions,
            y=[y_position] * len(x_positions),
            mode='markers+text',
            marker=dict(
                size=45,
                color='white',  # Fundo branco
                line=dict(width=3, color=color),  # Borda colorida
                symbol='circle'
            ),
            text=clean_texts,
            textposition="middle center",
            textfont=dict(
                size=10, 
                color='#2F4F4F',  # Mudança para cor escura para contraste
                family="Arial",
                weight="bold"
            ),
            hovertemplate='%{customdata}<extra></extra>',
            customdata=hover_texts,
            name=f'Nível {depth}',
            showlegend=True
        ))
        
        # Labels de nível
        fig.add_annotation(
            x=-max_width/2 - 100,
            y=y_position,
            text=f"<b>Nível {depth}</b>",
            showarrow=False,
            font=dict(size=12, color=color, family="Arial"),
            xanchor="right"
        )
    
    # Conexões
    for depth in sorted(depth_groups.keys())[:-1]:
        next_depth = depth + 1
        if next_depth in depth_groups:
            current_level = depth_groups[depth]
            next_level = depth_groups[next_depth]
            
            current_y = -depth * level_height
            next_y = -next_depth * level_height
            
            # Home para principais
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
                            color='rgba(105,105,105,0.4)', 
                            width=2,
                            dash='dot'
                        ),
                        showlegend=False,
                        hoverinfo='skip'
                    ))
    
    # Layout final
    fig.update_layout(
        title=dict(
            text=f"🗺️ Arquitetura do Site: {site_structure.get('domain', 'Site')}",
            font=dict(size=16, family="Arial", color="#2F4F4F"),
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
        height=500,
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=50, r=50, t=60, b=50),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.05,
            xanchor="center",
            x=0.5,
            font=dict(size=10, family="Arial", color="#2F4F4F")
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
    
    return "\n".join(insights)

# ========== FUNÇÕES EXISTENTES ==========
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
    for link in internal_links[:10]:
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

# ========== INTERFACE STREAMLIT ==========
st.set_page_config(page_title="SEO AI Strategist Pro", page_icon="🔭", layout="wide")

# ========== PÁGINA INICIAL ==========
def show_tool_info():
    """Exibe informações sobre a ferramenta apenas na página inicial"""
    if 'analysis_started' not in st.session_state:
        st.markdown("""
        ### 📚 Sobre a Auditoria de SEO e GEO On-Page

        **Análise completa de SEO tradicional e GEO (Generative Engine Optimization)** com inteligência artificial.

        **Funcionalidades principais:**
        - ✅ **SEO Técnico:** Performance e Core Web Vitals (Google PageSpeed)
        - ✅ **SEO On-Page:** Análise completa de elementos internos
        - ✅ **GEO (Generative Engine Optimization):** Otimização para IAs como ChatGPT, Gemini, Claude
        - ✅ **Análise de Conteúdo:** Legibilidade e qualidade textual
        - ✅ **Estrutura do Site:** Mapeamento e arquitetura de informação
        - ✅ **Dados Estruturados:** Schema.org e rich snippets
        - ✅ **Comparação Competitiva:** Benchmarking com concorrentes

        **Tecnologias:** Python, Streamlit, Google Gemini AI, PageSpeed Insights API

        ---
        """)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configurações de Análise")
    
    deep_analysis = st.checkbox("🔍 Análise profunda", value=True,
                               help="Inclui análise de dados estruturados")
    
    extract_structure = st.checkbox("🗺️ Mapear estrutura do site", value=True,
                                   help="Cria mapa visual da arquitetura do site")
    
    content_analysis_enabled = st.checkbox("📝 Análise avançada de conteúdo", value=True,
                                          help="Análise de legibilidade, estrutura e qualidade do conteúdo")
    
    geo_seo_enabled = st.checkbox("🤖 Análise de GEO (Generative Engine Optimization)", value=True,
                                 help="Otimização para IAs generativas como ChatGPT, Gemini, Claude")
    
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
    **GEO (IA):** FAQ, definições, exemplos e estrutura para IAs
    """)

st.title("🔭 Auditoria de SEO e GEO On-Page")
st.markdown("Análise completa de SEO tradicional e otimização para IAs generativas (GEO - Generative Engine Optimization).")

# Mostra informações apenas se análise não foi iniciada
show_tool_info()

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
        # Marca que análise foi iniciada
        st.session_state.analysis_started = True
        
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
                
                # Análises adicionais
                structured_data = {}
                site_structure = {}
                content_analysis = {}
                geo_analysis = {}
                
                if deep_analysis:
                    structured_data = analyze_structured_data(soup_principal)
                
                if extract_structure:
                    with st.spinner("🗺️ Mapeando estrutura do site..."):
                        site_structure = extract_site_structure(url_principal, max_pages=max_pages_sitemap)
                
                if content_analysis_enabled:
                    with st.spinner("📝 Analisando qualidade do conteúdo..."):
                        content_analysis = analyze_content_advanced(soup_principal, url_principal)
                
                if geo_seo_enabled:
                    with st.spinner("🤖 Analisando GEO para IAs..."):
                        geo_analysis = analyze_geo_ai_optimization(soup_principal, url_principal)
                
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
        overall_score = calculate_overall_seo_score(onpage_principal, psi_principal, {}, structured_data)
        
        # === SEÇÃO DE ANÁLISE DE CONTEÚDO ===
        if content_analysis_enabled and content_analysis:
            quality_data = content_analysis.get('content_quality', {})
            quality_score = quality_data.get('quality_score', 0)
            
            # Só exibe se houver dados relevantes
            if quality_score > 0:
                st.markdown("#### 📝 Análise Avançada de Conteúdo")
                
                # Dashboard de conteúdo
                content_dashboard = create_content_quality_dashboard(content_analysis)
                if content_dashboard:
                    st.plotly_chart(content_dashboard, use_container_width=True)
                
                # Métricas detalhadas
                col1, col2, col3, col4 = st.columns(4)
                
                readability_data = content_analysis.get('readability', {})
                headings_data = content_analysis.get('headings_analysis', {})
                
                with col1:
                    st.metric("🎯 Score de Qualidade", f"{quality_score}/100")
                    word_count = quality_data.get('total_words', 0)
                    st.metric("📝 Total de Palavras", word_count)
                
                with col2:
                    flesch_score = readability_data.get('flesch_score', 'N/A')
                    if isinstance(flesch_score, (int, float)) and flesch_score > 0:
                        st.metric("📖 Legibilidade (Flesch)", f"{flesch_score:.1f}")
                    else:
                        st.metric("📖 Legibilidade", "N/A")
                    
                    level = readability_data.get('level', 'N/A')
                    level_color = readability_data.get('level_color', '#696969')
                    if level != 'N/A':
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
                
                # Tabela detalhada de análise de conteúdo
                if quality_score > 0:
                    with st.expander("📋 Tabela Detalhada de Análise de Conteúdo"):
                        semantic_data = content_analysis.get('semantic_analysis', {})
                        top_words = semantic_data.get('top_keywords', {})
                        
                        if top_words:
                            # Cria DataFrame com top palavras
                            df_words = pd.DataFrame([
                                {"Palavra": palavra, "Frequência": freq} 
                                for palavra, freq in list(top_words.items())[:10]
                            ])
                            df_words.index = range(len(df_words))  # Reseta índice
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("**🔑 Top 10 Palavras-chave:**")
                                st.dataframe(df_words, use_container_width=True, hide_index=False)
                            
                            with col2:
                                # Métricas adicionais
                                vocab_richness = semantic_data.get('vocabulary_richness', 0)
                                st.metric("📊 Riqueza Vocabular", f"{vocab_richness:.2%}")
                                
                                duplication = quality_data.get('duplication_ratio', 0)
                                st.metric("📄 Taxa de Duplicação", f"{duplication:.1f}%")
                                
                                avg_sentence = readability_data.get('avg_sentence_length', 0)
                                st.metric("📏 Palavras por Frase", f"{avg_sentence:.1f}")
                
                st.divider()
        
        # === SEÇÃO DE ANÁLISE GEO (IA) ===
        if geo_seo_enabled and geo_analysis:
            geo_score = geo_analysis.get('geo_score', 0)
            
            if geo_score > 0:
                st.markdown("#### 🤖 Análise de GEO - Generative Engine Optimization")
                
                # Dashboard GEO
                geo_dashboard = create_geo_ai_dashboard(geo_analysis)
                if geo_dashboard:
                    st.plotly_chart(geo_dashboard, use_container_width=True)
                
                # Métricas GEO
                col1, col2, col3, col4 = st.columns(4)
                
                content_structure = geo_analysis.get('content_structure', {})
                factual_content = geo_analysis.get('factual_content', {})
                ai_format = geo_analysis.get('ai_friendly_format', {})
                authority_signals = geo_analysis.get('authority_signals', {})
                
                with col1:
                    st.metric("🎯 Score GEO (IA)", f"{geo_score}/100")
                    
                    faq_count = content_structure.get('faq_indicators', 0)
                    st.metric("❓ Indicadores FAQ", faq_count)
                
                with col2:
                    definitions = ai_format.get('definitions', 0)
                    st.metric("📖 Definições", definitions)
                    
                    examples = ai_format.get('examples', 0)
                    st.metric("💡 Exemplos", examples)
                
                with col3:
                    factual_indicators = factual_content.get('factual_indicators', 0)
                    st.metric("📊 Indicadores Factuais", factual_indicators)
                    
                    auth_links = factual_content.get('authoritative_links', 0)
                    st.metric("🔗 Links Autoritários", auth_links)
                
                with col4:
                    author_mentioned = "✅" if authority_signals.get('author_mentioned') else "❌"
                    st.metric("👤 Autor Mencionado", author_mentioned)
                    
                    article_schema = "✅" if authority_signals.get('article_schema') else "❌"
                    st.metric("📰 Schema Article", article_schema)
                
                # Insights GEO para IA
                geo_insights = []
                
                if geo_score >= 80:
                    geo_insights.append("🏆 **Excelente otimização para IAs generativas!**")
                elif geo_score >= 60:
                    geo_insights.append("👍 **Bom conteúdo para IA, pode melhorar**")
                else:
                    geo_insights.append("⚠️ **Conteúdo precisa ser otimizado para IAs**")
                
                if faq_count == 0:
                    geo_insights.append("❓ **Adicione formato FAQ** - IAs preferem perguntas e respostas claras")
                
                if definitions == 0:
                    geo_insights.append("📖 **Inclua definições claras** - Essencial para compreensão das IAs")
                
                if factual_indicators < 2:
                    geo_insights.append("📊 **Adicione mais dados factuais** - IAs valorizam informações verificáveis")
                
                if auth_links == 0:
                    geo_insights.append("🔗 **Inclua fontes autoritárias** - Aumenta credibilidade para IAs")
                
                if not authority_signals.get('author_mentioned'):
                    geo_insights.append("👤 **Mencione autoria** - IAs consideram autoridade do autor")
                
                if examples == 0:
                    geo_insights.append("💡 **Adicione exemplos práticos** - Facilita compreensão das IAs")
                
                # Análise de estrutura hierárquica
                hierarchy_score = content_structure.get('hierarchy_score', 0)
                if hierarchy_score < 70:
                    geo_insights.append("🏗️ **Melhore hierarquia de headings** - IAs seguem estrutura lógica")
                
                if geo_insights:
                    with st.expander("💡 Insights de GEO para IAs"):
                        for insight in geo_insights:
                            st.markdown(f"- {insight}")
                
                # Detalhes técnicos GEO
                with st.expander("🔧 Detalhes Técnicos GEO"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**📋 Estrutura de Conteúdo:**")
                        st.write(f"• Listas: {content_structure.get('lists_count', 0)}")
                        st.write(f"• Tabelas: {content_structure.get('tables_count', 0)}")
                        st.write(f"• Headings: {content_structure.get('headings_count', 0)}")
                        st.write(f"• Hierarquia: {hierarchy_score:.1f}%")
                        
                        st.markdown("**🤖 Formato Amigável para IA:**")
                        st.write(f"• Comparações: {ai_format.get('comparisons', 0)}")
                        st.write(f"• Instruções passo-a-passo: {ai_format.get('step_by_step', 0)}")
                    
                    with col2:
                        st.markdown("**📊 Conteúdo Factual:**")
                        st.write(f"• Citações: {factual_content.get('citations', 0)}")
                        st.write(f"• Palavras: {authority_signals.get('word_count', 0)}")
                        
                        st.markdown("**🏛️ Sinais de Autoridade:**")
                        st.write(f"• Data mencionada: {'✅' if authority_signals.get('date_mentioned') else '❌'}")
                        st.write(f"• Schema Article: {'✅' if authority_signals.get('article_schema') else '❌'}")
                
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
            
            # Análise estratégica
            strategy_insights = analyze_site_strategy(site_structure)
            if strategy_insights:
                st.markdown("**💡 Insights da Estrutura:**")
                st.markdown(strategy_insights)
            
            st.divider()
        
        # Primeira linha: Score geral e métricas principais
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            if overall_score > 0:
                fig_score = create_seo_score_gauge(overall_score, "Score Geral de SEO")
                if fig_score:
                    st.plotly_chart(fig_score, use_container_width=True)
            else:
                st.info("📊 Score de SEO não disponível")
        
        with col2:
            st.metric("📝 Palavras", onpage_principal.get("word_count", 0))
            st.metric("🖼️ Imagens", onpage_principal.get("image_count", 0))
        
        with col3:
            st.metric("🔗 Links Internos", onpage_principal.get("links_internos", 0))
            st.metric("❌ Imgs sem Alt", onpage_principal.get("images_sem_alt", 0))
        
        with col4:
            if psi_principal and 'mobile' in psi_principal:
                perf_mobile = psi_principal['mobile'].get('psi_performance', 0)
                if perf_mobile > 0:
                    st.metric("📱 Performance", f"{perf_mobile}/100")
                else:
                    st.metric("📱 Performance", "N/A")
            else:
                st.metric("📱 Performance", "N/A")
            
            if broken_links_principal:
                st.metric("🔗 Links Quebrados", len(broken_links_principal), delta_color="inverse")
            else:
                st.metric("🔗 Links Quebrados", "0 ✅")
        
        # Performance detalhada
        if psi_principal:
            mobile_perf = psi_principal.get('mobile', {}).get('psi_performance', 0)
            desktop_perf = psi_principal.get('desktop', {}).get('psi_performance', 0)
            
            if mobile_perf > 0 or desktop_perf > 0:
                st.markdown("#### 🚀 Performance Detalhada")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**📱 Mobile**")
                    mobile_data = psi_principal.get('mobile', {})
                    perf = mobile_data.get('psi_performance', 0)
                    seo = mobile_data.get('psi_seo', 0)
                    
                    if perf > 0:
                        fig_mobile = create_seo_score_gauge(perf, "Performance Mobile")
                        if fig_mobile:
                            st.plotly_chart(fig_mobile, use_container_width=True)
                    if seo > 0:
                        st.metric("SEO Score", f"{seo}/100")
                
                with col2:
                    st.markdown("**🖥️ Desktop**")
                    desktop_data = psi_principal.get('desktop', {})
                    perf_desk = desktop_data.get('psi_performance', 0)
                    seo_desk = desktop_data.get('psi_seo', 0)
                    
                    if perf_desk > 0:
                        fig_desktop = create_seo_score_gauge(perf_desk, "Performance Desktop")
                        if fig_desktop:
                            st.plotly_chart(fig_desktop, use_container_width=True)
                    if seo_desk > 0:
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
                            if comp_data['score'] > 0:
                                mini_gauge = create_seo_score_gauge(comp_data['score'], f"Score: {comp_data['domain']}")
                                if mini_gauge:
                                    st.plotly_chart(mini_gauge, use_container_width=True)
                            else:
                                st.info("Score não disponível")
                        
                        with col2:
                            st.metric("📝 Palavras", comp_data['onpage'].get("word_count", 0))
                            st.metric("🔗 Links Internos", comp_data['onpage'].get("links_internos", 0))
                        
                        with col3:
                            st.metric("🖼️ Imagens", comp_data['onpage'].get("image_count", 0))
                            perf_mobile = comp_data['psi'].get('mobile', {}).get('psi_performance', 0)
                            st.metric("📱 Performance", f"{perf_mobile}/100" if perf_mobile > 0 else "N/A")
                        
                        with col4:
                            st.metric("🏷️ Title Length", comp_data['onpage'].get('title_length', 0))
                            h1_count = comp_data['onpage'].get('h1_count', 0)
                            st.metric("📋 H1 Count", h1_count)
                        
                        # Análises adicionais do concorrente
                        if comp_data.get('content'):
                            content_score = comp_data['content'].get('content_quality', {}).get('quality_score', 0)
                            if content_score > 0:
                                with st.expander("📝 Análise de Conteúdo"):
                                    flesch_score = comp_data['content'].get('readability', {}).get('flesch_score', 'N/A')
                                    st.metric("Qualidade do Conteúdo", f"{content_score}/100")
                                    if isinstance(flesch_score, (int, float)) and flesch_score > 0:
                                        st.metric("Legibilidade Flesch", f"{flesch_score:.1f}")
                        
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
                
                df_display = df_comparativo[display_columns].rename(columns={
                    "word_count": "Palavras", 
                    "links_internos": "Links Internos", 
                    "image_count": "Imagens",
                    "title_length": "Tam. Título",
                    "Content Score": "Score Conteúdo"
                })
                
                st.dataframe(df_display, use_container_width=True)
                
                # Gráficos comparativos em tons de cinza
                st.markdown("#### 📈 Comparação Visual")
                
                site_principal = urlparse(url_principal).netloc
                
                # Paleta monocromática para gráficos
                def create_monochrome_colors(n_colors, highlight_index=0):
                    """Cria paleta monocromática com destaque para o site principal"""
                    colors = []
                    for i in range(n_colors):
                        if i == highlight_index:
                            colors.append('#2F4F4F')  # Destaque para site principal
                        else:
                            gray_intensity = 0.4 + (i * 0.2)  # Varia tons de cinza
                            colors.append(f'rgba(105,105,105,{min(gray_intensity, 1.0)})')
                    return colors
                
                n_sites = len(df_display)
                colors = create_monochrome_colors(n_sites)
                
                col1, col2 = st.columns(2)
                with col1:
                    fig_comp_seo = px.bar(df_display, x='Site', y='SEO Score', 
                                         title="Score Geral de SEO",
                                         color_discrete_sequence=colors)
                    fig_comp_seo.update_layout(
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        title_font_color='#2F4F4F'
                    )
                    st.plotly_chart(fig_comp_seo, use_container_width=True)
                
                with col2:
                    fig_comp_perf = px.bar(df_display, x='Site', y='Performance Mobile',
                                          title="Performance Mobile",
                                          color_discrete_sequence=colors)
                    fig_comp_perf.update_layout(
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        title_font_color='#2F4F4F'
                    )
                    st.plotly_chart(fig_comp_perf, use_container_width=True)
                
                # Gráfico adicional se há dados de conteúdo
                if "Score Conteúdo" in df_display.columns:
                    col3, col4 = st.columns(2)
                    
                    with col3:
                        fig_content = px.bar(df_display, x='Site', y='Score Conteúdo',
                                           title="Qualidade do Conteúdo",
                                           color_discrete_sequence=colors)
                        fig_content.update_layout(
                            plot_bgcolor='white',
                            paper_bgcolor='white',
                            title_font_color='#2F4F4F'
                        )
                        st.plotly_chart(fig_content, use_container_width=True)
        
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
            if content_score < 50 and content_score > 0:
                issues.append("📝 **Qualidade do conteúdo baixa** - Revise estrutura e legibilidade")
            
            flesch_score = content_analysis.get('readability', {}).get('flesch_score', 0)
            if isinstance(flesch_score, (int, float)) and flesch_score < 30 and flesch_score > 0:
                issues.append("📚 **Texto muito complexo** - Simplifique para melhor compreensão")
        
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
                "📊 Análise de comportamento de usuários",
                "🎯 Otimização para featured snippets"
            ]
        elif overall_score >= 60:
            st.warning("🚀 **Bom potencial!** Otimize:")
            recommendations = [
                "📱 Performance mobile (Core Web Vitals)",
                "🎯 Qualidade e estrutura do conteúdo",
                "🖼️ Alt text em todas as imagens",
                "🏗️ Implementação de dados estruturados"
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
            tab1, tab2, tab3, tab4 = st.tabs(["📊 On-Page", "🚀 Performance", "📝 Conteúdo", "🏗️ Estruturados"])
            
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
                if structured_data:
                    st.json(structured_data)
                else:
                    st.info("Análise de dados estruturados não realizada")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #696969; font-size: 0.8em;'>
<b>Auditoria de SEO e GEO On-Page v2.3</b> | SEO tradicional + Generative Engine Optimization
</div>
""", unsafe_allow_html=True)

# Rate limiting
if 'analysis_count' not in st.session_state:
    st.session_state.analysis_count = 0
    st.session_state.last_analysis_time = datetime.now()

if datetime.now() - st.session_state.last_analysis_time > timedelta(hours=1):
    st.session_state.analysis_count = 0
    st.session_state.last_analysis_time = datetime.now()
