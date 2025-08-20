# Streamlit SEO/GEO Auditor – App

## Estrutura do Projeto
```
seo-geo-auditor/
├── app.py              # Aplicação principal Streamlit
├── requirements.txt    # Dependências
├── README.md           # Documentação completa
└── .streamlit/
    └── secrets.toml    # Chaves privadas
```

---

## app.py
```python
# (código completo da aplicação já incluído no canvas anterior)
```

---

## requirements.txt
```
streamlit
requests
beautifulsoup4
google-generativeai
pandas
```

---

## README.md

# SEO/GEO Auditor (Streamlit + Gemini)

Ferramenta para auditar sites com base em checklist SEO On-Page + GEO (Generative Engine Optimization), atribuindo **score de prioridade (P0→P3 + GEO)** e gerando recomendações automáticas com o **Google Gemini API**.

---

## 🚀 Funcionalidades
- Rastreamento do domínio informado (mesmo host).
- Checklist P0 (crítico) → P3 (nice-to-have) + GEO.
- Score ponderado por prioridade.
- Integração com **Gemini** → diagnóstico robusto, recomendações, quick wins.
- Integração com **PageSpeed Insights** (opcional) → métricas Core Web Vitals.
- Exportação em **JSON** (relatório completo) e **CSV** (achados).
- Interface em **Streamlit** com progresso, tabelas e métricas.

---

## 🔑 Configuração das Chaves
Crie o arquivo `.streamlit/secrets.toml` na raiz do projeto:
```toml
GEMINI_API_KEY = "sua-chave"
PSI_API_KEY = "sua-chave-opcional"
```

---

## 📦 Instalação
Clone o repositório e instale as dependências:
```bash
git clone https://github.com/seuusuario/seo-geo-auditor.git
cd seo-geo-auditor
pip install -r requirements.txt
```

---

## ▶️ Execução
Rode a aplicação localmente:
```bash
streamlit run app.py
```

---

## 🌐 Deploy no Streamlit Cloud
1. Suba o repositório para o GitHub.
2. Vá em [Streamlit Cloud](https://share.streamlit.io/).
3. Conecte seu repositório.
4. Configure as **secrets** no menu `Settings > Secrets`.
5. Deploy!

---

## 📊 Saída Esperada
- **Score geral** de SEO/GEO.
- **Tabela de achados**: página, prioridade, achado, status.
- **Resumo Gemini**: pontos fortes, riscos, recomendações.
- **Download JSON/CSV** com relatório.

---

## 🔮 Roadmap Futuro
- Suporte a múltiplos domínios simultâneos.
- Cache de crawl.
- Exportação para PDF.
- Dashboard histórico.

---

## 📝 Licença
MIT
```

---

Agora o projeto está com **código, requirements e tutorial prontos** para GitHub/Streamlit Cloud. ✅
