# app.py
import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json

st.set_page_config(page_title="Diagnóstico de SEO com IA", page_icon="🚀", layout="wide")

try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    GEMINI_CONFIGURED = True
except Exception:
    st.error("🚨 Chave da API do Google não configurada. Adicione sua GOOGLE_API_KEY aos Secrets do Streamlit durante o deploy.")
    GEMINI_CONFIGURED = False

@st.cache_data(ttl=600)
def fetch_and_parse_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        data = {
            "title": soup.find('title').get_text(strip=True) if soup.find('title') else "Não encontrado",
            "meta_description": soup.find('meta', attrs={'name': 'description'})['content'] if soup.find('meta', attrs={'name': 'description'}) else "Não encontrada",
            "h1": soup.find('h1').get_text(strip=True) if soup.find('h1') else "Não encontrado",
            "h2s": [h2.get_text(strip=True) for h2 in soup.find_all('h2')],
            "word_count": len(soup.get_text().split()),
            "main_content": " ".join(p.get_text(strip=True) for p in soup.find_all('p'))
        }
        return data
    except requests.exceptions.RequestException as e:
        return {"error": f"Erro ao acessar a URL: {e}"}

def get_onpage_analysis_from_gemini(data):
    if not GEMINI_CONFIGURED: return {"error": "A API do Gemini não está configurada."}
    prompt = f"""
    Aja como um especialista em SEO. Analise os seguintes dados de uma página da web e forneça um diagnóstico completo de SEO On-Page.

    **Dados da Página:**
    - Título Atual: "{data['title']}"
    - Meta Descrição Atual: "{data['meta_description']}"
    - Cabeçalho H1: "{data['h1']}"
    - Sub-cabeçalhos H2: {data['h2s']}
    - Conteúdo Principal (parágrafos): "{data['main_content'][:4000]}"

    **Sua Tarefa:**
    Gere um relatório em formato JSON com as chaves: `analise_titulo_meta`, `analise_conteudo_keywords`, `analise_estrutura_h1_h2`.
    1. Para `analise_titulo_meta`, crie um objeto com as chaves `avaliacao` (análise de 1-2 frases) e `sugestoes` (uma lista de 3 objetos, cada um com `titulo_sugerido` e `meta_sugerida`).
    2. Para `analise_conteudo_keywords`, crie um objeto com `palavra_chave_principal`, `palavras_chave_secundarias` (lista de 3-5), `avaliacao_conteudo` (análise de 1-2 frases) e `sugestoes_conteudo` (lista de 2-3 tópicos).
    3. Para `analise_estrutura_h1_h2`, crie um objeto com a chave `avaliacao` (análise da estrutura de cabeçalhos).
    Responda apenas com o objeto JSON válido.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(cleaned_response)
    except Exception as e:
        return {"error": f"Erro na IA: {e}"}

st.image("https://storage.googleapis.com/maker-media-posts/media/2024/05/Gemini_logo_2023.svg.png", width=150)
st.title("Diagnóstico de SEO On-Page com IA")
st.markdown("Insira a URL de uma página e receba uma análise estratégica e sugestões de otimização geradas pelo Gemini.")

url_input = st.text_input("Insira a URL para análise:", placeholder="https://seusite.com.br/seu-artigo")

if st.button("Analisar Agora 🚀", type="primary"):
    if url_input and GEMINI_CONFIGURED:
        with st.spinner("🔍 **Passo 1/2:** Lendo e extraindo dados da sua página..."):
            extracted_data = fetch_and_parse_url(url_input)
        if "error" in extracted_data:
            st.error(extracted_data["error"])
        else:
            st.success("Dados extraídos com sucesso!")
            with st.spinner("🧠 **Passo 2/2:** A IA está montando o plano de ação..."):
                ai_analysis = get_onpage_analysis_from_gemini(extracted_data)
            if "error" in ai_analysis:
                st.error(ai_analysis["error"])
            else:
                st.success("Análise da IA concluída! Veja seu diagnóstico abaixo.")
                st.balloons()
                st.markdown("---")
                st.header(f"Resultados para: {url_input}")
                st.subheader("1. Análise de Título e Meta Descrição")
                st.info(f"**Avaliação da IA:** {ai_analysis.get('analise_titulo_meta', {}).get('avaliacao', 'N/A')}")
                st.write("**Sugestões de Otimização:**")
                for i, suggestion in enumerate(ai_analysis.get('analise_titulo_meta', {}).get('sugestoes', [])):
                    with st.expander(f"**Sugestão #{i+1}**"):
                        st.markdown(f"**Título:** `{suggestion.get('titulo_sugerido', 'N/A')}`")
                        st.markdown(f"**Meta Descrição:** `{suggestion.get('meta_sugerida', 'N/A')}`")
                st.subheader("2. Análise de Conteúdo e Palavras-chave")
                analise_kw = ai_analysis.get('analise_conteudo_keywords', {})
                st.info(f"**Palavra-chave Principal Identificada:** {analise_kw.get('palavra_chave_principal', 'N/A')}")
                st.write("**Sugestões para Enriquecer o Conteúdo:**")
                for topic in analise_kw.get('sugestoes_conteudo', []): st.markdown(f"- {topic}")
                st.subheader("3. Análise da Estrutura de Cabeçalhos")
                st.info(f"**Avaliação da IA:** {ai_analysis.get('analise_estrutura_h1_h2', {}).get('avaliacao', 'N/A')}")
    else:
        st.warning("Por favor, insira uma URL válida e verifique se a API Key está configurada.")
