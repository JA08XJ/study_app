import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import time  # 再試行時の待機用に追加

# --- 1. 基本設定 ---
st.set_page_config(page_title="Study App Pro", layout="wide")

# --- 補助関数: 分を「◯時間◯分」に変換 ---
def format_time(minutes):
    try:
        minutes = int(minutes)
    except:
        return "0分"
    h = minutes // 60
    m = minutes % 60
    return f"{h}時間{m}分" if h > 0 else f"{m}分"

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

# --- 🚨 強化版: 自動リトライ付き安全更新システム ---
def safe_update(sheet_name, df):
    """
    通信エラー時に最大3回まで自動で再試行します。
    """
    max_retries = 3
    for i in range(max_retries):
        try:
            # 空白を除去し、型を整理して送信（スマホエラー対策）
            df_to_save = df.copy()
            # 更新実行
            conn.update(worksheet=sheet_name, data=df_to_save)
            return True
        except Exception as e:
            if i < max_retries - 1:
                time.sleep(1) # 1秒待って再試行
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

# フィルタリング
my_logs = all_logs[all_logs["ユーザー名"].astype(str).str.strip() == user].copy()
my_subjs = all_subjs[all_subjs["ユーザー名"].astype(str).str.strip() == user].copy()
my_mats = all_mats[all_mats["ユーザー名"].astype(str).str.strip() == user].copy()
my_tar_df = all_tars[all_tars["ユーザー名"].astype(str).str.strip() == user].copy()

# 型変換
if not my_logs.empty:
    my_logs["時間(分)"] = pd.to_numeric(my_logs["時間(分)"], errors='coerce').fillna(0)
    my_logs["日付"] = pd.to_datetime(my_logs["日付"]).dt.date

daily_target = 120
if not my_tar_df.empty:
    try: daily_target = int(my_tar_df.iloc[0]["目標時間"])
    except: pass

my_valid_subjs = my_subjs["教科名"].unique().tolist()

# --- 🏆 サマリー表示 ---
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

# --- 4. タブ ---
tabs = st.tabs(["📝 記録", "📊 分析・履歴", "📚 本棚", "⚙️ 設定"])

# --- タブ1: 記録 ---
with tabs[0]:
    st.subheader("✍️ 学習の記録")
    with st.form("record_form", clear_on_submit=True):
        d = st.date_input("日付", datetime.date.today())
        s_choice = st.selectbox("教科", my_valid_subjs if my_valid_subjs else ["本棚で教科を追加してください"])
        filtered_mats = my_mats[my_mats["教科名"] == s_choice]["教材名"].unique().tolist()
        m_choice = st.selectbox("教材", filtered_mats if filtered_mats else ["教材がありません"])
        t = st.number_input("時間(分)", min_value=0, step=5, value=30)
        memo = st.text_input("メモ")
        
        if st.form_submit_button("🚀 記録を保存", use_container_width=True):
            if not my_valid_
