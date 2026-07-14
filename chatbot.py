import streamlit as st
import pandas as pd
import random
import joblib
import re
import os
import uuid
import base64
import time
import sqlite3
from datetime import datetime
DEBUG_MODE = True 

def init_db():

    conn = sqlite3.connect(
        "braveeve.db"
    )

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS responses (

        session_id TEXT,
        timestamp TEXT,
        name TEXT,
        distress_score INTEGER,
        question_number INTEGER,
        category TEXT,
        problem_item TEXT,
        answer TEXT,
        response_source TEXT,
        free_text TEXT,
        completed_at TEXT,
        session_duration_seconds REAL,
        session_duration_minutes REAL,

        UNIQUE(
            session_id,
            question_number
        )

)
    """)

    conn.commit()
    conn.close()

QUESTION_MASCOTS = {

    "Pain": "BraveEve_check_in",
    "Sleep": "BraveEve_deep_breath",
    "Tobacco use": "BraveEve_pointing_up",

    "Memory/Concentration": "BraveEve_thoughtful",
    "Sexual health": "holding_heart",
    "Loss or change of physical abilities": "BraveEve_encouraging",

    "Worry/Anxiety": "BraveEve_thoughtful",
    "Sadness/Depression": "holding_heart",
    "Loss of interest or enjoyment": "BraveEve_encouraging",
    "Grief or loss": "holding_heart",
    "Loneliness": "BraveEve_hearts",
    "Anger": "BraveEve_deep_breath",
    "Changes in appearance": "BraveEve_hearts",
    "Feelings of worthlessness or being a burden": "holding_heart",

    "Relationship with Spouse/Partner": "holding_heart",
    "Relationship with children": "BraveEve_hearts",
    "Relationship with Friends/Coworkers": "BraveEve_hearts",

    "Ability to have children": "holding_heart",
    "Prejudice or discrimination": "BraveEve_encouraging",

    "Taking care of myself": "BraveEve_check_in",
    "Taking care of others": "BraveEve_hearts",
    "Safety": "BraveEve_pointing_up",

    "Work": "BraveEve_encouraging",
    "School": "BraveEve_encouraging",
    "Housing/Utilities": "BraveEve_thoughtful",
    "Finances": "BraveEve_thoughtful",
    "Transportation": "BraveEve_pointing_up",
    "Child care": "BraveEve_hearts",
    "Having enough food": "BraveEve_check_in",
    "Access to medicine": "BraveEve_pointing_up",
    "Treatment decisions": "BraveEve_pointing_up",

    "Sense of meaning or purpose": "BraveEve_proud",
    "Death, dying, or afterlife": "holding_heart",
    "Relationship with the sacred": "BraveEve_proud",
    "Ritual or dietary needs": "BraveEve_proud"
}

QUESTION_LAYOUT = {

    "Pain": "top",
    "Sleep": "bottom_left",
    "Fatigue": "top",

    "Memory/Concentration": "bottom_right",

    "Worry/Anxiety": "bottom_left",
    "Sadness/Depression": "bottom_right",
    "Fear": "bottom_left",
    "Anger": "bottom_left",

    "Relationship with children": "bottom_right",
    "Relationship with family members": "bottom_right",

    "Work": "top",
    "Insurance": "top",
    "Transportation": "top",

    "Treatment decisions": "category",

    "Sense of meaning or purpose": "category",
    "Changes in faith or beliefs": "category",
    "Death, dying, or afterlife": "bottom_right"

}

def show_braveeve_card(
    text,
    mascot,
    title=None,
    side="right",
    width=110,
    top_offset=-15,
    card_color="#FFFFFF"
):
        
    with open(f"images/{mascot}.png", "rb") as f:
        img = base64.b64encode(f.read()).decode()

    if side == "right":

        mascot_html = f"""
        <img src="data:image/png;base64,{img}"
        style="
            position:absolute;
            top:{top_offset}px;
            right:10px;
            width:{width}px;
        ">
        """

        padding = f"padding-right:{width}px;"

    else:

        mascot_html = f"""
        <img src="data:image/png;base64,{img}"
        style="
            position:absolute;
            top:{top_offset}px;
            left:10px;
            width:{width}px;
        ">
        """

        padding = f"padding-left:{width}px;"

    title_html = ""

    if title:

        title_html = f"""
        <h2 style="
            color:#C85A84;
            margin-top:0;
            margin-bottom:15px;
        ">
            {title}
        </h2>
        """

    st.markdown(
        f"""
        <div style="
            position:relative;
            background:{card_color};
            padding:25px;
            border-radius:18px;
            box-shadow:0 2px 8px rgba(0,0,0,0.08);
            margin-bottom:20px;
            overflow:visible;
        ">

        {mascot_html}

        {title_html}

        <div style="
            font-size:18px;
            line-height:1.6;
            color:#333333;
            {padding}
        ">
            {text}
        </div>

        </div>
        """,
        unsafe_allow_html=True
    )

def mascot_html(name):

    with open(f"images/{name}.png", "rb") as f:
        img = base64.b64encode(f.read()).decode()

    return img

def show_mascot(
    name,
    width=40,
    align="center"
):

    img = mascot_html(name)

    st.markdown(
        f"""
        <div style="text-align:{align}; margin:8px 0;">
            <img src="data:image/png;base64,{img}"
                 width="{width}">
        </div>
        """,
        unsafe_allow_html=True
    )

# =========================================================
# PAGE CONFIG
# =========================================================

def get_base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()
daisy = get_base64("images/daisy.png")
bud = get_base64("images/bud.png")

def scroll_to_top():
    st.components.v1.html(
        """
        <script>
            window.parent.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        </script>
        """,
        height=0,
    )

st.set_page_config(
    page_title="BraveEve – Distress Check-in",
    page_icon="🌸",
    layout="centered"
)

st.markdown(
    f"""
    <style>

    /* Increase general text size */
    p, li, label, div {{
        font-size: 18px !important;
    }}

    /* Question text */
    .stMarkdown {{
        font-size: 18px !important;
    }}

    /* Radio buttons */
    div[role="radiogroup"] label {{
        font-size: 18px !important;
    }}

    /* Buttons */
    .stButton > button {{
        background-color: #C85A84 !important;
        color: white !important;
        border-radius: 12px;
        border: none;
        font-weight: 600;
        min-height: 50px;
    }}

    .stButton > button:hover {{
        background-color: #B04A72 !important;
        color: white !important;
    }}

    /* Card */
    .card {{
        background-color: white;
        padding: 20px;
        border-radius: 18px;
        border: 1px solid #F2D8E2;
        box-shadow: 0px 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }}

    /* Text area */
    textarea {{
        font-size: 18px !important;
    }}

    /* Text input */
    input {{
        font-size: 18px !important;
    }}

    /* LEFT SIDE BACKGROUND ELEMENTS */
    .flower1 {{
        position: fixed;
        top: 80px;
        left: 30px;
        width: 60px;
        opacity: 0.30;
        z-index: 0;
    }}

    .flower2 {{
        position: fixed;
        top: 250px;
        left: 4%;
        width: 35px;
        opacity: 0.30;
        z-index: 0;
    }}

    .flower3 {{
        position: fixed;
        bottom: 250px;
        left: 4%;
        width: 55px;
        opacity: 0.30;
        z-index: 0;
    }}

    .flower9 {{
        position: fixed;
        bottom: 10%;
        left: 5%;
        width: 65px;
        opacity: 0.30;
        z-index: 0;
    }}

    /* RIGHT SIDE BACKGROUND ELEMENTS */

    .flower4 {{
        position: fixed;
        bottom: 150px;
        right: 3%;
        width: 60px;
        opacity: 0.30;
        z-index: 0;
    }}

    .flower6 {{
        position: fixed;
        top: 60px;
        right: 5%;
        width: 55px;
        opacity: 0.30;
        z-index: 0;
    }}

    .flower7 {{
        position: fixed;
        top: 40%;
        right: 2%;
        width: 55px;
        opacity: 0.30;
        z-index: 0;
    }}


    /* BOTTOM FOOTER / CORNER ELEMENTS */
    .flower10 {{
        position: fixed;
        bottom: 4%;
        left: 50%;
        width: 52px;
        opacity: 0.30;
        z-index: 0;
    }}
    </style>

    <img class="flower1"
         src="data:image/png;base64,{daisy}">

    <img class="flower2"
         src="data:image/png;base64,{daisy}">

    <img class="flower3"
         src="data:image/png;base64,{bud}">

    <img class="flower4"
         src="data:image/png;base64,{daisy}">

    <img class="flower6"
         src="data:image/png;base64,{daisy}">

    <img class="flower7"
         src="data:image/png;base64,{bud}">

    <img class="flower9"
         src="data:image/png;base64,{daisy}">

    <img class="flower10"
         src="data:image/png;base64,{bud}">

    """,
    unsafe_allow_html=True
)

st.markdown("""
<style>
button:focus {
    outline: none !important;
    box-shadow: none !important;
}

