import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd
from io import BytesIO
import plotly.express as px

#############################
#     INITIAL SETUP         #
#############################
APP_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(APP_DIR, "data")
DAILY_STATE_DIR = os.path.join(DATA_DIR, "daily_state")
WORKOUTS_DIR = os.path.join(DATA_DIR, "workouts")
PROFILE_PATH = os.path.join(DATA_DIR, "athlete_profile.json")
FIT_SAMPLES_DIR = os.path.join(DATA_DIR, "fit_samples")

os.makedirs(DAILY_STATE_DIR, exist_ok=True)
os.makedirs(WORKOUTS_DIR, exist_ok=True)
os.makedirs(FIT_SAMPLES_DIR, exist_ok=True)


###############################################
# Load/save utilities (NO DUPLICATE CREATION) #
###############################################

def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


def load_daily_state(date_str):
    path = os.path.join(DAILY_STATE_DIR, f"{date_str}.json")
    return load_json(path)


def save_daily_state(date_str, state):
    path = os.path.join(DAILY_STATE_DIR, f"{date_str}.json")
    save_json(path, state)


def save_workout(date_str, workout_data, uploaded_file=None):
    # Pasta dos metadados
    date_dir = os.path.join(WORKOUTS_DIR, date_str)
    os.makedirs(date_dir, exist_ok=True)

    # Pasta para os arquivos .fit
    fit_dir = os.path.join(FIT_SAMPLES_DIR, date_str)
    os.makedirs(fit_dir, exist_ok=True)

    # ID único baseado na quantidade de arquivos existentes
    file_id = len(os.listdir(date_dir)) + 1

    # Salvar JSON de metadados
    meta_path = os.path.join(date_dir, f"workout_{file_id}.json")
    save_json(meta_path, workout_data)

    # Salvar o .fit original (ou tcx, json)
    if uploaded_file is not None:
        ext = uploaded_file.name.split(".")[-1]
        fit_path = os.path.join(fit_dir, f"workout_{file_id}.{ext}")

        with open(fit_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        workout_data["fit_file_path"] = fit_path
        save_json(meta_path, workout_data)



def load_workouts(date_str=None):
    """Load all workouts (optionally filtered by date)."""
    data = []
    for date_folder in os.listdir(WORKOUTS_DIR):
        if date_str and date_folder != date_str:
            continue
        folder_path = os.path.join(WORKOUTS_DIR, date_folder)
        for f in os.listdir(folder_path):
            w = load_json(os.path.join(folder_path, f))
            if w:
                w["date"] = date_folder
                data.append(w)
    return data


########################################
# Athlete Profile (demographics)
########################################

DEFAULT_PROFILE = {
    "age": 34,
    "sex": "female",
    "height_cm": 178,
    "FTP": 190,
    "VO2max_est": 51
}

if not os.path.exists(PROFILE_PATH):
    save_json(PROFILE_PATH, DEFAULT_PROFILE)

athlete_profile = load_json(PROFILE_PATH)


#############################
#         UI LAYOUT         #
#############################

st.set_page_config(page_title="Athlete Daily Logger", layout="wide")
st.title("🏃‍♀️ AthleteOPT Plataform")

tabs = st.tabs(["📁 Treino", "📊 Estado Diário", "📜 Histórico", "📈 Dashboard", "👤 Perfil"])


############################################
# TAB 1 — TREINO (UPLOAD .FIT / .TCX etc.)
############################################
with tabs[0]:
    st.header("📁 Upload de Treino")

    date = st.date_input("Data do treino", datetime.now().date())
    date_str = date.strftime("%Y-%m-%d")

    uploaded = st.file_uploader("Upload do arquivo (.fit, .tcx, .json)", type=["fit", "tcx", "json"])

    training_categories = {
        "Ciclismo": [
            "VO2max",
            "Sweetspot",
            "Endurance / Z2",
            "Tempo",
            "Sprints",
            "Treino Longo",
            "Outro"
        ],
        "Corrida": [
            "Intervalado",
            "Ritmo / Tempo Run",
            "Z2 / Endurance",
            "Longo",
            "Tiros",
            "Regenerativo",
            "Outro"
        ],
        "Natação": [
            "Técnica",
            "Series / Intervalado",
            "Endurance",
            "Sprint",
            "Longo",
            "Outro"
        ],
        "Musculação": [
            "Força",
            "Hipertrofia",
            "Resistência",
            "Treino de Core",
            "Circuito",
            "Outro"
        ],
        "Outros": [
            "Treino Geral",
            "Intervalado",
            "Endurance",
            "Mobilidade",
            "Outro"
        ]
    }

    modality = st.selectbox("Modalidade", list(training_categories.keys()))

    if uploaded:
        st.success("Arquivo recebido!")

        st.subheader("Tipo de sessão")
        session_type = st.selectbox(
            "Tipo de treino",
            training_categories[modality]
        )

        if session_type == "Outro":
            session_type = st.text_input("Descreva o tipo de treino")

        st.subheader("Estrutura da sessão")
        structure = st.text_area(
            "Estrutura (padrões de intervalos, distribuição de intensidade)",
            placeholder="Ex: 5x(3min @120% FTP / 3min Z2)\nOu: 10min warm-up + 2x20min sweetspot / 5min Z2"
        )

        st.subheader("Esforço percebido")
        perceived_exertion = st.slider("RPE (esforço percebido)", 1, 5, 3)

        st.subheader("Nutrição e Hidratação do Treino")
        carbs_session = st.number_input("Carboidratos ingeridos no treino (g)", min_value=0, step=5)
        hydration_session = st.number_input("Hidratação no treino (ml)", min_value=0, step=50)

        if st.button("Salvar treino"):
            workout_data = {
                "session_type": session_type,
                "structure": structure,
                "perceived_exertion": perceived_exertion,
                "file_name": uploaded.name,
                "modality": modality,
                "carbs_session": carbs_session,
                "hydration_session": hydration_session,
            }
            save_workout(date_str, workout_data, uploaded_file=uploaded)
            st.success("Treino salvo sem duplicação!")


############################################
# TAB 2 — ESTADO DIÁRIO
############################################
with tabs[1]:
    st.header("📊 Estado Diário da Atleta")

    date = st.date_input("Data", datetime.now().date())
    date_str = date.strftime("%Y-%m-%d")

    existing_state = load_daily_state(date_str) or {}

    # Util: converter HH:MM → horas float
    def parse_hhmm_to_hours(hhmm_str):
        try:
            h, m = hhmm_str.split(":")
            return int(h) + int(m)/60
        except:
            return None

    # Util: converter horas float → HH:MM
    def hours_to_hhmm(hours):
        if hours is None:
            return "08:00"
        h = int(hours)
        m = int((hours - h) * 60)
        return f"{h:02d}:{m:02d}"

    st.subheader("A. Sono & Repouso")

    sleep_default = existing_state.get("sleep_hours", 8)
    sleep_str = hours_to_hhmm(sleep_default)

    sleep_input = st.text_input("Horas de sono HH e MM)", value=sleep_str)
    sleep_quality = st.slider("Qualidade do sono (1-5)", 1, 5, existing_state.get("sleep_quality", 3))

    st.subheader("B. Estado geral & sintomas")
    muscle_soreness = st.slider("Dor muscular (1-5)", 1, 5, existing_state.get("muscle_soreness", 3))

    st.subheader("C. Estado fisiológico & recuperação")
    fatigue_score = st.slider("Fadiga (1-5)", 1, 5, existing_state.get("fatigue_score", 3))
    mood_score = st.slider("Humor (1-5)", 1, 5, existing_state.get("mood_score", 3))

    st.subheader("D. Metabolia / Glicemia / Nutrição")
    cgm_mean = st.number_input("Glicemia média dia anterior (mg/dL)", min_value=0.0, value=existing_state.get("cgm_mean", 0.0))
    time_in_range = st.number_input("Tempo em faixa dia anterior (%)", 0.0, 100.0, value=existing_state.get("time_in_range", 0.0))
    hypo_events = st.number_input("Eventos de hipo (24h)", 0, value=existing_state.get("hypo_events", 0))

    st.subheader("E. Menstrual / Hormonal")
    cycle_phase = st.selectbox(
        "Fase do ciclo",
        ["unknown", "follicular", "ovulatory", "luteal", "menstrual"],
        index=["unknown","follicular","ovulatory","luteal","menstrual"].index(existing_state.get("cycle_phase", "unknown"))
    )

    if cycle_phase == "menstrual":
        days_since_m_start = st.number_input(
            "Dias desde o início da menstruação",
            min_value=0,
            value=existing_state.get("days_since_menstruation_start", 0),
        )
    else:
        days_since_m_start = None

    hormonal_contraception = st.selectbox(
        "Usa contraceptivo hormonal?",
        ["yes", "no"],
        index=["yes", "no"].index(existing_state.get("hormonal_contraception", "no"))
    )

    symptoms_menstrual = st.selectbox(
        "Sintomas menstruais (intensidade)",
        ["none", "mild", "moderate", "severe"],
        index=["none","mild","moderate","severe"].index(existing_state.get("symptoms_menstrual", "none"))
    )

    # --- F. Estressores & Contexto ---
    st.subheader("F. Estressores & Contexto")

    worked_today = st.radio(
        "Trabalhou hoje?", 
        ["Sim", "Não"],
        index=["Sim","Não"].index(existing_state.get("worked_today", "Não"))
    )

    # Defaults
    work_intensity = None
    work_hours = 0.0
    trip = existing_state.get("trip", False)
    jetlag = existing_state.get("jetlag", False)

    if worked_today == "Sim":
        work_intensity = st.slider(
            "Intensidade do trabalho hoje (1–5)", 
            1, 5, 
            existing_state.get("work_intensity", 3)
        )

        work_hours = st.number_input(
            "Horas trabalhadas hoje",
            0.0, 24.0,
            value=float(existing_state.get("work_hours", 0.0)) if worked_today == "Sim" else 0.0,
            step=0.5
        )

    trip = st.checkbox("Viajou hoje?", value=existing_state.get("trip", False))
    if trip:
        jetlag = st.checkbox("Teve jetlag?", value=existing_state.get("jetlag", False))

    psych_stress = st.slider(
        "Estresse psicológico (1–5)",
        1, 5,
        existing_state.get("psych_stress", 2)
    )
    psych_stress_notes = st.text_area(
        "Quer descrever brevemente o motivo do estresse?",
        value=existing_state.get("psych_stress_notes", "")
    )

    # --- G. Ambiente ---
    st.subheader("G. Ambiente")
    temperature = st.number_input("Temperatura (°C)", value=existing_state.get("temperature", 23.0))
    humidity = st.number_input("Umidade (%)", value=existing_state.get("humidity", 50.0))

    # ----- SAVE BUTTON -----
    if st.button("Salvar estado diário"):
        sleep_hours = parse_hhmm_to_hours(sleep_input)

        daily_state = {
            "sleep_hours": sleep_hours,
            "sleep_quality": sleep_quality,
            "muscle_soreness": muscle_soreness,
            "fatigue_score": fatigue_score,
            "mood_score": mood_score,
            "cgm_mean": cgm_mean,
            "time_in_range": time_in_range,
            "hypo_events": hypo_events,

            # Menstrual
            "cycle_phase": cycle_phase,
            "days_since_menstruation_start": days_since_m_start,
            "hormonal_contraception": hormonal_contraception,
            "symptoms_menstrual": symptoms_menstrual,

            # Trabalho
            "worked_today": worked_today,
            "work_intensity": work_intensity,
            "work_hours": work_hours,
            "trip": trip,
            "jetlag": jetlag,

            # Estresse
            "psych_stress": psych_stress,
            "psych_stress_notes": psych_stress_notes,

            # Ambiente
            "temperature": temperature,
            "humidity": humidity,
        }

        save_daily_state(date_str, daily_state)
        st.success("Estado diário salvo com sucesso!")




############################################
# TAB 3 — HISTÓRICO
############################################
with tabs[2]:
    st.header("📜 Histórico")

    workouts = load_workouts()
    daily_states = sorted(os.listdir(DAILY_STATE_DIR))

    st.subheader("Treinos registrados")
    if workouts:
        df_w = pd.DataFrame(workouts)
        st.dataframe(df_w)
    else:
        st.info("Nenhum treino registrado ainda.")

    st.subheader("Estados diários registrados")
    if daily_states:
        st.write([d.replace(".json", "") for d in daily_states])
    else:
        st.info("Nenhum estado diário registrado.")



############################################
# TAB 4 — PERFIL
############################################
with tabs[3]:
    st.header("📈 Dashboard")

    workouts = load_workouts()

    if workouts:
        df = pd.DataFrame(workouts)

        st.subheader("Arquivos por modalidade")
        st.bar_chart(df["modality"].value_counts())

        st.subheader("Estatísticas por tipo de treino")
        st.write(
            df.groupby("modality")[["perceived_exertion", "carbs_session", "hydration_session"]]
            .agg(['mean', 'std'])
            .dropna(how="any")
            .round(2)
        )
        
        
        # -------------------------------------
        # 1. Carregar estados diários
        # -------------------------------------
        daily_states_files = sorted(os.listdir(DAILY_STATE_DIR))

        daily_records = []
        for f in daily_states_files:
            path = os.path.join(DAILY_STATE_DIR, f)
            data = load_json(path)
            if data:
                data["date"] = pd.to_datetime(f.replace(".json", ""))
                daily_records.append(data)

        df_daily = pd.DataFrame(daily_records)

        if df_daily.empty:
            st.warning("Nenhum estado diário registrado ainda.")
            st.stop()

        df_daily = df_daily.sort_values("date")

        # ---------------------------
        # 2. Filtro de período
        # ---------------------------
        st.subheader("Filtro de período")

        period = st.selectbox(
            "Período",
            ["Últimos 7 dias", "Últimos 30 dias", "Últimos 90 dias", "Todo o período"]
        )

        today = df_daily["date"].max()

        if period == "Últimos 7 dias":
            df_filt = df_daily[df_daily["date"] >= today - pd.Timedelta(days=7)]
        elif period == "Últimos 30 dias":
            df_filt = df_daily[df_daily["date"] >= today - pd.Timedelta(days=30)]
        elif period == "Últimos 90 dias":
            df_filt = df_daily[df_daily["date"] >= today - pd.Timedelta(days=90)]
        else:
            df_filt = df_daily.copy()

        

        # ---------------------------
        # 3. Seleção de métricas
        # ---------------------------
        cols_to_plot = [
            "sleep_hours",
            "sleep_quality",
            "muscle_soreness",
            "fatigue_score",
            "mood_score",
            "cgm_mean",
            "time_in_range",
            "hypo_events",
            "psych_stress"
        ]

        cols_existing = [c for c in cols_to_plot if c in df_filt.columns]
        if df_filt.empty or len(cols_existing) == 0:
            st.warning("Nenhum dado disponível para o período selecionado.")
        else:
            # ---------------------------
            # 4. Cálculo das estatísticas
            # ---------------------------
            stats = df_filt[cols_existing].agg(["mean", "std"]).T
            stats["mean"] = stats["mean"].round(2)
            stats["std"] = stats["std"].round(2)
            stats["n"] = df_filt.shape[0]  # número de dias usados

            #stats = stats.reset_index().rename(columns={"index": "metric"})

            # ---------------------------
            # 5. Gráfico Plotly
            # ---------------------------
            scores_1_5 = [
                "sleep_quality",
                "muscle_soreness",
                "fatigue_score",
                "mood_score",
                "psych_stress"
            ]

            continuous_metrics = [
                "sleep_hours",
                "cgm_mean",
                "time_in_range",
                "hypo_events"
            ]

            # Scores 1–5 (bar chart with error bars)
            stats_scores = stats.loc[scores_1_5].reset_index().rename(columns={"index": "metric"})
            fig_scores = px.bar(
                stats_scores,
                x="metric",
                y="mean",
                error_y="std",
                hover_data=["mean", "std", "n"],
                title=f"Estatísticas do período selecionado ({stats_scores['n'].iloc[0]} dias)"
            )
            st.plotly_chart(fig_scores, use_container_width=True)
            
            # Filter stats to only the metrics we care about
            stats_table = stats.loc[stats.index.intersection(continuous_metrics)].copy()

            # Optional: format nicely
            stats_table = stats_table.rename_axis("Metric").reset_index()
            stats_table["mean"] = stats_table["mean"].round(2)
            stats_table["std"] = stats_table["std"].round(2)

            # Display in Streamlit
            st.subheader("Continuous Metrics Summary")
            st.dataframe(stats_table, use_container_width=True)

    else:
        st.info("Nenhum treino registrado ainda.")


############################################
# TAB 5 — PERFIL
############################################
with tabs[4]:
    st.header("👤 Perfil da Atleta")

    profile = load_json(PROFILE_PATH)

    age = st.number_input("Idade", value=profile["age"])
    sex = st.selectbox("Sexo", ["female", "male"], index=0)
    height = st.number_input("Altura (cm)", value=profile["height_cm"])
    ftp = st.number_input("FTP (W)", value=profile["FTP"])
    vo2 = st.number_input("VO2max estimado", value=profile["VO2max_est"])

    if st.button("Salvar perfil"):
        new_profile = {
            "age": age,
            "sex": sex,
            "height_cm": height,
            "FTP": ftp,
            "VO2max_est": vo2
        }
        save_json(PROFILE_PATH, new_profile)
        st.success("Perfil atualizado!")
