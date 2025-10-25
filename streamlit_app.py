import time
import streamlit as st
import requests
import random
import geopandas as gpd
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image
from shapely.geometry import shape

# ---------------------------------------------------
# ✅ Fix for Streamlit Cloud CSS preload bug
# ---------------------------------------------------
time.sleep(0.5)

# ---------------------------------------------------
# Page setup
# ---------------------------------------------------
st.set_page_config(page_title="Guess the Country", layout="centered")

# ---------------------------------------------------
# API Endpoints
# ---------------------------------------------------
COUNTRY_API = "https://restcountries.com/v3.1/all"
GEOJSON_API = "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"

# ---------------------------------------------------
# Fetch Data from APIs (cached)
# ---------------------------------------------------
@st.cache_data
def get_countries():
    """Fetch all countries and flags."""
    try:
        countries = requests.get(COUNTRY_API).json()
        result = []
        for c in countries:
            if "name" in c and "cca3" in c:
                result.append({
                    "name": c["name"]["common"],
                    "code": c["cca3"],
                    "flag": c["flags"]["png"],
                })
        return result
    except Exception as e:
        st.error(f"Error fetching countries: {e}")
        return []

@st.cache_data
def get_world_geojson():
    """Load world shapes as GeoDataFrame."""
    try:
        data = requests.get(GEOJSON_API).json()
        return gpd.GeoDataFrame.from_features(data["features"])
    except Exception as e:
        st.error(f"Error fetching world map: {e}")
        return gpd.GeoDataFrame()

# ---------------------------------------------------
# Utility functions
# ---------------------------------------------------
def get_country_shape(world_gdf, code):
    """Return the GeoDataFrame of a specific country."""
    country = world_gdf[world_gdf["ISO_A3"] == code]
    return country if not country.empty else None


def overlay_flag_on_shape(flag_url, country_shape):
    """Overlay the country shape with its flag pattern."""
    try:
        flag_img = Image.open(BytesIO(requests.get(flag_url).content)).convert("RGBA")

        # Plot country shape to create a mask
        fig, ax = plt.subplots(figsize=(6, 4))
        country_shape.plot(ax=ax, color="white", edgecolor="black")
        ax.axis("off")

        buf = BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, transparent=True)
        plt.close(fig)
        buf.seek(0)
        mask = Image.open(buf).convert("L")

        # Resize flag to match the mask
        flag_img = flag_img.resize(mask.size)

        # Composite the flag only where the mask is white
        result = Image.composite(flag_img, Image.new("RGBA", flag_img.size, (0, 0, 0, 0)), mask)
        return result
    except Exception as e:
        st.error(f"Error generating flag map: {e}")
        return None

# ---------------------------------------------------
# Game Initialization
# ---------------------------------------------------
countries = get_countries()
world = get_world_geojson()

if "country" not in st.session_state:
    st.session_state.country = random.choice(countries)
    st.session_state.tries = 0
    st.session_state.score = 0

country = st.session_state.country

# ---------------------------------------------------
# App UI
# ---------------------------------------------------
st.title("🌍 Guess the Country Game (API Edition)")
st.caption("Flag + Map overlay powered by REST APIs")

# Get the country shape and render the flag map
country_shape = get_country_shape(world, country["code"])
if country_shape is not None:
    painted_map = overlay_flag_on_shape(country["flag"], country_shape)
    if painted_map:
        st.image(painted_map, caption="Which country is this?", use_container_width=True)
    else:
        st.warning("Could not render flag overlay for this country.")
else:
    st.warning("Country shape not found in the GeoJSON dataset.")

# Input field for guess
guess = st.text_input("Enter your guess:").strip()

# ---------------------------------------------------
# Game Logic
# ---------------------------------------------------
if st.button("Submit Guess"):
    if guess.lower() == country["name"].lower():
        st.success(f"✅ Correct! It was {country['name']}.")
        st.session_state.score += 1
        st.session_state.tries = 0
        st.session_state.country = random.choice(countries)
    else:
        st.session_state.tries += 1
        if st.session_state.tries >= 3:
            st.error(f"❌ Out of tries! The correct answer was {country['name']}.")
            st.session_state.tries = 0
            st.session_state.country = random.choice(countries)
        else:
            st.warning(f"Wrong! Try again ({3 - st.session_state.tries} attempts left).")

# ---------------------------------------------------
# Score & Controls
# ---------------------------------------------------
st.metric("Score", st.session_state.score)
st.button("Next Country", on_click=lambda: st.session_state.update({
    "country": random.choice(countries),
    "tries": 0
}))