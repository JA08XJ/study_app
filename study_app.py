import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import time

# --- 1. 基本設定 ---
st.set_page_config(page_title="Study App Pro", layout="wide")

# --- 補助関数: 分を「◯時間◯分」に変換（表示用） ---
def format_time(minutes):
    try:
        minutes = int(minutes)
    except:
        return "0分"
    h = minutes // 60
    m = minutes % 60
    if h > 0:
        return f"{h}時間{m}分"
    return f"{m}分"

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
TAR_COLS = ["ユーザー名", "目標時間"]

# 自動リトライ付き安全更新システム
def safe_update(sheet_name, df):
    max_retries = 3
    for i in range(max_retries):
        try:
            conn.update(worksheet=sheet_name, data=df)
            return True
        except Exception as e:
            if i < max_retries - 1:
                time.sleep(1)
                continue
            else:
                st.error(f"🚨 スプレッドシートの更新に失敗しました。\n\nエラー内容: {e}")
                return False

def load_data(sheet_name, expected_cols):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=expected_cols)
        return df.fillna("")
    except:
        return pd.DataFrame(columns=expected_cols)

# データ取得
all_logs = load_data("logs", LOG_COLS)
all_subjs = load_data("subjects", SUB_COLS)
all_mats = load_data("materials", MAT_COLS)
all_tars = load_data("targets", TAR_COLS)

# フィルタリング & 型変換
my_logs = all_logs[all_logs["ユーザー名"].astype(str).str.strip() == user].copy()
my_subjs = all_subjs[all_subjs["ユーザー名"].astype(str).str.strip() == user].copy()
my_mats = all_mats[all_mats["ユーザー名"].astype(str).str.strip() == user].copy()
my_tar_df = all_tars[all_tars["ユーザー名"].astype(str).str.strip() == user].copy()

if not my_logs.empty:
    my_logs["時間(分)"] = pd.to_numeric(my_logs["時間(分)"], errors='coerce').fillna(0)
    my_logs["日付"] = pd.to_datetime(my_logs["日付"]).dt.date

daily_target = 120
if not my_tar_df.empty:
    try: daily_target = int(my_tar_df.iloc[0]["目標時間"])
    except: pass

my_valid_subjs = my_subjs["教科名"].unique().tolist()

# --- 🏆 常に表示される「トップサマリー ＆ 目標ゲージ」 ---
st.title(f"🚀 {user}'s Study Room")

if not my_logs.empty:
    total_m = my_logs["時間(分)"].sum()
    today_m = my_logs[my_logs["日付"] == datetime.date.today()]["時間(分)"].sum()
    count_d = my_logs["日付"].nunique()
    avg_m = total_m / count_d if count_d > 0 else 0
else:
    total_m = today_m = count_d = avg_m = 0

m_col1, m_col2, m_col3, m_col4 = st.columns(4)
m_col1.metric("総学習時間", format_time(total_m))
m_col2.metric("今日の学習", format_time(today_m))
m_col3.metric("1日平均", format_time(avg_m))
m_col4.metric("学習日数", f"{count_d}日")

st.write(f"🎯 **目標達成率 ({format_time(today_m)} / {format_time(daily_target)})**")
progress = min(float(today_m / daily_target), 1.0) if daily_target > 0 else 0.0
st.progress(progress)
st.divider()

# --- 4. メイン画面 (タブ) ---
tabs = st.tabs(["📝 記録", "📊 分析・履歴", "📚 本棚", "⚙️ 設定"])

