# =============================================================================
# BLOCO 1 - IMPORTS E CONFIGURAÇÃO DO BANCO (SUPABASE / RENDER / LOCAL)
# =============================================================================
import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, date
from sqlalchemy import create_engine, text

try:
    DATABASE_URL = os.getenv("DATABASE_URL") or st.secrets.get("DATABASE_URL")
except Exception:
    DATABASE_URL = os.getenv("DATABASE_URL") or ""

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///campanha.db"

# O SQLAlchemy do PostgreSQL exige que comece com 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

IS_SQLITE = "sqlite" in DATABASE_URL

# Configura a engine conforme o banco utilizado (SQLite ou PostgreSQL/Supabase)
# pool_pre_ping evita erros de "conexão caiu" em bancos remotos (Supabase/Render)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    pool_pre_ping=not IS_SQLITE,
)

# =============================================================================
# BLOCO 2 - FUNÇÕES DE BANCO (COM ATUALIZAÇÃO AUTOMÁTICA DE COLUNAS)
# =============================================================================
def init_db():
    # FIX: "id INTEGER PRIMARY KEY AUTOINCREMENT" só é válido em SQLite.
    # Em Postgres/Supabase isso derrubava o app inteiro na primeira execução.
    id_col = "id INTEGER PRIMARY KEY AUTOINCREMENT" if IS_SQLITE else "id SERIAL PRIMARY KEY"

    try:
        with engine.begin() as conn:
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS contatos (
                    {id_col},
                    comprador TEXT, fornecedor TEXT, categoria TEXT,
                    cnpj TEXT, contato TEXT,
                    recebeu TEXT, fala_contador TEXT,
                    previsao_retorno TEXT, status TEXT, observacao TEXT
                );
            """))
    except Exception as e:
        st.error(f"❌ Não foi possível conectar/criar o banco de dados: {e}")
        st.stop()

    # FIX: a chave era "DATA DO CONTATO" (com espaços), o que gerava um
    # ALTER TABLE com sintaxe inválida e a coluna nunca era criada.
    # O restante do app referenciava "DATA_CONTATO" -> coluna inexistente ->
    # TODO o UPDATE de salvar falhava, sempre, para todos os campos.
    novas_colunas = {
        "cnpj": "TEXT",
        "data_contato": "TEXT",
        "canal_contato": "TEXT",
        "reenvio_necessario": "TEXT",
        "acompanha_reforma": "INTEGER DEFAULT 0",
        "discutiu_internamente": "INTEGER DEFAULT 0",
        "falou_contador": "INTEGER DEFAULT 0",
        "responsavel_contador": "TEXT",
        "definicao_2027": "TEXT",
        "data_proximo_contato": "TEXT",
        "proxima_acao": "TEXT",
        "canal": "TEXT",
        "recebeu_comunicado": "TEXT",
        "email_reenvio": "TEXT",
        "acompanha_reforma_txt": "TEXT",
        "discutiu_internamente_txt": "TEXT",
        "responsavel_interno": "TEXT",
        "definicao_preliminar": "TEXT",
        "alerta_critico": "TEXT",
    }
    with engine.begin() as conn:
        for col, tipo in novas_colunas.items():
            try:
                conn.execute(text(f"ALTER TABLE contatos ADD COLUMN {col} {tipo}"))
            except Exception:
                # Esperado: a coluna já existe a partir da 2ª execução em diante.
                pass


def seed():
    with engine.connect() as conn:
        try:
            count = conn.execute(text("SELECT COUNT(*) FROM contatos")).scalar()
            if count and count > 0:
                return
        except Exception:
            return

    arquivos = [f for f in os.listdir(".") if f.lower().endswith(".xlsx")]
    if not arquivos:
        return

    alvo = None
    for nome in ["Base-inicial-para-carga.xlsx", "BI_Campanha_Versao_SIMPLES.xlsx", "BI_Campanha.xlsx"]:
        if nome in arquivos:
            alvo = nome
            break
    if not alvo:
        alvo = arquivos[0]

    df = pd.read_excel(alvo, sheet_name=0)
    rename = {}
    for c in df.columns:
        lc = str(c).lower()
        if "comprador" in lc:
            rename[c] = "comprador"
        elif "fornecedor" in lc or "razao" in lc:
            rename[c] = "fornecedor"
        elif "cnpj" in lc:
            rename[c] = "cnpj"
        elif "categoria" in lc:
            rename[c] = "categoria"
        elif "contato" in lc or "telefone" in lc or "email" in lc:
            rename[c] = "contato"
    df = df.rename(columns=rename)

    colunas_necessarias = [
        "comprador", "fornecedor", "cnpj", "categoria", "contato", "data_contato",
        "canal_contato", "recebeu", "reenvio_necessario", "acompanha_reforma",
        "discutiu_internamente", "falou_contador", "responsavel_contador",
        "definicao_2027", "previsao_retorno", "data_proximo_contato", "status",
        "proxima_acao", "observacao",
    ]
    for col in colunas_necessarias:
        if col not in df.columns:
            df[col] = 0 if any(p in col for p in ["acompanha", "discutiu", "falou"]) else ""
    df = df.fillna("")

    try:
        df[colunas_necessarias].to_sql("contatos", engine, if_exists="append", index=False)
    except Exception as e:
        st.warning(f"⚠️ Não foi possível importar a planilha inicial ({alvo}): {e}")


init_db()
seed()

try:
    with engine.connect() as conn:
        total_login = conn.execute(text("SELECT COUNT(*) FROM contatos")).scalar() or 0
        atend_login = conn.execute(text(
            "SELECT COUNT(*) FROM contatos WHERE status NOT IN ('', 'Pendente', 'None') "
            "AND status IS NOT NULL AND status != ''"
        )).scalar() or 0
        perc_login = (atend_login / total_login * 100) if total_login else 0
except Exception:
    total_login = 0
    atend_login = 0
    perc_login = 0

# =============================================================================
# BLOCO 3 - USUÁRIOS
# =============================================================================
USUARIOS = {
    "Camila": {"senha": "Camila@2026", "nome_completo": "CAMILA CAROLINE DA SILVA"},
    "Gilcimar": {"senha": "Gil@2026", "nome_completo": "GILCIMAR SILVA"},
    "Janaina": {"senha": "Jana@2026", "nome_completo": "JANAINA APARECIDA VENANCIO"},
    "Maria Fatima": {"senha": "Fatima@2026", "nome_completo": "MARIA FATIMA"},
    "Rafael": {"senha": "Rafa@2026", "nome_completo": "RAFAEL NASCIMENTO"},
    "Waldecir": {"senha": "Wal@2026", "nome_completo": "WALDECIR MARQUES"},
    "Gestão": {"senha": "Mbp@Gestao2026", "nome_completo": "GESTÃO"},
}
COMPRADORES_CURTO = ["Camila", "Gilcimar", "Janaina", "Maria Fatima", "Rafael", "Waldecir", "Gestão"]
MAP_COMPRADOR = {k: v["nome_completo"] for k, v in USUARIOS.items()}
KEY_MAP = {
    "Camila": "perf_Camila", "Gilcimar": "perf_Gilcimar", "Janaina": "perf_Janaina",
    "Maria Fatima": "perf_Maria", "Rafael": "perf_Rafael", "Waldecir": "perf_Waldecir",
    "Gestão": "perf_Gestao",
}

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None
if "perfil" not in st.session_state:
    st.session_state.perfil = "Camila"
if "trocando_perfil" not in st.session_state:
    st.session_state.trocando_perfil = False


def fazer_login(u, p):
    if u in USUARIOS and USUARIOS[u]["senha"] == p:
        st.session_state.autenticado = True
        st.session_state.usuario_logado = u
        st.session_state.perfil = u
        return True
    return False


# =============================================================================
# BLOCO 4 - LOGIN
# =============================================================================
if not st.session_state.autenticado:
    st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp { background: #08162E !important; }
    .block-container { padding-top: 0 !important; max-width: 100% !important; }
    div[data-testid="stEmpty"] { display:none !important; }
    .login-card { background:#0F2242; border:1px solid #1E3A5F; border-radius:16px; padding:28px 26px; }
    div[data-testid="stSelectbox"] label, div[data-testid="stTextInput"] label { color:#8BA3C7 !important; font-size:11px !important; }
    div[data-baseweb="select"] > div { background:#132A4E !important; border:1px solid #1E3A5F !important; border-radius:8px !important; color:white !important; }
    div[data-baseweb="select"] span { color:white !important; }
    div[data-testid="stTextInput"] input { background:#132A4E !important; color:white !important; border:1px solid #1E3A5F !important; border-radius:8px !important; }
    div[data-testid="stButton"] > button[kind="primary"] { background:#ffc000 !important; color:#08162E !important; border-radius:8px !important; font-weight:800 !important; height:44px !important; }
    </style>
    """, unsafe_allow_html=True)
    left, right = st.columns([1.4, 0.75], gap="large")
    with left:
        st.markdown(f"""
        <div style="padding: 28px 20px 20px 48px;">
            <div style="display:inline-flex; align-items:center; gap:10px; background: rgba(255,192,0,0.12); border:1px solid rgba(255,192,0,0.25); padding:9px 16px; border-radius:24px; margin-bottom:26px;">
                <span style="color:#ffc000; font-size:12px; font-weight:800;">GRUPO MBP • CAMPANHA REFORMA</span>
            </div>
            <div style="font-size:52px; font-weight:900; color:white; line-height:0.92; margin-bottom:20px;">Organize com<br>clareza.<br>Entregue com<br><span style="color:#ffc000;">segurança.</span></div>
            <div style="display:flex; gap:14px;"><div style="flex:1; background:#0F2242; border:1px solid #1E3A5F; border-radius:14px; padding:16px;">
                <div style="color:#ffc000; font-size:11px; font-weight:800; margin-bottom:12px;">📊 VISÃO DA CAMPANHA - DADO REAL</div>
                <div style="display:flex; justify-content:space-between; margin-bottom:8px;"><span style="color:#8BA3C7; font-size:12px;">Fornecedores contatados</span><span style="color:white; font-size:12px; font-weight:700;">{perc_login:.1f}%</span></div>
                <div style="background:#08162E; height:6px; border-radius:3px; overflow:hidden;"><div style="background:#ffc000; width:{perc_login}%; height:100%;"></div></div>
                <div style="color:#5A7AA8; font-size:10px; margin-top:8px;">{atend_login} de {total_login} fornecedores</div>
            </div></div>
        </div>
        """, unsafe_allow_html=True)
    with right:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("""<div style="color:white; font-size:20px; font-weight:800; margin-bottom:6px;">Bem-vindo de volta</div><div style="color:#5A7AA8; font-size:12px; margin-bottom:22px;">Use seu usuário de comprador para continuar</div>""", unsafe_allow_html=True)
        usuario_sel = st.selectbox("Usuário", COMPRADORES_CURTO, key="login_user_fix")
        senha_input = st.text_input("Senha", type="password", placeholder="Digite sua senha", key="login_pass_fix")
        if st.button("Entrar no portal →", use_container_width=True, type="primary", key="btn_login_fix"):
            if fazer_login(usuario_sel, senha_input):
                st.rerun()
            else:
                st.error("Senha incorreta")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# =============================================================================
