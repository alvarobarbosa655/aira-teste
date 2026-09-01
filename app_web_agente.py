# -*- coding: utf-8 -*-
"""
app_web_agente.py

Agente de IA de Fusão Multimodal para Recuperação de Áreas Degradadas
Norte de Minas Gerais - Ecótonos (Cerrado / Caatinga / Mata Seca / Veredas)

Projeto: Unimontes + Conservação Internacional (CI-Brasil) + NOVE Global

Stack: Streamlit + Pydantic + Google Gemini (SDK google-genai)

Para executar:
    pip install streamlit pydantic google-genai
    streamlit run app_web_agente.py

Configuração da chave de API (uma das duas formas):
    1) Arquivo .streamlit/secrets.toml:
           GEMINI_API_KEY = "sua-chave-aqui"
    2) Variável de ambiente:
           export GEMINI_API_KEY="sua-chave-aqui"
"""

import os
import json
import time
from typing import List, Literal, Optional

import streamlit as st
from pydantic import BaseModel, Field

# ==========================================================================
# CONFIGURAÇÃO DA PÁGINA (deve ser a primeira chamada Streamlit do script)
# ==========================================================================
st.set_page_config(
    page_title="Agente IA | Recuperação de Áreas Degradadas - Norte de MG",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================================================
# CONSTANTES DO PROJETO
# ==========================================================================
SENHA_ACESSO = "unimontes2026"
TETO_CUSTO_HA = 16000.00

MODELOS_GEMINI_FALLBACK = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-3.6-flash",
]

# Galeria de fitofisionomias do Norte de Minas Gerais (imagens reais em alta
# resolução, hospedadas no Wikimedia Commons, licenças livres/CC).
GALERIA_BIOMAS = [
    {
        "titulo": "Cerrado",
        "descricao": "Árvores retorcidas, casca grossa e solo avermelhado (latossolo).",
        "url": "https://upload.wikimedia.org/wikipedia/commons/8/8b/Cerrado_S%C3%A3o_Roque_de_Minas_MG.jpg",
    },
    {
        "titulo": "Caatinga",
        "descricao": "Vegetação xerófita, mandacarus e árvores caducifólias adaptadas à seca.",
        "url": "https://upload.wikimedia.org/wikipedia/commons/6/6b/Caatinga_vegetation_in_Brazil.jpg",
    },
    {
        "titulo": "Veredas",
        "descricao": "Buritizais (Mauritia flexuosa) ao redor de nascentes e cursos d'água.",
        "url": "https://upload.wikimedia.org/wikipedia/commons/0/0e/Buriti_Mauritia_flexuosa.jpg",
    },
    {
        "titulo": "Mata Seca",
        "descricao": "Floresta estacional decidual, caducifólia no período de estiagem.",
        "url": "https://upload.wikimedia.org/wikipedia/commons/3/3b/Floresta_estacional_decidual.jpg",
    },
]

# ==========================================================================
# MODELOS PYDANTIC (SAÍDA ESTRUTURADA DO AGENTE)
# ==========================================================================


class EspecificacaoPlantio(BaseModel):
    espacamento_tecnico: str = Field(
        ..., description="Ex: 3x3m - 1.111 mudas/ha"
    )
    qtd_mudas_por_hectare: int = Field(..., description="Quantidade de mudas por hectare")
    valor_unitario_medio_muda: float = Field(..., description="Valor unitário médio da muda em R$")
    custo_total_mudas_ha: float = Field(..., description="Custo total de mudas por hectare em R$")
    tecnica_preparo_coveamento: str = Field(
        ..., description="Dimensões da cova, calagem e adubação recomendadas"
    )
    controle_erosao_e_vocorocas: str = Field(
        ..., description="Técnicas de contenção de erosão e voçorocas, ex: paliçadas de bambu"
    )
    especies_nativas_recomendadas: List[str] = Field(
        ..., description="Mínimo de 4 espécies nativas reais do bioma/ecótono"
    )


