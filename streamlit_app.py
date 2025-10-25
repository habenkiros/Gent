import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import random
import pycountry
import requests
from io import BytesIO
from PIL import Image, ImageDraw
import numpy as np

st.set_page_config(page_title="Guess the Country", layout="centered")

# --- Load world map once ---
world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))

# --- Initialize session state ---
if "score" not in st.session_state:
    st.session_state.score = 0
if "tries" not in st.session_state:
    st.session_state.tries = 0
if "country" not in st.session_state:
    st.session_state.country = random.choice(world["name"].unique())

st.title("🌍 Guess the Country Game")

# --- Get flag image ---
def get_flag(country_name):
    try:
        code = pycountry.countries.lookup(country_name).alpha_2.lower()
        url = f"https://flagcdn.com/w320/{code}.png"
        response = requests.get(url)
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except:
        return None

# --- Draw country shape filled with flag texture ---
def draw_flag_map(country_name):
    country_shape = world[world['name'] == country_name]

    if country_shape.empty:
        st.warning("Country not found on map dataset.")
        return

    flag = get_flag(country_name)
    if not flag:
        st.warning("Flag not found.")
        return

    # Plot shape to an image buffer (for mask)
    fig, ax = plt.subplots(figsize=(6,4))
    country_shape.plot(ax=ax, color="white", edgecolor="black")
    ax.axis("off")

    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, transparent=True)
    buf.seek(0)
    mask_img = Image.open(buf).convert("L")

    # Resize flag to match mask
    flag = flag.resize(mask_img.size)

    # Make white (outside) transparent
    country_img = Image.composite(flag, Image.new("RGBA", flag.size, (0,0,0,0)), mask_img)

    st.image(country_img, caption="Guess which country this is!", use_container_width=True)

# --- Display country map with flag overlay ---
draw_flag_map(st.session_state.country)

# --- Guess input ---
guess = st.text_input("Your guess:").strip()

if st.button("Submit Guess"):
    if guess.lower() == st.session_state.country.lower():
        st.success(f"✅ Correct! It was {st.session_state.country}.")
        st.session_state.score += 1
        st.session_state.tries = 0
        st.session_state.country = random.choice(world["name"].unique())
    else:
        st.session_state.tries += 1
        if st.session_state.tries >= 3:
            st.error(f"❌ It was {st.session_state.country}.")
            st.session_state.tries = 0
            st.session_state.country = random.choice(world["name"].unique())
        else:
            st.warning(f"Try again! ({3 - st.session_state.tries} attempts left)")

# --- Show Score ---
st.metric("Score", st.session_state.score)