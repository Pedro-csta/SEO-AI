line=dict(
                            color='rgba(100,100,100,0.4)', 
                            width=2,
                            dash='dot'
                        ),
                        showlegend=False,
                        hoverinfo='skip'
                    ))
            else:
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
    
    fig.update_layout(
        title=dict(
            text=f"Arquitetura do Site: {site_structure.get('domain', 'Site')}",
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
    
    max_depth = max(depth_analysis.keys()) if depth_analysis else 0
    if max_depth <= 2:
        insights.append("Estrutura rasa: Boa para SEO, fácil navegação")
    elif max_depth <= 4:
        insights.append("Estrutura média: Adequada, mas pode ser otimizada")
    else:
        insights.append("Estrutura muito profunda: Pode dificultar indexação")
    
    pages_per_level = [len(depth_analysis.get(i, [])) for i in range(max_depth + 1)]
    if len(pages_per_level) > 1 and pages_per_level[1] > pages_per_level[0] * 3:
        insights.append("Muitas páginas no segundo nível: Considere subcategorias")
    
    home_links = len(depth_analysis.get(0, []))
    if home_links > 10:
        insights.append("Muitos links na home: Pode diluir autoridade")
    elif home_links < 3:
        insights.append("Poucos links na home: Pode prejudicar descoberta de conteúdo")
    
    return "\n".join(insights)

# ANALISE DE VELOCIDADE APROFUNDADA
def analyze_page_speed_details(psi_data):
    if not psi_data or 'mobile' not in psi_data:
        return {}
    
    speed_metrics = {
        'lcp': 'N/A',
        'fid': 'N/A',
        'cls': 'N/A',
        'fcp': 'N/A',
        'speed_index': 'N/A',
        'total_blocking_time': 'N/A'
    }
    
    mobile_perf = psi_data.get('mobile', {}).get('psi_performance', 0)
    
    if mobile_perf >= 90:
        speed_metrics.update({
            'lcp': '< 2.5s',
            'fid': '< 100ms', 
            'cls': '< 0.1',
            'fcp': '< 1.8s'
        })
    elif mobile_perf >= 70:
        speed_metrics.update({
            'lcp': '2.5-4.0s',
            'fid': '100-300ms',
            'cls': '0.1-0.25', 
            'fcp': '1.8-3.0s'
        })
    else:
        speed_metrics.update({
            'lcp': '> 4.0s',
            'fid': '> 300ms',
            'cls': '> 0.25',
            'fcp': '> 3.0s'
        })
    
    return speed_metrics

def create_speed_metrics_dashboard(psi_data):
    if not psi_data or 'mobile' not in psi_data:
        return None
    
    mobile_perf = psi_data.get('mobile', {}).get('psi_performance', 0)
    desktop_perf = psi_data.get('desktop', {}).get('psi_performance', 0)
    
    metrics = analyze_page_speed_details(psi_data)
    
    categories = ['Performance Mobile', 'Performance Desktop', 'LCP Score', 'FID Score', 'CLS Score']
    
    lcp_score = 90 if '< 2.5s' in str(metrics.get('lcp', '')) else 70 if '2.5-4.0s' in str(metrics.get('lcp', '')) else 30
    fid_score = 90 if '< 100ms' in str(metrics.get('fid', '')) else 70 if '100-300ms' in str(metrics.get('fid', '')) else 30
    cls_score = 90 if '< 0.1' in str(metrics.get('cls', '')) else 70 if '0.1-0.25' in str(metrics.get('cls', '')) else 30
    
    values = [mobile_perf, desktop_perf, lcp_score, fid_score, cls_score]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Métricas de Velocidade',
        line=dict(color='#3B82F6', width=2),
        fillcolor='rgba(59, 130, 246, 0.3)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[25, 50, 75, 100],
                ticktext=['Ruim', 'Regular', 'Bom', 'Excelente']
            )
        ),
        title=dict(
            text="Análise Detalhada de Performance",
            font=dict(size=16),
            x=0.5
        ),
        height=400,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return fig

