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

# 厳格な列定義
LOG_COLS = ["ユーザー名", "日付", "教科", "教材名", "時間(分)", "メモ"]
SUB_COLS = ["ユーザー名", "教科名"]
MAT_COLS = ["ユーザー名", "教科名", "教材名"]

def load_data_strict(sheet_name, expected_cols):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=expected_cols)
        # 既存の列が期待通りかチェックし、足りなければ補完
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        return df[expected_cols].fillna("") # 列順を強制的に固定
    except:
        return pd.DataFrame(columns=expected_cols)

# データの読み込み
all_logs = load_data_strict("logs", LOG_COLS)
all_subjs = load_data_strict("subjects", SUB_COLS)
all_mats = load_data_strict("materials", MAT_COLS)

# ログインユーザーの分だけ抽出
my_logs = all_logs[all_logs["ユーザー名"] == user].copy()
my_subjs = all_subjs[all_subjs["ユーザー名"] == user].copy()
my_mats = all_mats[all_mats["ユーザー名"] == user].copy()

st.title(f"🚀 {user}'s Room")

# --- 4. メイン画面 ---
tabs = st.tabs(["📝 記録", "📊 分析", "⚙️ 設定"])

with tabs[0]:
    st.subheader("✍️ 今日の学習")
    valid_subjs = my_subjs["教科名"].unique().tolist()
    
    with st.form("record_form", clear_on_submit=True):
        d = st.date_input("日付", datetime.date.today())
        s_choice = st.selectbox("教科", valid_subjs if valid_subjs else ["設定から追加してください"])
        
        m_list = my_mats[my_mats["教科名"] == s_choice]["教材名"].tolist()
        m_choice = st.selectbox("教材", m_list if m_list else ["設定から追加してください"])
        
        t = st.number_input("時間(分)", min_value=0, step=5, value=30)
        memo = st.text_input("メモ")
        
        if st.form_submit_button("🚀 記録を保存", use_container_width=True):
            new_row = pd.DataFrame([[user, str(d), s_choice, m_choice, int(t), memo]], columns=LOG_COLS)
            conn.update(worksheet="logs", data=pd.concat([all_logs, new_row], ignore_index=True))
            st.success("保存完了！")
            st.rerun()

with tabs[1]:
    st.subheader("📊 学習データ")
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

with tabs[2]:
    st.subheader("⚙️ 専用設定")
    
    # 教科設定
    st.write("📘 教科の追加・編集")
    ed_s = st.data_editor(my_subjs[["教科名"]], num_rows="dynamic", use_container_width=True, key="ed_s")
    if st.button("教科を保存"):
        new_s = ed_s.dropna(subset=["教科名"])
        new_s["ユーザー名"] = user
        other_s = all_subjs[all_subjs["ユーザー名"] != user]
        # 保存前に列順を確実に固定
        final_s = pd.concat([other_s, new_s], ignore_index=True)[SUB_COLS]
        conn.update(worksheet="subjects", data=final_s)
        st.success("保存しました")
        st.rerun()

    st.divider()

    # 教材設定
    st.write("📚 教材の追加・編集")
    ed_m = st.data_editor(my_mats[["教科名", "教材名"]], num_rows="dynamic", use_container_width=True, key="ed_m")
    if st.button("教材を保存"):
        new_m = ed_m.dropna(subset=["教科名", "教材名"])
        new_m["ユーザー名"] = user
        other_m = all_mats[all_mats["ユーザー名"] != user]
        final_m = pd.concat([other_m, new_m], ignore_index=True)[MAT_COLS]
        conn.update(worksheet="materials", data=final_m)
        st.success("保存しました")
        st.rerun()

if st.sidebar.button("ログアウト"):
    st.session_state.user = None
    st.rerun()
