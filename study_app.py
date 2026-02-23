import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import matplotlib.pyplot as plt

# --- A. 基本設定 ---
st.set_page_config(page_title="Study App Pro", layout="centered")

# --- B. ログイン機能 ---
if 'user' not in st.session_state:
    st.session_state.user = None

def login():
    st.title("🔐 Study App Login")
    u_input = st.text_input("ユーザー名", key="login_user")
    p_input = st.text_input("パスワード", type="password", key="login_pw")
    if st.button("ログイン", use_container_width=True, type="primary"):
        if "passwords" in st.secrets and u_input in st.secrets["passwords"]:
            if str(p_input) == str(st.secrets["passwords"][u_input]):
                st.session_state.user = u_input
                st.rerun()
            else:
                st.error("パスワードが違います")
        else:
            st.error("ユーザー名が見つかりません")

if st.session_state.user is None:
    login()
    st.stop()

# --- C. データ連携 (Google Sheets) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_read(sheet_name, default_cols):
    try:
        # 400エラー回避のため、一旦データ全体を読み込む
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=default_cols)
        return df.fillna("")
    except:
        # シートが空、または読み込みエラー時は空の枠組みを返す
        return pd.DataFrame(columns=default_cols)

# 期待される列名
LOG_COLS = ["ユーザー名", "日付", "教科", "教材名", "時間(分)", "メモ"]
SUB_COLS = ["教科名"]
MAT_COLS = ["教科名", "教材名"]

try:
    all_logs = safe_read("logs", LOG_COLS)
    subj_df = safe_read("subjects", SUB_COLS)
    mat_df = safe_read("materials", MAT_COLS)
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

user = st.session_state.user
# 自分のデータのみ抽出
if not all_logs.empty and "ユーザー名" in all_logs.columns:
    log_df = all_logs[all_logs["ユーザー名"] == user].copy()
else:
    log_df = pd.DataFrame(columns=LOG_COLS)

valid_subjects = subj_df["教科名"].dropna().tolist() if not subj_df.empty else []

st.title(f"🚀 {user}'s Study Room")

# --- D. メイン画面 ---
tabs = st.tabs(["📝 記録", "📊 分析", "⚙️ 設定"])

with tabs[0]:
    st.subheader("✍️ 学習の記録")
    with st.form("record_form", clear_on_submit=True):
        d = st.date_input("日付", datetime.date.today())
        s_choice = st.selectbox("教科", valid_subjects if valid_subjects else ["未登録"])
        
        m_list = []
        if not mat_df.empty and "教科名" in mat_df.columns:
            m_list = mat_df[mat_df["教科名"] == s_choice]["教材名"].tolist()
        m_choice = st.selectbox("教材", m_list if m_list else ["未登録"])
        
        t = st.number_input("時間(分)", min_value=0, step=5, value=30)
        c = st.text_input("メモ")
        
        if st.form_submit_button("🚀 記録を保存", use_container_width=True):
            # 常に期待される列順でデータを作成
            new_row = pd.DataFrame([[user, str(d), s_choice, m_choice, int(t), c]], columns=LOG_COLS)
            # 既存データが空の場合でも対応
            updated_logs = pd.concat([all_logs if not all_logs.empty else pd.DataFrame(columns=LOG_COLS), new_row], ignore_index=True)
            conn.update(worksheet="logs", data=updated_logs)
            st.success("保存しました！")
            st.rerun()

with tabs[1]:
    st.subheader("📊 学習データ")
    if not log_df.empty and "時間(分)" in log_df.columns:
        log_numeric = log_df.copy()
        log_numeric["時間(分)"] = pd.to_numeric(log_numeric["時間(分)"], errors='coerce')
        sub_sum = log_numeric.groupby("教科")["時間(分)"].sum()
        if not sub_sum.empty:
            fig, ax = plt.subplots()
            ax.pie(sub_sum, labels=sub_sum.index, autopct='%1.1f%%', startangle=90)
            st.pyplot(fig)
        st.dataframe(log_df.drop(columns=["ユーザー名"], errors="ignore"), use_container_width=True, hide_index=True)
    else:
        st.info("まだ記録がありません。")

with tabs[2]:
    st.subheader("⚙️ 教科・教材の管理")
    st.write("📘 教科の編集")
    new_subj = st.data_editor(subj_df if not subj_df.empty else pd.DataFrame(columns=SUB_COLS), num_rows="dynamic", use_container_width=True, key="ed_s")
    if st.button("教科を保存"):
        conn.update(worksheet="subjects", data=new_subj)
        st.rerun()

    st.write("📚 教材の編集")
    new_mat = st.data_editor(mat_df if not mat_df.empty else pd.DataFrame(columns=MAT_COLS), num_rows="dynamic", use_container_width=True, key="ed_m")
    if st.button("教材を保存"):
        conn.update(worksheet="materials", data=new_mat)
        st.rerun()

if st.sidebar.button("ログアウト"):
    st.session_state.user = None
    st.rerun()
    
