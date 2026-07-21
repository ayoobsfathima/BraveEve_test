import streamlit as st
import pandas as pd
import random
import joblib
import re
import os
import uuid
import base64
import time
import psycopg2
from psycopg2 import pool as pg_pool
from datetime import datetime
from streamlit_scroll_to_top import scroll_to_here
DEBUG_MODE = True 

@st.cache_resource
def get_pool():
    return pg_pool.ThreadedConnectionPool(
        1, 10, st.secrets["db_url"]
    )

def get_connection():
    return get_pool().getconn()

def release_connection(conn):
    get_pool().putconn(conn)

@st.cache_resource
def init_db():

    conn = get_connection()

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
    release_connection(conn)

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

# =========================================================
# SECTION INTRO HEADERS (shown at the top of each section page,
# in fixed order: Physical, Emotional, Social, Practical, Spiritual)
# =========================================================

SECTION_INTROS = [

    "[Name], let's start with how your body has been feeling. "
    "Have you had any of these concerns in the past week, including today?",

    "Now, [Name], I'd like to check in on how you've been feeling inside. "
    "Have any of these been on your mind this past week, including today?",

    "Next, [Name], let's talk about the people around you. "
    "Have you had any of these concerns in the past week, including today?",

    "[Name], now I'd like to ask about some everyday things in your life. "
    "Take your time — you can always pause if you need to. "
    "Have you noticed any of these in the past week, including today?",

    "Lastly, [Name], I'd like to ask about your faith and beliefs. "
    "Have any of these been on your mind this past week, including today?"

]

# =========================================================
# EMPATHETIC RESPONSES TO THE SHARED SECTION NOTES,
# chosen at random based on the NLP model's Yes/No prediction
# =========================================================

NOTES_RESPONSE_YES = [

    "I can truly feel how much you're carrying right now, [Name], and I am "
    "so deeply sorry that things are this heavy. Please know you don't have "
    "to navigate this overwhelming weight all by yourself.",

    "Hearing you talk about this, [Name], it's completely clear how "
    "exhausting and intense everything is for you right now. I'm right "
    "here with you, and we can take this as slowly as you need.",

    "I'm so sorry, [Name]. I can hear the immense weight in your voice "
    "right now, and it makes complete sense that you feel entirely "
    "overwhelmed by all of this.",

    "Thank you for being so open with me, [Name]. I can hear how "
    "incredibly painful and chaotic things feel right now. Let's take a "
    "deep breath together — we will go entirely at your pace.",

    "It sounds like you are being pushed to your absolute limit right "
    "now, [Name], and I am so incredibly sorry. No one should have to "
    "bear this kind of distress alone.",

    "I can hear how entirely drained and overwhelmed you feel, [Name]. "
    "I'm so sorry things are this hard. Let's see if we can find even "
    "just one or two small areas where we can bring you a little relief.",

    "I am listening closely, [Name], and I can hear just how heavy, raw, "
    "and overwhelming this moment is for you. I'm so sorry you are going "
    "through this, but I'm glad you're telling me.",

    "Everything you're describing sounds incredibly heavy and "
    "overwhelming, [Name]. I'm so sorry it's reached this point. Let's "
    "look at this list together specifically to see how we can lift some "
    "of this weight off your shoulders."

]

NOTES_RESPONSE_NO = [

    "It brings me so much joy to hear that you're in a really good, "
    "steady space right now, [Name]! I'm so glad to hear that things are "
    "feeling manageable.",

    "I am incredibly glad to hear that you are feeling steady and doing "
    "well today, [Name]. It sounds like you've found a really good "
    "balance right now.",

    "That is wonderful to hear, [Name]! I'm so glad you're feeling good "
    "and that things are going smoothly for you today.",

    "I'm so happy you're feeling well and steady right now, [Name]. "
    "Let's do a quick check on these items just to ensure we keep things "
    "running this smoothly for you.",

    "It is so refreshing to hear that you're doing well and feeling "
    "peaceful today, [Name]. I'm truly glad to know that things are "
    "feeling lighter for you.",

    "I love hearing that, [Name]! It sounds like you're in a really "
    "steady place today, which is fantastic news.",

    "I'm so glad to hear you're doing well, [Name]. Even when things are "
    "steady, we like to double-check the little things just to make sure "
    "nothing is quietly pulling your energy away.",

    "Thank you for sharing that, [Name] — I'm truly happy to hear that "
    "you're feeling well and that life feels manageable and stable for "
    "you right now."

]

# =========================================================
# ROTATING PROMPTS FOR THE SHARED SECTION NOTES BOX
# =========================================================

