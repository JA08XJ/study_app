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

# --- 画面構成 ---
st.set_page_config(page_title="Study Analytics Pro", layout="wide")
st.title("🚀 Study Analytics Pro")

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
# 🌟 TOP: 4 Metrics
# ==========================================
today_str = str(datetime.date.today())
df_today = log_df[log_df["日付"] == today_str] if not log_df.empty else pd.DataFrame()

col1, col2, col3, col4 = st.columns(4)
with col1:
    t_today = pd.to_numeric(df_today["時間(分)"], errors='coerce').sum() if not df_today.empty else 0
    st.metric("Today's Study", f"{int(t_today)} min")
with col2:
    t_total = pd.to_numeric(log_df["時間(分)"], errors='coerce').sum() if not log_df.empty else 0
    st.metric("Total Time", f"{int(t_total // 60)}h {int(t_total % 60)}m")
with col3:
    streak = len(log_df["日付"].unique()) if not log_df.empty else 0
    st.metric("Study Days", f"{streak} days")
with col4:
    avg = round(t_total / streak) if streak > 0 else 0
    st.metric("Daily Average", f"{int(avg)} min")

st.divider()

# ==========================================
# Main Tabs
# ==========================================
tabs = st.tabs(["📝 Record", "📊 Stats", "🎞️ History", "⚙️ Config"])

# --- Tab 1: Record ---
with tabs[0]:
    col_in, _ = st.columns([1, 1])
    with col_in:
        st.subheader("✍️ Quick Record")
        d = st.date_input("Date", datetime.date.today())
        s_choice = st.selectbox("Subject (教科)", valid_subjects if valid_subjects else ["No Data"])
        m_list = [m for m in st.session_state.mat_df[st.session_state.mat_df["教科名"] == s_choice]["教材名"].tolist() if m and m.strip()]
        m_choice = st.selectbox("Material (教材)", m_list if m_list else ["No Data"])
        t = st.number_input("Time (min)", min_value=0, step=5, value=30)
        c = st.text_input("Comment")
        if st.button("🚀 Save Record", use_container_width=True):
            new_log = pd.DataFrame([[str(d), s_choice, m_choice, str(t), c]], columns=["日付", "教科", "教材名", "時間(分)", "メモ"])
            save_csv(pd.concat([log_df, new_log], ignore_index=True), STUDY_FILE)
            st.balloons()
            st.rerun()

# --- Tab 2: Stats ---
with tabs[1]:
    if not log_df.empty:
        c1, c2 = st.columns(2)
        log_numeric = log_df.copy()
        log_numeric["時間(分)"] = pd.to_numeric(log_numeric["時間(分)"], errors='coerce')
        with c1:
            st.subheader("🍕 Subject Balance")
            sub_sum = log_numeric.groupby("教科")["時間(分)"].sum()
            fig, ax = plt.subplots()
            pie_colors = [subj_colors.get(subj, '#cccccc') for subj in sub_sum.index]
            ax.pie(sub_sum, labels=sub_sum.index, autopct='%1.1f%%', startangle=90, colors=pie_colors)
            st.pyplot(fig)
        with c2:
            st.subheader("📈 Study Trend")
            log_numeric['date_dt'] = pd.to_datetime(log_numeric['日付'])
            trend = log_numeric.groupby('date_dt')['時間(分)'].sum().reset_index().tail(7)
            st.line_chart(trend.set_index('date_dt'))

# --- Tab 3: History ---
with tabs[2]:
    st.subheader("🎞️ History Editor")
    if not log_df.empty:
        def highlight_row(row):
            color = subj_colors.get(row["教科"], "")
            return [f"background-color: {color}; color: black;"] * len(row) if color else [""] * len(row)
        styled_log = log_df.style.apply(highlight_row, axis=1)
        edited_log = st.data_editor(styled_log, num_rows="dynamic", use_container_width=True, key="log_edit_main")
        if st.button("Update History"):
            save_csv(edited_log, STUDY_FILE)
            st.rerun()

# --- Tab 4: Config (教科は上に小さく、教材を下に広く) ---
with tabs[3]:
    st.subheader("⚙️ Configuration")
    
    # 1. Subjects (教科設定) - あまり重要ではないので折りたたみ形式に
    with st.expander("🛠️ 1. 教科名の編集 (Subject Setup)", expanded=False):
        st.caption("教科を追加・削除したいときだけここを開いてください。")
        edited_s = st.data_editor(
            st.session_state.subj_df, 
            num_rows="dynamic", 
            key="s_config_table", 
            use_container_width=True
        )
        if st.button("Save Subjects"):
            save_csv(edited_s, SUBJECTS_FILE)
            st.session_state.subj_df = load_csv(SUBJECTS_FILE, ["教科名"])
            st.rerun()

    st.markdown("---")

    # 2. Materials (教材管理) - こちらをメインにドーンと表示
    st.markdown("### 📚 2. 教材の管理 (Materials Management)")
    if not valid_subjects:
        st.info("上の「教科名の編集」パネルを開いて、教科を登録してください。")
    else:
        updated_all_m = []
        # 各教科の教材エディタを並べる
        for s in valid_subjects:
            with st.expander(f"📘 {s} の教材", expanded=True):
                current_m = st.session_state.mat_df[st.session_state.mat_df["教科名"] == s][["教材名"]]
                edited_m = st.data_editor(
                    current_m, 
                    num_rows="dynamic", 
                    key=f"editor_{s}", 
                    use_container_width=True,
                    column_config={"教材名": st.column_config.TextColumn("教材名を入力")}
                )
                for _, row in edited_m.iterrows():
                    m_name = str(row["教材名"]).strip()
                    if m_name:
                        updated_all_m.append({"教科名": s, "教材名": m_name})
        
        st.markdown(" ") # 少しスペース
        if st.button("✅ 教材の変更をまとめて保存", use_container_width=True, type="primary"):
            new_mat_df = pd.DataFrame(updated_all_m, columns=["教科名", "教材名"])
            save_csv(new_mat_df, MATERIALS_FILE)
            st.session_state.mat_df = load_csv(MATERIALS_FILE, ["教科名", "教材名"])
            st.success("全ての教材を更新しました！")
            st.rerun()