# BLOCO 5 - TELA PRINCIPAL E INTERFACE COMPLETA
# =============================================================================
# PERFORMANCE: cacheia a leitura da tabela por alguns segundos. O cache é
# limpo manualmente logo após cada UPDATE bem-sucedido (e na troca de
# comprador), então os dados nunca ficam desatualizados na tela.
@st.cache_data(ttl=30, show_spinner=False)
def carregar_contatos():
    return pd.read_sql(text("SELECT * FROM contatos"), engine).fillna("")

perfil_curto = st.session_state.perfil
active_key = KEY_MAP.get(perfil_curto, "perf_Camila")

# Se acabamos de trocar de comprador, mostra a tela de carregamento por um
# instante (garante que o cache de dados novos seja usado) e então segue
# para o painel de verdade em uma nova rodada de execução.
if st.session_state.trocando_perfil:
    carregar_contatos.clear()
    st.session_state.trocando_perfil = False
    st.rerun()

css_botoes_perfil = ""
for nome, chave in KEY_MAP.items():
    if nome == perfil_curto:
        css_botoes_perfil += f"""
        .st-key-{chave} button {{
            background: #FFC107 !important;
            color: #111827 !important;
            border: none !important;
            font-weight: 800 !important;
        }}
        .st-key-{chave} button p, .st-key-{chave} button span {{
            color: #111827 !important;
        }}
        """
    else:
        css_botoes_perfil += f"""
        .st-key-{chave} button {{
            background: #FFFFFF !important;
            color: #111827 !important;
            border: 1px solid #D1D5DB !important;
            font-weight: 600 !important;
        }}
        .st-key-{chave} button p, .st-key-{chave} button span {{
            color: #111827 !important;
        }}
        """

