import streamlit as st
from openai import OpenAI
import json
from datetime import date
from supabase import create_client, Client

# --- ✅ アクセス制限パス設定（全体への入口） ---
ACCESS_PASS = "forest2025"

# --- APIキー（Secrets管理） ---
API_KEY = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=API_KEY)

# --- Supabaseクライアント ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Streamlit UI設定 ---
st.set_page_config(
    page_title="🌿 不登校・ひきこもり相談AIエージェント",
    layout="wide",
)

# --- カスタムCSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic&display=swap');
body {
    font-family: 'Zen Maru Gothic', sans-serif;
    background: linear-gradient(180deg, #fff7ec 0%, #fff1de 50%, #ffeacf 100%);
    color: #333;
}
.stApp { padding: 2rem; }
h1 {
    color: #2e7d32;
    text-align: center;
    font-weight: 700;
    margin-bottom: 0.3rem;
    font-size: 2.5rem;
}
.stTextArea textarea {
    background-color: #d9f0d9;
    border-radius: 1.2rem;
    border: 1px solid #a8d5a2;
    color: #2e4d32;
    font-size: 1.05rem;
    padding: 0.8rem;
}
.user-bubble {
    background-color: #d0f0c0;
    color: #1b3d1b;
    border-radius: 1rem;
    padding: 0.8rem;
    margin: 0.4rem 0;
    box-shadow: 0px 2px 6px rgba(0,0,0,0.1);
}
.bot-bubble {
    background-color: #e6ffe6;
    color: #2e7d32;
    border-radius: 1rem;
    padding: 0.8rem;
    margin: 0.4rem 0;
    box-shadow: 0px 2px 6px rgba(0,0,0,0.1);
}
.stButton>button {
    background-color: #66bb6a;
    color: white;
    border-radius: 1.5rem;
    border: none;
    padding: 0.6rem 1.2rem;
    font-size: 1rem;
    transition: 0.2s;
}
.stButton>button:hover {
    background-color: #4caf50;
}
footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 🔐 1. アクセス用パスワード認証（共通の入口）
# ============================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h1>🌿 不登校・ひきこもり相談AIエージェントへようこそ</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#2e7d32;'>アクセスにはパスワードが必要です</p>", unsafe_allow_html=True)
    password_input = st.text_input("🔑 アクセス用パスワードを入力してください", type="password", placeholder="パスワードを入力")
    if st.button("はじめる 🌱"):
        if password_input == ACCESS_PASS:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います。")
    st.stop()

# ============================================================
# 🧑‍💻 2. Supabase ユーザー登録・ログイン
# ============================================================
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<h1>👥 ログイン / 新規登録</h1>", unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["ログイン", "新規登録"])

    with tab_login:
        login_email = st.text_input("メールアドレス", key="login_email")
        login_password = st.text_input("パスワード", type="password", key="login_password")

        if st.button("ログイン"):
            if not login_email or not login_password:
                st.error("メールアドレスとパスワードを入力してください。")
            else:
                try:
                    res = supabase.auth.sign_in_with_password(
                        {"email": login_email, "password": login_password}
                    )
                    st.session_state.user = res.user
                    st.success("ログインしました。")
                    st.rerun()
                except Exception as e:
                    st.error(f"ログインに失敗しました: {e}")

    with tab_signup:
        signup_email = st.text_input("新規登録用メールアドレス", key="signup_email")
        signup_password = st.text_input("新規登録用パスワード（6文字以上推奨）", type="password", key="signup_password")

        if st.button("アカウント作成"):
            if not signup_email or not signup_password:
                st.error("メールアドレスとパスワードを入力してください。")
            else:
                try:
                    res = supabase.auth.sign_up(
                        {"email": signup_email, "password": signup_password}
                    )
                    st.success("登録しました。確認メールが届いていれば、メール認証後にログインしてください。")
                except Exception as e:
                    st.error(f"登録に失敗しました: {e}")

    st.stop()

# ここに来たら Supabase ログイン済み
user = st.session_state.user
user_id = getattr(user, "id", None)
if user_id is None and isinstance(user, dict):
    user_id = user.get("id")

if not user_id:
    st.error("ユーザーIDが取得できませんでした。Supabaseの認証設定を確認してください。")
    st.stop()

# ログアウトボタン
with st.sidebar:
    st.markdown(f"**ログイン中:** {getattr(user, 'email', '')}")
    if st.button("ログアウト"):
        st.session_state.user = None
        st.session_state.chat_history = []
        st.session_state.current_phase = None
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        st.rerun()

# ============================================================
# 🌱 3. チャット用のセッション状態
# ============================================================
if "chat_history" not in st.session_state:
    # chat_history は「今日の会話のみ」を保持（DBから読み込む）
    st.session_state.chat_history = []

if "current_phase" not in st.session_state:
    st.session_state.current_phase = None

today_str = date.today().isoformat()

# ============================================================
# 📥 4. 今日の会話履歴を Supabase から読み込む
# ============================================================
def load_today_history(user_id: str):
    try:
        res = supabase.table("user_chats").select("*") \
            .eq("user_id", user_id) \
            .eq("chat_date", today_str) \
            .order("message_time", desc=False) \
            .execute()
        data = res.data if hasattr(res, "data") else res.get("data", [])
    except Exception as e:
        st.error(f"会話履歴の読み込み中にエラーが発生しました: {e}")
        data = []

    history = []
    current_phase = None
    for row in data:
        history.append({
            "user": row.get("user_message", ""),
            "bot": row.get("bot_message", ""),
        })
        # 本日のフェーズは、最初に設定されたものを採用
        if row.get("phase") and current_phase is None:
            current_phase = row.get("phase")

    st.session_state.chat_history = history
    st.session_state.current_phase = current_phase

# 毎リロード時に最新を取得
load_today_history(user_id)

# ============================================================
# 📚 5. 知識ベース（完全版）
# ============================================================
knowledge_base = {
    "phases": {
        "phase_1": {
            "名称": "閉塞期（閉じこもり・虚無感）",
            "特徴": "本人は無力感・自己否定感を抱え、外界との接触を避けている。自室に閉じこもり、会話も極端に減少。",
            "本人語": ["死んでもいいかなって思うことがある", "誰にも会いたくない", "何もしたくない", "自分には価値がない"],
            "支援方向": "責めずに、ただ「そこにいてよい」ことを示す。家族や支援者は無理な接触を控える。",
            "関連概念": ["自己否定", "閉じこもり", "生きる意味の喪失", "実存的不安"]
        },
        "phase_2": {
            "名称": "揺らぎ期（関係への欲求と不安）",
            "特徴": "自分の状況に疑問を持ち始め、外との関係に揺らぎが出てくる。まだ行動には出ない。",
            "本人語": ["こんなままでいいのかな", "誰かと話した方がいいのかなと思うときがある", "外に出たい気もするけど怖い"],
            "支援方向": "共感的に話を聴き、本人の“希求”の芽を育てる。安全な居場所の提案。",
            "関連概念": ["関係希求", "揺らぎ", "対人不安", "親との葛藤"]
        },
        "phase_3": {
            "名称": "希求・模索期（意味や繋がりの模索）",
            "特徴": "他者と関わりたいという欲求が芽生え、行動を模索する。居場所や支援者との出会いが重要な転機になる。",
            "本人語": ["誰かと少し話せるとホッとする", "○○に行ってみようかなと思った", "ちょっとだけ外に出てみた"],
            "支援方向": "自己選択を尊重したうえで、非評価的な居場所の紹介や第三者との緩やかなつながりを促す。",
            "関連概念": ["居場所", "非評価", "第三者", "模索と再意味化"]
        },
        "phase_4": {
            "名称": "転回期（新たな価値観との出会い）",
            "特徴": "過去の経験を新しい意味で捉え直し、「自分なりの社会参加」への第一歩を踏み出す段階。",
            "本人語": ["前は失敗と思ってたけど、今はいい経験だったと思える", "無理に働かなくてもいいって思えるようになった", "少しずつ人とも話せてる"],
            "支援方向": "“働く／働かない”にこだわらず、本人の価値観の変容を支援。QOL向上を重視。",
            "関連概念": ["再意味化", "折り合い", "多様な生き方", "主体の回復"]
        }
    },
    "triggers": {
        "変容の契機": [
            "否定されない対話の経験",
            "家族の接し方の変化（干渉から見守りへ）",
            "居場所での安心体験",
            "他者の語りからの気づき",
            "第三者の介入（訪問、支援者、同世代）",
            "就労・社会体験での“つまずき”と意味づけの変化"
        ]
    },
    "supports": {
        "訪問相談": "本人が出られない状況に対して、支援者が家庭を訪問し接点をつくる。",
        "居場所活動": "何も求められず、安心して存在できる場の提供。対人関係の再構築の基盤。",
        "就労支援": "働くことそのものではなく、“働けるかもしれない”と思える段階を支援。段階的な関わりが必要。",
        "親支援": "親自身の不安と孤立を軽減し、本人への接し方の学習や価値観の更新を促す。"
    }
}

# ============================================================
# 🧠 6. システムプロンプト生成
# ============================================================
def build_system_prompt(fixed_phase=None, is_first_today=False):
    prompt = "あなたはひきこもり支援の専門家です。\n"
    prompt += "以下の知識ベースに基づき、利用者の状態に共感的に寄り添いながら、日本語で丁寧に応答してください。\n"
    prompt += "フェーズは phase_1〜phase_4 の4段階です。\n\n"

    if is_first_today:
        prompt += (
            "今日はその日の最初の相談です。今回の相談者の発言内容から、現在のフェーズを "
            "phase_1〜phase_4 の中から一つだけ選んで推定してください。\n"
            "そのうえで、支援の方向性も踏まえて回答してください。\n"
            "出力は必ず次の形式に従ってください。\n"
            "【phase】phase_1 または phase_2 または phase_3 または phase_4\n"
            "【response】相談者への回答文\n\n"
        )
    else:
        if fixed_phase:
            prompt += (
                f"本日はすでにフェーズが推定されています。現在のフェーズは {fixed_phase} です。\n"
                "フェーズの再推定は行わず、このフェーズを前提に、相談者の新しい発言にピンポイントに回答してください。\n"
            )
        prompt += (
            "本日はフェーズ再判定は不要です。出力は基本的に次の形式にしてください。\n"
            "【response】相談者への回答文\n\n"
        )

    prompt += "知識ベースは次の通りです。\n"
    prompt += json.dumps(knowledge_base, ensure_ascii=False, indent=2)

    return prompt

# ============================================================
# 🤖 7. GPT応答生成 ＋ Supabase 保存
# ============================================================
def generate_response(user_input: str) -> str:
    # 今日の最初の相談かどうか
    is_first_today = (len(st.session_state.chat_history) == 0 or st.session_state.current_phase is None)
    fixed_phase = None if is_first_today else st.session_state.current_phase

    messages = []
    messages.append({
        "role": "system",
        "content": build_system_prompt(fixed_phase=fixed_phase, is_first_today=is_first_today)
    })

    # GPTに渡す履歴は「今日の分」だけ（chat_historyは今日のみ）
    for chat in st.session_state.chat_history:
        messages.append({"role": "user", "content": f"相談者の発言: {chat['user']}"})
        messages.append({"role": "assistant", "content": chat["bot"]})

    # 今回の相談内容
    messages.append({"role": "user", "content": f"相談者の発言: {user_input}"})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7,
    )
    answer_full = response.choices[0].message.content.strip()

    # --- 応答テキストとフェーズの抽出 ---
    response_text = answer_full
    phase_for_row = None

    if is_first_today:
        # 初回のみフェーズを推定してもらう
        phase_candidate = None
        if "【phase】" in answer_full:
            after_phase = answer_full.split("【phase】", 1)[1]
            first_line = after_phase.splitlines()[0].strip()
            for key in ["phase_1", "phase_2", "phase_3", "phase_4"]:
                if key in first_line:
                    phase_candidate = key
                    break

        if phase_candidate is None:
            phase_candidate = "phase_1"

        phase_for_row = phase_candidate

        # 応答部分を抽出
        if "【response】" in answer_full:
            response_text = answer_full.split("【response】", 1)[1].strip()
        else:
            response_text = answer_full.strip()

        # 本日の current_phase を確定（メモリ）
        st.session_state.current_phase = phase_for_row
    else:
        # 2回目以降はフェーズは固定（DB保存には current_phase を使う）
        phase_for_row = st.session_state.current_phase
        if "【response】" in answer_full:
            response_text = answer_full.split("【response】", 1)[1].strip()
        else:
            response_text = answer_full.strip()

    # --- Supabase に保存 ---
    try:
        supabase.table("user_chats").insert({
            "user_id": user_id,
            "chat_date": today_str,
            "user_message": user_input,
            "bot_message": response_text,
            "phase": phase_for_row
        }).execute()
    except Exception as e:
        st.error(f"会話の保存中にエラーが発生しました: {e}")

    # 画面上の chat_history は次回リロード時に DB から再取得される
    return response_text