button:focus-visible {
    outline: none !important;
    box-shadow: none !important;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# LOAD CSV DATA
# =========================================================

@st.cache_data
def load_data():

    flow_df = pd.read_csv(
        "BraveEve_conversation_flow.csv"
    )

    static_df = pd.read_csv(
        "BraveEve_static_messages.csv"
    )

    name_df = pd.read_csv(
        "BraveEve_name_affirmations.csv"
    )

    distress_df = pd.read_csv(
        "BraveEve_distress_score_responses.csv"
    )

    variables_df = pd.read_csv(
        "BraveEve_16th june.csv"
    )

    nlp_df = pd.read_csv(
        "BraveEve_NLP_dataset.csv"
    )

    return (
        flow_df,
        static_df,
        name_df,
        distress_df,
        variables_df,
        nlp_df
    )

(
    flow_df,
    static_df,
    name_df,
    distress_df,
    variables_df,
    nlp_df
) = load_data()

@st.cache_data
def create_question_bank(df):

    return (
        df.groupby("Problem List Item", sort=False, dropna=True)
          .apply(lambda x: x.sample(1))
          .reset_index(drop=True)
    )

question_bank = create_question_bank(variables_df)

def get_message(key):

    result = static_df.loc[
        static_df["Key"] == key,
        "Message"
    ]

    if len(result) > 0:
        return result.iloc[0]

    return ""

def personalize(text):

    if pd.isna(text):
        return ""

    return str(text).replace(
        "[Name]",
        st.session_state.name
    )
    
# =========================================================
# LOAD NLP MODEL
# =========================================================

@st.cache_resource
def load_model():

    return joblib.load("sentiment_model.pkl")

try:

    model = load_model()

except Exception as e:

    st.error(
        f"Model could not be loaded: {e}"
    )

    st.stop()

# =========================================================
# TEXT CLEANING FUNCTION
# =========================================================

def clean_text(text):

    text = str(text).lower()

    contractions = {
        "i'm": "i am",
        "im": "i am",
        "don't": "do not",
        "cant": "cannot",
        "can't": "cannot",
        "won't": "will not",
        "isn't": "is not",
        "aren't": "are not",
        "wasn't": "was not",
        "weren't": "were not",
        "haven't": "have not",
        "hasn't": "has not",
        "hadn't": "had not",
        "shouldn't": "should not",
        "wouldn't": "would not",
        "couldn't": "could not",
        "didn't": "did not",
        "dont": "do not",
        "doesnt": "does not",
        "shouldnt": "should not",
        "ik": "i know",
        "theyre": "they are",
        "idk": "i do not know",
        "wanna": "want to",
        "gonna": "going to",
        "i'll": "i will"
    }

    for key, value in contractions.items():
        text = text.replace(key, value)

    text = re.sub(r'[^a-zA-Z\s]', '', text)

    text = re.sub(r'\s+', ' ', text).strip()

    return text

# =========================================================
# SAVE RESPONSES
# =========================================================

def save_responses():

    if len(st.session_state.responses) == 0:
        return

    session_duration = None

    if (
        st.session_state.session_start_time
        is not None
    ):

        session_duration = (
            time.time()
            - st.session_state.session_start_time
            - st.session_state.total_paused_seconds
        )

    completed_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    conn = sqlite3.connect(
        "braveeve.db"
    )

    cursor = conn.cursor()

    for row in st.session_state.responses:

        cursor.execute("""
        INSERT INTO responses VALUES (
        ?,?,?,?,?,?,?,?,?,?,?,?,?
        )
        """, (

            row["session_id"],
            str(row["timestamp"]),
            row["name"],
            row["distress_score"],
            row["question_number"],
            row["category"],
            row["problem_item"],
            row["answer"],
            row["response_source"],
            row["free_text"],
            completed_time,
            round(
                session_duration,
                2
            ),
            round(
                session_duration / 60,
                2
            )

        ))

    conn.commit()
    conn.close()

    st.session_state.responses = []

# =========================================================
# SESSION STATE
# =========================================================

if "step" not in st.session_state:

    st.session_state.step = 0
    st.session_state.name = ""
    st.session_state.q2_phrase = ""
    st.session_state.day_reply = ""
    st.session_state.distress_score = None
    st.session_state.nccn_index = 0
    st.session_state.responses = []

if "question_answered" not in st.session_state:
    st.session_state.question_answered = False

if "show_prediction" not in st.session_state:
    st.session_state.show_prediction = None

if "saved_to_file" not in st.session_state:
    st.session_state.saved_to_file = False

if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""

if "day_feeling" not in st.session_state:
    st.session_state.day_feeling = ""

if "score_reply" not in st.session_state:
    st.session_state.score_reply = ""

if "show_example" not in st.session_state:
    st.session_state.show_example = False

if "response_message" not in st.session_state:
    st.session_state.response_message = ""

if "response_type" not in st.session_state:
    st.session_state.response_type = ""

if "session_id" not in st.session_state:
    st.session_state.session_id = (
        datetime.now().strftime("%Y%m%d")
        + "_"
        + str(uuid.uuid4())[:6]
    )

if "show_distress_help" not in st.session_state:
    st.session_state.show_distress_help = False

if "debug_prediction" not in st.session_state:
    st.session_state.debug_prediction = ""

if "session_start_time" not in st.session_state:
    st.session_state.session_start_time = None

if "pause_start_time" not in st.session_state:
    st.session_state.pause_start_time = None

if "total_paused_seconds" not in st.session_state:
    st.session_state.total_paused_seconds = 0

init_db()

# =========================================================
# STEP 0 – NAME
# =========================================================

if st.session_state.step == 0:

    c1, c2, c3 = st.columns([1,3,1])

    with c2:
        st.image(
            "images/header.png",
            use_container_width=True
        )

    st.markdown(
        """
        <p style="
            text-align:center;
            color:#7A6A72;
            font-size:18px;
            margin-top:-10px;
            margin-bottom:10px;
        ">
            A supportive check-in tool for women receiving cancer care
        </p>
        """,
        unsafe_allow_html=True
    )

    st.divider()

if st.session_state.step == 0:

    img = mascot_html("BraveEve_waving")

    st.markdown(
    f"""
    <div style="
    position:relative;
    background:white;
    padding:25px;
    border-radius:18px;
    box-shadow:0 2px 8px rgba(0,0,0,0.08);
    margin-bottom:20px;
    overflow:visible;
    ">

    <img src="data:image/png;base64,{img}"
    style="
    position:absolute;
    top:20px;
    right:10px;
    width:130px;
    "/>

    <h2 style="
    color:#C85A84;
    margin-top:0;
    margin-bottom:15px;
    ">
    🌸 Hello! I'm BraveEve
    </h2>

    <p style="
    font-size:18px;
    line-height:1.6;
    padding-right:110px;
    ">
    {get_message("ASK_NAME")}
    </p>

    </div>
    """,
    unsafe_allow_html=True
    )

    name = st.text_input(
        "Your name"
    )

    if st.button("Continue") and name.strip():

        st.session_state.name = name.strip()

        st.session_state.session_start_time = (
            time.time()
        )

        st.session_state.q2_phrase = random.choice(
            name_df["Messages"].dropna().tolist()
        )

        st.session_state.step = 1

        st.rerun()

# =========================================================
# STEP 1 – NAME AFFIRMATION
# =========================================================

elif st.session_state.step == 1:

    affirmation = st.session_state.q2_phrase.replace(
        "[Name]",
        st.session_state.name
    )

    show_braveeve_card(
        text=affirmation,
        mascot="BraveEve_grateful",
        side="right",
        width=105,
        top_offset=-5,
        card_color="#FFF5F8"
    )

    if st.button("Next"):
        st.session_state.step = 2
        st.rerun()

# =========================================================
# STEP 2 – DAY FEELING
# =========================================================

elif st.session_state.step == 2:

    st.write(get_message("ASK_DAY_FEELING"))

    choice = st.radio(
        "",
        [
            "It's been good",
            "It's been a little difficult",
            "I'm just okay"
        ]
    )

    if st.button("Continue"):

        st.session_state.day_feeling = choice

        if choice == "It's been good":

            st.session_state.day_reply = get_message(
                "DAY_FEELING_GOOD"
            )

        elif choice == "I'm just okay":

            st.session_state.day_reply = get_message(
                "DAY_FEELING_OKAY"
            )

        else:

            st.session_state.day_reply = get_message(
                "DAY_FEELING_STRUGGLE"
            )

        st.session_state.step = 21

        st.rerun()

# =========================================================
# STEP 2A – DAY FEELING RESPONSE
# =========================================================

elif st.session_state.step == 21:

    show_braveeve_card(
        text=st.session_state.day_reply,
        mascot="BraveEve_proud",
        side="right",
        width=100
    )

    if st.button("Continue"):

        st.session_state.step = 3

        st.rerun()

# =========================================================
# STEP 3 – DISTRESS AWARENESS
# =========================================================

elif st.session_state.step == 3:

    show_braveeve_card(
        text=get_message("ASK_DISTRESS_AWARENESS"),
        mascot="BraveEve_thoughtful",
        side="left",
        width=110,
        top_offset=10,
        card_color="#FFFDF8"
    )

    c1, c2 = st.columns(2, gap="small")

    with c1:
        yes_clicked = st.button(
            "Yes",
            use_container_width=True,
            key="distress_yes"
        )

    with c2:
        no_clicked = st.button(
            "No",
            use_container_width=True,
            key="distress_no"
        )

    if yes_clicked:
        st.session_state.step = 4
        st.rerun()

    if no_clicked:
        st.session_state.step = 4
        st.rerun()


# =========================================================
# STEP 4 – DISTRESS EXPLANATION
# =========================================================

elif st.session_state.step == 4:

    show_braveeve_card(
        text=random.choice([
            get_message("EXPLAIN_DISTRESS_1"),
            get_message("EXPLAIN_DISTRESS_2")
        ]),
        mascot="BraveEve_pointing_up",
        side="right",
        width=120,
        top_offset=0,
        card_color="#FAF6FF"
    )

    st.write(
        get_message("DISTRESS_UNDERSTOOD")
    )

    c1, c2 = st.columns(2, gap="small")

    with c1:
        yes_clicked = st.button(
            "Yes",
            use_container_width=True,
            key="distress_understood_yes"
        )

    with c2:
        no_clicked = st.button(
            "No",
            use_container_width=True,
            key="distress_understood_no"
        )

    if yes_clicked:

        st.session_state.step = 5

        st.rerun()

    if no_clicked:

        st.session_state.step = 41

        st.rerun()

# =========================================================
# STEP 4A – RE-EXPLAIN DISTRESS
# =========================================================

elif st.session_state.step == 41:

    show_braveeve_card(
        text=get_message("DISTRESS_REEXPLAIN"),
        mascot="BraveEve_pointing_up",
        side="left",
        width=120,
        top_offset=0,
        card_color="#FEEDFD"
    )

    st.write(
        get_message("DISTRESS_REEXPLAIN_CHECK")
    )

    c1, c2 = st.columns(2, gap="small")

    with c1:
        yes_clicked = st.button(
            "Yes",
            use_container_width=True,
            key="distress_reexplained_yes"
        )

    with c2:
        no_clicked = st.button(
            "No",
            use_container_width=True,
            key="distress_reexplained_no"
        )

    if yes_clicked:

        st.session_state.step = 5

        st.rerun()

    if no_clicked:

        st.session_state.show_distress_help = True

        st.rerun()

    if st.session_state.show_distress_help:

        st.warning(
            get_message(
                "DISTRESS_NOT_UNDERSTOOD_HELP"
            )
        )

        if st.button(
            "Continue",
            use_container_width=True,
            key="distress_help_continue"
        ):

            st.session_state.show_distress_help = False

            st.session_state.step = 5

            st.rerun()

# =========================================================
# STEP 5 – DISTRESS SCORE
# =========================================================

elif st.session_state.step == 5:

    st.write(
        get_message("ASK_DISTRESS_SCORE")
    )

    score = st.slider(
        "Distress score",
        0,
        10,
        5
    )

    if st.button("Continue"):

        st.session_state.distress_score = score

        if score <= 3:

            st.session_state.score_reply = random.choice([
                get_message("SCORE_RESPONSE_LOW"),
                get_message("SCORE_RESPONSE_LOW_2")
            ])

        elif score <= 6:

            st.session_state.score_reply = random.choice([
                get_message("SCORE_RESPONSE_MODERATE"),
                get_message("SCORE_RESPONSE_MODERATE_2")
            ])

        else:

            st.session_state.score_reply = random.choice([
                get_message("SCORE_RESPONSE_HIGH"),
                get_message("SCORE_RESPONSE_HIGH_2")
            ])

        st.session_state.step = 51

        st.rerun()

# =========================================================
# STEP 5A – SCORE RESPONSE
# =========================================================

elif st.session_state.step == 51:

    st.info(
        st.session_state.score_reply
    )

    if st.button("Continue"):

        st.session_state.step = 6

        st.rerun()


# =========================================================
# STEP 6 – QUESTION TRANSITION
# =========================================================

elif st.session_state.step == 6:

    msg = random.choice([
        get_message("QUESTION_TRANSITION"),
        get_message("QUESTION_TRANSITION_2")
    ])

    msg = msg.replace(
        "[Name]",
        st.session_state.name
    )

    show_braveeve_card(
        text=msg,
        mascot="BraveEve_few_questions",
        side="right",
        width=120,
        top_offset=5,
        card_color="#FAF6FF"
    )
    
    c1, c2, c3 = st.columns(3, gap="small")

    with c1:
        begin_clicked = st.button(
            "Begin",
            use_container_width=True
        )

    with c2:
        pause_clicked = st.button(
            "Pause",
            use_container_width=True
        )

    with c3:
        stop_clicked = st.button(
            "Stop",
            use_container_width=True
        )

    if begin_clicked:
        st.session_state.step = 7
        st.rerun()

    if pause_clicked:
        st.session_state.step = 888
        st.rerun()

    if stop_clicked:
        st.session_state.step = 999
        st.rerun()

# =========================================================
# STEP 7 – QUESTION LOOP
# =========================================================


elif st.session_state.step == 7:
    st.components.v1.html(
        """
        <script>
        window.parent.scrollTo(0,0);
        </script>
        """,
        height=0
    )

    if st.session_state.nccn_index >= len(question_bank):

        st.session_state.step = 999
        st.rerun()

    row = question_bank.iloc[
        st.session_state.nccn_index
    ]

    progress = (
        st.session_state.nccn_index + 1
    ) / len(question_bank)

    with st.container(border=True):

        st.markdown(
            f"**Question {st.session_state.nccn_index + 1} of {len(question_bank)}**"
        )

        st.progress(progress)

    st.markdown(
        f"""
        <div style="
            display:inline-block;
            background:#F8DCE6;
            color:#A3476A;
            padding:6px 14px;
            border-radius:20px;
            font-size:15px;
            margin-bottom:10px;
        ">
            {row['Category']}
        </div>
        """,
        unsafe_allow_html=True
    )

    question = personalize(
        row["BraveEve's Conversational Question"]
    )

    problem = row["Problem List Item"]

    mascot = QUESTION_MASCOTS.get(problem)
    layout = QUESTION_LAYOUT.get(problem, "none")

    st.markdown(
        f"""
        <div class="card">

        <h3 style="
            color:#C85A84;
            margin-bottom:10px;
        ">
            {row["Problem List Item"]}
        </h3>

        <div style="
            font-size:22px;
            line-height:1.6;
            color:#333333;
            margin-bottom:10px;
        ">
            {question}
        </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    if mascot:

        if layout == "top":

            show_mascot(
                mascot,
                width=95,
                align="right"
            )

        elif layout == "bottom_left":

            st.markdown("<br>", unsafe_allow_html=True)

            show_mascot(
                mascot,
                width=100,
                align="left"
            )

        elif layout == "bottom_right":

            st.markdown("<br>", unsafe_allow_html=True)

            show_mascot(
                mascot,
                width=100,
                align="right"
            )

        elif layout == "category":

            show_mascot(
                mascot,
                width=90,
                align="center"
            )
            
    # =====================================================
    # EXAMPLE SECTION
    # =====================================================
    if st.button(
        "💡Click here for an example of what someone experiencing this might say",
        key=f"example_btn_{st.session_state.nccn_index}",
    ):
        st.session_state.show_example = True
    
    if st.session_state.show_example:

        verbatim = personalize(
            str(row["Verbatim"])
        )

        if (
            verbatim.strip() != ""
            and verbatim.lower() != "nan"
        ):

            st.markdown(
                f'> {verbatim}'
            )

        else:

            st.write(
                "No example is available for this question."
            )
    st.divider()  
    
    # =====================================================
    # YES / NO FIRST
    # =====================================================

    if not st.session_state.question_answered:
        st.write(
                "Your answer:"
            )
        c1, c2 = st.columns(2)

        with c1:
            yes_clicked = st.button(
                "Yes",
                use_container_width=True
            )

        with c2:
            no_clicked = st.button(
                "No",
                use_container_width=True
            )

        if yes_clicked:

            yes_response = personalize(
                row["Yes"]
            )

            st.session_state.response_message = yes_response
            st.session_state.response_type = "info"

            st.session_state.responses.append({

                "session_id": st.session_state.session_id,
                "timestamp": datetime.now(),
                "name": st.session_state.name,
                "distress_score": st.session_state.distress_score,
                "question_number": st.session_state.nccn_index + 1,
                "category": row["Category"],
                "problem_item": row["Problem List Item"],
                "answer": "YES",
                "response_source": "BUTTON",
                "free_text": ""

            })

            st.session_state.question_answered = True

            st.rerun()

        if no_clicked:

            no_response = personalize(
                row["No"]
            )

            st.session_state.response_message = no_response
            st.session_state.response_type = "success"

            st.session_state.responses.append({

                "session_id": st.session_state.session_id,
                "timestamp": datetime.now(),
                "name": st.session_state.name,
                "distress_score": st.session_state.distress_score,
                "question_number": st.session_state.nccn_index + 1,
                "category": row["Category"],
                "problem_item": row["Problem List Item"],
                "answer": "NO",
                "response_source": "BUTTON",
                "free_text": ""

            })

            st.session_state.question_answered = True

            st.rerun()

    # =====================================================
    # OR TEXT RESPONSE
    # =====================================================

    if not st.session_state.question_answered:

        st.markdown("### OR")

        user_text = st.text_area(
            "You can share your thoughts here",
            key=f"text_{st.session_state.nccn_index}"
        )

        if st.button("Submit Response"):

            if user_text.strip() != "":

                cleaned = clean_text(
                    user_text
                )

                prediction = model.predict(
                    [cleaned]
                )[0]

                st.session_state.debug_prediction = prediction

                if prediction == "YES":

                    st.session_state.response_message = personalize(
                        row["Yes"]
                    )

                    st.session_state.response_type = "info"

                else:

                    st.session_state.response_message = personalize(
                        row["No"]
                    )

                    st.session_state.response_type = "success"

                st.session_state.responses.append({
                    "session_id": st.session_state.session_id,
                    "timestamp": datetime.now(),
                    "name": st.session_state.name,
                    "distress_score": st.session_state.distress_score,
                    "question_number": st.session_state.nccn_index + 1,
                    "category": row["Category"],
                    "problem_item": row["Problem List Item"],
                    "answer": prediction,
                    "response_source": "NLP",
                    "free_text": user_text
                })

                st.session_state.question_answered = True

                st.rerun()

    # =====================================================
    # SHOW RESPONSE
    # =====================================================

    if (
        st.session_state.question_answered
        and st.session_state.response_message
    ):

        if st.session_state.response_type == "info":

            st.info(
                st.session_state.response_message
            )

        else:

            st.success(
                st.session_state.response_message
            )

        if (
            DEBUG_MODE
            and st.session_state.debug_prediction
        ):

            st.caption(
                f"Prediction: {st.session_state.debug_prediction}"
            )

    # =====================================================
    # NEXT QUESTION
    # =====================================================

    if st.session_state.question_answered:

        st.divider()

        if (
            st.session_state.nccn_index
            < len(question_bank) - 1
        ):

            if st.button("Next Question →"):

                text_key = (
                    f"text_{st.session_state.nccn_index}"
                )

                if text_key in st.session_state:

                    del st.session_state[text_key]

                st.session_state.question_answered = False
                st.session_state.show_example = False
                st.session_state.show_prediction = None

                st.session_state.response_message = ""
                st.session_state.response_type = ""
                st.session_state.debug_prediction = ""
                st.session_state.nccn_index += 1
                st.rerun()

        else:

            if st.button("Finish"):
                save_responses()
                st.session_state.step = 999

                st.rerun()

    # =====================================================
    # PAUSE / STOP
    # =====================================================

    if st.session_state.nccn_index < len(question_bank) - 1:

        st.divider()

        s1, s2 = st.columns(2)

        if s1.button("Pause"):

            st.session_state.pause_start_time = (
                time.time()
            )

            st.session_state.step = 888

            st.rerun()

        if s2.button("Stop"):

            save_responses()

            st.session_state.step = 999

            st.rerun()

# =========================================================
# PAUSE PAGE
# =========================================================

elif st.session_state.step == 888:

    show_braveeve_card(
        title="🌿Check-in Paused",
        text=get_message("PAUSE_MESSAGE"),
        mascot="BraveEve_deep_breath",
        side="right",
        width=155,
        top_offset=25,
        card_color="#FFFDF8"
    )

    c1, c2 = st.columns(2)

    with c1:

        resume_clicked = st.button(
            "Resume",
            use_container_width=True
        )

    with c2:

        stop_clicked = st.button(
            "Stop",
            use_container_width=True
        )

    if resume_clicked:

        if (
            st.session_state.pause_start_time
            is not None
        ):

            st.session_state.total_paused_seconds += (
                time.time()
                - st.session_state.pause_start_time
            )

            st.session_state.pause_start_time = None

        resume_msg = get_message(
            "RESUME_MESSAGE"
        )

        resume_msg = personalize(
            resume_msg
        )

        st.session_state.resume_text = (
            resume_msg
        )

        st.session_state.step = 889

        st.rerun()

    if stop_clicked:

        if (
            st.session_state.pause_start_time
            is not None
        ):

            st.session_state.total_paused_seconds += (
                time.time()
                - st.session_state.pause_start_time
            )

            st.session_state.pause_start_time = None

        save_responses()

        st.session_state.step = 999

        st.rerun()

# =========================================================
# RESUME PAGE
# =========================================================

elif st.session_state.step == 889:

    show_braveeve_card(
        text=st.session_state.resume_text,
        mascot="BraveEve_excited",
        side="right",
        width=85,
        top_offset=-75,
        card_color="#FFF5F8"
    )

    if st.button("Continue"):

        st.session_state.step = 7

        st.rerun()

# =========================================================
# END PAGE
# =========================================================
    
elif st.session_state.step == 999:

    end_message = random.choice([
        get_message("END_MESSAGE"),
        get_message("END_MESSAGE_2")
    ])

    end_message = personalize(end_message)

    st.balloons()

    show_braveeve_card(
        text=end_message,
        mascot="BraveEve_thank_you",
        side="right",
        width=145,
        top_offset=5,
        card_color="#FFF8FB"
    )

    # Decorative icons
    show_mascot(
        "heart_bubble",
        width=55,
        align="center"
    )

    show_mascot(
        "holding_heart",
        width=90,
        align="left"
    )

    show_mascot(
        "heart",
        width=35,
        align="right"
    )

    if (
        st.session_state.distress_score is not None
        and st.session_state.distress_score >= 4
    ):

        st.warning(
            get_message("DISTRESS_ALERT")
        )

    st.markdown("---")

    st.caption(
        get_message("DISCLAIMER")
    )

    st.stop()



