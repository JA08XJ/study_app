import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import matplotlib.pyplot as plt

# --- 1. 基本設定 ---
st.set_page_config(page_title="Study App Pro", layout="centered")

# --- 2. ログイン機能 ---
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

# --- 3. データ連携設定 ---
user = st.session_state.user
conn = st.connection("gsheets", type=GSheetsConnection)

LOG_COLS = ["ユーザー名", "日付", "教科", "教材名", "時間(分)", "メモ"]
SUB_COLS = ["ユーザー名", "教科名"]
MAT_COLS = ["ユーザー名", "教科名", "教材名"]

# データ読み込み（ここは既存の方法でOK）
def load_data(sheet_name, expected_cols):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=expected_cols)
        return df.fillna("")
    except:
        return pd.DataFrame(columns=expected_cols)

all_logs = load_data("logs", LOG_COLS)
all_subjs = load_data("subjects", SUB_COLS)
all_mats = load_data("materials", MAT_COLS)

# ログインユーザーのデータのみ抽出
my_logs = all_logs[all_logs["ユーザー名"] == user].copy()
my_subjs = all_subjs[all_subjs["ユーザー名"] == user].copy()
my_mats = all_mats[all_mats["ユーザー名"] == user].copy()
my_valid_subjs = my_subjs["教科名"].unique().tolist()

st.title(f"🚀 {user}'s Room")

# --- 4. メイン画面 ---
tabs = st.tabs(["📝 記録", "📊 分析", "⚙️ 設定"])

# --- 記録タブ ---
with tabs[0]:
    st.subheader("✍️ 学習の記録")
    with st.form("record_form", clear_on_submit=True):
        d = st.date_input("日付", datetime.date.today())
        s_choice = st.selectbox("教科", my_valid_subjs if my_valid_subjs else ["設定から追加してください"])
        
        filtered_mats = my_mats[my_mats["教科名"] == s_choice]["教材名"].unique().tolist()
        m_choice = st.selectbox("教材", filtered_mats if filtered_mats else ["教材がありません"])
        
        t = st.number_input("時間(分)", min_value=0, step=5, value=30)
        memo = st.text_input("メモ")
        
        if st.form_submit_button("🚀 記録を保存"):
            if not my_valid_subjs or not filtered_mats:
                st.error("教科と教材を正しく設定してください")
            else:
                new_row = pd.DataFrame([[user, str(d), s_choice, m_choice, int(t), memo]], columns=LOG_COLS)
                # 既存データと合体させて上書き
                conn.update(worksheet="logs", data=pd.concat([all_logs, new_row], ignore_index=True))
                st.success("保存完了！")
                st.rerun()

# --- 分析タブ ---
with tabs[1]:
    st.subheader("📊 分析")
    if not my_logs.empty:
        my_logs["時間(分)"] = pd.to_numeric(my_logs["時間(分)"], errors='coerce')
        sub_sum = my_logs.groupby("教科")["時間(分)"].sum()
        if not sub_sum.empty:
            fig, ax = plt.subplots()
            ax.pie(sub_sum, labels=sub_sum.index, autopct='%1.1f%%', startangle=90)
            st.pyplot(fig)
        st.dataframe(my_logs.drop(columns=["ユーザー名"]), use_container_width=True, hide_index=True)
    else:
        st.info("データがありません。")

# --- 設定タブ (エンターキー問題を完全解消) ---
with tabs[2]:
    st.subheader("⚙️ 専用設定")
    
    # 教科の追加
    st.write("📘 教科の追加")
    new_s_name = st.text_input("新しい教科名を入力", key="s_input")
    if st.button("教科を保存"):
        if new_s_name:
            new_s_df = pd.DataFrame([[user, new_s_name]], columns=SUB_COLS)
            # 他人のデータを守りつつ自分のデータを追加して更新
            combined_subjs = pd.concat([all_subjs, new_s_df], ignore_index=True)
            conn.update(worksheet="subjects", data=combined_subjs)
            st.success(f"{new_s_name} を登録しました！")
            st.rerun()

    st.divider()

    # 教材の追加
    st.write("📚 教材の追加")
    target_s = st.selectbox("どの教科の教材？", my_valid_subjs if my_valid_subjs else ["先に教科を登録してください"])
    new_m_name = st.text_input("新しい教材名を入力", key="m_input")
    if st.button("教材を保存"):
        if target_s and new_m_name and target_s != "先に教科を登録してください":
            new_m_df = pd.DataFrame([[user, target_s, new_m_name]], columns=MAT_COLS)
            combined_mats = pd.concat([all_mats, new_m_df], ignore_index=True)
            conn.update(worksheet="materials", data=combined_mats)
            st.success(f"{new_m_name} を登録しました！")
            st.rerun()

if st.sidebar.button("ログアウト"):
    st.session_state.user = None
    st.rerun()