# COMPARACAO COMPETITIVA AVANCADA
def create_competitive_radar_chart(all_competitors_data):
    if not all_competitors_data or len(all_competitors_data) < 2:
        return None
    
    fig = go.Figure()
    
    categories = ['SEO Score', 'Performance', 'Segurança', 'Acessibilidade', 'Tech Stack']
    colors = ['#1E3A8A', '#DC2626', '#059669', '#7C3AED', '#EA580C']
    
    for i, competitor in enumerate(all_competitors_data):
        tech_count = 0
        if competitor.get('technologies'):
            for category, techs in competitor['technologies'].items():
                tech_count += len(techs)
        tech_score = min(100, tech_count * 10)
        
        values = [
            competitor.get('score', 0),
            competitor.get('psi', {}).get('mobile', {}).get('psi_performance', 0),
            competitor.get('security', {}).get('score', 0),
            competitor.get('accessibility', {}).get('score', 0),
            tech_score
        ]
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=competitor.get('domain', f'Site {i+1}'),
            line=dict(color=colors[i % len(colors)], width=2),
            fillcolor=f'rgba({int(colors[i % len(colors)][1:3], 16)}, {int(colors[i % len(colors)][3:5], 16)}, {int(colors[i % len(colors)][5:7], 16)}, 0.1)'
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[25, 50, 75, 100]
            )
        ),
        title=dict(
            text="Comparação Competitiva - Radar 360 graus",
            font=dict(size=16),
            x=0.5
        ),
        height=500,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return fig

# INSIGHTS AUTOMATIZADOS
def generate_automated_insights(main_data, competitors_data):
    insights = []
    
    main_score = main_data.get('score', 0)
    main_perf = main_data.get('psi', {}).get('mobile', {}).get('psi_performance', 0)
    main_security = main_data.get('security', {}).get('score', 0)
    
    if competitors_data:
        competitor_scores = [comp.get('score', 0) for comp in competitors_data]
        competitor_perfs = [comp.get('psi', {}).get('mobile', {}).get('psi_performance', 0) for comp in competitors_data]
        
        avg_competitor_score = sum(competitor_scores) / len(competitor_scores) if competitor_scores else 0
        avg_competitor_perf = sum(competitor_perfs) / len(competitor_perfs) if competitor_perfs else 0
        
        if main_score > avg_competitor_score:
            insights.append(f"Vantagem competitiva: Seu score SEO ({main_score}) está {main_score - avg_competitor_score:.0f} pontos acima da média dos concorrentes")
        else:
            insights.append(f"Gap competitivo: Seu score SEO está {avg_competitor_score - main_score:.0f} pontos abaixo da média dos concorrentes")
        
        if main_perf > avg_competitor_perf:
            insights.append(f"Performance superior: Sua velocidade mobile ({main_perf}) supera a média dos concorrentes")
        else:
            insights.append(f"Performance inferior: Sua velocidade mobile precisa melhorar para competir")
    
    if main_security < 60:
        insights.append("Alerta de segurança: Headers de segurança insuficientes - prioridade alta")
    
    if main_perf < 50:
        insights.append("Performance crítica: Velocidade muito baixa afeta SEO e conversões")
    
    main_technologies = main_data.get('technologies', {})
    cms_detected = main_technologies.get('cms', [])
    if not cms_detected:
        insights.append("CMS não detectado: Considere implementar um CMS para facilitar a gestão")
    
    analytics_detected = main_technologies.get('analytics', [])
    if not analytics_detected:
        insights.append("Analytics ausente: Implemente Google Analytics para monitorar performance")
    
    return insights

# INTERFACE STREAMLIT
st.set_page_config(page_title="SEO AI Strategist Pro", page_icon="🔭", layout="wide")

# Sidebar
with st.sidebar:
    st.header("Configurações de Análise")
    
    deep_analysis = st.checkbox("Análise profunda", value=True,
                               help="Inclui análise de dados estruturados")
    
    extract_structure = st.checkbox("Mapear estrutura do site", value=True,
                                   help="Cria mapa visual da arquitetura do site")
    
    analyze_tech_stack = st.checkbox("Detectar tecnologias", value=True,
                                    help="Identifica CMS, frameworks, analytics, etc.")
    
    analyze_security = st.checkbox("Análise de segurança", value=True,
                                  help="Verifica headers de segurança")
    
    max_pages_sitemap = st.slider("Máx. páginas para sitemap", 10, 50, 20,
                                 help="Limite de páginas para análise de estrutura")
    
    st.divider()
    st.markdown("### Métricas Ideais")
    st.info("""
    Title: 30-60 caracteres
    Meta Description: 150-160 caracteres
    H1: Apenas 1 por página
    Conteúdo: Mínimo 300 palavras
    Performance: Acima de 80
    Segurança: Acima de 70
    Acessibilidade: Acima de 90
    """)
    
    st.divider()
    st.markdown("### Funcionalidades Avançadas")
    st.markdown("""
    **Detecção de Tecnologias:**
    - CMS (WordPress, Shopify, etc.)
    - Frameworks JS/CSS
    - Ferramentas de Analytics
    - CDNs e Servidores Web
    
    **Análise de Segurança:**
    - Headers de segurança HTTP
    - Proteção XSS
    - Políticas de conteúdo
    
    **Acessibilidade:**
    - Alt text em imagens
    - Labels em formulários
    - Estrutura de headings
    """)

