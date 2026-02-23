import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# --- スプレッドシート設定 ---
# ⚠️ 自分のスプレッドシートのURLをここに貼り付けてください
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/17dLEGfEtm17PKb2x5lxSzeFmV_t_LBPsMHOZzfuqD4g/edit?usp=sharing"

st.set_page_config(page_title="Study App Pro", layout="centered")

# Googleスプレッドシートへの接続設定
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    return conn.read(spreadsheet=SPREADSHEET_URL, worksheet=name).fillna("")

# データの読み込み
log_df = load_sheet("logs")
subj_df = load_sheet("subjects")
mat_df = load_sheet("materials")

# 有効なリスト作成
valid_subjects = [s for s in subj_df["教科名"].tolist() if s]
cmap = plt.get_cmap('Pastel1')
subj_colors = {s: mcolors.to_hex(cmap(i % cmap.N)) for i, s in enumerate(valid_subjects)}

st.title("🚀 Cloud Study App")

# --- メトリクス表示 ---
today_str = str(datetime.date.today())
df_today = log_df[log_df["日付"] == today_str]
t_today = pd.to_numeric(df_today["時間(分)"], errors='coerce').sum()
t_total = pd.to_numeric(log_df["時間(分)"], errors='coerce').sum()

c1, c2 = st.columns(2)
c1.metric("今日", f"{int(t_today)} min")
c2.metric("合計", f"{int(t_total // 60)}h {int(t_total % 60)}m")

st.divider()

tabs = st.tabs(["📝 記録", "📊 分析", "⚙️ 設定"])

# --- Tab 1: Record ---
with tabs[0]:
    with st.form("record_form"):
        d = st.date_input("日付", datetime.date.today())
        s_choice = st.selectbox("教科", valid_subjects if valid_subjects else ["未登録"])
        m_list = mat_df[mat_df["教科名"] == s_choice]["教材名"].tolist()
        m_choice = st.selectbox("教材", m_list if m_list else ["未登録"])
        t = st.number_input("時間(分)", min_value=0, step=5, value=30)
        c = st.text_input("メモ")
        
        if st.form_submit_button("🚀 保存"):
            new_data = pd.DataFrame([[str(d), s_choice, m_choice, str(t), c]], columns=log_df.columns)
            updated_df = pd.concat([log_df, new_data], ignore_index=True)
            conn.update(spreadsheet=SPREADSHEET_URL, worksheet="logs", data=updated_df)
            st.success("Googleスプレッドシートに保存しました！")
            st.rerun()

# --- Tab 2: Stats ---
with tabs[1]:
    if not log_df.empty:
        log_numeric = log_df.copy()
        log_numeric["時間(分)"] = pd.to_numeric(log_numeric["時間(分)"], errors='coerce')
        sub_sum = log_numeric.groupby("教科")["時間(分)"].sum()
        fig, ax = plt.subplots()
        ax.pie(sub_sum, labels=sub_sum.index, autopct='%1.1f%%', colors=[subj_colors.get(s, "#eee") for s in sub_sum.index])
        st.pyplot(fig)
        
        st.markdown("### 🎞️ 履歴")
        st.dataframe(log_df, use_container_width=True, hide_index=True)

# --- Tab 3: Config ---
with tabs[2]:
    with st.expander("教科の編集"):
        ed_s = st.data_editor(subj_df, num_rows="dynamic", use_container_width=True)
        if st.button("教科を保存"):
            conn.update(spreadsheet=SPREADSHEET_URL, worksheet="subjects", data=ed_s)
            st.rerun()
            
    st.markdown("### 教材の管理")
    updated_m_list = []
    for s in valid_subjects:
        with st.expander(f"📘 {s}"):
            curr_m = mat_df[mat_df["教科名"] == s][["教材名"]]
            ed_m = st.data_editor(curr_m, num_rows="dynamic", key=f"ed_{s}", use_container_width=True)
            for _, row in ed_m.iterrows():
                if row["教材名"]: updated_m_list.append({"教科名": s, "教材名": row["教材名"]})
    
    if st.button("✅ 教材をまとめて保存"):
        conn.update(spreadsheet=SPREADSHEET_URL, worksheet="materials", data=pd.DataFrame(updated_m_list))
        st.rerun()
