import streamlit as st
import google.generativeai as genai
import pdfplumber
import pandas as pd
import json, re, time
from collections import deque

st.set_page_config(page_title="Parser de Gabaritos", layout="wide")
st.title("📥 Parser de Gabaritos (PDF → JSON → CSV)")

MODEL_NAME = "gemini-2.5-flash-lite"
STD_COLS   = ["ano","dia","area","co_prova","ordem","gabarito","lingua"]

_call_times = deque() 
def throttle(rpm_limit: int = 14, window: int = 60):
    """Garante no máx `rpm_limit` chamadas por janela de `window` segundos."""
    now = time.time()

    while _call_times and now - _call_times[0] > window:
        _call_times.popleft()

    if len(_call_times) >= rpm_limit:
        sleep_for = window - (now - _call_times[0]) + 0.05
        time.sleep(max(0, sleep_for))
        now = time.time()

        while _call_times and now - _call_times[0] > window:
            _call_times.popleft()
    _call_times.append(time.time())

def extract_text_from_pdf(file) -> str:
    txt = []
    with pdfplumber.open(file) as pdf:
        for p in pdf.pages:
            t = p.extract_text() or ""
            txt.append(t)
    return "\n".join(txt)

def chunk_text(s: str, max_chars=11000, overlap=400):
    if not s: return []
    s = s.strip()
    if len(s) <= max_chars:
        return [s]
    chunks, i = [], 0
    while i < len(s):
        j = min(i + max_chars, len(s))
        chunk = s[i:j]
        chunks.append(chunk)
        if j == len(s): break
        i = j - overlap
    return chunks

def coerce_area(q: int, ano: int | None) -> str:
    if ano and ano <= 2008: return "GERAL"
    if   1 <= q <= 45:   return "CH" #Ciencias Humanas
    elif 46 <= q <= 90:  return "CN" # Ciencias da natureza
    elif 91 <= q <= 135: return "LC" # Linguagens e codigos
    elif 136 <= q <= 180:return "MT" # Matematica
    return "GERAL"

def day_from_q(q: int) -> int:
    return 1 if q <= 90 else 2

def detect_color(text: str, filename: str | None = None):
    def _find(s):
        m = re.search(r"\b(AMARELA|AMARELO|AZUL|BRANCO|ROSA|CINZA)\b", s or "", flags=re.I)
        if not m: return None
        c = m.group(1).upper()
        return "AMARELA" if c.startswith("AMAREL") else c
    return _find(text) or _find(filename or "")

def detect_year(text: str, filename: str | None = None):
    m = re.search(r"\b(20\d{2}|200\d)\b", text or "")
    if m: return int(m.group(1))
    if filename:
        m = re.search(r"\b(20\d{2}|200\d)\b", filename)
        if m: return int(m.group(1))
    return None

def robust_json_loads(s: str):
    try:
        return json.loads(s)
    except Exception:
        pass
    m = re.search(r"\[[\s\S]*\]", s)
    if m:
        return json.loads(m.group(0))
    raise ValueError("Resposta não é JSON válido.")

def normalize_items(items, ano_hint=None, cor_hint=None):
    rows = []
    for it in items:
        try:
            ordem = int(it.get("ordem"))
        except Exception:
            continue
        alt = (it.get("gabarito") or "").strip().upper()
        if alt not in list("ABCDE"):
            continue
        ano    = int(it.get("ano") or (ano_hint or 0))
        dia    = int(it.get("dia") or day_from_q(ordem))
        area   = (it.get("area") or "").strip().upper()
        if not area:
            area = coerce_area(ordem, ano or ano_hint)
        cor    = (it.get("co_prova") or cor_hint or "DESCONHECIDA").strip().upper()
        if cor.startswith("AMAREL"): cor = "AMARELA"
        lingua = it.get("lingua")
        if lingua:
            lingua = lingua.strip().upper()
            if "INGL" in lingua: lingua = "INGLES"
            if "ESP"  in lingua: lingua = "ESPANHOL"
        rows.append([ano, dia, area, cor, ordem, alt, lingua or None])

    if not rows:
        return pd.DataFrame(columns=STD_COLS)
    df = pd.DataFrame(rows, columns=STD_COLS)
    df = df.drop_duplicates(subset=["ano","dia","co_prova","ordem","lingua"], keep="first")
    df = df.sort_values(["ano","dia","co_prova","ordem","lingua"], kind="stable")
    return df[STD_COLS]

def regex_fallback_pairs(text: str):
    pairs = re.findall(r"(?<!\d)(\d{1,3})\s*[:\-]?\s*([ABCDE])\b", text)
    seen = set(); out = []
    for q, g in pairs:
        qi = int(q)
        if qi not in seen:
            seen.add(qi); out.append((qi, g))
    return out