NOTES_BOX_PROMPTS = [

    "If you have any other concerns or feel like there's something else "
    "you need to get off your chest, this is a safe space to do so.",

    "If there's anything else on your mind or something you're currently "
    "struggling with, please feel free to share it here. I'm listening.",

    "Is there anything else you'd like to talk about? If something has "
    "been particularly challenging or troubling lately, you can always "
    "share it here.",

    "Please feel free to share any other concerns, or anything else "
    "that might be bothering you, right here.",

    "If you just need a moment to share what's happening, feel free to "
    "write it down here."

]

# =========================================================
# CLOSING ACKNOWLEDGMENT MESSAGES (final page, chosen at random)
# =========================================================

CLOSING_ACKNOWLEDGMENTS = [

    "That's the last of it, [Name] — you've made it through. Answering "
    "these honestly isn't easy, and it took real courage to sit with "
    "these questions today. Thank you for trusting me with this.",

    "That's the final question, [Name] — you did it. Opening up "
    "honestly like this isn't easy, and it takes real strength to get "
    "through it all. Thank you for trusting me with your story today.",

    "We're all done, [Name]. I know looking closely at these things can "
    "be tough, and I'm so glad you stayed with it. Thank you for your "
    "honesty and for sharing this space with me.",

    "That's the last of it, [Name]. Being vulnerable takes a lot of "
    "courage, and you did incredibly well today. Thank you for placing "
    "your trust in me.",

    "You've officially made it through, [Name]. Reflecting on these "
    "questions takes a lot of emotional energy, and you showed real "
    "bravery by facing them. Thank you for trusting me.",

    "And that brings us to the end, [Name]. I truly appreciate how open "
    "you've been. It's never easy to sit with these kinds of questions, "
    "and I'm incredibly grateful for your trust.",

    "That's everything, [Name] — you made it to the finish line. It "
    "takes massive courage to be this honest, even when it feels heavy. "
    "Thank you for letting me in and sharing this.",

    "We've covered it all, [Name]. Thank you for being so deeply honest "
    "today. It isn't easy to face these thoughts head-on, and I hold "
    "your trust with a lot of respect.",

    "That wraps things up, [Name]. You can take a deep breath — you "
    "made it through. Sitting with these questions takes genuine "
    "courage, and I appreciate you trusting me with your answers.",

    "That's the last one, [Name]. You made it through a tough process "
    "with total honesty, and that takes real bravery. Thank you for "
    "trusting me.",

    "You've made it through the whole way, [Name]. I know this wasn't a "
    "simple walk in the park, and your courage to speak your truth "
    "today means a lot. Thank you for your trust."

]

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

    /* Reduce Streamlit's default reserved space above the content,
       so scrolling to top lands closer to the actual page content */
    .block-container {{
        padding-top: 2rem !important;
    }}

    /* Prevent the browser from auto-restoring scroll position
       when content shifts, which fights our scroll-to-top script */
    html, body {{
        overflow-anchor: none !important;
    }}

    /* Animated tick pop on the section checklists, size unchanged */
    [data-testid="stCheckbox"] svg {{
        transition: transform 0.15s ease-in-out;
    }}

    [data-testid="stCheckbox"]:has(input:checked) svg {{
        transform: scale(1.3);
    }}

    /* Increase general text size */
    p, li, label, div {{
        font-size: 18px !important;
    }}

    /* Question text */
    .stMarkdown {{
        font-size: 18px !important;
    }}

    /* Checklist checkboxes - bigger target + a pleasant check animation */
    [data-testid="stCheckbox"] label {{
        align-items: center;
        gap: 12px;
        cursor: pointer;
    }}

    [data-testid="stCheckbox"] label > div:not([data-testid="stWidgetLabel"]) {{
        width: 28px !important;
        height: 28px !important;
        min-width: 28px !important;
        border-radius: 8px !important;
        border: 2px solid #D96C97 !important;
        transition: transform 0.15s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    }}

    [data-testid="stCheckbox"] label > div:not([data-testid="stWidgetLabel"]) svg {{
        width: 16px;
        height: 16px;
    }}

    [data-testid="stCheckbox"] label:hover > div:not([data-testid="stWidgetLabel"]) {{
        border-color: #B04A72 !important;
        box-shadow: 0 0 0 4px rgba(217, 108, 151, 0.15);
    }}

    [data-testid="stCheckbox"] label[data-selected="true"] > div:not([data-testid="stWidgetLabel"]) {{
        animation: checkPop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    }}

    @keyframes checkPop {{
        0%   {{ transform: scale(0.55); }}
        60%  {{ transform: scale(1.18); }}
        100% {{ transform: scale(1); }}
    }}

    [data-testid="stCheckbox"] label > div:not([data-testid="stWidgetLabel"]) svg polyline {{
        stroke-dasharray: 20;
        stroke-dashoffset: 20;
    }}

    [data-testid="stCheckbox"] label[data-selected="true"] > div:not([data-testid="stWidgetLabel"]) svg polyline {{
        animation: drawCheck 0.22s ease-out 0.08s forwards;
    }}

    @keyframes drawCheck {{
        to {{ stroke-dashoffset: 0; }}
    }}

    /* Checklist item card - hint icon floats in its rounded top-right corner
       instead of taking up a text column */
    [data-testid="stVerticalBlock"]:has([data-testid="stPopover"]) {{
        position: relative !important;
    }}

    [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) {{
        flex-wrap: nowrap !important;
        align-items: flex-start !important;
        gap: 0 !important;
        column-gap: 0 !important;
    }}

    [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > [data-testid="stColumn"]:first-child {{
        flex: 1 1 100% !important;
        width: 100% !important;
        padding-right: 36px !important;
    }}

    [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > [data-testid="stColumn"]:last-child {{
        flex: 0 0 0 !important;
        width: 0 !important;
        min-width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: visible !important;
    }}

    [data-testid="stPopover"] {{
        position: absolute !important;
        top: 8px !important;
        right: 8px !important;
        z-index: 2;
    }}

    /* Hint ("what someone might say") icon - a filled lightbulb glyph with a
       soft resting glow so it visibly reads as tappable */
    [data-testid="stPopover"] [data-testid="stPopoverButton"] {{
        background-color: rgba(255, 255, 255, 0.85) !important;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23D96C97'%3E%3Cpath d='M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7z'/%3E%3C/svg%3E") !important;
        background-repeat: no-repeat !important;
        background-position: center !important;
        background-size: 17px 17px !important;
        border: none !important;
        min-height: unset !important;
        width: 32px !important;
        height: 32px !important;
        padding: 0 !important;
        border-radius: 50% !important;
        box-shadow: 0 0 0 5px rgba(217, 108, 151, 0.10), 0 2px 6px rgba(217, 108, 151, 0.30) !important;
        transition: background-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
    }}

    [data-testid="stPopover"] [data-testid="stPopoverButton"]:hover {{
        background-color: #FFFFFF !important;
        box-shadow: 0 0 0 7px rgba(217, 108, 151, 0.16), 0 3px 10px rgba(217, 108, 151, 0.40) !important;
        transform: scale(1.05);
    }}

    /* the emoji text + chevron are replaced by the glyph above */
    [data-testid="stPopover"] [data-testid="stPopoverButton"] p,
    [data-testid="stPopover"] [data-testid="stPopoverButton"] [data-testid="stIconMaterial"] {{
        display: none !important;
    }}

    /* Affirmation text below a checked item - fade + slide in */
    [data-testid="stAlert"] {{
        animation: affirmationFadeIn 0.45s ease-out;
    }}

    @keyframes affirmationFadeIn {{
        0%   {{ opacity: 0; transform: translateX(-16px); }}
        100% {{ opacity: 1; transform: translateX(0); }}
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
        "BraveEve_variables_15.csv",
        encoding="cp1252"
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

    # Deterministic (not random) — this copy is only used to derive the
    # stable list of items/categories and their fixed question numbers.
    # It intentionally does NOT decide which phrasing variant is shown.
    return (
        df.groupby("Problem List Item", sort=False, dropna=True, group_keys=False)
          .first()
          .reset_index()
    )

question_bank = create_question_bank(variables_df)

SECTIONS = list(question_bank["Category"].unique())

ITEM_QUESTION_NUMBER = {
    item: idx + 1
    for idx, item in enumerate(question_bank["Problem List Item"])
}

SECTION_NOTES_QUESTION_NUMBER = {
    section: 1000 + idx
    for idx, section in enumerate(SECTIONS)
}

def sample_question_variants(df):

    # Random on purpose — called once per session so each person gets a
    # fresh, randomly chosen phrasing variant per item for that session.
    return (
        df.groupby("Problem List Item", sort=False, dropna=True, group_keys=False)
          .sample(n=1)
          .reset_index(drop=True)
    )

def get_section_items(section_name):

    return st.session_state.session_question_bank[
        st.session_state.session_question_bank["Category"] == section_name
    ].reset_index(drop=True)

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

    conn = get_connection()

    cursor = conn.cursor()

    for row in st.session_state.responses:

        cursor.execute("""
        INSERT INTO responses VALUES (
        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
        )
        ON CONFLICT (session_id, question_number)
        DO UPDATE SET
            answer = EXCLUDED.answer,
            response_source = EXCLUDED.response_source,
            free_text = EXCLUDED.free_text,
            completed_at = EXCLUDED.completed_at,
            session_duration_seconds = EXCLUDED.session_duration_seconds,
            session_duration_minutes = EXCLUDED.session_duration_minutes
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
    release_connection(conn)

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
    st.session_state.section_index = 0
    st.session_state.section_checks = {}
    st.session_state.session_question_bank = sample_question_variants(
        variables_df
    )
    st.session_state.trigger_scroll = True
    st.session_state.awaiting_continue = False
    st.session_state.pending_message = ""
    st.session_state.note_prompt_order = random.sample(
        NOTES_BOX_PROMPTS, len(NOTES_BOX_PROMPTS)
    )
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

    if st.session_state.get("trigger_scroll", False):

        scroll_to_here(
            0,
            key=f"scroll_{st.session_state.section_index}"
        )

        st.session_state.trigger_scroll = False

    if st.session_state.section_index >= len(SECTIONS):

        st.session_state.step = 999

        st.rerun()

    section_name = SECTIONS[st.session_state.section_index]

    section_df = get_section_items(section_name)

    progress = (
        st.session_state.section_index + 1
    ) / len(SECTIONS)

    section_mascot = None

    for _, m_row in section_df.iterrows():

        candidate = QUESTION_MASCOTS.get(
            m_row["Problem List Item"]
        )

        if candidate:

            section_mascot = candidate

            break

    mascot_img_tag = ""

    if section_mascot:

        mascot_b64 = mascot_html(section_mascot)

        mascot_img_tag = (
            f'<img src="data:image/png;base64,{mascot_b64}" '
            f'width="130" style="margin-top:-10px;">'
        )

    st.markdown(
        f"""
        <div style="
            display:flex;
            justify-content:space-between;
            align-items:center;
            margin-bottom:10px;
        ">
            <div style="
                display:inline-block;
                background:#F8DCE6;
                color:#A3476A;
                padding:6px 14px;
                border-radius:20px;
                font-size:15px;
            ">
                {section_name}
            </div>
            {mascot_img_tag}
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.container(border=True):

        st.markdown(
            f"**Section {st.session_state.section_index + 1} of {len(SECTIONS)}**"
        )

        st.progress(progress)

    intro_text = personalize(
        SECTION_INTROS[st.session_state.section_index]
        if st.session_state.section_index < len(SECTION_INTROS)
        else "Have you had concerns about any of these, in the past week including today?"
    )

    st.markdown(
        f"""
        <h3 style="
            color:#C85A84;
            margin:12px 0 8px 0;
        ">
            {intro_text}
        </h3>
        <div style="
            font-size:15px;
            color:#666666;
            margin-bottom:12px;
        ">
            Mark all that apply. Tap the 💡 next to an item for an example of what someone experiencing this might say.
        </div>
        """,
        unsafe_allow_html=True
    )

    # =====================================================
    # ITEM CHECKLIST FOR THIS SECTION
    # =====================================================

    for i, row in section_df.iterrows():

        item = row["Problem List Item"]

        question = personalize(
            row["BraveEve's Conversational Question"]
        )

        check_key = f"chk_{st.session_state.section_index}_{i}"

        with st.container(border=True):

            col1, col2 = st.columns([0.85, 0.15])

            with col1:

                checked = st.checkbox(
                    f"**{item}:** {question}",
                    key=check_key,
                    value=st.session_state.section_checks.get(
                        item, False
                    )
                )

            with col2:

                with st.popover("💡"):

                    verbatim = personalize(
                        str(row["Verbatim"])
                    )

                    if (
                        verbatim.strip() != ""
                        and verbatim.lower() != "nan"
                    ):

                        st.caption(
                            "Example of what someone experiencing this might say:"
                        )

                        st.markdown(f"> {verbatim}")

                    else:

                        st.caption(
                            "No example is available for this item."
                        )

            st.session_state.section_checks[item] = checked

            if checked:

                affirmation = personalize(
                    str(row["Yes"])
                )

                if (
                    affirmation.strip() != ""
                    and affirmation.lower() != "nan"
                ):

                    st.success(affirmation)

    st.divider()

    # =====================================================
    # SHARED NOTES BOX FOR THIS SECTION
    # =====================================================

    note_key = f"section_note_{st.session_state.section_index}"

    note_prompt = st.session_state.note_prompt_order[
        st.session_state.section_index % len(st.session_state.note_prompt_order)
    ]

    st.markdown(f"**{note_prompt}**")

    user_note = st.text_area(
        note_prompt,
        key=note_key,
        label_visibility="collapsed",
        disabled=st.session_state.awaiting_continue
    )

    # =====================================================
    # EMPATHETIC RESPONSE TO THE NOTES (shown after submitting)
    # =====================================================

    if st.session_state.awaiting_continue:

        st.markdown(
            f"""
            <div style="
                background:#FFF3F8;
                border:1px solid #F3C6DA;
                border-radius:14px;
                padding:18px 20px;
                margin:14px 0 18px 0;
                font-size:17px;
                color:#7A3B54;
                line-height:1.5;
            ">
                {st.session_state.pending_message}
            </div>
            """,
            unsafe_allow_html=True
        )

        scroll_to_here(
            0,
            key=f"scroll_msg_{st.session_state.section_index}"
        )

        is_last_section = (
            st.session_state.section_index == len(SECTIONS) - 1
        )

        if st.button(
            "Finish" if is_last_section else "Continue",
            type="primary"
        ):

            st.session_state.awaiting_continue = False
            st.session_state.pending_message = ""

            st.session_state.section_checks = {}
            st.session_state.section_index += 1
            st.session_state.trigger_scroll = True

            st.rerun()

    else:

        # =================================================
        # NAVIGATION
        # =================================================

        nav_col1, nav_col2 = st.columns(2)

        with nav_col1:

            if st.session_state.section_index > 0:

                if st.button("Back"):

                    st.session_state.section_index -= 1

                    st.session_state.section_checks = {}

                    st.session_state.trigger_scroll = True

                    st.rerun()

        with nav_col2:

            is_last_section = (
                st.session_state.section_index == len(SECTIONS) - 1
            )

            next_clicked = st.button(
                "Finish" if is_last_section else "Next",
                type="primary"
            )

        if next_clicked:

            for i, row in section_df.iterrows():

                item = row["Problem List Item"]

                is_checked = st.session_state.section_checks.get(
                    item, False
                )

                st.session_state.responses.append({

                    "session_id": st.session_state.session_id,
                    "timestamp": datetime.now(),
                    "name": st.session_state.name,
                    "distress_score": st.session_state.distress_score,
                    "question_number": ITEM_QUESTION_NUMBER[item],
                    "category": row["Category"],
                    "problem_item": item,
                    "answer": "YES" if is_checked else "NO",
                    "response_source": "CHECKBOX",
                    "free_text": ""

                })

            note_text = user_note.strip()

            if note_text != "":

                cleaned = clean_text(note_text)

                prediction = model.predict(
                    [cleaned]
                )[0]

            else:

                prediction = ""

            st.session_state.responses.append({

                "session_id": st.session_state.session_id,
                "timestamp": datetime.now(),
                "name": st.session_state.name,
                "distress_score": st.session_state.distress_score,
                "question_number": SECTION_NOTES_QUESTION_NUMBER[section_name],
                "category": section_name,
                "problem_item": "Section Notes",
                "answer": prediction,
                "response_source": "NLP" if note_text != "" else "NONE",
                "free_text": note_text

            })

            save_responses()

            note_given = note_text != ""
            pred_clean = str(prediction).strip().lower()

            if note_given and pred_clean in ("yes", "no"):

                bank = (
                    NOTES_RESPONSE_YES
                    if pred_clean == "yes"
                    else NOTES_RESPONSE_NO
                )

                st.session_state.pending_message = personalize(
                    random.choice(bank)
                )

                st.session_state.awaiting_continue = True

                st.rerun()

            else:

                st.session_state.section_checks = {}
                st.session_state.section_index += 1
                st.session_state.trigger_scroll = True

                st.rerun()

        # =================================================
        # PAUSE / STOP
        # =================================================

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

    scroll_to_here(0, key="scroll_final_page")

    closing_acknowledgment = personalize(
        random.choice(CLOSING_ACKNOWLEDGMENTS)
    )

    st.markdown(
        f"""
        <div style="
            background:#FFF3F8;
            border:1px solid #F3C6DA;
            border-radius:14px;
            padding:18px 20px;
            margin-bottom:16px;
            font-size:17px;
            color:#7A3B54;
            line-height:1.5;
        ">
            {closing_acknowledgment}
        </div>
        """,
        unsafe_allow_html=True
    )

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



