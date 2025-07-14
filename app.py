# app.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
import advertools as adv
from urllib.parse import urlparse, urljoin
import extruct

# =================================================================================
# CONFIGURAÇÃO GERAL E DAS APIS
# =================================================================================

st.set_page_config(page_title="Diagnóstico de SEO Avançado com IA", page_icon="🏆", layout="wide")

# Configuração das APIs usando os secrets do Streamlit
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    PAGESPEED_API_KEY = st.secrets["PAGESPEED_API_KEY"]
    APIS_CONFIGURED = True
except (KeyError, Exception) as e:
    st.error(f"🚨 Chave de API não configurada. Verifique seu arquivo secrets.toml. Erro: {e}")
    APIS_CONFIGURED = False

# =================================================================================
# MÓDULOS DE EXTRAÇÃO E ANÁLISE
# =================================================================================

@st.cache_data(ttl=600)
def run_full_analysis(url):
    """
    Orquestra todas as análises: On-Page, Técnica, Performance e E-E-A-T.
    """
    report = {}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    # --- 1. Extração HTML Base ---
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        report['status_code'] = response.status_code
    except requests.exceptions.RequestException as e:
        return {"error": f"Erro fatal ao acessar a URL: {e}"}

    # --- 2. Análise On-Page ---
    h1s = [h1.get_text(strip=True) for h1 in soup.find_all('h1')]
    report['on_page'] = {
        "url": url,
        "title": soup.find('title').get_text(strip=True) if soup.find('title') else "Não encontrado",
        "meta_description": soup.find('meta', attrs={'name': 'description'})['content'] if soup.find('meta', attrs={'name': 'description'}) else "Não encontrada",
        "h1s": h1s,
        "h2s": [h2.get_text(strip=True) for h2 in soup.find_all('h2')],
        "word_count": len(soup.get_text().split()),
        "main_content_sample": " ".join(p.get_text(strip=True) for p in soup.find_all('p'))[:5000]
    }

    # --- 3. Análise Técnica ---
    base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    robots_url = urljoin(base_url, '/robots.txt')
    sitemap_url_list = adv.sitemap_to_df(urljoin(base_url, '/sitemap.xml')).get('sitemap', []).tolist()
    schema_data = extruct.extract(response.content, base_url=base_url)
    report['technical'] = {
        "robots_txt_url": robots_url,
        "sitemap_urls": sitemap_url_list,
        "schema_markup": schema_data,
        "canonical_tag": soup.find('link', rel='canonical')['href'] if soup.find('link', rel='canonical') else "Não encontrada"
    }

    # --- 4. Análise de Performance (API PageSpeed) ---
    pagespeed_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&key={PAGESPEED_API_KEY}&strategy=DESKTOP"
    try:
        pagespeed_response = requests.get(pagespeed_url)
        pagespeed_data = pagespeed_response.json()
        if 'error' in pagespeed_data:
            report['performance'] = {"error": pagespeed_data['error']['message']}
        else:
            metrics = pagespeed_data['lighthouseResult']['audits']
            report['performance'] = {
                "lcp": metrics['largest-contentful-paint']['displayValue'],
                "cls": metrics['cumulative-layout-shift']['displayValue'],
                "speed_index": metrics['speed-index']['displayValue'],
                "performance_score": int(pagespeed_data['lighthouseResult']['categories']['performance']['score'] * 100),
                "main_opportunities": [
                    item['heading'] for item in metrics['metrics']['details']['items'][0].get('opportunity_details', [])
                ][:3] if 'items' in metrics['metrics']['details'] and metrics['metrics']['details']['items'] else []
            }
    except Exception as e:
        report['performance'] = {"error": f"Não foi possível obter os dados do PageSpeed: {e}"}

    # --- 5. Análise de E-E-A-T ---
    report['eeat'] = {
        "author_info_found": "author" in soup.get_text().lower(),
        "about_us_link_found": bool(soup.find('a', string=lambda t: t and 'sobre' in t.lower())),
        "contact_link_found": bool(soup.find('a', string=lambda t: t and 'contato' in t.lower())),
        "external_links": [a['href'] for a in soup.find_all('a', href=True) if urlparse(a['href']).netloc != urlparse(url).netloc]
    }
    
    return report

