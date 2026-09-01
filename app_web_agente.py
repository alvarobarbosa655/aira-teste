# -*- coding: utf-8 -*-
"""
app_web_agente.py

Agente de IA de Fusão Multimodal para Recuperação de Áreas Degradadas
Norte de Minas Gerais - Ecótonos (Cerrado / Caatinga / Mata Seca / Veredas)

Projeto: Unimontes + Conservação Internacional (CI-Brasil) + NOVE Global
Stack: Streamlit + Pydantic + Google Gemini (SDK google-genai)
"""

import os
import json
import time
from typing import List, Literal, Optional

import streamlit as st
from pydantic import BaseModel, Field

# ==========================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================================================
st.set_page_config(
    page_title="AIRA | Diagnóstico e Manejo de Áreas Degradadas - Unimontes",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================================================
# CONSTANTES DO PROJETO
# ==========================================================================
SENHA_ACESSO = "unimontes2026"
TETO_CUSTO_HA = 16000.00

# Lista de modelos ativos e testados com redundância e alta disponibilidade
MODELOS_GEMINI_FALLBACK = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.1-flash-lite",
]

# Galeria técnica de fitofisionomias do Norte de Minas Gerais
GALERIA_BIOMAS = [
    {
        "titulo": "Cerrado Típico (Stricto Sensu)",
        "descricao": "Estrato arbóreo com troncos retorcidos, casca espessa, gramíneas e latossolos avermelhados.",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Cerrado%20Brasileiro.jpg",
    },
    {
        "titulo": "Caatinga Hiperxerófila",
        "descricao": "Vegetação xerófila, cactáceas nativas (mandacaru/xique-xique) e arbustos caducifólios em solo raso.",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/CAATINGA%20SERT%C3%83O.JPG",
    },
    {
        "titulo": "Veredas e Nascentes",
        "descricao": "Áreas hidromórficas com agrupamento de palmeiras Buriti (Mauritia flexuosa) margeando cursos hídricos.",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Buritis%20em%20Veredas%20(2).jpg",
    },
    {
        "titulo": "Mata Seca (Floresta Decidual)",
        "descricao": "Floresta Estacional Decidual sobre relevo calcário, com perda foliar severa no período de estiagem.",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Estrada%20entra%20a%20Mata%20Seca.jpg",
    },
]

# ==========================================================================
# MODELOS PYDANTIC (SAÍDA ESTRUTURADA)
# ==========================================================================

class EspecificacaoPlantio(BaseModel):
    espacamento_tecnico: str = Field(..., description="Ex: 3x3 metros (1.111 mudas/ha)")
    qtd_mudas_por_hectare: int = Field(..., description="Quantidade estimada de mudas por hectare")
    valor_unitario_medio_muda: float = Field(..., description="Valor unitário médio da muda em reais (R$)")
    custo_total_mudas_ha: float = Field(..., description="Custo total de mudas por hectare em reais (R$)")
    tecnica_preparo_coveamento: str = Field(..., description="Dimensões da cova, calagem e adubação recomendadas")
    controle_erosao_e_vocorocas: str = Field(..., description="Técnicas de contenção física de erosão (ex: paliçadas de bambu)")
    especies_nativas_recomendadas: List[str] = Field(..., description="Mínimo de 4 espécies nativas recomendadas para a fitofisionomia")

class SemanaCronograma(BaseModel):
    numero_semana: int = Field(..., description="Número sequencial da semana (1, 2, 3 ou 4)")
    titulo_fase: str = Field(..., description="Título da etapa executiva de campo")
    acoes_praticas: List[str] = Field(..., description="Lista de ações operacionais a serem executadas")
    ferramentas_insumos: List[str] = Field(..., description="Equipamentos, insumos e materiais necessários")

class DiagnosticoCompleto(BaseModel):
    bioma_ou_transicao: str = Field(..., description="Fitofisionomia ou zona de transição (ex: Transição Mata Seca ⇄ Caatinga)")
    eh_zona_transicao: bool = Field(..., description="Indica se a área situa-se em faixa de ecótono")
    justificativa_ecologica_bioma: str = Field(..., description="Explicação técnica da classificação e resolução de conflito satélite x campo")
    grau_degradacao: Literal["Baixo", "Medio", "Alto", "Critico"] = Field(..., description="Nível de degradação da área")
    principais_fatores_criticos: List[str] = Field(..., description="Fatores limitantes do terreno")
    resumo_diagnostico: str = Field(..., description="Parecer técnico detalhado do especialista")
    especificacao_plantio: EspecificacaoPlantio
    cronograma_4_semanas: List[SemanaCronograma]
    custo_total_estimado_por_ha: float = Field(..., description="Custo total por hectare (insumos + mudas + mão de obra)")
    dentro_do_teto_16k: bool = Field(..., description="Verificação de conformidade com o teto de R$ 16.000,00/ha")
    tempo_estimado_recuperacao: str = Field(..., description="Tempo previsto para reestabelecimento funcional da cobertura")

# ==========================================================================
# UTILITÁRIOS
# ==========================================================================

def obter_api_key() -> Optional[str]:
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.environ.get("GEMINI_API_KEY")

