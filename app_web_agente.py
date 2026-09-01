import streamlit as st
import os
import json
import warnings
from pydantic import BaseModel, Field
from typing import Literal, List
from google import genai
from google.genai import types

warnings.filterwarnings("ignore")

# Configuração da página Web
st.set_page_config(page_title="AIRA - Diagnóstico Ambiental (Unimontes)", page_icon="🌿", layout="wide")

# 1. Molde Pydantic com suporte a Zonas de Transição Ecológica
class DiagnosticoAmbiental(BaseModel):
    bioma_ou_transicao: str = Field(description="Bioma ou zona de transição/ecótono identificada")
    eh_zona_transicao: bool = Field(description="True se for uma área de transição/interseção ecológica")
    grau_degradacao: Literal["Baixo", "Medio", "Alto", "Critico"] = Field(description="Nível de degradação da área")
    principais_problemas: List[str] = Field(description="Problemas encontrados no terreno")
    intervencao_sugerida: str = Field(description="Recomendação técnica de manejo adaptada à fisionomia regional")
    especies_recomendadas: List[str] = Field(description="Exemplos de espécies nativas recomendadas para o bioma")
    custo_estimado_por_hectare: float = Field(description="Custo em reais por hectare")
    viavel_orcamento_16k: bool = Field(description="True se o custo for até R$ 16.000,00 por hectare")

# Chave do Gemini fica 100% segura e oculta no backend
API_KEY_INTERNA = "AQ.Ab8RN6J_WWIvdIYEylXVXAXULnbzv1pHGqovRdnzmdaQQcPQ2g"
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", API_KEY_INTERNA))

# Senha simples de acesso do projeto
SENHA_CORRETA = "unimontes2026"

# Barra lateral limpa e profissional
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/natural-food.png", width=64)
    st.title("Painel AIRA")
    st.caption("Universidade Estadual de Montes Claros • Unimontes")
    st.caption("Projeto Conservação Internacional / NOVE Global")
    st.markdown("---")
    
    # Campo amigável de Senha de Acesso
    senha_digitada = st.text_input("🔐 Senha de Acesso ao Projeto:", type="password", value="unimontes2026", help="Senha padrão do projeto: unimontes2026")
    
    if senha_digitada == SENHA_CORRETA:
        st.success("🟢 Acesso Liberado")
    else:
        st.error("🔴 Acesso Bloqueado")

# --- INTERFACE VISUAL (TELA) ---
st.title("🌿 Projeto AIRA / Unimontes")
st.subheader("Painel Inteligente de Diagnóstico e Recuperação de Áreas Degradadas")
st.caption("Desenvolvido para zonas de transição ecológica no Norte de Minas (Mata Seca, Caatinga, Cerrado e Veredas)")
st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 🛰️ 1. Dados de Satélite e Campo")
    
    nome_area = st.text_input("Nome da Propriedade / Talhão:", value="Fazenda Piloto 40ha")
    
    opcoes_biomas = [
        "Transição: Mata Seca ⇄ Caatinga (Ecótono)",
        "Transição: Cerrado ⇄ Mata Seca",
        "Transição: Vereda ⇄ Cerrado",
        "Mata Seca (Caducifólia)",
        "Caatinga",
        "Cerrado Típico",
        "Vereda (Área Úmida)"
    ]
    bioma_selecionado = st.selectbox("Classificação Fisionômica / Bioma:", opcoes_biomas)
    
    tamanho_ha = st.number_input("Tamanho da Área (Hectares):", min_value=1.0, value=40.0, step=1.0)
    
    st.markdown("#### Indicadores de Sensoriamento Remoto (Sentinel / MDE):")
    ndvi = st.slider("Índice NDVI (Vigor da Vegetação):", min_value=0.0, max_value=1.0, value=0.52, step=0.01)
    relevo = st.selectbox("Declividade / Relevo:", ["Plano", "Ondulado / Acidentado", "Serra / Muito Íngreme"])
    
    st.markdown("#### Observações Coletadas em Campo (App Mobile):")
    problemas_selecionados = st.multiselect(
        "Problemas e Feições no Terreno:",
        [
            "Presença de Voçoroca / Ravinas Profundas", 
            "Infestação de Capim Braquiária", 
            "Solo Arenoso / Baixa Matéria Orgânica", 
            "Indícios de Queimada Recente", 
            "Ausência de Mudas Nativas",
            "Solo Exposto e Compactado"
        ],
        default=["Presença de Voçoroca / Ravinas Profundas", "Infestação de Capim Braquiária"]
    )
    
    botao_analisar = st.button("🚀 Executar Diagnóstico com Agente de IA", type="primary", use_container_width=True)

with col2:
    st.markdown("### 📋 2. Diagnóstico e Plano de Manejo Gerado")
    
    if botao_analisar:
        if senha_digitada != SENHA_CORRETA:
            st.error("⛔ Senha de acesso incorreta! Por favor, insira a senha correta no menu lateral esquerdo.")
        else:
            with st.spinner("O Agente de IA está cruzando os dados e calculando a intervenção..."):
                relato = f"""
                Propriedade: {nome_area}, {tamanho_ha} hectares.
                Classificação ecológica: {bioma_selecionado}.
                Satélite: NDVI de {ndvi}, Relevo {relevo}.
                Campo: Problemas identificados: {', '.join(problemas_selecionados)}.
                """
                
                try:
                    client = genai.Client(api_key=GEMINI_API_KEY)
                    resposta = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=f"Você é o Agente Especialista do Projeto AIRA/Unimontes. Analise os dados considerando regras regionais do Norte de Minas e preencha o diagnóstico: {relato}",
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=DiagnosticoAmbiental,
                        ),
                    )
                    
                    resultado = json.loads(resposta.text)
                    
                    grau = resultado["grau_degradacao"]
                    if grau in ["Alto", "Critico"]:
                        st.error(f"**Grau de Degradação:** {grau}")
                    elif grau == "Medio":
                        st.warning(f"**Grau de Degradação:** {grau}")
                    else:
                        st.success(f"**Grau de Degradação:** {grau}")
                    
                    if resultado.get("eh_zona_transicao", False):
                        st.info(f"🔄 **Zona de Transição Ecológica Detectada:** Intervenção adaptada para transição ({resultado.get('bioma_ou_transicao', '')}).")
                    
                    st.write(f"**💡 Intervenção Recomendada:**\n\n{resultado['intervencao_sugerida']}")
                    
                    if "especies_recomendadas" in resultado and resultado["especies_recomendadas"]:
                        st.write(f"**🌱 Espécies Nativas Sugeridas:** {', '.join(resultado['especies_recomendadas'])}")
                    
                    m1, m2 = st.columns(2)
                    custo = resultado['custo_estimado_por_hectare']
                    m1.metric("Custo Estimado / ha", f"R$ {custo:,.2f}")
                    
                    viavel = resultado['viavel_orcamento_16k']
                    if viavel:
                        m2.metric("Orçamento (Teto R$ 16k da Conservação Int.)", "✅ Aprovado (Dentro da Meta)")
                    else:
                        m2.metric("Orçamento (Teto R$ 16k da Conservação Int.)", "❌ Excede Teto")
                    
                    st.markdown("#### 🔍 Problemas Registrados:")
                    for p in resultado["principais_problemas"]:
                        st.write(f"- {p}")
                    
                    with st.expander("Ver JSON Estruturado (Dados para QGIS e Relatório)"):
                        st.json(resultado)
                        
                except Exception as e:
                    st.error(f"Erro ao consultar o agente: {e}")
    else:
        st.write("👈 Preencha os dados à esquerda e clique no botão para gerar a análise.")
