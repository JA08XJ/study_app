import streamlit as st
import pandas as pd
import os
import datetime
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# --- ファイル設定 ---
STUDY_FILE = "study_data.csv"
MATERIALS_FILE = "materials_list.csv"
SUBJECTS_FILE = "subjects_list.csv"

def load_csv(file, cols):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file, dtype=str, encoding='utf-8')
            for col in cols:
                if col not in df.columns:
                    df[col] = ""
            df = df.replace(["0", "None", "nan", "NaN"], "")
            return df[cols].fillna("")
        except:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_csv(df, file):
    df = df.replace(["0", "None", "nan", "NaN"], "")
    df = df[df.iloc[:, 0] != ""] 
    df.to_csv(file, index=False, encoding='utf-8')

# --- カラー生成 ---
def get_subject_colors(subjects):
    cmap = plt.get_cmap('Pastel1')
    colors = {}
    for i, s in enumerate(subjects):
        colors[s] = mcolors.to_hex(cmap(i % cmap.N))
    return colors

# --- 画面構成 (スマホ向けに centered レイアウトに変更) ---
st.set_page_config(page_title="Study App", layout="centered", initial_sidebar_state="collapsed")

# スマホ向けに文字サイズや余白を少し調整するCSS
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #eee; text-align: center;}
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Study App")

# データの読み込み
if 'subj_df' not in st.session_state:
    st.session_state.subj_df = load_csv(SUBJECTS_FILE, ["教科名"])
if 'mat_df' not in st.session_state:
    st.session_state.mat_df = load_csv(MATERIALS_FILE, ["教科名", "教材名"])

log_df = load_csv(STUDY_FILE, ["日付", "教科", "教材名", "時間(分)", "メモ"])

# 有効な教科リストとカラー
valid_subjects = [s for s in st.session_state.subj_df["教科名"].tolist() if s and s.strip()]
subj_colors = get_subject_colors(valid_subjects)

# ==========================================
# 🌟 TOP: Metrics (スマホ用に 2x2 のグリッド配置)
# ==========================================
today_str = str(datetime.date.today())
df_today = log_df[log_df["日付"] == today_str] if not log_df.empty else pd.DataFrame()

t_today = pd.to_numeric(df_today["時間(分)"], errors='coerce').sum() if not df_today.empty else 0
t_total = pd.to_numeric(log_df["時間(分)"], errors='coerce').sum() if not log_