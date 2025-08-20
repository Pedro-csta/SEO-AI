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

st.set_page_config(page_title="Dashboard de SEO com IA", page_icon="🏆", layout="wide")

# Configuração das APIs usando os secrets do Streamlit
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    PAGESPEED_API_KEY = st.secrets["PAGESPEED_API_KEY"]
    APIS_CONFIGURED = True
except (KeyError, Exception) as e:
    st.error(f"🚨 Chave de API não configurada. Verifique seu arquivo secrets.toml. Erro: {e}")
    APIS_CONFIGURED = False

# =================================================================================
# MÓDULOS DE EXTRAÇÃO DE DADOS (CACHE APRIMORADO)
# =================================================================================

@st.cache_data(ttl=3600, show_spinner=False) # Aumenta o cache para 1 hora
def run_full_analysis(url):
    """Orquestra todas as análises: On-Page, Técnica, Performance e E-E-A-T."""
    report = {}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    # --- 1. Extração HTML Base ---
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException as e:
        return {"error": f"Erro fatal ao acessar a URL: {e}"}

    # --- 2. Análise On-Page ---
    report['on_page'] = {
        "url": url,
        "title": soup.find('title').get_text(strip=True) if soup.find('title') else "",
        "meta_description": soup.find('meta', attrs={'name': 'description'})['content'] if soup.find('meta', attrs={'name': 'description'}) else "",
        "h1s": [h1.get_text(strip=True) for h1 in soup.find_all('h1')],
        "word_count": len(soup.get_text().split()),
        "main_content_sample": " ".join(p.get_text(strip=True) for p in soup.find_all('p'))[:4000]
    }

    # --- 3. Análise Técnica ---
    base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    report['technical'] = {
        "schema_markup": extruct.extract(response.content, base_url=base_url),
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
                "lcp": metrics.get('largest-contentful-paint', {}).get('displayValue', 'N/A'),
                "cls": metrics.get('cumulative-layout-shift', {}).get('displayValue', 'N/A'),
                "speed_index": metrics.get('speed-index', {}).get('displayValue', 'N/A'),
                "performance_score": int(pagespeed_data['lighthouseResult']['categories']['performance']['score'] * 100)
            }
    except Exception:
        report['performance'] = {"error": "Não foi possível obter os dados do PageSpeed."}
        
    # --- 5. Análise de E-E-A-T ---
    report['eeat'] = {
        "author_info_found": "author" in soup.get_text().lower(),
        "about_us_link_found": bool(soup.find('a', string=lambda t: t and 'sobre' in t.lower())),
        "contact_link_found": bool(soup.find('a', string=lambda t: t and 'contato' in t.lower())),
    }
    return report

# =================================================================================
# NOVO MÓDULO DE IA - FOCADO EM DADOS ESTRUTURADOS (JSON)
# =================================================================================