# ============================================================
# 🏷 8. タイトル・フェーズ表示
# ============================================================
st.markdown("<h1>🤖🌿 AIエージェントへ相談する</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#2e7d32;'>温かく寄り添い、少しずつ一歩を。</p>", unsafe_allow_html=True)

st.markdown("### 🌿 現在の推定フェーズ")

phase_display = [
    ("phase_1", "Phase 1：閉塞期（閉じこもり・虚無感）"),
    ("phase_2", "Phase 2：揺らぎ期（関係を求めたい気持ちと不安）"),
    ("phase_3", "Phase 3：希求・模索期（関わりや意味の模索）"),
    ("phase_4", "Phase 4：転回期（価値観の転換と再出発）"),
]

if st.session_state.current_phase is None:
    st.markdown("まだフェーズは推定されていません。最初の相談内容を送信すると推定されます。")

for key, label in phase_display:
    mark = "●" if st.session_state.current_phase == key else "○"
    st.markdown(f"[{mark}] {label}")

st.markdown("---")

# ============================================================
# 📤 9. 送信処理
# ============================================================
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
    # 入力欄クリア & 再読み込み
    st.session_state["user_input"] = ""
    st.rerun()

# --- 入力欄 ---
st.text_area(
    "ご相談内容を入力してください",
    height=120,
    placeholder="どんなことでも大丈夫です。",
    key="user_input"
)
st.button("送信 🌱", on_click=submit)