class SemanaCronograma(BaseModel):
    numero_semana: int
    titulo_fase: str
    acoes_praticas: List[str]
    ferramentas_insumos: List[str]


class DiagnosticoCompleto(BaseModel):
    bioma_ou_transicao: str = Field(
        ..., description="Ex: Transição Mata Seca ⇄ Caatinga"
    )
    eh_zona_transicao: bool
    grau_degradacao: Literal["Baixo", "Medio", "Alto", "Critico"]
    principais_fatores_criticos: List[str]
    resumo_diagnostico: str = Field(..., description="Parecer técnico detalhado do especialista")
    especificacao_plantio: EspecificacaoPlantio
    cronograma_4_semanas: List[SemanaCronograma]
    custo_total_estimado_por_ha: float
    dentro_do_teto_16k: bool
    tempo_estimado_recuperacao: str


# ==========================================================================
# UTILITÁRIOS
# ==========================================================================


def obter_api_key() -> Optional[str]:
    """Lê a chave de API do Gemini a partir de st.secrets ou de variável de ambiente."""
    chave = None
    try:
        chave = st.secrets["GEMINI_API_KEY"]
    except Exception:
        chave = os.environ.get("GEMINI_API_KEY")
    return chave


def montar_prompt(dados_campo: dict) -> str:
    """Monta o prompt de fusão multimodal com os dados macro (satélite) e micro (campo)."""
    prompt = f"""
Você é um Engenheiro Florestal e Agrônomo Sênior, especialista em recuperação de
áreas degradadas em ecótonos do Norte de Minas Gerais (transições entre Cerrado,
Caatinga, Mata Seca e Veredas), atuando no projeto Unimontes / Conservação
Internacional (CI-Brasil) / NOVE Global.

Sua tarefa é atuar como um Agente de Fusão Multimodal, cruzando dados MACRO de
sensoriamento remoto (satélite Sentinel-2 / NDVI / relevo) com dados MICRO
coletados em campo via aplicativo mobile, para emitir um diagnóstico técnico
estruturado e um plano de recuperação executável.

Lembre-se: o NDVI de satélite sozinho tem ~50% de erro em zonas de transição
(falso positivo de vegetação verde que na verdade é eucalipto/braquiária;
falsa degradação na Mata Seca durante a estiagem, quando a floresta perde as
folhas naturalmente). Use o julgamento agronômico de campo para corrigir o
viés do dado de satélite.

--- DADOS MACRO (SATÉLITE) ---
NDVI médio da área: {dados_campo['ndvi']}
Relevo / Declividade: {dados_campo['relevo']}
Período da coleta: {dados_campo['periodo_coleta']}

--- DADOS MICRO (CAMPO / APP MOBILE) ---
Município/Região: {dados_campo['regiao']}
Tipo de solo observado: {dados_campo['tipo_solo']}
Presença de voçorocas/erosão: {dados_campo['erosao']}
Presença de braquiária/invasoras: {dados_campo['invasoras']}
Proximidade de curso d'água / nascente: {dados_campo['agua']}
Uso anterior da terra: {dados_campo['uso_anterior']}
Observações adicionais do técnico de campo: {dados_campo['observacoes']}

--- RESTRIÇÃO ORÇAMENTÁRIA ---
Teto de custo de referência da Conservação Internacional: R$ {TETO_CUSTO_HA:,.2f} por hectare recuperado.

--- INSTRUÇÕES ---
1. Determine o bioma real ou a transição ecológica (ecótono), corrigindo o
   viés do NDVI com os dados de campo.
2. Classifique o grau de degradação.
3. Liste os principais fatores críticos do terreno.
4. Escreva um parecer técnico detalhado (resumo_diagnostico).
5. Especifique tecnicamente o plantio: espaçamento, quantidade de mudas/ha,
   valor unitário médio de muda (mercado de mudas nativas em MG),
   custo total de mudas por hectare, técnica de coveamento (dimensões,
   calagem, adubação), controle de erosão/voçorocas, e no mínimo 4 espécies
   nativas REAIS do bioma/ecótono identificado.
6. Monte um cronograma prático das 4 primeiras semanas de campo.
7. Calcule o custo total estimado por hectare (mudas + insumos + mão de obra +
   controle de erosão) e indique se está dentro do teto de R$ 16.000,00/ha.
8. Estime o tempo de recuperação (ex: "18 a 24 meses para cobertura funcional").

Responda ESTRITAMENTE no formato JSON estruturado solicitado, em português do Brasil.
"""
    return prompt.strip()