def montar_prompt(dados_campo: dict) -> str:
    prompt = f"""
Você é um Engenheiro Florestal e Fitossociólogo Sênior, especialista em recuperação de
áreas degradadas em zonas de transição ecológica (ecótonos) do Norte de Minas Gerais 
(Mata Seca, Caatinga, Cerrado e Veredas), atuando no projeto Unimontes / Conservação
Internacional (CI-Brasil) / NOVE Global.

Sua função é operar como Agente de Fusão Multimodal: cruzar os dados MACRO de sensoriamento 
remoto (satélite Sentinel-2 / NDVI / relevo) com os dados MICRO coletados em campo via 
aplicativo móvel, emitindo um diagnóstico técnico estruturado e um plano executivo de manejo.

Atenção metodológica: o NDVI de satélite isolado apresenta cerca de 50% de erro em zonas 
de transição (falso positivo de vigor em áreas tomadas por braquiária/eucalipto; e falso 
negativo de degradação na Mata Seca durante a estiagem devido à caducifólia). Utilize a 
observação de campo para calibrar com exatidão o diagnóstico.

--- DADOS DE SENSORIAMENTO REMOTO (SATÉLITE) ---
NDVI médio da área: {dados_campo['ndvi']}
Relevo / Declividade: {dados_campo['relevo']}
Período da imagem: {dados_campo['periodo_coleta']}

--- DADOS DE CAMPO (APLICATIVO MOBILE) ---
Município / Talhão: {dados_campo['regiao']}
Tipo de solo observado: {dados_campo['tipo_solo']}
Erosão / Feições físicas: {dados_campo['erosao']}
Cobertura de invasoras (Braquiária): {dados_campo['invasoras']}
Proximidade hídrica / Veredas: {dados_campo['agua']}
Histórico de uso da terra: {dados_campo['uso_anterior']}
Observações complementares: {dados_campo['observacoes']}

--- PARÂMETROS FINANCEIROS ---
Teto de custo de referência da Conservação Internacional: R$ {TETO_CUSTO_HA:,.2f} por hectare.

--- DIRETRIZES DE SAÍDA ---
1. Caracterize com precisão a Fitofisionomia / Ecótono em 'bioma_ou_transicao' e justifique em 'justificativa_ecologica_bioma'.
2. Classifique o grau de degradação e aponte os fatores críticos limitantes.
3. Elabore parecer técnico detalhado.
4. Especifique o plantio: espaçamento técnico, densidade de mudas/ha, custo unitário e total de mudas, preparo do solo/coveamento, contenção de voçorocas e pelo menos 4 espécies nativas adequadas.
5. Formule o cronograma executivo das 4 primeiras semanas de intervenção.
6. Calcule o custo global por hectare e indique conformidade com o teto de R$ 16.000,00.

Retorne estritamente o objeto JSON validado conforme o schema Pydantic.
"""
    return prompt.strip()

def chamar_agente_gemini(api_key: str, dados_campo: dict) -> DiagnosticoCompleto:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    prompt = montar_prompt(dados_campo)
    ultimo_erro = None

    for modelo in MODELOS_GEMINI_FALLBACK:
        for tentativa in range(1, 3):
            try:
                response = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=DiagnosticoCompleto,
                        temperature=0.3,
                    ),
                )
                dados_json = json.loads(response.text)
                return DiagnosticoCompleto.model_validate(dados_json)
            except Exception as e:
                ultimo_erro = e
                time.sleep(1.5)

    raise RuntimeError(f"Falha na comunicação com o agente: {ultimo_erro}")

# ==========================================================================
# GERENCIAMENTO DE SESSÃO
# ==========================================================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "diagnostico" not in st.session_state:
    st.session_state.diagnostico = None
if "erro_login" not in st.session_state:
    st.session_state.erro_login = False

def autenticar():
    if st.session_state.get("campo_senha", "") == SENHA_ACESSO:
        st.session_state.autenticado = True
        st.session_state.erro_login = False
    else:
        st.session_state.erro_login = True

def encerrar_sessao():
    st.session_state.autenticado = False
    st.session_state.diagnostico = None

# ==========================================================================
# ESTILO VISUAL CORPORATIVO / RESPONSIVO
# ==========================================================================
st.markdown(
    """
    <style>
    .main { background-color: #F8FAFC; }
    
    .header-institucional {
        border-bottom: 2px solid #E2E8F0;
        padding-bottom: 1rem;
        margin-bottom: 1.5rem;
    }
    .titulo-principal {
        color: #0F172A;
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .subtitulo-institucional {
        color: #475569;
        font-size: 0.95rem;
        font-weight: 500;
    }
    
    .card-bioma-destaque {
        background-color: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-left: 6px solid #1E40AF;
        border-radius: 6px;
        padding: 1.25rem;
        margin-bottom: 1.25rem;
    }
    .tag-ecotono {
        background-color: #EFF6FF;
        color: #1E40AF;
        border: 1px solid #BFDBFE;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 4px;
        display: inline-block;
        margin-bottom: 0.5rem;
    }
    .nome-fitofisionomia {
        font-size: 1.4rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.35;
        margin-bottom: 0.5rem;
        word-wrap: break-word;
        white-space: normal;
    }
    
    .box-indicador {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem 1.1rem;
        min-height: 90px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .rotulo-indicador {
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.35rem;
    }
    .valor-indicador {
        font-size: 1.18rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.35;
        white-space: normal;
        word-break: break-word;
    }
    
    .card-semana-exec {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #334155;
        border-radius: 6px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================================================
# TELA DE AUTENTICAÇÃO (SEM CAIXA BRANCA VAZIA)
# ==========================================================================
if not st.session_state.autenticado:
    st.markdown(
        """
        <div class="header-institucional" style="text-align: center;">
            <div class="titulo-principal">Sistema AIRA • Recuperação de Áreas Degradadas</div>
            <div class="subtitulo-institucional">Universidade Estadual de Montes Claros (Unimontes) | Conservação Internacional | NOVE Global</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_l1, col_l2, col_l3 = st.columns([1, 1.3, 1])
    with col_l2:
        with st.container(border=True):
            st.markdown("#### Autenticação Técnica")
            st.caption("Acesso restrito a pesquisadores e corpo técnico credenciado