# --- タブ1: 記録 ---
with tabs[0]:
    st.subheader("✍️ 学習の記録")
    with st.form("record_form", clear_on_submit=True):
        d = st.date_input("日付", datetime.date.today())
        s_choice = st.selectbox("教科", my_valid_subjs if my_valid_subjs else ["本棚から追加してください"])
        filtered_mats = my_mats[my_mats["教科名"] == s_choice]["教材名"].unique().tolist()
        m_choice = st.selectbox("教材", filtered_mats if filtered_mats else ["教材がありません"])
        
        # 【今回の修正箇所】時間と分を分けて入力
        st.write("学習時間")
        col_h, col_m = st.columns(2)
        h_val = col_h.number_input("時間", min_value=0, max_value=24, value=0, step=1)
        m_val = col_m.number_input("分", min_value=0, max_value=59, value=30, step=5)
        
        memo = st.text_input("メモ")
        
        if st.form_submit_button("🚀 記録を保存", use_container_width=True):
            total_input_minutes = (h_val * 60) + m_val
            
            if not my_valid_subjs or not filtered_mats:
                st.error("教科と教材を正しく設定してください")
            elif total_input_minutes == 0:
                st.error("時間を入力してください")
            else:
                new_row = pd.DataFrame([[
                    str(user), 
                    d.strftime("%Y-%m-%d"), 
                    str(s_choice), 
                    str(m_choice), 
                    int(total_input_minutes), 
                    str(memo)
                ]], columns=LOG_COLS)
                if safe_update("logs", pd.concat([all_logs, new_row], ignore_index=True)):
                    st.success(f"保存完了！ ({format_time(total_input_minutes)})")
                    time.sleep(0.5)
                    st.rerun()

# --- タブ2: 分析・履歴 ---
with tabs[1]:
    if not my_logs.empty:
        col_left, col_right = st.columns([1, 1])
        with col_left:
            st.subheader("📊 教科別バランス")
            sub_sum = my_logs.groupby("教科")["時間(分)"].sum()
            fig, ax = plt.subplots()
            ax.pie(sub_sum, labels=sub_sum.index, autopct='%1.1f%%', startangle=90)
            st.pyplot(fig)
        with col_right:
            st.subheader("📋 履歴一覧")
            display_df = my_logs.sort_values(by="日付", ascending=False)
            for idx, row in display_df.iterrows():
                with st.expander(f"📅 {row['日付']} | 🏷️ {row['教科']} ({format_time(row['時間(分)'])})"):
                    st.write(f"**📖 教材**: {row['教材名']}")
                    st.write(f"**📝 メモ**: {row['メモ']}")
    else:
        st.info("データがありません")

# --- タブ3: 本棚 ---
with tabs[2]:
    st.subheader("📚 本棚の管理")
    col_add1, col_add2 = st.columns(2)
    with col_add1:
        with st.expander("➕ 教科を作成"):
            new_s = st.text_input("教科名", key="s_in")
            if st.button("作成"):
                if new_s:
                    new_row = pd.DataFrame([[user, new_s]], columns=SUB_COLS)
                    if safe_update("subjects", pd.concat([all_subjs, new_row], ignore_index=True)): st.rerun()
    with col_add2:
        with st.expander("➕ 教材を登録"):
            target_s = st.selectbox("教科を選択", my_valid_subjs)
            new_m = st.text_input("教材名", key="m_in")
            if st.button("登録"):
                if target_s and new_m:
                    new_row = pd.DataFrame([[user, target_s, new_m]], columns=MAT_COLS)
                    if safe_update("materials", pd.concat([all_mats, new_row], ignore_index=True)): st.rerun()

    st.divider()
    for subj in my_valid_subjs:
        st.markdown(f"#### 🏷️ {subj}")
        mats = my_mats[my_mats["教科名"] == subj]
        for idx, row in mats.iterrows():
            with st.expander(f"📖 {row['教材名']}"):
                edit_name = st.text_input("編集", value=row['教材名'], key=f"edit_{idx}")
                b1, b2 = st.columns(2)
                if b1.button("更新", key=f"upd_{idx}"):
                    all_mats.loc[idx, "教材名"] = edit_name
                    if safe_update("materials", all_mats): st.rerun()
                if b2.button("🗑️ 削除", key=f"del_{idx}"):
                    if safe_update("materials", all_mats.drop(idx)): st.rerun()

# --- タブ4: 設定 ---
with tabs[3]:
    st.subheader("⚙️ 設定")
    nt = st.number_input("1日の目標時間(分)", min_value=1, value=daily_target)
    st.caption(f"現在の設定: {format_time(nt)}")
    if st.button("目標を更新"):
        other_tars = all_tars[all_tars["ユーザー名"].astype(str).str.strip() != user]
        new_row = pd.DataFrame([[user, nt]], columns=TAR_COLS)
        if safe_update("targets", pd.concat([other_tars, new_row], ignore_index=True)):
            st.success("目標を更新しました！")
            st.rerun()

if st.sidebar.button("ログアウト"):
    st.session_state.user = None
    st.rerun()