# ============================================================
# 🕒 10. 今日の会話履歴表示（画面下）
# ============================================================
st.markdown("### 💬 今日の対話")

for chat in st.session_state.chat_history:
    st.markdown(
        f"<div class='user-bubble'><b>あなた：</b> {chat['user']}</div>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<div class='bot-bubble'><b>AIエージェント：</b> {chat['bot']}</div>",
        unsafe_allow_html=True
    )

# ============================================================
# 📅 11. 過去の会話を日付選択で閲覧
# ============================================================
st.markdown("---")
st.markdown("### 📅 過去の相談をひらく")

try:
    res_dates = supabase.table("user_chats").select("chat_date") \
        .eq("user_id", user_id) \
        .order("chat_date", desc=True) \
        .execute()
    data_dates = res_dates.data if hasattr(res_dates, "data") else res_dates.get("data", [])
    date_options = sorted({row["chat_date"] for row in data_dates}, reverse=True)
except Exception as e:
    st.error(f"過去の相談日リスト取得中にエラーが発生しました: {e}")
    date_options = []

if date_options:
    selected_date = st.selectbox(
        "日付を選択すると、その日の相談内容が表示されます",
        options=date_options,
        format_func=lambda d: str(d),
        key="history_date_select"
    )

    if selected_date:
        st.markdown(f"#### 📖 {selected_date} の相談履歴")
        try:
            res_hist = supabase.table("user_chats").select("*") \
                .eq("user_id", user_id) \
                .eq("chat_date", selected_date) \
                .order("message_time", desc=False) \
                .execute()
            hist = res_hist.data if hasattr(res_hist, "data") else res_hist.get("data", [])
        except Exception as e:
            st.error(f"過去の相談履歴取得中にエラーが発生しました: {e}")
            hist = []

        if not hist:
            st.info("この日には記録された相談はありません。")
        else:
            for row in hist:
                st.markdown(
                    f"<div class='user-bubble'><b>あなた：</b> {row.get('user_message','')}</div>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"<div class='bot-bubble'><b>AIエージェント：</b> {row.get('bot_message','')}</div>",
                    unsafe_allow_html=True
                )
else:
    st.info("まだ記録された過去の相談はありません。")

