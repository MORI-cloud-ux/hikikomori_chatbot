import streamlit as st
from openai import OpenAI
import json

# --- ✅ アクセス制限パス設定 ---
ACCESS_PASS = "forest2025"

# --- APIキー（Secrets管理） ---
# Streamlit上で: Manage App → Secrets → OPENAI_API_KEY = "sk-xxx"
API_KEY = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=API_KEY)

# --- Streamlit UI設定 ---
st.set_page_config(
    page_title="🌿 不登校・ひきこもり相談AIエージェント",
    layout="wide",
)

# --- カスタムCSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic&display=swap');
body { font-family: 'Zen Maru Gothic', sans-serif; background: linear-gradient(180deg, #fff7ec 0%, #fff1de 50%, #ffeacf 100%); color: #333; }
.stApp { padding: 2rem; }
h1 { color: #2e7d32; text-align: center; font-weight: 700; margin-bottom: 0.3rem; font-size: 2.5rem; }
.stTextArea textarea { background-color: #d9f0d9; border-radius: 1.2rem; border: 1px solid #a8d5a2; color: #2e4d32; font-size: 1.05rem; padding: 0.8rem; }
.user-bubble { background-color: #d0f0c0; color: #1b3d1b; border-radius: 1rem; padding: 0.8rem; margin: 0.4rem 0; box-shadow: 0px 2px 6px rgba(0,0,0,0.1); }
.bot-bubble { background-color: #e6ffe6; color: #2e7d32; border-radius: 1rem; padding: 0.8rem; margin: 0.4rem 0; box-shadow: 0px 2px 6px rgba(0,0,0,0.1); }
.stButton>button { background-color: #66bb6a; color: white; border-radius: 1.5rem; border: none; padding: 0.6rem 1.2rem; font-size: 1rem; transition: 0.2s; }
.stButton>button:hover { background-color: #4caf50; }
footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- ✅ パスワード認証 ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h1>🌿 不登校・ひきこもり相談AIエージェントへようこそ</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#2e7d32;'>アクセスにはパスワードが必要です</p>", unsafe_allow_html=True)
    password_input = st.text_input("🔑 パスワードを入力してください", type="password", placeholder="パスワードを入力")
    if st.button("はじめる 🌱"):
        if password_input == ACCESS_PASS:
            st.session_state.authenticated = True
            st.experimental_rerun()
        else:
            st.error("パスワードが違います。")
    st.stop()

# --- タイトル ---
st.markdown("<h1>🤖🌿 AIエージェントへ相談する</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#2e7d32;'>温かく寄り添い、少しずつ一歩を。</p>", unsafe_allow_html=True)

# --- チャット履歴とフェーズ管理 ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_phase" not in st.session_state:
    st.session_state.current_phase = None

# --- 知識ベース（完全版） ---
knowledge_base = {
    "phases": {
        "phase_1": {"名称": "閉塞期（閉じこもり・虚無感）", "特徴": "本人は無力感・自己否定感を抱え、外界との接触を避けている。自室に閉じこもり、会話も極端に減少。", "本人語": ["死んでもいいかなって思うことがある","誰にも会いたくない","何もしたくない","自分には価値がない"], "支援方向": "責めずに、ただ「そこにいてよい」ことを示す。家族や支援者は無理な接触を控える。", "関連概念": ["自己否定","閉じこもり","生きる意味の喪失","実存的不安"]},
        "phase_2": {"名称": "揺らぎ期（関係への欲求と不安）", "特徴": "自分の状況に疑問を持ち始め、外との関係に揺らぎが出てくる。まだ行動には出ない。", "本人語": ["こんなままでいいのかな","誰かと話した方がいいのかなと思うときがある","外に出たい気もするけど怖い"], "支援方向": "共感的に話を聴き、本人の“希求”の芽を育てる。安全な居場所の提案。", "関連概念": ["関係希求","揺らぎ","対人不安","親との葛藤"]},
        "phase_3": {"名称": "希求・模索期（意味や繋がりの模索）", "特徴": "他者と関わりたいという欲求が芽生え、行動を模索する。居場所や支援者との出会いが重要な転機になる。", "本人語": ["誰かと少し話せるとホッとする","○○に行ってみようかなと思った","ちょっとだけ外に出てみた"], "支援方向": "自己選択を尊重したうえで、非評価的な居場所の紹介や第三者との緩やかなつながりを促す。", "関連概念": ["居場所","非評価","第三者","模索と再意味化"]},
        "phase_4": {"名称": "転回期（新たな価値観との出会い）", "特徴": "過去の経験を新しい意味で捉え直し、「自分なりの社会参加」への第一歩を踏み出す段階。", "本人語": ["前は失敗と思ってたけど、今はいい経験だったと思える","無理に働かなくてもいいって思えるようになった","少しずつ人とも話せてる"], "支援方向": "“働く／働かない”にこだわらず、本人の価値観の変容を支援。QOL向上を重視。", "関連概念": ["再意味化","折り合い","多様な生き方","主体の回復"]}
    },
    "triggers": {
        "変容の契機": ["否定されない対話の経験","家族の接し方の変化（干渉から見守りへ）","居場所での安心体験","他者の語りからの気づき","第三者の介入（訪問、支援者、同世代）","就労・社会体験での“つまずき”と意味づけの変化"]
    },
    "supports": {
        "訪問相談": "本人が出られない状況に対して、支援者が家庭を訪問し接点をつくる。",
        "居場所活動": "何も求められず、安心して存在できる場の提供。対人関係の再構築の基盤。",
        "就労支援": "働くことそのものではなく、“働けるかもしれない”と思える段階を支援。段階的な関わりが必要。",
        "親支援": "親自身の不安と孤立を軽減し、本人への接し方の学習や価値観の更新を促す。"
    }
}

# --- システムプロンプト生成 ---
def build_system_prompt(fixed_phase=None):
    prompt = "あなたはひきこもり支援の専門家です。\n"
    prompt += "以下の知識ベースに基づき、利用者のPhaseを提示して、状態に応じて共感的に応答してください。\n"
    if fixed_phase:
        prompt += f"今回の相談は phase: {fixed_phase} に固定します。\n"
    prompt += f"知識ベース: {json.dumps(knowledge_base, ensure_ascii=False)}"
    return prompt

# --- GPT応答生成 ---
def generate_response(user_input: str) -> str:
    messages = []
    if not st.session_state.chat_history:
        messages.append({"role": "system", "content": build_system_prompt()})
    else:
        messages.append({"role": "system", "content": build_system_prompt(st.session_state.current_phase)})

    messages.append({"role": "user", "content": f"相談者の発言: {user_input}"})
    for chat in st.session_state.chat_history:
        messages.append({"role": "user", "content": chat["user"]})
        messages.append({"role": "assistant", "content": chat["bot"]})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7,
    )
    answer = response.choices[0].message.content

    if not st.session_state.current_phase:
        st.session_state.current_phase = "phase_1"  # 1回目はGPTで判定してもよい

    st.session_state.chat_history.append({
        "user": user_input,
        "bot": answer,
        "phase": st.session_state.current_phase
    })
    return answer

# --- 送信処理 ---
def submit():
    user_text = st.session_state.get("user_input", "").strip()
    if not user_text:
        st.warning("何か入力してください。")
        return
    with st.spinner("AIエージェントは考えています…"):
        try:
            generate_response(user_text)
        except Exception as e:
            st.error(f"エラー: {e}")
            return
    st.session_state["user_input"] = ""

# --- 入力欄 ---
st.text_area("ご相談内容を入力してください", height=120, placeholder="どんなことでも大丈夫です。", key="user_input")
st.button("送信 🌱", on_click=submit)

# --- チャット履歴表示 ---
st.markdown("### 💬 これまでの対話")
for chat in st.session_state.chat_history:
    st.markdown(f"<div class='user-bubble'><b>あなた：</b> {chat['user']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='bot-bubble'><b>AIエージェント：</b> {chat['bot']}</div>", unsafe_allow_html=True)
