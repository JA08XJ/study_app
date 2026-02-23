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

# --- 3. データ連携 ---
user = st.session_state.user
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name, default_cols):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=default_cols)
        df.columns = [c.strip() for c in df.columns]
        return df.fillna("")
    except:
        return pd.DataFrame(columns=default_cols)

LOG_COLS = ["ユーザー名", "日付", "教科", "教材名", "時間(分)", "メモ"]
SUB_COLS = ["ユーザー名", "教科名"]
MAT_COLS = ["ユーザー名", "教科名", "教材名"]

# 全データ読み込み
all_logs = load_data("logs", LOG_COLS)
all_subjects = load_data("subjects", SUB_COLS)
all_materials = load_data("materials", MAT_COLS)

# ログインユーザーのデータのみに絞り込み
my_logs = all_logs[all_logs["ユーザー名"] == user].copy()
my_subjects = all_subjects[all_subjects["ユーザー名"] == user].copy()
my_materials = all_materials[all_materials["ユーザー名"] == user].copy()

valid_subject_list = my_subjects["教科名"].unique().tolist()

st.title(f"🚀 {user}'s Study Room")

# --- 4. メイン画面 ---
tabs = st.tabs(["📝 記録", "📊 分析", "⚙️ 設定"])

# --- タブ1: 記録 ---
with tabs[0]:
    st.subheader("✍️ 今日の学習")
    with st.form("record_form", clear_on_submit=True):
        d = st.date_input("日付", datetime.date.today())
        s_choice = st.selectbox("教科", valid_subject_list if valid_subject_list else ["未登録"])
        
        m_list = my_materials[my_materials["教科名"] == s_choice]["教材名"].tolist()
        m_choice = st.selectbox("教材", m_list if m_list else ["未登録"])
        
        t = st.number_input("時間(分)", min_value=0, step=5, value=30)
        c = st.text_input("メモ")
        
        if st.form_submit_button("🚀 記録を保存", use_container_width=True):
            new_row = pd.DataFrame([[user, str(d), s_choice, m_choice, int(t), c]], columns=LOG_COLS)
            # 全データに新しい行を加えて更新
            updated_all_logs = pd.concat([all_logs, new_row], ignore_index=True)
            conn.update(worksheet="logs", data=updated_all_logs)
            st.success("保存しました！")
            st.rerun()

# --- タブ2: 分析 ---
with tabs[1]:
    st.subheader("📊 学習データ")
    if not my_logs.empty:
        log_numeric = my_logs.copy()
        log_numeric["時間(分)"] = pd.to_numeric(log_numeric["時間(分)"], errors='coerce')
        sub_sum = log_numeric.groupby("教科")["時間(分)"].sum()
        if not sub_sum.empty:
            fig, ax = plt.subplots()
            ax.pie(sub_sum, labels=sub_sum.index, autopct='%1.1f%%', startangle=90)
            st.pyplot(fig)
        st.dataframe(my_logs.drop(columns=["ユーザー名"]), use_container_width=True, hide_index=True)
    else:
        st.info("データがありません。")

# --- タブ3: 設定 ---
with tabs[2]:
    st.subheader("⚙️ 自分専用の設定")
    
    # 教科の編集
    st.write("📘 教科の追加・編集")
    # ユーザーに見せるのは「教科名」のみだが、保存時は「ユーザー名」を付与する
    ed_s = st.data_editor(my_subjects[["教科名"]], num_rows="dynamic", use_container_width=True, key="ed_s")
    if st.button("教科を保存"):
        # 編集後のデータにユーザー名を付け直す
        new_my_subjects = ed_s.dropna(subset=["教科名"])
        new_my_subjects["ユーザー名"] = user
        # 他人のデータを消さないように、一旦自分の分以外と合体させて保存
        others_subjects = all_subjects[all_subjects["ユーザー名"] != user]
        updated_all_subjects = pd.concat([others_subjects, new_my_subjects], ignore_index=True)
        conn.update(worksheet="subjects", data=updated_all_subjects)
        st.success("教科を更新しました")
        st.rerun()

    st.divider()

    # 教材の編集
    st.write("📚 教材の追加・編集")
    ed_m = st.data_editor(my_materials[["教科名", "教材名"]], num_rows="dynamic", use_container_width=True, key="ed_m")
    if st.button("教材を保存"):
        new_my_materials = ed_m.dropna(subset=["教科名", "教材名"])
        new_my_materials["ユーザー名"] = user
        others_materials = all_materials[all_materials["ユーザー名"] != user]
        updated_all_materials = pd.concat([others_materials, new_my_materials], ignore_index=True)
        conn.update(worksheet="materials", data=updated_all_materials)
        st.success("教材を更新しました")
        st.rerun()

# --- 5. サイドバー ---
with st.sidebar:
    st.write(f"👤 ログイン中: {user}")
    if st.button("ログアウト"):
        st.session_state.user = None
        st.rerun()