st.title("SEO AI Strategist Pro")
st.markdown("Análise avançada de SEO com IA, comparação competitiva e insights estratégicos.")

st.subheader("Análise Principal")
url_principal = st.text_input("Insira a URL do seu site:", key="url_principal",
                             placeholder="https://seusite.com.br")

# Validação em tempo real
if url_principal:
    is_valid, validation_result = validate_url(url_principal)
    if not is_valid:
        st.error(f"Erro: {validation_result}")
    else:
        if validation_result != url_principal:
            st.info(f"URL corrigida para: {validation_result}")
            url_principal = validation_result

st.subheader("Análise Competitiva (Opcional)")
competidores_raw = st.text_area("URLs dos concorrentes (uma por linha):", 
                                key="url_competidores", height=100,
                                placeholder="https://concorrente1.com\nhttps://concorrente2.com")

if st.button("Iniciar Análise Completa", type="primary"):
    if not url_principal:
        st.error("Por favor, insira a URL do seu site.")
    else:
        # Validação final
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
                
                # Análises adicionais se ativadas
                structured_data = {}
                site_structure = {}
                
                if deep_analysis:
                    structured_data = analyze_structured_data(soup_principal)
                
                if extract_structure:
                    with st.spinner("Mapeando estrutura do site..."):
                        site_structure = extract_site_structure(url_principal, max_pages=max_pages_sitemap)
                
                psi_principal = get_pagespeed_insights(url_principal)
                broken_links_principal = check_broken_links(url_principal, links_principais)
                
            except Exception as e:
                st.error(f"Erro na análise: {str(e)}")
                st.stop()
        
        st.success("Análise principal concluída!")
        
        # DASHBOARD PRINCIPAL
        st.divider()
        st.subheader(f"Dashboard: {urlparse(url_principal).netloc}")
        
        # Calcula score geral
        overall_score = calculate_overall_seo_score(onpage_principal, psi_principal, {}, structured_data)
        
        # SECAO DE SITEMAP
        if site_structure and site_structure.get('structure'):
            st.markdown("#### Mapa da Estrutura do Site")
            
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.metric("Páginas Encontradas", site_structure.get('unique_pages', 0))
            with col_info2:
                st.metric("Total de Links", site_structure.get('total_links_found', 0))
            with col_info3:
                max_depth = max([page['depth'] for page in site_structure['structure']]) if site_structure['structure'] else 0
                st.metric("Profundidade Máxima", max_depth)
            
            # Visualização do sitemap
            sitemap_fig = create_sitemap_visualization(site_structure)
            if sitemap_fig:
                st.plotly_chart(sitemap_fig, use_container_width=True)
            
            # Análise estratégica da estrutura
            strategy_insights = analyze_site_strategy(site_structure)
            if strategy_insights:
                st.markdown("**Insights da Estrutura:**")
                st.markdown(strategy_insights)
            
            st.divider()
        
        # SECAO DE TECNOLOGIAS
        if technologies_principal and analyze_tech_stack:
            st.markdown("#### Stack Tecnológico")
            
            # Cria visualização do stack tecnológico
            tech_fig = create_tech_stack_visualization(technologies_principal)
            if tech_fig:
                st.plotly_chart(tech_fig, use_container_width=True)
            
            # Mostra detalhes das tecnologias em expandir
            with st.expander("Ver tecnologias detalhadas"):
                for category, techs in technologies_principal.items():
                    if techs:
                        st.write(f"**{category.replace('_', ' ').title()}:** {', '.join(techs)}")
        
        # SECAO DE SEGURANCA E ACESSIBILIDADE
        if analyze_security:
            col_sec, col_acc = st.columns(2)
            
            with col_sec:
                st.markdown("#### Análise de Segurança")
                if security_principal:
                    sec_score = security_principal.get('score', 0)
                    sec_grade = security_principal.get('grade', 'D')
                    
                    # Gauge de segurança
                    security_gauge = create_seo_score_gauge(sec_score, f"Segurança: {sec_grade}")
                    st.plotly_chart(security_gauge, use_container_width=True)
                    
                    # Detalhes dos headers
                    with st.expander("Headers de segurança"):
                        for header, status in security_principal.get('details', {}).items():
                            st.write(f"{header}: {status}")
            
            with col_acc:
                st.markdown("#### Análise de Acessibilidade")
                if accessibility_principal:
                    acc_score = accessibility_principal.get('score', 0)
                    acc_grade = accessibility_principal.get('grade', 'D')
                    
                    # Gauge de acessibilidade  
                    accessibility_gauge = create_seo_score_gauge(acc_score, f"Acessibilidade: {acc_grade}")
                    st.plotly_chart(accessibility_gauge, use_container_width=True)
                    
                    # Issues encontradas
                    issues = accessibility_principal.get('issues', [])
                    if issues:
                        with st.expander("Problemas de acessibilidade"):
                            for issue in issues:
                                st.write(f"• {issue}")
                    else:
                        st.success("Nenhum problema básico de acessibilidade encontrado!")
        
        # Primeira linha: Score geral e métricas principais
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
                st.metric("Links Quebrados", len(broken_links_principal), delta_color="inverse")
            else:
                st.metric("Links Quebrados", "0")
        
        # Performance detalhada com Core Web Vitals
        if psi_principal:
            st.markdown("#### Análise Detalhada de Performance")
            
            # Dashboard de velocidade
            speed_radar = create_speed_metrics_dashboard(psi_principal)
            if speed_radar:
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.plotly_chart(speed_radar, use_container_width=True)
                with col2:
                    # Core Web Vitals detalhados
                    speed_metrics = analyze_page_speed_details(psi_principal)
                    st.markdown("**Core Web Vitals:**")
                    st.write(f"LCP: {speed_metrics.get('lcp', 'N/A')}")
                    st.write(f"FID: {speed_metrics.get('fid', 'N/A')}")
                    st.write(f"CLS: {speed_metrics.get('cls', 'N/A')}")
                    st.write(f"FCP: {speed_metrics.get('fcp', 'N/A')}")
            else:
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
        
        # Dados estruturados
        if deep_analysis and structured_data:
            st.markdown("#### Dados Estruturados")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Schemas JSON-LD", structured_data.get('json_ld_count', 0))
            with col2:
                st.metric("Microdata", structured_data.get('microdata_count', 0))
            with col3:
                total_schemas = len(structured_data.get('schemas_found', []))
                st.metric("Total de Schemas", total_schemas)
            
            if structured_data.get('schemas_found'):
                st.write("**Schemas detectados:**")
                for schema in structured_data['schemas_found']:
                    st.write(f"- {schema['type']} ({schema['method']})")
        
        # ANALISE COMPETITIVA
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
            competitor_dashboards = []
            
            for i, url_comp in enumerate(urls_competidores_limpas):
                is_valid, url_comp = validate_url(url_comp)
                if is_valid:
                    try:
                        with st.spinner(f"Analisando {urlparse(url_comp).netloc}..."):
                            onpage_comp, _, soup_comp, technologies_comp, security_comp, accessibility_comp = onpage_checks(url_comp)
                            if onpage_comp:
                                psi_comp = get_pagespeed_insights(url_comp)
                                structured_comp = analyze_structured_data(soup_comp)
                                site_structure_comp = extract_site_structure(url_comp, max_pages=max_pages_sitemap//2) if extract_structure else {}
                                comp_score = calculate_overall_seo_score(onpage_comp, psi_comp, {}, structured_comp)
                                
                                # Armazena dados do concorrente para dashboard individual
                                competitor_dashboards.append({
                                    'url': url_comp,
                                    'domain': urlparse(url_comp).netloc,
                                    'onpage': onpage_comp,
                                    'psi': psi_comp,
                                    'structured': structured_comp,
                                    'site_structure': site_structure_comp,
                                    'technologies': technologies_comp,
                                    'security': security_comp,
                                    'accessibility': accessibility_comp,
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
            
            # DASHBOARDS INDIVIDUAIS DOS CONCORRENTES
            if competitor_dashboards:
                st.markdown("#### Análise Individual dos Concorrentes")
                
                # Tabs para cada concorrente
                tab_names = [f"{comp['domain']}" for comp in competitor_dashboards]
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
                            st.metric("Palavras", comp_data['onpage'].get("word_count", 0))
                            st.metric("Links Internos", comp_data['onpage'].get("links_internos", 0))
                        
                        with col3:
                            st.metric("Imagens", comp_data['onpage'].get("image_count", 0))
                            perf_mobile = comp_data['psi'].get('mobile', {}).get('psi_performance', 0)
                            st.metric("Performance Mobile", f"{perf_mobile}/100")
                        
                        with col4:
                            # Novas métricas: Segurança e Acessibilidade
                            if comp_data.get('security'):
                                sec_score = comp_data['security'].get('score', 0)
                                st.metric("Segurança", f"{sec_score}/100")
                            else:
                                st.metric("Segurança", "N/A")
                            
                            if comp_data.get('accessibility'):
                                acc_score = comp_data['accessibility'].get('score', 0)
                                st.metric("Acessibilidade", f"{acc_score}/100")
                            else:
                                st.metric("Acessibilidade", "N/A")
                        
                        # Tecnologias do concorrente
                        if comp_data.get('technologies'):
                            with st.expander(f"Ver tecnologias de {comp_data['domain']}"):
                                tech_comp_fig = create_tech_stack_visualization(comp_data['technologies'])
                                if tech_comp_fig:
                                    st.plotly_chart(tech_comp_fig, use_container_width=True)
                        
                        # Sitemap do concorrente (se disponível)
                        if comp_data.get('site_structure') and comp_data['site_structure'].get('structure'):
                            with st.expander(f"Ver estrutura de {comp_data['domain']}"):
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
                
                # RADAR COMPETITIVO 360 GRAUS
                st.markdown("#### Análise Competitiva 360 graus")
                
                # Prepara dados para o radar incluindo o site principal
                all_sites_data = [{
                    'domain': urlparse(url_principal).netloc,
                    'score': overall_score,
                    'psi': psi_principal,
                    'technologies': technologies_principal,
                    'security': security_principal,
                    'accessibility': accessibility_principal
                }] + competitor_dashboards
                
                competitive_radar = create_competitive_radar_chart(all_sites_data)
                if competitive_radar:
                    st.plotly_chart(competitive_radar, use_container_width=True)
                
                # INSIGHTS AUTOMATIZADOS
                st.markdown("#### Insights Automatizados")
                
                main_site_data = {
                    'score': overall_score,
                    'psi': psi_principal,
                    'technologies': technologies_principal,
                    'security': security_principal,
                    'accessibility': accessibility_principal
                }
                
                automated_insights = generate_automated_insights(main_site_data, competitor_dashboards)
                
                if automated_insights:
                    for insight in automated_insights:
                        st.markdown(f"- {insight}")
                else:
                    st.info("Nenhum insight específico detectado. Continue monitorando!")
                
                # Gráficos comparativos tradicionais
                st.markdown("#### Comparação Visual Detalhada")
                
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
        
        # RECOMENDACOES FINAIS
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
            issues.append(f"{onpage_principal.get('images_sem_alt', 0)} imagens sem alt text - Prejudica acessibilidade")
        
        if broken_links_principal:
            issues.append(f"{len(broken_links_principal)} links quebrados - Prejudica experiência do usuário")
        
        if psi_principal and psi_principal.get('mobile', {}).get('psi_performance', 0) < 60:
            issues.append("Performance baixa - Afeta ranking e experiência")
        
        if deep_analysis and structured_data and len(structured_data.get('schemas_found', [])) == 0:
            issues.append("Dados estruturados ausentes - Oportunidade perdida para rich snippets")
        
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
        
        # Dados técnicos completos (expansível)
        with st.expander("Ver todos os dados técnicos"):
            tab1, tab2, tab3, tab4 = st.tabs(["On-Page", "Performance", "Tecnologias", "Segurança & Outros"])
            
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

# RODAPE E INFORMACOES
st.divider()
st.markdown("""
### Sobre o SEO AI Strategist Pro

**A ferramenta mais completa de análise SEO do mercado**, combinando análise técnica avançada com inteligência artificial para fornecer insights estratégicos únicos.

#### Funcionalidades Principais:
- Performance & Core Web Vitals (Google PageSpeed Insights)
- Análise on-page completa com validação robusta
- Detecção de tecnologias (tipo Wappalyzer) - CMS, frameworks, analytics
- Análise de segurança - Headers HTTP e proteções
- Auditoria de acessibilidade - WCAG básico
- Mapeamento de arquitetura - Visualização da estrutura do site
- Comparação competitiva avançada - Radar 360 graus e insights automatizados
- Score geral de SEO - Algoritmo proprietário
- Dados estruturados - Schema.org e microdata

#### Tecnologias Detectadas:
**CMS:** WordPress, Shopify, Drupal, Magento, Webflow, Wix  
**Analytics:** Google Analytics, Facebook Pixel, Hotjar, Mixpanel  
**Frameworks:** React, Vue.js, Angular, jQuery, Bootstrap, Tailwind  
**CDN:** Cloudflare, Amazon CloudFront, Google Cloud  
**E-commerce:** WooCommerce, Shopify, BigCommerce  

#### Análise de Segurança:
- Content Security Policy (CSP)
- HTTP Strict Transport Security (HSTS) 
- X-Frame-Options
- X-XSS-Protection
- Headers de proteção de conteúdo

#### Auditoria de Acessibilidade:
- Alt text em imagens
- Labels em formulários
- Estrutura semântica de headings
- Compliance WCAG básico

#### Visualizações Avançadas:
- Gráficos Gauge para scores individuais
- Radar 360 graus para comparação competitiva
- Mapa hierárquico da arquitetura do site
- Dashboards interativos com Plotly

#### Inteligência Artificial:
- Insights automatizados baseados em análise comparativa
- Recomendações priorizadas por impacto
- Estratégias competitivas personalizadas

**Desenvolvido com:** Python, Streamlit, Google Gemini AI, PageSpeed Insights API, Plotly, BeautifulSoup

---
**Próximas atualizações:** Análise de backlinks, monitoramento de posições, alertas automáticos, relatórios em PDF
""")

# Rate limiting e controle de uso
if 'analysis_count' not in st.session_state:
    st.session_state.analysis_count = 0
    st.session_state.last_analysis_time = datetime.now()

# Reset contador a cada hora
if datetime.now() - st.session_state.last_analysis_time > timedelta(hours=1):
    st.session_state.analysis_count = 0
    st.session_state.last_analysis_time = datetime.now()import streamlit as st
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
        'advertising': [],
        'javascript_frameworks': [],
        'css_frameworks': [],
        'web_servers': [],
        'cdn': [],
        'ecommerce': [],
        'security': [],
        'hosting': []
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
        'Joomla': ['joomla', '/components/', '/modules/'],
        'Shopify': ['shopify', 'cdn.shopify.com', 'shopify-section'],
        'Magento': ['magento', '/skin/frontend/'],
        'WooCommerce': ['woocommerce', 'wc-', 'wp-content/plugins/woocommerce'],
        'Squarespace': ['squarespace', 'squarespace.com'],
        'Wix': ['wix.com', 'wixstatic.com'],
        'Webflow': ['webflow.com', 'webflow.io']
    }
    
    for cms, patterns in cms_patterns.items():
        if any(pattern in html_content for pattern in patterns):
            technologies['cms'].append(cms)
    
    # Analytics & Tracking
    analytics_patterns = {
        'Google Analytics': ['google-analytics.com', 'gtag(', 'ga(', 'googletagmanager'],
        'Google Tag Manager': ['googletagmanager.com', 'gtm.js'],
        'Facebook Pixel': ['fbevents.js', 'facebook.net/tr', 'fbq('],
        'Hotjar': ['hotjar.com', 'hjid'],
        'Mixpanel': ['mixpanel.com', 'mixpanel.init'],
        'Adobe Analytics': ['omniture.com', 's_code.js'],
        'Yandex Metrica': ['metrica.yandex'],
        'Clarity': ['clarity.ms']
    }
    
    for tool, patterns in analytics_patterns.items():
        if any(pattern in html_content for pattern in patterns):
            technologies['analytics'].append(tool)
    
    # JavaScript Frameworks
    js_frameworks = {
        'React': ['react.js', '_react', 'react.production', 'react.development'],
        'Vue.js': ['vue.js', 'vue.min.js', '__vue__'],
        'Angular': ['angular.js', 'angular.min.js', 'ng-'],
        'jQuery': ['jquery', 'jquery.min.js'],
        'Bootstrap': ['bootstrap.css', 'bootstrap.js', 'bootstrap.min'],
        'Tailwind CSS': ['tailwindcss', 'tailwind.css'],
        'Next.js': ['_next/', 'next.js'],
        'Nuxt.js': ['_nuxt/', 'nuxt.js']
    }
    
    for framework, patterns in js_frameworks.items():
        if any(pattern in html_content for pattern in patterns):
            cat = 'css_frameworks' if 'css' in framework.lower() or framework in ['Bootstrap', 'Tailwind CSS'] else 'javascript_frameworks'
            technologies[cat].append(framework)
    
    # CDN Detection
    cdn_patterns = {
        'Cloudflare': ['cloudflare', 'cf-ray'],
        'Amazon CloudFront': ['cloudfront.net'],
        'Google Cloud CDN': ['googleapis.com'],
        'KeyCDN': ['keycdn.com'],
        'MaxCDN': ['maxcdn.com'],
        'Fastly': ['fastly.com']
    }
    
    for cdn, patterns in cdn_patterns.items():
        if any(pattern in str(headers).lower() for pattern in patterns):
            technologies['cdn'].append(cdn)
        if any(pattern in html_content for pattern in patterns):
            technologies['cdn'].append(cdn)
    
    # E-commerce
    ecommerce_patterns = {
        'Shopify': ['shopify', 'shopify-section'],
        'WooCommerce': ['woocommerce'],
        'Magento': ['magento'],
        'PrestaShop': ['prestashop'],
        'OpenCart': ['opencart'],
        'BigCommerce': ['bigcommerce']
    }
    
    for platform, patterns in ecommerce_patterns.items():
        if any(pattern in html_content for pattern in patterns):
            technologies['ecommerce'].append(platform)
    
    # Security
    security_headers = {
        'Content Security Policy': 'content-security-policy',
        'HSTS': 'strict-transport-security',
        'X-Frame-Options': 'x-frame-options',
        'X-XSS-Protection': 'x-xss-protection',
        'X-Content-Type-Options': 'x-content-type-options'
    }
    
    for security_name, header_name in security_headers.items():
        if header_name in [h.lower() for h in headers.keys()]:
            technologies['security'].append(security_name)
    
    # Web Server Detection
    server_header = headers.get('Server', headers.get('server', ''))
    if server_header:
        if 'nginx' in server_header.lower():
            technologies['web_servers'].append('Nginx')
        if 'apache' in server_header.lower():
            technologies['web_servers'].append('Apache')
        if 'cloudflare' in server_header.lower():
            technologies['web_servers'].append('Cloudflare')
        if 'microsoft' in server_header.lower() or 'iis' in server_header.lower():
            technologies['web_servers'].append('IIS')
    
    # Remove duplicatas
    for category in technologies:
        technologies[category] = list(set(technologies[category]))
    
    return technologies

def create_tech_stack_visualization(technologies):
    categories = []
    counts = []
    details = []
    colors_map = {
        'cms': '#8B5CF6',
        'analytics': '#10B981', 
        'javascript_frameworks': '#F59E0B',
        'css_frameworks': '#3B82F6',
        'cdn': '#EF4444',
        'ecommerce': '#8B5A00',
        'security': '#059669',
        'web_servers': '#DC2626'
    }
    
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
        marker=dict(
            color=[colors_map.get(cat.lower().replace(' ', '_'), '#6B7280') for cat in categories],
            line=dict(width=1, color='white')
        ),
        text=[f"{count} tecnologia{'s' if count > 1 else ''}" for count in counts],
        textposition='inside',
        hovertemplate='<b>%{y}</b><br>Tecnologias: %{customdata}<extra></extra>',
        customdata=details
    ))
    
    fig.update_layout(
        title=dict(
            text="Stack Tecnológico Detectado",
            font=dict(size=16, family="Arial"),
            x=0.5
        ),
        xaxis=dict(title="Número de Tecnologias"),
        yaxis=dict(title=""),
        height=400,
        margin=dict(l=150, r=50, t=50, b=50),
        plot_bgcolor='#FAFAFA',
        paper_bgcolor='white'
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
        'X-XSS-Protection': 10,
        'Referrer-Policy': 10,
        'Permissions-Policy': 5
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
    
    images = soup.find_all('img')
    images_without_alt = [img for img in images if not img.get('alt')]
    if images_without_alt:
        accessibility_issues.append(f"{len(images_without_alt)} imagens sem alt text")
        accessibility_score -= min(30, len(images_without_alt) * 5)
    
    inputs = soup.find_all('input')
    inputs_without_labels = []
    for input_elem in inputs:
        input_id = input_elem.get('id')
        if input_id:
            label = soup.find('label', {'for': input_id})
            if not label:
                inputs_without_labels.append(input_elem)
        else:
            inputs_without_labels.append(input_elem)
    
    if inputs_without_labels:
        accessibility_issues.append(f"{len(inputs_without_labels)} inputs sem labels")
        accessibility_score -= min(20, len(inputs_without_labels) * 3)
    
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    if not headings:
        accessibility_issues.append("Nenhum heading encontrado")
        accessibility_score -= 15
    
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
        "microdata_count": 0,
        "schemas_found": [],
        "errors": [],
        "recommendations": []
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
                "valid": True,
                "position": i + 1
            })
        except json.JSONDecodeError as e:
            structured_data["errors"].append(f"JSON-LD inválido na posição {i + 1}: {str(e)[:100]}")
    
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
    
    if structured_data["json_ld_count"] == 0 and structured_data["microdata_count"] == 0:
        structured_data["recommendations"].append("Implementar dados estruturados para melhorar a visibilidade nos resultados de busca")
    
    if len(structured_data["schemas_found"]) == 0:
        structured_data["recommendations"].append("Adicionar Schema.org adequado ao tipo de conteúdo (Article, Product, Organization, etc.)")
    
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

