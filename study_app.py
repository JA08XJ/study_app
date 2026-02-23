import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# --- 1. 基本設定（モバイル最適化） ---
st.set_page_config(page_title="Study App Pro", layout="centered", initial_sidebar_state="collapsed")

# --- 2. ログイン機能 ---
if 'user' not in st.session_state:
    st.session_state.user = None

def login():
    st.markdown("### 🔐 Study App Login")
    user_input = st.text_input("ユーザー名")
    pw_input = st.text_input("パスワード", type="password")
    if st.button("ログイン", use_container_width=True, type="primary"):
        # Secrets の [passwords] セクションを確認
        if "passwords" in st.secrets and user_input in st.secrets["passwords"]:
            if pw_input == st.secrets["passwords"][user_input]:
                st.session_state.user = user_input
                st.rerun()
            else:
                st.error("パスワードが違います")
        else:
            st.error("ユーザー名が見つかりません。Secretsの設定を確認してください。")

if st.session_state.user is None:
    login()
    st.stop() # ログインするまで以下のコードを実行しない

# --- 3. ログイン後の処理 ---
user = st.session_state.user
st.sidebar.write(f"👤 ログイン中: {user}")
if st.sidebar.button("ログアウト"):
    st.session_state.user = None
    st.rerun()

# --- 4. データ連携 (Google Sheets) ---
# Secretsの [connections.gsheets] で指定したURLを自動取得します
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    # スプレッドシートから読み込み（キャッシュなしで最新を取得）
    return conn.read(worksheet=sheet_name, ttl=0).fillna("")

try:
    all_logs = load_data("logs")
    subj_df = load_data("subjects")
    mat_df = load_data("materials")
except Exception as e:
    st.error(f"データの読み込みに失敗しました。シート名を確認してください: {e}")
    st.stop()

# ログインユーザーのデータのみ抽出
log_df = all_logs[all_logs["ユーザー名"] == user].copy()
valid_subjects = [s for s in subj_df["教科名"].tolist() if s]

st.title(f"🚀 {user}'s Study App")

# --- 5. メトリクス表示 ---
today_str = str(datetime.date.today())
df_today = log_df[log_df["日付"] == today_str]
t_today = pd.to_numeric(df_today["時間(分)"], errors='coerce').sum()
t_total = pd.to_numeric(log_df["時間(分)"], errors='coerce').sum()

col1, col2 = st.columns(2)
col1.metric("今日", f"{int(t_today)} min")
col2.metric("累計", f"{int(t_total // 60)}h {int(t_total % 60)}m")

st.divider()

# --- 6. タブメニュー ---
tabs = st.tabs(["📝 記録", "📊 分析", "⚙️ 設定"])

with tabs[0]:
    st.subheader("✍️ 今日の学習")
    with st.form("record_form", clear_on_submit=True):
        d = st.date_input("日付", datetime.date.today())
        s_choice = st.selectbox("教科", valid_subjects if valid_subjects else ["未登録"])
        
        # 教科に合わせて教材リストをフィルタリング
        m_list = mat_df[mat_df["教科名"] == s_choice]["教材名"].tolist()
        m_choice = st.selectbox("教材", m_list if m_list else ["未登録"])
        
        t = st.number_input("時間(分)", min_value=0, step=5, value=30)
        c = st.text_input("メモ")
        
        if st.form_submit_button("🚀 記録を保存", use_container_width=True):
            # 新しい行を作成（全列分：ユーザー名, 日付, 教科, 教材名, 時間(分), メモ）
            new_row = pd.DataFrame([[user, str(d), s_choice, m_choice, str(t), c]], columns=all_logs.columns)
            updated_logs = pd.concat([all_logs, new_row], ignore_index=True)
            
            # スプレッドシートを更新
            conn.update(worksheet="logs", data=updated_logs)
            st.success("スプレッドシートに保存しました！")
            st.rerun()

with tabs[1]:
    st.subheader("📊 学習データ")
    if not log_df.empty:
        log_numeric = log_df.copy()
        log_numeric["時間(分)"] = pd.to_numeric(log_numeric["時間(分)"], errors='coerce')
        
        # 円グラフ
        sub_sum = log_numeric.groupby("教科")["時間(分)"].sum()
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.pie(sub_sum, labels=sub_sum.index, autopct='%1.1f%%', startangle=90)
        st.pyplot(fig)
        
        st.divider()
        st.markdown("### 🎞️ 過去の履歴")
        st.dataframe(log_df.drop(columns=["ユーザー名"]), use_container_width=True, hide_index=True)
    else:
        st.info("まだ記録がありません。")

with tabs[2]:
    st.subheader("⚙️ 全体設定")
    st.caption("※教科と教材は全ユーザー共通です")
    
    with st.expander("🛠️ 教科の編集"):
        ed_s = st.data_editor(subj_df, num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button("教科を保存", use_container_width=True):
            conn.update(worksheet="subjects", data=ed_s)
            st.rerun()
            
    with st.expander("📚 教材の管理"):
        updated_m_list = []
        for s in valid_subjects:
            st.write(f"📘 {s}")
            curr_m = mat_df[mat_df["教科名"] == s][["教材名"]]
            ed_m = st.data_editor(curr_m, num_rows="dynamic", key=f"ed_{s}", use_container_width=True, hide_index=True)
            for _, row in ed_m.iterrows():
                if row["教材名"]:
                    updated_m_list.append({"教科名": s, "教材名": row["教材名"]})
        
        if st.button("教材をまとめて保存", use_container_width=True):
            conn.update(worksheet="materials", data=pd.DataFrame(updated_m_list))
            st.rerun()
