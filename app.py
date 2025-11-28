import streamlit as st
import json
from openai import OpenAI

# ==============================
# Streamlit設定
# ==============================
st.set_page_config(page_title="発達支援相談AIエージェント", layout="centered")

# ==============================
# パスワード認証
# ==============================
PASSWORD = "forest2025"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align:center;'>🌿 発達支援相談AIエージェント</h2>", unsafe_allow_html=True)
    pwd = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン"):
        if pwd == PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います。")
    st.stop()

# ==============================
# OpenAI設定（Secrets推奨）
# ==============================
API_KEY = st.secrets.get("OPENAI_API_KEY", "")
client = OpenAI(api_key=API_KEY)

# ==============================
# JSON読み込み
# ==============================
with open("nd_kb_v2.json", "r", encoding="utf-8") as f:
    kb = json.load(f)

# ==============================
# スコアリング
# ==============================
def score_categories(text):
    scores = []
    for cat in kb["categories"]:
        score = 0
        for kw in cat.get("nlp_keywords", []):
            if kw in text:
                score += 1
        scores.append((cat["name"], score, cat))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores

# ==============================
# GPT回答生成
# ==============================
def generate_response(history, category_name, user_input, support, rationale, source):
    history_text = "\n".join(
        [f"保護者: {m[0]}" if m[1] == "user" else f"AI: {m[0]}" for m in history[-4:]]
    )

    prompt = f"""
あなたは保護者支援専門のやさしい発達支援カウンセラーです。
専門用語を使わず、今日から家庭でできる具体的な工夫を、会話のようにわかりやすく伝えてください。
500文字前後、共感をこめて。

【相談履歴】
{history_text}

【今回の相談】
{user_input}

【推定される発達特性】
{category_name}

【支援の方向性】
{support}

【背景理解】
{rationale}

※ 出典は文末に「📚 出典：」の形で記載してください。
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# ==============================
# UIスタイル
# ==============================
st.markdown("""
<style>
body { background-color: #fff7ed; font-family: 'Zen Maru Gothic', sans-serif; }

.user-bubble {
    background: #dff4ff;
    padding: 14px;
    margin: 10px 0;
    border-radius: 18px 18px 0px 18px;
    border: 1px solid #96c7e6;
    max-width: 80%;
    margin-left: auto;
}

.bot-bubble {
    background: #fffdf8;
    padding: 14px;
    margin: 10px 0;
    border-radius: 18px 18px 18px 0px;
    border: 1px solid #e5c7a5;
    max-width: 80%;
    margin-right: auto;
}

.title {
    font-size: 30px;
    text-align: center;
    font-weight: 700;
    color: #405c3d;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">🌿 発達支援相談AIエージェント</div>', unsafe_allow_html=True)
st.write("気になる様子を自由に書いてください。")

# ==============================
# チャット履歴
# ==============================
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg, sender in st.session_state.messages:
    bubble = "user-bubble" if sender == "user" else "bot-bubble"
    st.markdown(f'<div class="{bubble}">{msg}</div>', unsafe_allow_html=True)

# ==============================
# 入力欄（自動クリア＆安全）
# ==============================
user_input = st.chat_input("入力してください")

if user_input:
    st.session_state.messages.append((user_input, "user"))

    scores = score_categories(user_input)
    selected_name, _, selected_category = scores[0]

    supports = selected_category.get("recommended_supports", {})
    first = (supports.get("immediate") or supports.get("short_term") or supports.get("long_term") or [{}])[0]

    support = first.get("description", "家庭や学校での環境調整が有効とされています。")
    rationale = first.get("rationale", "行動の背景には特性理解が重要とされています。")
    source = first.get("source", "文部科学省 特別支援教育ガイドライン（2023）")

    answer = generate_response(st.session_state.messages, selected_name, user_input, support, rationale, source)

    full_answer = f"{answer}\n\n📚 出典：{source}"
    st.session_state.messages.append((full_answer, "bot"))

    st.rerun()
