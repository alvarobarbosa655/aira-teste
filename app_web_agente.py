# -*- coding: utf-8 -*-
"""
app_web_agente.py

Agente de IA de Fusão Multimodal para Recuperação de Áreas Degradadas
Norte de Minas Gerais - Ecótonos (Cerrado / Caatinga / Mata Seca / Veredas)

Projeto: Unimontes + Conservação Internacional (CI-Brasil) + NOVE Global
Stack: Streamlit + Google Gemini (SDK google-genai) com Streaming
"""

import os
import json
import time
from typing import Optional
import streamlit as st

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

MODELOS_GEMINI_FALLBACK = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
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
aplicativo móvel, emitindo um diagnóstico técnico e um plano executivo de manejo.

Atenção metodológica: o NDVI de satélite isolado apresenta cerca de 50% de erro em zonas 
de transição (falso positivo de vigor em áreas tomadas por braquiária/eucalipto; e falso 
negativo de degradação na Mata Seca durante a estiagem devido à caducifólia). Utilize a 
observação de campo para calibrar com exatidão o diagnóstico.

--- DADOS DE SENSORIAMENTO REMOTO (SATÉLITE) ---
- NDVI médio da área: {dados_campo['ndvi']}
- Relevo / Declividade: {dados_campo['relevo']}
- Período da imagem: {dados_campo['periodo_coleta']}

--- DADOS DE CAMPO (APLICATIVO MOBILE) ---
- Município / Talhão: {dados_campo['regiao']}
- Tipo de solo observado: {dados_campo['tipo_solo']}
- Erosão / Feições físicas: {dados_campo['erosao']}
- Cobertura de invasoras (Braquiária): {dados_campo['invasoras']}
- Proximidade hídrica / Veredas: {dados_campo['agua']}
- Histórico de uso da terra: {dados_campo['uso_anterior']}
- Observações complementares: {dados_campo['observacoes']}

--- PARÂMETROS FINANCEIROS ---
Teto de custo de referência da Conservação Internacional: R$ {TETO_CUSTO_HA:,.2f} por hectare.

--- INSTRUÇÕES DE FORMATAÇÃO ---
Responda em Markdown bem estruturado, seguindo EXATAMENTE esta ordem de seções:

# 1. Classificação da Fitofisionomia
- Identifique o bioma ou ecótono (zona de transição).
- Justifique tecnicamente a classificação, explicando como os dados de campo calibram/corrigem o NDVI de satélite.

# 2. Diagnóstico de Degradação
- Classifique o grau: Baixo, Médio, Alto ou Crítico.
- Liste os fatores críticos e limitantes do terreno.
- Emita um parecer técnico detalhado.

# 3. Especificação Técnica de Plantio
- Espaçamento técnico e densidade de mudas por hectare.
- Valor unitário médio e custo total de mudas por hectare.
- Método de preparo do solo e coveamento (dimensões da cova, calagem, adubação).
- Técnicas de controle de erosão e voçorocas.
- Mínimo de 6 espécies nativas recomendadas, com nome científico entre parênteses.

# 4. Cronograma Executivo de Recuperação

⚠️ ATENÇÃO — REGRA OBRIGATÓRIA PARA O CRONOGRAMA:
Detalhe o cronograma MÊS A MÊS do Mês 1 ao Mês 12.
A partir do Mês 13, agrupe em TRIMESTRES (ex: Mês 13-15, Mês 16-18, Mês 19-21, Mês 22-24).
Acima de 24 meses, agrupe em SEMESTRES (ex: Mês 25-30, Mês 31-36).
NUNCA agrupe períodos maiores que 6 meses numa única entrada.

Para CADA período, informe obrigatoriamente:
- **Ações práticas**: lista clara das operações de campo.
- **Meta da etapa**: resultado ecológico esperado ao final do período.
- **Insumos e ferramentas**: equipamentos e materiais necessários.

Use uma tabela Markdown com as colunas: | Período | Ações Práticas | Meta da Etapa | Insumos / Ferramentas |

# 5. Projeção de Recuperação Ecológica
Apresente uma tabela Markdown com a evolução estimada nos marcos: Mês 0, 3, 6, 9, 12, 15, 18, 21, 24, 30, 36.
Colunas: | Mês | Cobertura Vegetal (%) | Estabilização da Erosão (%) | Infiltração Hídrica (%) |