# SITEMAP E MAPEAMENTO
def extract_site_structure(url, max_depth=2, max_pages=20):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        base_domain = urlparse(url).netloc
        
        links = soup.find_all("a", href=True)
        internal_links = []
        
        for link in links:
            href = link.get('href')
            if href:
                full_url = urljoin(url, href)
                parsed = urlparse(full_url)
                
                if parsed.netloc == base_domain and not href.startswith('#'):
                    link_info = {
                        'url': full_url,
                        'path': parsed.path,
                        'text': link.get_text(strip=True)[:50],
                        'depth': len(parsed.path.strip('/').split('/')) if parsed.path != '/' else 0
                    }
                    internal_links.append(link_info)
        
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
    if not site_structure.get('structure'):
        return None
    
    pages = site_structure['structure']
    
    depth_groups = {}
    for page in pages:
        depth = page['depth']
        if depth not in depth_groups:
            depth_groups[depth] = []
        depth_groups[depth].append(page)
    
    max_per_level = 12
    for depth in depth_groups:
        if len(depth_groups[depth]) > max_per_level:
            depth_groups[depth] = depth_groups[depth][:max_per_level]
    
    fig = go.Figure()
    
    colors = ['#1E3A8A', '#7C3AED', '#059669', '#DC2626', '#EA580C', '#0891B2']
    
    level_height = 150
    max_width = 1200
    
    for depth in sorted(depth_groups.keys()):
        pages_at_depth = depth_groups[depth]
        color = colors[depth % len(colors)]
        
        num_pages = len(pages_at_depth)
        if num_pages == 1:
            x_positions = [0]
        else:
            spacing = max_width / (num_pages + 1)
            x_positions = [spacing * (i + 1) - max_width/2 for i in range(num_pages)]
        
        y_position = -depth * level_height
        
        clean_texts = []
        hover_texts = []
        
        for i, page in enumerate(pages_at_depth):
            page_text = page['text'].strip()
            
            if not page_text or len(page_text) < 3:
                path_parts = page['path'].strip('/').split('/')
                if path_parts and path_parts[-1]:
                    page_text = path_parts[-1].replace('-', ' ').replace('_', ' ')
                    page_text = ' '.join(word.capitalize() for word in page_text.split())
                else:
                    page_text = "Home" if depth == 0 else f"Página {i+1}"
            
            if len(page_text) > 15:
                display_text = page_text[:12] + "..."
            else:
                display_text = page_text
            
            clean_texts.append(display_text)
            
            hover_text = f"<b>{page_text}</b><br>"
            hover_text += f"URL: {page['url']}<br>"
            hover_text += f"Nível: {depth}<br>"
            hover_text += f"Profundidade: {len(page['path'].strip('/').split('/')) if page['path'] != '/' else 0}"
            hover_texts.append(hover_text)
        
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
        
        fig.add_annotation(
            x=-max_width/2 - 100,
            y=y_position,
            text=f"<b>Nível {depth}</b>",
            showarrow=False,
            font=dict(size=14, color=color, family="Arial"),
            xanchor="right"
        )
    
    # Conexões entre níveis
    for depth in sorted(depth_groups.keys())[:-1]:
        next_depth = depth + 1
        if next_depth in depth_groups:
            current_level = depth_groups[depth]
            next_level = depth_groups[next_depth]
            
            current_y = -depth * level_height
            next_y = -next_depth * level_height
            
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
                            dash='
