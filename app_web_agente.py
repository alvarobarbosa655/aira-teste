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
            st.caption("Acesso restrito a pesquisadores e corpo técnico credenciado.")
            
            st.text_input(
                "Código de Acesso do Projeto",
                type="password",
                key="campo_senha",
                placeholder="Insira a credencial técnica",
            )
            st.button("Acessar Painel", type="primary", use_container_width=True, on_click=autenticar)
            
            if st.session_state.erro_login:
                st.error("Credencial inválida. Consulte a coordenação do projeto.")

    st.write("")
    st.markdown("##### Fitofisionomias de Referência no Norte de Minas Gerais")
    st.caption("Ecótonos e zonas de transição ecológica sob monitoramento pelo sistema:")

    cols_gal = st.columns(4)
    for col, item in zip(cols_gal, GALERIA_BIOMAS):
        with col:
            st.markdown(
                f"""
                <img src="{item['url']}" style="width:100%; height:160px; object-fit:cover; border-radius:6px; border:1px solid #CBD5E1;"
                     alt="{item['titulo']}"
                     onerror="this.onerror=null;this.replaceWith(Object.assign(document.createElement('div'),{{innerText:'Registro visual de {item['titulo']}',style:'padding:2rem;background:#F1F5F9;border-radius:6px;text-align:center;color:#64748B;font-size:0.85rem;'}}));" />
                """,
                unsafe_allow_html=True,
            )
            st.markdown(f"**{item['titulo']}**")
            st.caption(item['descricao'])

    st.stop()

# ==========================================================================
# PAINEL DE CONTROLE (USUÁRIO AUTENTICADO)
# ==========================================================================

with st.sidebar:
    st.markdown("### Painel Operacional")
    st.caption("Credencial validada | Nível Técnico")
    st.button("Encerrar Sessão", on_click=encerrar_sessao, use_container_width=True)
    st.divider()
    st.markdown("**Projeto:** AIRA - Restauração Ecológica")
    st.markdown("**Instituição:** Unimontes")
    st.markdown("**Parceria:** CI-Brasil / NOVE Global")
    st.markdown(f"**Teto de Referência:** R$ {TETO_CUSTO_HA:,.2f} / ha")
    st.divider()

    chave = obter_api_key()
    if chave:
        st.caption("Status da Conexão: Operacional (API Ativa)")
    else:
        st.caption("Status da Conexão: Chave de API não identificada")