# 6. Análise Orçamentária
- Custo total estimado por hectare (insumos + mudas + mão de obra), com detalhamento.
- Verificação de conformidade com o teto de R$ 16.000,00/ha.
- Tempo estimado de recuperação funcional do ecossistema.

Seja técnico, preciso e objetivo. Use tabelas sempre que possível para organizar dados numéricos.
"""
    return prompt.strip()

@st.cache_resource(show_spinner=False)
def criar_cliente_gemini(api_key: str):
    """Reutiliza o cliente entre as reexecuções do Streamlit."""
    from google import genai
    return genai.Client(api_key=api_key)

def gerar_stream_gemini(api_key: str, dados_campo: dict):
    """Retorna um generator de streaming do Gemini."""
    from google.genai import types

    client = criar_cliente_gemini(api_key)
    prompt = montar_prompt(dados_campo)
    ultimo_erro = None

    for modelo in MODELOS_GEMINI_FALLBACK:
        try:
            response = client.models.generate_content_stream(
                model=modelo,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                ),
            )
            # Testa se o stream funciona retornando o generator
            return response, modelo
        except Exception as e:
            ultimo_erro = e
            time.sleep(0.5)
            continue

    raise RuntimeError(f"Falha na comunicação com o agente: {ultimo_erro}")

def stream_chunks(response):
    """Extrai os pedaços de texto do stream do Gemini para o st.write_stream."""
    for chunk in response:
        if chunk.text:
            yield chunk.text

# ==========================================================================
# GERENCIAMENTO DE SESSÃO
# ==========================================================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "diagnostico_texto" not in st.session_state:
    st.session_state.diagnostico_texto = None
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
    st.session_state.diagnostico_texto = None

# ==========================================================================
# ESTILO VISUAL CORPORATIVO / RESPONSIVO
# ==========================================================================
st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"], .main {
        background-color: var(--background-color);
        color: var(--text-color);
    }

    .header-institucional {
        border-bottom: 2px solid color-mix(in srgb, var(--text-color) 18%, transparent);
        padding-bottom: 1rem;
        margin-bottom: 1.5rem;
    }
    .titulo-principal {
        color: var(--text-color);
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .subtitulo-institucional {
        color: color-mix(in srgb, var(--text-color) 72%, transparent);
        font-size: 0.95rem;
        font-weight: 500;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================================================
# TELA DE AUTENTICAÇÃO
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

# ==========================================================================
# FORMULÁRIO DE ENTRADA
# ==========================================================================
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

# ==========================================================================
# PROCESSAMENTO COM STREAMING (RESPOSTA EM TEMPO REAL)
# ==========================================================================
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

        st.divider()

        try:
            response, modelo_usado = gerar_stream_gemini(chave_api, dados_input)
            st.caption(f"Modelo: `{modelo_usado}` • Streaming ativo")

            # O texto aparece em tempo real enquanto o Gemini gera
            texto_completo = st.write_stream(stream_chunks(response))

            # Salva no session_state para persistir entre reruns
            st.session_state.diagnostico_texto = texto_completo

            st.success("✅ Diagnóstico concluído com sucesso.")

        except Exception as ex:
            st.session_state.diagnostico_texto = None
            st.error(f"Falha no processamento: {ex}")

# ==========================================================================
# EXIBIÇÃO DO RESULTADO SALVO (após rerun do Streamlit)
# ==========================================================================
if st.session_state.diagnostico_texto and not btn_processar:
    st.divider()
    st.markdown(st.session_state.diagnostico_texto)

# ==========================================================================
# BOTÕES DE EXPORTAÇÃO (sempre visíveis quando há resultado)
# ==========================================================================
if st.session_state.diagnostico_texto:
    st.divider()
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        st.download_button(
            label="📄 Exportar Relatório (Markdown)",
            data=st.session_state.diagnostico_texto,
            file_name="diagnostico_tecnico_unimontes.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col_exp2:
        # Exporta também como JSON simples para GIS
        dados_json_export = {
            "projeto": "AIRA - Unimontes / CI-Brasil / NOVE Global",
            "teto_custo_ha": TETO_CUSTO_HA,
            "relatorio_completo": st.session_state.diagnostico_texto,
        }
        st.download_button(
            label="📊 Exportar para GIS (JSON)",
            data=json.dumps(dados_json_export, ensure_ascii=False, indent=2),
            file_name="diagnostico_tecnico_unimontes.json",
            mime="application/json",
            use_container_width=True,
        )
