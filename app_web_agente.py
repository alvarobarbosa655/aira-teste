import streamlit as st
import os
import json
import time 
import warnings
from pydantic import BaseModel, Field
from typing import Literal, List
from google import genai
from google.genai import types

warnings.filterwarnings("ignore")

# Configuração da página Web
st.set_page_config(
    page_title="AIRA - Sistema Inteligente de Recuperação Ambiental",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS personalizada para um design moderno e executivo
st.markdown("""
<style>
    .main { background-color: #F8FAFC; }
    .stMetric {
        background-color: #FFFFFF;
        padding: 14px;
        border-radius: 10px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .card-semana {
        background: #FFFFFF;
        border-left: 5px solid #2D6A4F;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 12px;
        border-top: 1px solid #E2E8F0;
        border-right: 1px solid #E2E8F0;
        border-bottom: 1px solid #E2E8F0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }
    .badge-transicao {
        background-color: #E0F2FE;
        color: #0369A1;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
        margin-bottom: 8px;
    }
    .hero-title {
        color: #1B4332;
        font-weight: 800;
        font-size: 2.2rem;
        margin-bottom: 0px;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# REGISTRO DE METADADOS DAS FOTOGRAFIAS REAIS DOS BIOMAS BRASILEIROS
# -------------------------------------------------------------
# 1. CERRADO: Paisagem típica do Brasil Central / MG com árvores de casca grossa e galhos retorcidos, solo avermelhado e gramíneas nativas.
FOTO_CERRADO = {
    "url": "https://images.unsplash.com/photo-1620052581237-5d36667be337?auto=format&fit=crop&w=800&q=80",
    "titulo": "🌾 Cerrado Típico (Brasil Central / MG)",
    "descricao": "Árvores de troncos retorcidos, gramíneas nativas e solo avermelhado típico do Planalto Central."
}

# 2. CAATINGA: Vegetação xerófita do Sertão brasileiro com cactáceas nativas (Mandacaru / Facheiro) e arbustos decíduos sobre solo pedregoso.
FOTO_CAATINGA = {
    "url": "https://images.unsplash.com/photo-1596707323868-963d3e691230?auto=format&fit=crop&w=800&q=80",
    "titulo": "🌵 Caatinga Hiperxerófila (Sertão)",
    "descricao": "Presença de Mandacarus nativos e arbustos caducifólios adaptados à aridez, sem areia desértica."
}

# 3. VEREDAS: Ecossistema hidromórfico com agrupamento icônico de palmeiras Buriti (Mauritia flexuosa) e curso d'água cristalina.
FOTO_VEREDAS = {
    "url": "https://images.unsplash.com/photo-1582650625119-3a31f8418b7d?auto=format&fit=crop&w=800&q=80",
    "titulo": "💧 Veredas & Buritizais (Norte de MG)",
    "descricao": "Palmeiras Buriti (Mauritia flexuosa) margeando nascentes e cursos d'água em solo hidromórfico."
}

# 4. MATA SECA: Floresta Estacional Decidual de transição regional com perda sazonal de folhagem e relevo cárstico.
FOTO_MATA_SECA = {
    "url": "https://images.unsplash.com/photo-1511497584788-87676104235f?auto=format&fit=crop&w=800&q=80",
    "titulo": "🍂 Mata Seca (Floresta Decidual)",
    "descricao": "Vegetação arbórea de transição ecológica com caducifólia severa no período de estiagem."
}

# -------------------------------------------------------------
# 1. CONTROLE DE SESSÃO / TELA DE LOGIN COM FOTOGRAFIAS REAIS DO BRASIL
# -------------------------------------------------------------
SENHA_CORRETA = "unimontes2026"

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# Se não estiver logado, exibe a tela de login visual com fotografias autênticas
if not st.session_state.autenticado:
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_login, col_galeria = st.columns([1.1, 1.4], gap="large")
    
    with col_login:
        st.markdown("<p class='hero-title'>🌿 Projeto AIRA</p>", unsafe_allow_html=True)
        st.markdown("### **Diagnóstico & Restauração de Áreas Degradadas**")
        st.caption("Universidade Estadual de Montes Claros • Unimontes")
        st.caption("Parceria: Conservação Internacional (CI-Brasil) & NOVE Global")
        st.markdown("---")
        
        st.markdown("#### 🔐 Acesso Restrito à Equipe Técnica")
        st.info("Painel de inteligência multimodal para ecótonos do Norte de Minas.")
        
        with st.form("form_login"):
            senha_input = st.text_input("Digite o Código de Acesso do Projeto:", type="password", placeholder="Digite sua senha...")
            btn_entrar = st.form_submit_button("🚀 Acessar Painel do Agente", type="primary", use_container_width=True)
            
            if btn_entrar:
                if senha_input == SENHA_CORRETA:
                    st.session_state.autenticado = True
                    st.rerun()
                else:
                    st.error("Código de acesso incorreto. Tente novamente.")
                    
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("💡 Senha padrão do projeto: `unimontes2026`")

    with col_galeria:
        st.markdown("### 🇧🇷 Biomas & Zonas de Transição do Norte de Minas")
        st.caption("Fotografias reais das fitofisionomias brasileiras monitoradas pelo sistema:")
        
        g_col1, g_col2 = st.columns(2)
        
        with g_col1:
            st.image(FOTO_CERRADO["url"], caption=FOTO_CERRADO["titulo"], use_container_width=True)
            st.image(FOTO_CAATINGA["url"], caption=FOTO_CAATINGA["titulo"], use_container_width=True)
            
        with g_col2:
            st.image(FOTO_MATA_SECA["url"], caption=FOTO_MATA_SECA["titulo"], use_container_width=True)
            st.image(FOTO_VEREDAS["url"], caption=FOTO_VEREDAS["titulo"], use_container_width=True)

    st.stop()

# -------------------------------------------------------------
# 2. MODELO DE DADOS AVANÇADO (PYDANTIC)
# -------------------------------------------------------------
class EtapaSemanal(BaseModel):
    semana_num: int = Field(description="Número da semana (1, 2, 3 ou 4)")
    titulo_fase: str = Field(description="Ex: Isolamento e Controle de Invasoras")
    acoes_principais: List[str] = Field(description="Passo a passo prático de campo")
    insumos_e_ferramentas: str = Field(description="Ferramentas, mudas ou insumos necessários")

class EspecificacaoPlantio(BaseModel):
    espacamento_tecnico: str = Field(description="Ex: 3x3 metros em quincôncio (1.111 mudas/ha)")
    qtd_mudas_por_hectare: int = Field(description="Quantidade estimada de mudas por hectare")
    valor_unitario_medio_muda: float = Field(description="Valor médio por muda em reais (ex: 4.50)")
    custo_total_mudas_ha: float = Field(description="Custo total com mudas por hectare")
    tecnica_preparo_coveamento: str = Field(description="Dimensões da cova (ex: 40x40x40cm), adubação e calagem")
    controle_erosao_e_voçorocas: str = Field(description="Recomendação para ravinas/voçorocas (ex: paliçadas de bambu)")
    especies_nativas_recomendadas: List[str] = Field(description="Lista com pelo menos 4 espécies nativas recomendadas para o bioma")

class DiagnosticoCompleto(BaseModel):
    bioma_ou_transicao: str = Field(description="Bioma ou zona de transição identificada")
    eh_zona_transicao: bool = Field(description="True se for área de ecótono / transição")
    grau_degradacao: Literal["Baixo", "Medio", "Alto", "Critico"]
    principais_fatores_criticos: List[str] = Field(description="Problemas que causaram a degradação")
    resumo_diagnostico: str = Field(description="Parecer técnico detalhado do especialista")
    especificacao_plantio: EspecificacaoPlantio
    cronograma_4_semanas: List[EtapaSemanal]
    custo_total_estimado_por_ha: float = Field(description="Custo global por hectare (insumos + mudas + mão de obra)")
    dentro_do_teto_16k: bool = Field(description="True se o custo for até R$ 16.000,00")
    tempo_estimado_recuperacao: str = Field(description="Ex: 2 a 3 anos com monitoramento bianual")

# Chave do Gemini
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

# -------------------------------------------------------------
# 3. INTERFACE PRINCIPAL (USUÁRIO LOGADO)
# -------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/natural-food.png", width=60)
    st.markdown("### **Projeto AIRA**")
    st.caption("Universidade Estadual de Montes Claros • Unimontes")
    st.caption("Parceria: Conservação Internacional / NOVE Global")
    st.markdown("---")
    st.markdown("👤 **Usuário:** Pesquisador Autorizado")
    st.markdown("🟢 **Status:** Conectado à IA Especialista")
    
    if st.button("🚪 Sair do Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

# Cabeçalho Principal
st.title("🌿 AIRA • Painel de Diagnóstico e Plano de Manejo")
st.caption("Inteligência Artificial Multimodal para Recuperação de Áreas Degradadas no Norte de Minas")
st.markdown("---")

col_esq, col_dir = st.columns([1.1, 1.3])

with col_esq:
    st.markdown("### 🛰️ 1. Parâmetros de Sensoriamento e Campo")
    
    with st.expander("📍 Identificação da Propriedade", expanded=True):
        nome_area = st.text_input("Nome da Propriedade / Talhão:", value="Fazenda Piloto 40ha - Norte de MG")
        tamanho_ha = st.number_input("Área a Recuperar (Hectares):", min_value=1.0, value=40.0, step=1.0)
        
        opcoes_biomas = [
            "Transição: Mata Seca ⇄ Caatinga (Ecótono)",
            "Transição: Cerrado ⇄ Mata Seca",
            "Transição: Vereda ⇄ Cerrado",
            "Mata Seca (Caducifólia)",
            "Caatinga Hiperxerófila",
            "Cerrado Típico (Stricto Sensu)",
            "Vereda (Zona Hidromórfica)"
        ]
        bioma_selecionado = st.selectbox("Classificação Fisionômica / Bioma:", opcoes_biomas)

    with st.expander("📡 Dados de Satélite (Sentinel-2 / MDE)", expanded=True):
        ndvi = st.slider("Índice NDVI (Vigor Vegetativo):", min_value=0.0, max_value=1.0, value=0.48, step=0.01,
                         help="Valores abaixo de 0.50 indicam perda severa de cobertura verde no período.")
        relevo = st.selectbox("Declividade e Relevo do Terreno:", ["Plano (0 - 3%)", "Ondulado / Acidentado (8 - 20%)", "Serra / Declividade Severa (> 20%)"])

    with st.expander("📱 Feições Coletadas em Campo (App Mobile)", expanded=True):
        problemas_selecionados = st.multiselect(
            "Problemas e Feições Observadas no Terreno:",
            [
                "Presença de Voçoroca / Ravinamento Ativo", 
                "Infestação Severa de Capim Braquiária", 
                "Solo Arenoso com Horizonte Orgânico Degradado", 
                "Solo Exposto e Compactado por Pisoteio", 
                "Histórico de Queimadas Recentes", 
                "Ausência Quase Total de Banco de Sementes Nativas"
            ],
            default=["Presença de Voçoroca / Ravinamento Ativo", "Infestação Severa de Capim Braquiária", "Solo Arenoso com Horizonte Orgânico Degradado"]
        )

    botao_executar = st.button("🚀 Gerar Diagnóstico e Cronograma Completo", type="primary", use_container_width=True)

with col_dir:
    st.markdown("### 📋 2. Diagnóstico Técnico & Plano Executivo")
    
    if botao_executar:
        if not GEMINI_API_KEY:
            st.error("⚠️ Chave de API não configurada nos Secrets do Streamlit.")
        else:
            with st.spinner("🤖 O Agente de IA está processando as variáveis e calculando o plano detalhado..."):
                relato_dados = f"""
                Propriedade: {nome_area}, {tamanho_ha} ha.
                Fisionomia: {bioma_selecionado}.
                Sensoriamento: NDVI {ndvi}, Relevo {relevo}.
                Campo: {', '.join(problemas_selecionados)}.
                Teto Orçamentário Referência: R$ 16.000,00 por hectare (Conservação Internacional).
                """
                
                modelos = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-3.6-flash']
                sucesso = False
                resultado_obj = None
                ultimo_erro = None
                
                client = genai.Client(api_key=GEMINI_API_KEY)
                
                for mod in modelos:
                    try:
                        resp = client.models.generate_content(
                            model=mod,
                            contents=f"Você é o Agente Especialista Sênior em Restauração Florestal do Projeto AIRA/Unimontes. Analise o caso detalhadamente, fornecendo plano de plantio com espaçamento, quantidade e custo de mudas, e cronograma detalhado de 4 semanas: {relato_dados}",
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                response_schema=DiagnosticoCompleto,
                            ),
                        )
                        resultado_obj = json.loads(resp.text)
                        sucesso = True
                        break
                    except Exception as err:
                        ultimo_erro = err
                        time.sleep(1)

                if sucesso and resultado_obj:
                    # Tabs organizadas para melhor visualização
                    tab1, tab2, tab3, tab4 = st.tabs([
                        "🌿 Diagnóstico Geral", 
                        "📅 Cronograma de 4 Semanas", 
                        "🌱 Mudas & Especificação", 
                        "🗺️ Orçamento & GIS"
                    ])
                    
                    with tab1:
                        grau = resultado_obj["grau_degradacao"]
                        if grau in ["Alto", "Critico"]:
                            st.error(f"**Grau de Degradação:** {grau.upper()}")
                        elif grau == "Medio":
                            st.warning(f"**Grau de Degradação:** {grau.upper()}")
                        else:
                            st.success(f"**Grau de Degradação:** {grau.upper()}")

                        if resultado_obj.get("eh_zona_transicao", False):
                            st.markdown(f"<div class='badge-transicao'>🔄 Zona de Tensão Ecológica: {resultado_obj.get('bioma_ou_transicao')}</div>", unsafe_allow_html=True)

                        st.markdown("#### 📝 Parecer Técnico do Especialista:")
                        st.write(resultado_obj["resumo_diagnostico"])
                        
                        st.markdown("#### ⚠️ Fatores Críticos Identificados:")
                        for fat in resultado_obj["principais_fatores_criticos"]:
                            st.write(f"• {fat}")
                        
                        st.info(f"⏳ **Tempo Estimado para Regeneração:** {resultado_obj.get('tempo_estimado_recuperacao', '2 a 4 anos')}")

                    with tab2:
                        st.markdown("#### 📅 Cronograma Executivo de Campo (Primeiras 4 Semanas)")
                        st.caption("Plano tático de intervenção imediata para garantia de pega e contenção:")
                        
                        for etapa in resultado_obj.get("cronograma_4_semanas", []):
                            st.markdown(f"""
                            <div class='card-semana'>
                                <h4 style='margin:0; color:#1B4332;'>Semana {etapa['semana_num']}: {etapa['titulo_fase']}</h4>
                                <p style='margin-top:6px; margin-bottom:4px;'><b>Ações Práticas:</b></p>
                                <ul style='margin-bottom:6px;'>
                                    {''.join([f"<li>{acao}</li>" for acao in etapa['acoes_principais']])}
                                </ul>
                                <p style='margin:0; color:#475569; font-size:0.88rem;'>🛠️ <b>Insumos & Ferramentas:</b> {etapa['insumos_e_ferramentas']}</p>
                            </div>
                            """, unsafe_allow_html=True)

                    with tab3:
                        st.markdown("#### 🌱 Especificações Técnicas de Plantio e Mudas")
                        plantio = resultado_obj["especificacao_plantio"]
                        
                        m_a, m_b = st.columns(2)
                        m_a.metric("Mudas por Hectare", f"{plantio['qtd_mudas_por_hectare']:,} un.")
                        m_b.metric("Valor Médio / Muda", f"R$ {plantio['valor_unitario_medio_muda']:.2f}")

                        st.markdown(f"**📐 Espaçamento Recomendado:** {plantio['espacamento_tecnico']}")
                        st.markdown(f"**🚜 Preparo do Solo e Coveamento:** {plantio['tecnica_preparo_coveamento']}")
                        st.markdown(f"**🪵 Manejo de Invasoras & Erosão:** {plantio['controle_erosao_e_voçorocas']}")
                        
                        st.markdown("#### 🌳 Espécies Nativas Selecionadas para o Bioma:")
                        esp_cols = st.columns(2)
                        for idx, esp in enumerate(plantio["especies_nativas_recomendadas"]):
                            esp_cols[idx % 2].write(f"🌿 **{esp}**")

                    with tab4:
                        st.markdown("#### 💰 Análise Financeira por Hectare")
                        plantio = resultado_obj["especificacao_plantio"]
                        
                        c1, c2 = st.columns(2)
                        c1.metric("Custo de Mudas / ha", f"R$ {plantio['custo_total_mudas_ha']:,.2f}")
                        c2.metric("Custo Total Estimado / ha", f"R$ {resultado_obj['custo_total_estimado_por_ha']:,.2f}")
                        
                        orc_ok = resultado_obj["dentro_do_teto_16k"]
                        if orc_ok:
                            st.success(f"✅ **Viabilidade Orçamentária Aprovada:** Custo dentro do teto de R$ 16.000/ha da Conservação Internacional.")
                        else:
                            st.warning(f"⚠️ **Atenção ao Teto:** Custo excede R$ 16.000/ha. Recomenda-se aumentar espaçamento ou mesclar com cercamento.")

                        st.markdown("---")
                        with st.expander("📦 Exportar Objeto JSON Estruturado (QGIS / Relatório)"):
                            st.json(resultado_obj)
                else:
                    st.error(f"Erro momentâneo de conexão. Clique no botão novamente para tentar. (Detalhes: {ultimo_erro})")
    else:
        st.info("👈 Ajuste os parâmetros de satélite e campo à esquerda e clique em **Gerar Diagnóstico** para visualizar o plano completo.")