def get_strategic_report_from_gemini(full_report):
    """
    Envia o relatório completo para o Gemini e pede o diagnóstico estratégico.
    """
    if not APIS_CONFIGURED:
        return "Erro: APIs não configuradas."

    # Limpa dados muito grandes antes de enviar
    full_report['on_page']['main_content_sample'] = full_report['on_page']['main_content_sample'][:4000]
    full_report['technical']['sitemap_urls'] = full_report['technical']['sitemap_urls'][:10] # Amostra do sitemap

    prompt = f"""
    Aja como um Estrategista de SEO Sênior de classe mundial. Você acaba de receber um diagnóstico completo de uma página da web. Sua tarefa é analisar TODOS esses dados e gerar um plano de ação estratégico para o cliente.

    **DADOS DO DIAGNÓSTICO COMPLETO:**
    ```json
    {json.dumps(full_report, indent=2, ensure_ascii=False)}
    ```

    **PLANO DE AÇÃO ESTRATÉGICO:**
    Com base em TODOS os dados acima, e considerando a importância de otimizar para a busca por IA (Google SGE), gere um relatório com a seguinte estrutura em Markdown:

    ###  Diagnóstico Estratégico de SEO para a Era da IA

    #### Pontuação de Prontidão para IA (0-100)
    * **Nota:** [Dê uma nota de 0 a 100]
    * **Justificativa:** [Explique a nota em 2-3 frases, com base na clareza do conteúdo, estrutura e sinais de E-E-A-T.]

    #### Análise SWOT de SEO On-Page
    * **Forças (Strengths):** [Liste 2-3 pontos fortes encontrados na análise.]
    * **Fraquezas (Weaknesses):** [Liste 2-3 pontos fracos encontrados.]
    * **Oportunidades (Opportunities):** [Liste 2-3 oportunidades de melhoria, especialmente as de alto impacto.]
    * **Ameaças (Threats):** [Liste 1-2 ameaças, como baixa performance ou falta de sinais E-E-A-T.]

    #### Plano de Ação Priorizado
    * **1. (Ação de Altíssimo Impacto):** [Descreva a primeira ação recomendada e o porquê.]
    * **2. (Ação de Médio Impacto):** [Descreva a segunda ação recomendada e o porquê.]
    * **3. (Ação de Bom Hábito):** [Descreva a terceira ação recomendada e o porquê.]
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro ao gerar o relatório final com a IA: {e}"

# =================================================================================
# INTERFACE DA APLICAÇÃO (STREAMLIT UI)
# =================================================================================

st.image("https://storage.googleapis.com/maker-media-posts/media/2024/05/Gemini_logo_2023.svg.png", width=150)
st.title("Diagnóstico de SEO Avançado com IA")
st.markdown("Uma ferramenta robusta que analisa os pilares de On-Page, Técnico, Performance e E-A-T do seu site, gerando um plano de ação estratégico com o Google Gemini.")

url_input = st.text_input("Insira a URL completa para uma análise profunda:", placeholder="https://exemplo.com.br/pagina")

if st.button("Gerar Diagnóstico Completo 🏆", type="primary"):
    if url_input and APIS_CONFIGURED:
        # --- Orquestração da Análise ---
        with st.spinner("Iniciando diagnóstico... Esta análise completa pode levar até 60 segundos."):
            st.info("Passo 1/4: Analisando HTML e conteúdo On-Page...", icon="📝")
            full_report = run_full_analysis(url_input)

        if "error" in full_report:
            st.error(full_report["error"])
        else:
            st.info("Passo 2/4: Consultando a API do Google PageSpeed...", icon="⚡")
            # A função run_full_analysis já chama a API, aqui apenas atualizamos o status
            
            st.info("Passo 3/4: Verificando sinais técnicos e de E-A-T...", icon="🛠️")
            # A função run_full_analysis já faz isso
            
            st.info("Passo 4/4: A IA está montando o plano de ação estratégico...", icon="🧠")
            strategic_report = get_strategic_report_from_gemini(full_report)
            
            st.success("Diagnóstico Estratégico Concluído!")
            st.balloons()
            
            # --- Exibição dos Resultados ---
            st.markdown("---")
            st.header(f"Resultados para: {url_input}")
            
            # O relatório principal gerado pela IA
            st.markdown(strategic_report)
            
            # Expander com os dados brutos coletados para consulta
            with st.expander("🔬 Clique para ver o diagnóstico detalhado (dados coletados)"):
                st.json(full_report)

    else:
        st.warning("Por favor, insira uma URL válida e verifique se as chaves de API estão configuradas.")