def get_strategic_dashboard_from_gemini(full_report):
    """Envia o relatório completo para o Gemini e pede um JSON estruturado para o dashboard."""
    if not APIS_CONFIGURED: return {"error": "APIs não configuradas."}
    
    # Prepara uma versão mais enxuta do relatório para o prompt
    report_sample = {
        "on_page": full_report["on_page"],
        "performance": full_report["performance"],
        "eeat": full_report["eeat"]
    }

    prompt = f"""
    Aja como um software de análise de SEO de classe mundial, como o Ahrefs ou Semrush.
    Analise os seguintes dados brutos de uma página da web e sua performance.

    **DADOS DO DIAGNÓSTICO:**
    ```json
    {json.dumps(report_sample, indent=2, ensure_ascii=False)}
    ```

    **Sua Tarefa:**
    Gere um relatório em formato JSON para popular um dashboard interativo. O JSON deve ter as seguintes chaves principais: `dashboard_scores` e `action_plan`.

    1. `dashboard_scores`: Um objeto com as seguintes chaves numéricas (valores de 0 a 100): `on_page_score`, `technical_score` e `eeat_score`. Para cada score, adicione uma `justificativa` de uma frase.

    2. `action_plan`: Um objeto com quatro chaves: `on_page`, `technical`, `performance`, e `eeat`. Cada chave deve conter uma lista de até 3 objetos de melhoria. Cada objeto na lista deve ter as seguintes chaves:
       - `ponto_de_melhoria`: (String) O problema encontrado.
       - `impacto`: (String) Por que este problema é importante para o SEO.
       - `solucao`: (String) Uma recomendação clara e acionável para corrigi-lo.
       - `severidade`: (String) Classifique como "Crítico", "Importante", ou "Otimização".

    Responda apenas com o objeto JSON válido.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(cleaned_response)
    except Exception as e:
        return {"error": f"Erro ao gerar o relatório com a IA: {e}"}

# =================================================================================
# NOVA INTERFACE DA APLICAÇÃO (STREAMLIT UI v2.0)
# =================================================================================

st.image("https://storage.googleapis.com/maker-media-posts/media/2024/05/Gemini_logo_2023.svg.png", width=150)
st.title("Dashboard de SEO Estratégico com IA")
st.markdown("Uma ferramenta robusta que analisa os pilares de On-Page, Técnico, Performance e E-A-T do seu site, gerando um dashboard de insights com o Google Gemini.")

url_input = st.text_input("Insira a URL completa para gerar seu dashboard:", placeholder="https://exemplo.com.br/pagina")

if st.button("Gerar Dashboard 🏆", type="primary"):
    if url_input and APIS_CONFIGURED:
        with st.spinner("Realizando análise profunda... Isso pode levar até 60 segundos."):
            raw_data = run_full_analysis(url_input)
            
            if "error" in raw_data:
                st.error(raw_data["error"])
            else:
                ai_dashboard_data = get_strategic_dashboard_from_gemini(raw_data)

        if "error" in ai_dashboard_data:
            st.error(ai_dashboard_data["error"])
        else:
            st.success("Dashboard gerado com sucesso!")
            st.balloons()
            
            # --- NOVO DASHBOARD RESUMO ---
            st.header("Dashboard de Saúde do SEO")
            scores = ai_dashboard_data.get('dashboard_scores', {})
            performance_score = raw_data.get('performance', {}).get('performance_score', 0)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("PERFORMANCE ⚡", f"{performance_score}/100", help="Nota do Google PageSpeed Insights. Acima de 90 é excelente.")
            with col2:
                st.metric("ON-PAGE 📝", f"{scores.get('on_page_score', 0)}/100", help=scores.get('justificativa', 'Nota gerada pela IA sobre a qualidade do conteúdo e HTML.'))
            with col3:
                st.metric("TÉCNICO 🛠️", f"{scores.get('technical_score', 0)}/100", help=scores.get('justificativa', 'Nota gerada pela IA sobre a saúde técnica da página.'))
            with col4:
                st.metric("E-A-T 🧑‍🔬", f"{scores.get('eeat_score', 0)}/100", help=scores.get('justificativa', 'Nota gerada pela IA sobre os sinais de confiança e autoridade.'))

            st.markdown("---")
            
            # --- NOVO PLANO DE AÇÃO COM ABAS ---
            st.header("Plano de Ação Priorizado")
            action_plan = ai_dashboard_data.get('action_plan', {})
            
            on_page_actions = action_plan.get('on_page', [])
            tech_actions = action_plan.get('technical', [])
            perf_actions = action_plan.get('performance', [])
            eeat_actions = action_plan.get('eeat', [])

            tab1, tab2, tab3, tab4 = st.tabs([f"On-Page ({len(on_page_actions)})", f"Técnico ({len(tech_actions)})", f"Performance ({len(perf_actions)})", f"E-A-T ({len(eeat_actions)})"])

            def display_actions(tab, actions):
                with tab:
                    if not actions:
                        st.success("Nenhum ponto crítico de melhoria encontrado nesta categoria! 🎉")
                    for action in actions:
                        severity = action.get('severidade', 'Otimização')
                        if severity == "Crítico":
                            icon = "🔴"
                        elif severity == "Importante":
                            icon = "🟠"
                        else:
                            icon = "🟢"
                        
                        with st.expander(f"{icon} **{action.get('ponto_de_melhoria', 'Item de Ação')}**"):
                            st.markdown(f"**IMPACTO:** {action.get('impacto', 'N/A')}")
                            st.markdown(f"**SOLUÇÃO:** {action.get('solucao', 'N/A')}")
            
            display_actions(tab1, on_page_actions)
            display_actions(tab2, tech_actions)
            display_actions(tab3, perf_actions)
            display_actions(tab4, eeat_actions)

    else:
        st.warning("Por favor, insira uma URL válida e verifique se as chaves de API estão configuradas.")