def chamar_agente_gemini(api_key: str, dados_campo: dict) -> DiagnosticoCompleto:
    """
    Chama a API do Gemini com fallback automático entre modelos e retry em
    caso de sobrecarga (503), retornando um objeto DiagnosticoCompleto validado.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    prompt = montar_prompt(dados_campo)

    ultimo_erro = None
    max_tentativas_por_modelo = 2

    for modelo in MODELOS_GEMINI_FALLBACK:
        for tentativa in range(1, max_tentativas_por_modelo + 1):
            try:
                st.toast(f"Consultando modelo {modelo} (tentativa {tentativa})...", icon="🤖")
                response = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=DiagnosticoCompleto,
                        temperature=0.4,
                    ),
                )

                texto_bruto = response.text
                dados_json = json.loads(texto_bruto)
                diagnostico = DiagnosticoCompleto.model_validate(dados_json)
                return diagnostico

            except Exception as e:
                ultimo_erro = e
                mensagem_erro = str(e).lower()
                sobrecarregado = (
                    "503" in mensagem_erro
                    or "overloaded" in mensagem_erro
                    or "unavailable" in mensagem_erro
                    or "resource_exhausted" in mensagem_erro
                    or "429" in mensagem_erro
                )
                if sobrecarregado and tentativa < max_tentativas_por_modelo:
                    time.sleep(2 * tentativa)
                    continue
                else:
                    # Passa para o próximo modelo da lista de fallback
                    break

    raise RuntimeError(
        f"Todos os modelos Gemini falharam após fallback e retry. "
        f"Último erro registrado: {ultimo_erro}"
    )


# ==========================================================================
# ESTADO DE SESSÃO
# ==========================================================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "diagnostico" not in st.session_state:
    st.session_state.diagnostico = None
if "erro_login" not in st.session_state:
    st.session_state.erro_login = False


def tentar_login():
    senha_digitada = st.session_state.get("campo_senha", "")
    if senha_digitada == SENHA_ACESSO:
        st.session_state.autenticado = True
        st.session_state.erro_login = False
    else:
        st.session_state.erro_login = True


def logout():
    st.session_state.autenticado = False
    st.session_state.diagnostico = None


# ==========================================================================
# ESTILO (CSS) GLOBAL
# ==========================================================================
st.markdown(
    """
    <style>
    .main {
        background-color: #f7f9f6;
    }
    .bloco-titulo {
        text-align: center;
        padding-top: 1.5rem;
        padding-bottom: 0.5rem;
    }
    .bloco-titulo h1 {
        color: #1b5e20;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }
    .bloco-titulo p {
        color: #4e5d52;
        font-size: 1.05rem;
    }
    .cartao-login {
        max-width: 420px;
        margin: 0 auto;
        padding: 2rem 2rem 1.5rem 2rem;
        background: white;
        border-radius: 16px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.08);
        border: 1px solid #e3e8e0;
    }
    .rodape-parceiros {
        text-align: center;
        color: #7a877d;
        font-size: 0.85rem;
        padding-top: 2rem;
    }
    .card-metrica {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid #e3e8e0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================================================
# TELA DE LOGIN
# ==========================================================================
if not st.session_state.autenticado:
    st.markdown(
        """
        <div class="bloco-titulo">
            <h1>🌱 Agente IA de Recuperação de Áreas Degradadas</h1>
            <p>Unimontes · Conservação Internacional (CI-Brasil) · NOVE Global — Norte de Minas Gerais</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    col_esq, col_centro, col_dir = st.columns([1, 1.3, 1])
    with col_centro:
        st.markdown('<div class="cartao-login">', unsafe_allow_html=True)
        st.markdown("#### 🔒 Acesso Restrito ao Painel Técnico")
        st.text_input(
            "Senha de acesso",
            type="password",
            key="campo_senha",
            placeholder="Digite a senha do projeto",
        )
        st.button("Entrar", type="primary", use_container_width=True, on_click=tentar_login)
        if st.session_state.erro_login:
            st.error("Senha incorreta. Verifique com a coordenação do projeto Unimontes.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    st.markdown("### 🌎 Fitofisionomias do Norte de Minas Gerais")
    st.caption(
        "Zona de ecótonos complexos — transições entre Cerrado, Caatinga, Mata Seca e Veredas."
    )

    cols_galeria = st.columns(4)
    for col, bioma in zip(cols_galeria, GALERIA_BIOMAS):
        with col:
            try:
                st.image(bioma["url"], caption=bioma["titulo"], use_container_width=True)
            except Exception:
                st.info(f"{bioma['titulo']} (imagem indisponível no momento)")
            st.caption(bioma["descricao"])

    st.markdown(
        """
        <div class="rodape-parceiros">
        Projeto de restauração ecológica em parceria com Universidade Estadual de Montes Claros (Unimontes),
        Conservação Internacional (CI-Brasil) e financiamento NOVE Global.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.stop()

# ==========================================================================
# PAINEL PRINCIPAL (PÓS-LOGIN)
# ==========================================================================

with st.sidebar:
    st.markdown("## 🌱 Painel do Agente")
    st.success("Sessão autenticada")
    st.button("🚪 Sair", on_click=logout, use_container_width=True)
    st.divider()
    st.markdown("**Projeto:** Recuperação de Áreas Degradadas")
    st.markdown("**Região:** Norte de Minas Gerais")
    st.markdown("**Parceiros:** Unimontes · CI-Brasil · NOVE Global")
    st.divider()
    st.markdown(f"**Teto de custo de referência:**  \nR$ {TETO_CUSTO_HA:,.2f} / hectare")

    api_key_disponivel = obter_api_key()
    if api_key_disponivel:
        st.caption("✅ Chave de API do Gemini configurada.")
    else:
        st.caption("⚠️ Chave de API do Gemini não configurada (secrets ou variável de ambiente).")

st.markdown(
    """
    <div class="bloco-titulo">
        <h1>🌿 Diagnóstico de Fusão Multimodal</h1>
        <p>Cruzamento de dados de satélite (macro) com dados de campo (micro) para decisão agronômica estruturada</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.form("form_dados_campo"):
    st.markdown("#### 📡 Dados Macro — Satélite (Sentinel-2 / NDVI)")
    col1, col2, col3 = st.columns(3)
    with col1:
        ndvi = st.number_input(
            "NDVI médio da área (0.0 a 1.0)", min_value=0.0, max_value=1.0, value=0.35, step=0.01
        )
    with col2:
        relevo = st.selectbox(
            "Relevo / Declividade",
            ["Plano (0-3%)", "Suave ondulado (3-8%)", "Ondulado (8-20%)", "Forte ondulado (20-45%)", "Montanhoso (>45%)"],
        )
    with col3:
        periodo_coleta = st.selectbox(
            "Período da coleta de imagem",
            ["Período chuvoso (out-mar)", "Período de estiagem (abr-set)"],
        )

    st.markdown("#### 🧑‍🌾 Dados Micro — Coleta em Campo (App Mobile)")
    col4, col5 = st.columns(2)
    with col4:
        regiao = st.text_input("Município / Região", value="Montes Claros - MG")
        tipo_solo = st.selectbox(
            "Tipo de solo observado",
            ["Latossolo vermelho", "Argissolo", "Neossolo litólico", "Cambissolo", "Solo raso/pedregoso", "Solo hidromórfico (vereda)"],
        )
        erosao = st.selectbox(
            "Presença de voçorocas / erosão",
            ["Ausente", "Incipiente (sulcos)", "Moderada (ravinas)", "Severa (voçorocas ativas)"],
        )
    with col5:
        invasoras = st.selectbox(
            "Presença de braquiária / invasoras",
            ["Ausente", "Baixa cobertura (<25%)", "Média cobertura (25-60%)", "Alta cobertura (>60%)"],
        )
        agua = st.selectbox(
            "Proximidade de curso d'água / nascente",
            ["Sem corpo hídrico próximo", "Próximo a curso d'água intermitente", "Próximo a curso d'água perene", "Área de vereda / nascente"],
        )
        uso_anterior = st.text_input("Uso anterior da terra", value="Pastagem degradada")

    observacoes = st.text_area(
        "Observações adicionais do técnico de campo",
        placeholder="Ex: presença de cupinzeiros, afloramento rochoso, indícios de fogo recente, etc.",
    )

    enviar = st.form_submit_button("🚀 Gerar Diagnóstico com o Agente IA", type="primary", use_container_width=True)

if enviar:
    api_key = obter_api_key()
    if not api_key:
        st.error(
            "Chave de API do Gemini não encontrada. Configure `st.secrets['GEMINI_API_KEY']` "
            "ou a variável de ambiente `GEMINI_API_KEY` antes de continuar."
        )
    else:
        dados_campo = {
            "ndvi": ndvi,
            "relevo": relevo,
            "periodo_coleta": periodo_coleta,
            "regiao": regiao,
            "tipo_solo": tipo_solo,
            "erosao": erosao,
            "invasoras": invasoras,
            "agua": agua,
            "uso_anterior": uso_anterior,
            "observacoes": observacoes if observacoes else "Nenhuma observação adicional.",
        }
        with st.spinner("O agente está cruzando os dados de satélite com os dados de campo..."):
            try:
                diagnostico = chamar_agente_gemini(api_key, dados_campo)
                st.session_state.diagnostico = diagnostico
                st.success("Diagnóstico gerado com sucesso.")
            except Exception as e:
                st.session_state.diagnostico = None
                st.error(f"Não foi possível gerar o diagnóstico. Detalhes: {e}")

# ==========================================================================
# EXIBIÇÃO DO DIAGNÓSTICO EM ABAS
# ==========================================================================
if st.session_state.diagnostico:
    diag: DiagnosticoCompleto = st.session_state.diagnostico

    st.divider()

    aba1, aba2, aba3, aba4 = st.tabs(
        [
            "🌿 Diagnóstico Geral",
            "📅 Cronograma de 4 Semanas",
            "🌱 Mudas & Plantio",
            "💰 Análise Orçamentária",
        ]
    )

    # -------- ABA 1: DIAGNÓSTICO GERAL --------
    with aba1:
        colA, colB, colC = st.columns(3)
        with colA:
            st.markdown('<div class="card-metrica">', unsafe_allow_html=True)
            st.metric("Bioma / Transição", diag.bioma_ou_transicao)
            st.markdown("</div>", unsafe_allow_html=True)
        with colB:
            st.markdown('<div class="card-metrica">', unsafe_allow_html=True)
            st.metric("Zona de Transição (Ecótono)?", "Sim" if diag.eh_zona_transicao else "Não")
            st.markdown("</div>", unsafe_allow_html=True)
        with colC:
            cor_grau = {
                "Baixo": "🟢", "Medio": "🟡", "Alto": "🟠", "Critico": "🔴",
            }.get(diag.grau_degradacao, "⚪")
            st.markdown('<div class="card-metrica">', unsafe_allow_html=True)
            st.metric("Grau de Degradação", f"{cor_grau} {diag.grau_degradacao}")
            st.markdown("</div>", unsafe_allow_html=True)

        st.write("")
        st.markdown("##### ⚠️ Principais Fatores Críticos")
        for fator in diag.principais_fatores_criticos:
            st.markdown(f"- {fator}")

        st.write("")
        st.markdown("##### 📝 Parecer Técnico Detalhado")
        st.info(diag.resumo_diagnostico)

        st.write("")
        st.markdown(f"**⏳ Tempo estimado de recuperação:** {diag.tempo_estimado_recuperacao}")

    # -------- ABA 2: CRONOGRAMA DE 4 SEMANAS --------
    with aba2:
        st.markdown("##### 📅 Cronograma Executivo — Primeiras 4 Semanas de Campo")
        for semana in sorted(diag.cronograma_4_semanas, key=lambda s: s.numero_semana):
            with st.expander(f"Semana {semana.numero_semana} — {semana.titulo_fase}", expanded=(semana.numero_semana == 1)):
                st.markdown("**Ações práticas:**")
                for acao in semana.acoes_praticas:
                    st.markdown(f"- {acao}")
                st.markdown("**Ferramentas / Insumos:**")
                for item in semana.ferramentas_insumos:
                    st.markdown(f"- {item}")

    # -------- ABA 3: MUDAS & ESPECIFICAÇÃO DE PLANTIO --------
    with aba3:
        esp = diag.especificacao_plantio
        st.markdown("##### 🌱 Especificação Técnica de Plantio")

        col1, col2, col3 = st.columns(3)
        col1.metric("Espaçamento técnico", esp.espacamento_tecnico)
        col2.metric("Mudas por hectare", f"{esp.qtd_mudas_por_hectare:,}")
        col3.metric("Valor unitário médio", f"R$ {esp.valor_unitario_medio_muda:,.2f}")

        st.write("")
        st.markdown(f"**💵 Custo total de mudas por hectare:** R$ {esp.custo_total_mudas_ha:,.2f}")

        st.write("")
        st.markdown("##### 🕳️ Técnica de Preparo e Coveamento")
        st.write(esp.tecnica_preparo_coveamento)

        st.markdown("##### 🌊 Controle de Erosão e Voçorocas")
        st.write(esp.controle_erosao_e_vocorocas)

        st.markdown("##### 🌳 Espécies Nativas Recomendadas")
        for especie in esp.especies_nativas_recomendadas:
            st.markdown(f"- {especie}")

    # -------- ABA 4: ANÁLISE ORÇAMENTÁRIA --------
    with aba4:
        st.markdown("##### 💰 Análise Orçamentária")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Custo total estimado por hectare", f"R$ {diag.custo_total_estimado_por_ha:,.2f}")
        with col2:
            diferenca = TETO_CUSTO_HA - diag.custo_total_estimado_por_ha
            st.metric(
                "Teto CI-Brasil (R$ 16.000,00/ha)",
                "✅ Dentro do teto" if diag.dentro_do_teto_16k else "❌ Acima do teto",
                delta=f"R$ {diferenca:,.2f}",
            )

        if diag.dentro_do_teto_16k:
            st.success("O custo estimado está dentro do teto de referência da Conservação Internacional.")
        else:
            st.warning("O custo estimado ULTRAPASSA o teto de referência de R$ 16.000,00/ha. Revisar plano de plantio.")

        st.write("")
        st.markdown("##### 🗺️ JSON Estruturado (compatível com QGIS)")
        json_saida = diag.model_dump()
        st.json(json_saida)

        st.download_button(
            label="⬇️ Baixar JSON do Diagnóstico",
            data=json.dumps(json_saida, ensure_ascii=False, indent=2),
            file_name="diagnostico_area_degradada.json",
            mime="application/json",
            use_container_width=True,
        )
else:
    st.info("Preencha os dados macro (satélite) e micro (campo) acima e clique em **Gerar Diagnóstico** para iniciar a análise do agente.")