st.markdown(
    """
    <div class="header-institucional">
        <div class="titulo-principal">Diagnóstico de Fusão Multimodal e Plano de Manejo</div>
        <div class="subtitulo-institucional">Integração de sensoriamento remoto orbital e levantamento expedito de campo</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.form("form_parametros_campo"):
    st.markdown("##### 1. Dados de Sensoriamento Remoto (Sentinel-2 / MDE)")
    c1, c2, c3 = st.columns(3)
    with c1:
        ndvi = st.number_input("NDVI Médio da Gleba (0.00 a 1.00)", min_value=0.0, max_value=1.0, value=0.42, step=0.01)
    with c2:
        relevo = st.selectbox(
            "Declividade e Relevo",
            ["Plano (0 a 3%)", "Suave Ondulado (3 a 8%)", "Ondulado / Acidentado (8 a 20%)", "Forte Ondulado / Serra (> 20%)"]
        )
    with c3:
        periodo_coleta = st.selectbox(
            "Sazonalidade da Imagem",
            ["Período Seco / Estiagem (Abril a Setembro)", "Período Chuvoso (Outubro a Março)"]
        )

    st.markdown("##### 2. Parâmetros de Campo (Inspeção / App Mobile)")
    c4, c5 = st.columns(2)
    with c4:
        regiao = st.text_input("Identificação da Propriedade / Município", value="Talhão Piloto 40ha - Norte de Minas")
        tipo_solo = st.selectbox(
            "Caracterização Pedológica Visual",
            ["Latossolo Vermelho/Amarelo", "Argissolo com horizonte B textural", "Neossolo Litólico / Pedregoso", "Solo Arenoso com baixa matéria orgânica", "Gleissolo / Hidromórfico (Vereda)"]
        )
        erosao = st.selectbox(
            "Processos Erosivos Ativos",
            ["Sem erosão evidente", "Laminar / Sulcos iniciais", "Erosão em ravinas", "Voçorocamento severo em expansão"]
        )
    with c5:
        invasoras = st.selectbox(
            "Infestação de Espécies Invasoras (Braquiária)",
            ["Ausente", "Esparsa (< 25% da área)", "Moderada (25 a 60% da área)", "Dominante (> 60% da área, suprimindo regeneração)"]
        )
        agua = st.selectbox(
            "Recursos Hídricos e Proximidade",
            ["Sem corpo d'água adjacente", "Próximo a drenagem intermitente", "Próximo a curso d'água perene", "Área de cabeceira / Vereda de Buriti"]
        )
        uso_anterior = st.text_input("Histórico de Uso da Terra", value="Pastagem extensiva com compactação")

    observacoes = st.text_area(
        "Anotações Complementares do Técnico",
        placeholder="Informe detalhes sobre banco de sementes, queimadas recentes, afloramentos rochosos, etc."
    )

    btn_processar = st.form_submit_button("Processar Diagnóstico Multimodal", type="primary", use_container_width=True)

if btn_processar:
    chave_api = obter_api_key()
    if not chave_api:
        st.error("Chave de API do Gemini não configurada nos Secrets ou no ambiente.")
    else:
        dados_input = {
            "ndvi": ndvi,
            "relevo": relevo,
            "periodo_coleta": periodo_coleta,
            "regiao": regiao,
            "tipo_solo": tipo_solo,
            "erosao": erosao,
            "invasoras": invasoras,
            "agua": agua,
            "uso_anterior": uso_anterior,
            "observacoes": observacoes if observacoes else "Sem observações adicionais.",
        }
        with st.spinner("O agente está executando a fusão dos dados e calculando o plano técnico..."):
            try:
                diag_resultado = chamar_agente_gemini(chave_api, dados_input)
                st.session_state.diagnostico = diag_resultado
                st.success("Análise fitossociológica e plano de intervenção concluídos.")
            except Exception as ex:
                st.session_state.diagnostico = None
                st.error(f"Falha no processamento: {ex}")

# ==========================================================================
# EXIBIÇÃO DOS RESULTADOS EM ABAS TÉCNICAS (SEM CORTE DE TEXTO)
# ==========================================================================
if st.session_state.diagnostico:
    d: DiagnosticoCompleto = st.session_state.diagnostico
    st.divider()

    aba_bioma, aba_cronograma, aba_plantio, aba_orcamento = st.tabs(
        [
            "1. Fitofisionomia & Diagnóstico",
            "2. Cronograma Executivo (4 Semanas)",
            "3. Especificação de Plantio & Mudas",
            "4. Análise Orçamentária & GIS",
        ]
    )

    # -------------------------------------------------------------
    # ABA 1: CLASSIFICAÇÃO DA FITOFISIONOMIA E DIAGNÓSTICO
    # -------------------------------------------------------------
    with aba_bioma:
        st.markdown(
            f"""
            <div class="card-bioma-destaque">
                <span class="tag-ecotono">{"ZONA DE TRANSIÇÃO ECOLÓGICA (ECÓTONO)" if d.eh_zona_transicao else "FITOFISIONOMIA PRINCIPAL"}</span>
                <div class="nome-fitofisionomia">{d.bioma_ou_transicao}</div>
                <div style="color: #475569; font-size: 0.95rem; line-height: 1.5;">
                    <b>Interpretação e Calibração de Campo:</b> {d.justificativa_ecologica_bioma}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.markdown(
                f"""
                <div class="box-indicador">
                    <div class="rotulo-indicador">Grau de Degradação</div>
                    <div class="valor-indicador">{d.grau_degradacao}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_stat2:
            st.markdown(
                f"""
                <div class="box-indicador">
                    <div class="rotulo-indicador">Tempo Previsto de Recuperação</div>
                    <div class="valor-indicador">{d.tempo_estimado_recuperacao}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_stat3:
            enquadramento_txt = "Conforme (Dentro da Meta)" if d.dentro_do_teto_16k else "Excede Teto Orçamentário"
            st.markdown(
                f"""
                <div class="box-indicador">
                    <div class="rotulo-indicador">Enquadramento Orçamentário</div>
                    <div class="valor-indicador">{enquadramento_txt}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("##### Fatores Críticos e Limitantes do Terreno")
        for fator in d.principais_fatores_criticos:
            st.markdown(f"• {fator}")

        st.markdown("##### Parecer Técnico Estruturado")
        st.info(d.resumo_diagnostico)

    # -------------------------------------------------------------
    # ABA 2: CRONOGRAMA EXECUTIVO DAS 4 PRIMEIRAS SEMANAS
    # -------------------------------------------------------------
    with aba_cronograma:
        st.markdown("##### Cronograma Tático de Intervenção Inicial")
        st.caption("Planejamento sequencial para contenção de degradação e implantação vegetal:")

        for sem in sorted(d.cronograma_4_semanas, key=lambda s: s.numero_semana):
            st.markdown(
                f"""
                <div class="card-semana-exec">
                    <div style="font-weight: 700; font-size: 1.05rem; color: #0F172A; margin-bottom: 0.3rem;">
                        Semana {sem.numero_semana} — {sem.titulo_fase}
                    </div>
                    <div style="font-size: 0.9rem; color: #334155; margin-bottom: 0.4rem;">
                        <b>Operações de Campo:</b>
                        <ul style="margin-top: 0.2rem; margin-bottom: 0.4rem; padding-left: 1.2rem;">
                            {''.join([f'<li>{acao}</li>' for acao in sem.acoes_praticas])}
                        </ul>
                    </div>
                    <div style="font-size: 0.85rem; color: #64748B;">
                        <b>Insumos e Equipamentos:</b> {', '.join(sem.ferramentas_insumos)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # -------------------------------------------------------------
    # ABA 3: ESPECIFICAÇÃO TÉCNICA DE PLANTIO E MUDAS
    # -------------------------------------------------------------
    with aba_plantio:
        p = d.especificacao_plantio
        st.markdown("##### Parâmetros Silviculturais e Densidade de Mudas")

        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            st.markdown(
                f"""
                <div class="box-indicador">
                    <div class="rotulo-indicador">Espaçamento Técnico</div>
                    <div class="valor-indicador">{p.espacamento_tecnico}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_p2:
            st.markdown(
                f"""
                <div class="box-indicador">
                    <div class="rotulo-indicador">Densidade Recomendada</div>
                    <div class="valor-indicador">{p.qtd_mudas_por_hectare:,} mudas/ha</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_p3:
            st.markdown(
                f"""
                <div class="box-indicador">
                    <div class="rotulo-indicador">Valor Médio / Muda</div>
                    <div class="valor-indicador">R$ {p.valor_unitario_medio_muda:,.2f}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(f"**Custo Total de Aquisição de Mudas:** R$ {p.custo_total_mudas_ha:,.2f} / hectare")
        st.divider()

        st.markdown("##### Método de Preparo de Solo e Coveamento")
        st.write(p.tecnica_preparo_coveamento)

        st.markdown("##### Controle de Erosão e Estabilização Física")
        st.write(p.controle_erosao_e_vocorocas)

        st.markdown("##### Espécies Nativas Indicadas para o Bioma / Ecótono")
        col_esp1, col_esp2 = st.columns(2)
        for idx, esp in enumerate(p.especies_nativas_recomendadas):
            if idx % 2 == 0:
                col_esp1.markdown(f"• **{esp}**")
            else:
                col_esp2.markdown(f"• **{esp}**")

    # -------------------------------------------------------------
    # ABA 4: ANÁLISE ORÇAMENTÁRIA E DADOS GIS
    # -------------------------------------------------------------
    with aba_orcamento:
        st.markdown("##### Conformidade com o Teto Orçamentário")

        col_o1, col_o2 = st.columns(2)
        with col_o1:
            st.markdown(
                f"""
                <div class="box-indicador">
                    <div class="rotulo-indicador">Custo Global Estimado</div>
                    <div class="valor-indicador">R$ {d.custo_total_estimado_por_ha:,.2f} / ha</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_o2:
            saldo = TETO_CUSTO_HA - d.custo_total_estimado_por_ha
            status_teto = "Conforme (Dentro da Meta)" if d.dentro_do_teto_16k else "Não Conforme"
            st.markdown(
                f"""
                <div class="box-indicador">
                    <div class="rotulo-indicador">Teto Conservação Internacional (R$ 16.000,00)</div>
                    <div class="valor-indicador">{status_teto} <span style="font-size:0.9rem;font-weight:500;color:#16A34A;">(Saldo: R$ {saldo:,.2f})</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if d.dentro_do_teto_16k:
            st.success("O custo total projetado atende rigorosamente aos parâmetros de referência do projeto.")
        else:
            st.warning("O custo projetado ultrapassa o teto de R$ 16.000,00/ha. Recomenda-se ajustar o espaçamento ou combinar com indução natural.")

        st.divider()
        st.markdown("##### Estrutura de Dados para Integração GIS (QGIS / ArcGIS)")
        dados_exportacao = d.model_dump()
        st.json(dados_exportacao)

        st.download_button(
            label="Exportar Arquivo JSON do Diagnóstico",
            data=json.dumps(dados_exportacao, ensure_ascii=False, indent=2),
            file_name="diagnostico_tecnico_unimontes.json",
            mime="application/json",
            use_container_width=True,
        )