st.markdown("Cole a chave, envie 1+ PDFs e baixe o CSV com todas as questões.")

api_key = st.text_input("GEMINI_API_KEY", type="password", placeholder="AIza...")
uploaded_files = st.file_uploader("📄 PDFs do gabarito", type=["pdf"], accept_multiple_files=True)

with st.expander("Opções (opcional)"):
    ano_forcado = st.number_input("Forçar ano (0 = inferir)", min_value=0, max_value=2100, value=0, step=1)
    cor_forcada = st.selectbox("Forçar cor (vazio = detectar)", ["", "AMARELA", "AZUL", "BRANCO", "ROSA", "CINZA"])
    cor_forcada = cor_forcada or None
    rpm_limit   = st.number_input("Limite de chamadas por minuto (<=15)", min_value=1, max_value=15, value=14, step=1)

if st.button("🚀 Extrair e gerar CSV", use_container_width=True):
    if not api_key:
        st.error("Cole sua chave da API primeiro.")
    elif not uploaded_files:
        st.error("Envie pelo menos um PDF.")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(MODEL_NAME)
        except Exception as e:
            st.error(f"Erro configurando Gemini: {e}")
            st.stop()

        dfs_total = []

        for f in uploaded_files:
            st.write(f"🧾 **{f.name}**")
            text = extract_text_from_pdf(f)
            if not text.strip():
                st.warning("PDF sem texto extraível.")
                continue

            ano_hint = ano_forcado or detect_year(text, f.name) or None
            cor_hint = cor_forcada or detect_color(text, f.name) or None

            chunks = chunk_text(text, max_chars=11000, overlap=400)
            st.caption(f"Processando em {len(chunks)} parte(s)…")
            prog = st.progress(0)

            dfs_file = []
            for idx, ch in enumerate(chunks, start=1):
                prompt = f"""
Você é um parser de gabaritos do ENEM.
Extraia **TODAS** as questões presentes **neste trecho** e retorne **APENAS** um JSON array.

Formato exato de cada item:
{{
  "ano": {ano_hint if ano_hint is not None else "null"},
  "dia": null,
  "area": null,
  "co_prova": {json.dumps(cor_hint) if cor_hint else "null"},
  "ordem": 1,
  "gabarito": "A",
  "lingua": null
}}

Regras:
- Não trunque nem resuma. Liste **todas** as questões deste trecho.
- "gabarito" ∈ {{A,B,C,D,E}}.
- Se houver duas alternativas (língua inglesa/espanhol), crie **dois** itens com "lingua": "INGLES" e "ESPANHOL".
- Se "dia" ou "area" não estiverem claras, deixe null (eu infiro depois).
- Responda **somente** o JSON array (sem markdown).

Texto do trecho:
{ch}
""".strip()

                try:
                    throttle(rpm_limit=rpm_limit)

                    resp = model.generate_content(
                        prompt,
                        generation_config={"response_mime_type": "application/json"}
                    )
                    items = robust_json_loads(resp.text)
                    df_chunk = normalize_items(items, ano_hint=ano_hint, cor_hint=cor_hint)
                    dfs_file.append(df_chunk)
                except Exception as e:
                    st.error(f"Falha no chunk {idx}: {e}")

                prog.progress(int(idx/len(chunks)*100))

            df_file = pd.concat(dfs_file, ignore_index=True) if dfs_file else pd.DataFrame(columns=STD_COLS)

            pares = regex_fallback_pairs(text)
            if pares:
                extras = []
                for qi, g in pares:
                    if not ((df_file["ordem"] == qi).any()):
                        ano = ano_hint or 0
                        dia = day_from_q(qi)
                        area = coerce_area(qi, ano)
                        extras.append([ano, dia, area, cor_hint or "DESCONHECIDA", qi, g, None])
                if extras:
                    df_file = pd.concat([df_file, pd.DataFrame(extras, columns=STD_COLS)], ignore_index=True)
                    df_file = df_file.drop_duplicates(subset=["ano","dia","co_prova","ordem","lingua"])
                    df_file = df_file.sort_values(["ano","dia","co_prova","ordem","lingua"], kind="stable")

            if df_file.empty:
                st.warning("Nada extraído deste arquivo.")
            else:
                st.success(f"✅ {len(df_file)} linhas extraídas deste arquivo.")
                st.dataframe(df_file.head(20), use_container_width=True)
                dfs_total.append(df_file)

        if dfs_total:
            final = pd.concat(dfs_total, ignore_index=True)
            final = final[STD_COLS]
            st.markdown("### 📦 Consolidado")
            st.dataframe(final, use_container_width=True)
            st.download_button(
                "💾 Baixar CSV consolidado",
                data=final.to_csv(index=False, sep=";").encode("utf-8"),
                file_name="gabaritos_enem.csv",
                mime="text/csv"
            )