st.markdown(f"""
<style>
#MainMenu, footer, header {{visibility: hidden;}}
.stApp {{ background: #F6F7F9 !important; }}
.block-container {{ max-width: 100% !important; padding-top: 1rem !important; }}

section[data-testid="stSidebar"] {{
    background-color: #0F172A !important;
    border-right: 1px solid #1E293B;
}}

.badge {{ font-size:11px; font-weight:600; padding:5px 10px; border-radius:20px; border:1px solid;}}
.badge-Verde {{ background:#ECFDF5; color:#065F46; border-color:#A7F3D0;}}
.badge-Amarelo {{ background:#FEFCE8; color:#854D0E; border-color:#FDE68A;}}
.badge-Laranja {{ background:#FFF7ED; color:#9A3412; border-color:#FDBA74;}}
.badge-Vermelho {{ background:#FEF2F2; color:#991B1B; border-color:#FECACA;}}
.badge-Cinza {{ background:#F3F4F6; color:#374151; border-color:#D1D5DB;}}
.badge-Pendente {{ background:#F9FAFB; color:#6B7280; border-color:#E5E7EB;}}

label {{ font-size:11px !important; font-weight:600 !important; color:#111827 !important;}}
div[data-testid="stCheckbox"] label span, div[data-testid="stCheckbox"] label p {{ color: #111827 !important; font-weight: 500 !important; }}
div[data-testid="stTextInput"] input {{ background: white !important; color: #111827 !important; border: 1px solid #D1D5DB !important; }}
div[data-baseweb="select"] > div {{ background: white !important; color: #111827 !important; border: 1px solid #D1D5DB !important; }}
div[data-baseweb="select"] span {{ color: #111827 !important; }}
textarea {{ background: white !important; color: #111827 !important; }}
div[data-testid="stExpander"] {{ background:white !important; border:1px solid #D1D5DB !important; border-radius:14px !important; margin-bottom:8px !important; }}
div[data-testid="stExpander"] details summary p {{ color:#111827 !important; font-weight:700 !important; }}

{css_botoes_perfil}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; padding: 5px 0;">
            <div style="background: #FFC107; color: #111827; width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 16px;">M</div>
            <div>
                <div style="color: #FFC107; font-weight: 800; font-size: 14px;">MBP • Campanha</div>
                <div style="color: #FFC107; font-size: 11px; opacity: 0.8;">Reforma 2026</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <div style="background: #1E293B; padding: 10px; border-radius: 10px; font-size: 12px; color: #94A3B8; margin-top: 12px;">
            Logado como:<br><b style='color: #FFC107; font-size: 13px;'>{st.session_state.usuario_logado}</b>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        "<p style='font-size: 11px; text-transform: uppercase; color: #FFC107; font-weight: 800; margin-bottom: 5px;'>👥 Alternar Perfil</p>",
        unsafe_allow_html=True)

    icones_perfil = {"Camila": "👤", "Gilcimar": "📊", "Janaina": "📑", "Maria Fatima": "📌", "Rafael": "📈",
                      "Waldecir": "📋", "Gestão": "⚡"}

    for nome in COMPRADORES_CURTO:
        ico = icones_perfil.get(nome, "•")
        if st.button(f"{ico}  {nome}", key=KEY_MAP[nome], use_container_width=True):
            if nome != st.session_state.perfil:
                st.session_state.perfil = nome
                st.session_state.trocando_perfil = True
                st.rerun()

    st.markdown("---")
    if st.button("🚪 Sair do Sistema", use_container_width=True, type="secondary"):
        st.session_state.autenticado = False
        st.rerun()

perfil_real = MAP_COMPRADOR[perfil_curto]

# LOADING ATÉ ATUALIZAR
df_all = carregar_contatos()

if perfil_curto == "Gestão":
    st.markdown(f"""<div style="font-size:22px; font-weight:800; color:#111827; margin:10px 0;">🏢 Fornecedores • Gestão</div>""", unsafe_allow_html=True)

    f1, f2 = st.columns([3, 2])
    with f1:
        filtro_comp = st.selectbox("Ver somente:", ["Todos"] + [MAP_COMPRADOR[c] for c in COMPRADORES_CURTO if c!= "Gestão"])
    with f2:
        busca = st.text_input("Buscar:", placeholder="Fornecedor")

    df_f = df_all.copy()
    if filtro_comp!= "Todos":
        comp_curto_sel = [k for k,v in MAP_COMPRADOR.items() if v == filtro_comp][0]
        df_f = df_f[df_f["comprador"].astype(str).str.upper().str.contains(comp_curto_sel.upper())]
    if busca:
        df_f = df_f[df_f["fornecedor"].astype(str).str.upper().str.contains(busca.upper())]

    status_counts = df_f["status"].fillna("Pendente").replace("", "Pendente").value_counts()
    def get(s): return int(status_counts.get(s, 0))


    total = len(df_f)
    verde, amarelo, laranja, vermelho, cinza, pendente = get("Verde"), get("Amarelo"), get("Laranja"), get(
        "Vermelho"), get("Cinza"), get("Pendente")

    atendidos = total - pendente
    perc = (atendidos / total * 100) if total > 0 else 0

    # === BARRA DE PORCENTAGEM QUE FALTAVA ===
    st.markdown(f"""
     <div style="display:flex; gap:15px; margin-bottom:10px;">
         <div style="background:white; border:1px solid #E5E7EB; border-radius:10px; padding:10px 20px;">
             <div style="font-size:11px; color:#6B7280; font-weight:700;">ATENDIDOS</div>
             <div style="font-size:22px; font-weight:900;">{atendidos} <span style="font-size:14px; color:#16A34A;">{perc:.1f}%</span></div>
         </div>
         <div style="background:white; border:1px solid #E5E7EB; border-radius:10px; padding:10px 20px;">
             <div style="font-size:11px; color:#6B7280; font-weight:700;">PENDENTES</div>
             <div style="font-size:22px; font-weight:900;">{pendente} <span style="font-size:14px; color:#DC2626;">{100 - perc:.1f}%</span></div>
         </div>
     </div>
     """, unsafe_allow_html=True)
    st.progress(perc / 100)

    # === CARTÕES COLORIDOS ===
    st.markdown("""
     <style>
    .card {border-radius:10px; padding:12px; text-align:center; color:white; font-weight:800;}
    .c-verde{background:#16A34A}.c-amarelo{background:#CA8A04}.c-laranja{background:#EA580C}
    .c-vermelho{background:#DC2626}.c-cinza{background:#6B7280}.c-pendente{background:#111827}.c-total{background:#E5E7EB; color:#111827; border:1px solid #D1D5DB}
     </style>
     """, unsafe_allow_html=True)

    a, b, c, d, e, f, g = st.columns(7)
    with a:
        st.markdown(f'<div class="card c-total">{total}<br><small>TOTAL</small></div>', unsafe_allow_html=True)
    with b:
        st.markdown(f'<div class="card c-verde">{verde}<br><small>VERDE</small></div>', unsafe_allow_html=True)
    with c:
        st.markdown(f'<div class="card c-amarelo">{amarelo}<br><small>AMARELO</small></div>', unsafe_allow_html=True)
    with d:
        st.markdown(f'<div class="card c-laranja">{laranja}<br><small>LARANJA</small></div>', unsafe_allow_html=True)
    with e:
        st.markdown(f'<div class="card c-vermelho">{vermelho}<br><small>VERMELHO</small></div>', unsafe_allow_html=True)
    with f:
        st.markdown(f'<div class="card c-cinza">{cinza}<br><small>CINZA</small></div>', unsafe_allow_html=True)
    with g:
        st.markdown(f'<div class="card c-pendente">{pendente}<br><small>PENDENTE</small></div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-top:15px'></div>", unsafe_allow_html=True)
    colunas_gestao = ["fornecedor", "comprador", "categoria", "status", "recebeu", "data_contato", "canal_contato",
                      "previsao_retorno", "responsavel_contador", "definicao_2027", "observacao"]
    colunas_gestao = [c for c in colunas_gestao if c in df_f.columns]
    st.dataframe(df_f[colunas_gestao], use_container_width=True, height=550)
    st.stop()

# COMPRADOR
df = df_all[df_all["comprador"] == perfil_real]
if df.empty:
    df = df_all[df_all["comprador"].str.contains(perfil_curto.upper(), na=False)]

total = len(df)
cont = len(df[~df["status"].isin(["", "Pendente", "None"])])
perc = cont / total * 100 if total else 0
st.markdown(
    f"""<div style="display:flex; justify-content:space-between; margin:10px 0 16px 0;"><div><div style="font-size:20px; font-weight:800; color:#111827;">🏢 Fornecedores • {perfil_curto}</div><div style="font-size:13px; color:#6B7280;">{cont} atendidos de {total} • {perc:.1f}% concluído</div></div></div>""",
    unsafe_allow_html=True)

f_busca1, f_busca2, f_busca3, f_busca4 = st.columns([3, 1.5, 1, 1])
with f_busca1:
    busca_comprador = st.text_input("🔍 Buscar fornecedor rápido:", placeholder="Ex: GRUPO ROCHA",
                                     key=f"busca_{perfil_curto}")
with f_busca2:
    filtro_status_c = st.selectbox("Status:",
                                    ["Todos", "Pendente", "Vermelho", "Amarelo", "Verde", "Laranja", "Cinza"],
                                    key=f"fstat_{perfil_curto}")

df_filtrado = df.copy()
if busca_comprador:
    q = busca_comprador.lower()
    df_filtrado = df_filtrado[df_filtrado["fornecedor"].str.lower().str.contains(q, na=False) | df_filtrado[
        "categoria"].str.lower().str.contains(q, na=False)]
if filtro_status_c != "Todos":
    df_filtrado = df_filtrado[
        df_filtrado["status"].str.contains(filtro_status_c, case=False, na=False)] if filtro_status_c != "Pendente" else \
        df_filtrado[df_filtrado["status"].isin(["", "Pendente", "None"])]

# FIX: lista única usada tanto nas opções do selectbox quanto no cálculo do
# índice inicial, para "PRÓXIMA AÇÃO" não abrir com o valor deslocado.
OPCOES_PROXIMA_ACAO = ["Nenhuma", "Aguardar retorno", "Reenviar e-mail", "Escalar p/ Fiscal"]

col_left, col_right = st.columns(2)
for idx, (i, row) in enumerate(df_filtrado.iterrows()):
    target = col_left if idx % 2 == 0 else col_right
    badge = row.get("status") or "Pendente"
    recebeu_val = row.get("recebeu") or "Pendente"

    bc = "Pendente" if badge in ["", "Pendente"] else (
        "Verde" if "VERDE" in badge.upper() else "Amarelo" if "AMARELO" in badge.upper() else "Vermelho" if "VERMELHO" in badge.upper() else "Laranja" if "LARANJA" in badge.upper() else "Cinza")
    icon = "⚪" if badge in ["", "Pendente"] else "🟢" if bc == "Verde" else "🔴" if bc == "Vermelho" else "🟡" if bc == "Amarelo" else "🟠"

    titulo = f"{icon} {row.get('fornecedor')}"

    with target:
        with st.expander(titulo, expanded=False):
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; border-bottom: 1px solid #E5E7EB; padding-bottom: 10px;">
                <div>
                    <div style="font-size: 15px; font-weight: 800; color: #111827;">{row.get('fornecedor')}</div>
                    <div style="font-size: 11px; font-weight: 700; color: #6B7280; text-transform: uppercase; margin-top: 2px;">
                        {row.get('categoria')}
                    </div>
                </div>
                <div>
                    <span class="badge badge-{bc}">{badge}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # O st.form agrupa todos os campos para que nada recarregue enquanto a pessoa digita
            with st.form(key=f"form_{idx}_{row['id']}"):
                c1, c2 = st.columns(2)
                with c1:
                    # FIX: era row.get("DATA_CONTATO") (maiúsculo) -> nunca batia
                    # com a coluna real "data_contato" -> campo sempre em branco.
                    val_data = row.get("data_contato")
                    data_inicial = None
                    if val_data and str(val_data).strip() != "":
                        try:
                            data_inicial = datetime.strptime(str(val_data).strip(), "%d/%m/%Y").date()
                        except Exception:
                            pass

                    data_contato_obj = st.date_input("DATA DO CONTATO", value=data_inicial, format="DD/MM/YYYY", key=f"data_contato_{idx}_{row['id']}")
                    data_contato = data_contato_obj.strftime("%d/%m/%Y") if data_contato_obj else ""
                with c2:
                    # FIX: era row.get("CANAL_CONTATO") -> coluna real é "canal_contato"
                    opcoes_canal = ["LIGAÇÃO/WHATS", "E-MAIL", "REUNIÃO", "OUTRO"]
                    canal_atual = row.get("canal_contato")
                    canal_contato = st.selectbox(
                        "CANAL", opcoes_canal,
                        index=opcoes_canal.index(canal_atual) if canal_atual in opcoes_canal else 0,
                        key=f"canal_{idx}_{row['id']}")

                c3, c4 = st.columns(2)
                with c3:
                    recebeu = st.selectbox("RECEBEU COMUNICADO?", ["Pendente", "Sim", "Não"],
                                            index=["Pendente", "Sim", "Não"].index(recebeu_val) if recebeu_val in ["Pendente", "Sim", "Não"] else 0, key=f"rec_{idx}_{row['id']}")
                with c4:
                    reenvio = st.selectbox("REENVIO NECESSÁRIO?", ["Não", "Sim"],
                                            index=["Não", "Sim"].index(row.get("reenvio_necessario")) if row.get("reenvio_necessario") in ["Não", "Sim"] else 0, key=f"reenvio_{idx}_{row['id']}")

                chk1 = st.checkbox("Já acompanha Reforma?", value=bool(row.get("acompanha_reforma", 0)), key=f"chk1_{idx}_{row['id']}")
                chk2 = st.checkbox("Já discutiu internamente?", value=bool(row.get("discutiu_internamente", 0)), key=f"chk2_{idx}_{row['id']}")
                chk3 = st.checkbox("Já falou c/ contador?", value=bool(row.get("falou_contador", 0)), key=f"chk3_{idx}_{row['id']}")

                c5, c6 = st.columns(2)
                with c5:
                    resp_cont = st.text_input("RESPONSÁVEL INTERNO / CONTADOR", value=str(row.get("responsavel_contador") or ""), placeholder="Ex: João - Contador", key=f"resp_{idx}_{row['id']}")
                with c6:
                    opcoes_2027 = [
                        "Em análise",
                        "Manter Simples Nacional",
                        "Migrar para Simples Híbrido",
                        "Migrar para Lucro Presumido",
                        "Migrar para Lucro Real",
                        "Aguardando orientação contábil",
                        "Ainda sem definição",
                        "Não informado"
                    ]
                    def_2027 = st.selectbox("DEFINIÇÃO PRELIMINAR 2027", opcoes_2027,
                                            index=opcoes_2027.index(row.get("definicao_2027")) if row.get(
                                                "definicao_2027") in opcoes_2027 else 0, key=f"def_{idx}_{row['id']}")

                c7, c8 = st.columns(2)
                with c7:
                    # FIX: era row.get("PREVISAO_RETORNO") -> coluna real é "previsao_retorno"
                    val_prev = row.get("previsao_retorno")
                    data_prev_ini = None
                    if val_prev and str(val_prev).strip() != "":
                        try:
                            data_prev_ini = datetime.strptime(str(val_prev).strip(), "%d/%m/%Y").date()
                        except Exception:
                            pass
                    prev_obj = st.date_input("PREVISÃO RETORNO", value=data_prev_ini, format="DD/MM/YYYY", key=f"prev_{idx}_{row['id']}")
                    prev = prev_obj.strftime("%d/%m/%Y") if prev_obj else ""
                with c8:
                    # FIX: era row.get("DATA_PROXIMO_CONTATO") -> coluna real é "data_proximo_contato"
                    val_prox = row.get("data_proximo_contato")
                    data_prox_ini = None
                    if val_prox and str(val_prox).strip() != "":
                        try:
                            data_prox_ini = datetime.strptime(str(val_prox).strip(), "%d/%m/%Y").date()
                        except Exception:
                            pass
                    prox_contato_obj = st.date_input("DATA PRÓXIMO CONTATO", value=data_prox_ini, format="DD/MM/YYYY", key=f"prox_contato_{idx}_{row['id']}")
                    prox_contato = prox_contato_obj.strftime("%d/%m/%Y") if prox_contato_obj else ""

                c9, c10 = st.columns(2)
                with c9:
                    status = st.selectbox("STATUS OFICIAL", ["Pendente - Fornecedor Não contatado", "Verde - Confirmado", "Amarelo - Em avaliação", "Laranja - Sem definição", "Vermelho - Não pretende alterar", "Cinza - Não localizado"],
                                           index=["Pendente", "Verde", "Amarelo", "Laranja", "Vermelho", "Cinza"].index(badge) if badge in ["Pendente", "Verde", "Amarelo", "Laranja", "Vermelho", "Cinza"] else 0, key=f"stat_{idx}_{row['id']}")
                with c10:
                    # FIX: lista de opções e lista usada no .index() agora são a mesma
                    # (antes o .index() usava uma lista sem "Nenhuma" e deslocava a seleção).
                    valor_acao_atual = row.get("proxima_acao")
                    prox_acao = st.selectbox(
                        "PRÓXIMA AÇÃO", OPCOES_PROXIMA_ACAO,
                        index=OPCOES_PROXIMA_ACAO.index(valor_acao_atual) if valor_acao_atual in OPCOES_PROXIMA_ACAO else 0,
                        key=f"acao_{idx}_{row['id']}")

                obs = st.text_area("OBSERVAÇÃO + EVIDÊNCIAS", value=str(row.get("observacao") or ""), key=f"obs_{idx}_{row['id']}", height=70)

                # Dentro do form, o st.form_submit_button substitui o st.button comum
                submitted = st.form_submit_button("💾 SALVAR", use_container_width=True)

                if submitted:
                    try:
                        with engine.begin() as conn:
                            conn.execute(text("""
                                UPDATE contatos SET
                                    data_contato=:dc, canal_contato=:cc, recebeu=:r, reenvio_necessario=:rn,
                                    acompanha_reforma=:ar, discutiu_internamente=:di, falou_contador=:fc,
                                    responsavel_contador=:rc, definicao_2027=:d27, previsao_retorno=:p,
                                    data_proximo_contato=:dpc, status=:s, proxima_acao=:pa, observacao=:o
                                WHERE id=:id
                            """), {
                                "dc": data_contato, "cc": canal_contato, "r": recebeu, "rn": reenvio,
                                "ar": 1 if chk1 else 0, "di": 1 if chk2 else 0, "fc": 1 if chk3 else 0,
                                "rc": resp_cont, "d27": def_2027, "p": prev, "dpc": prox_contato,
                                "s": status, "pa": prox_acao, "o": obs, "id": int(row['id'])
                            })
                        carregar_contatos.clear()  # invalida o cache para refletir o salvamento imediatamente
                        st.success("✅ SALVO COM SUCESSO!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ ERRO AO SALVAR: {e}")