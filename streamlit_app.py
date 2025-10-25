import streamlit as st
import requests
import random
import geopandas as gpd
import matplotlib.pyplot as plt
from io import BytesIO
from shapely.geometry import shape
from PIL import Image, ImageDraw

st.set_page_config(page_title="Guess the Country", layout="centered")

# -------------------------------
# API SOURCES
# -------------------------------
COUNTRY_API = "https://restcountries.com/v3.1/all"
GEOJSON_API = "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"

# -------------------------------
# Fetch all countries (cached)
# -------------------------------
@st.cache_data
def get_countries():
    countries = requests.get(COUNTRY_API).json()
    return [
        {
            "name": c["name"]["common"],
            "code": c["cca3"],
            "flag": c["flags"]["png"],
        }
        for c in countries
        if "name" in c and "cca3" in c
    ]

@st.cache_data
def get_world_geojson():
    data = requests.get(GEOJSON_API).json()
    return gpd.GeoDataFrame.from_features(data["features"])

# -------------------------------
# Utility functions
# -------------------------------
def get_country_shape(world_gdf, code):
    country = world_gdf[world_gdf["ISO_A3"] == code]
    return country if not country.empty else None

def overlay_flag_on_shape(flag_url, country_shape):
    # Download flag image
    flag_img = Image.open(BytesIO(requests.get(flag_url).content)).convert("RGBA")

    # Plot country shape to create a mask
    fig, ax = plt.subplots(figsize=(6, 4))
    country_shape.plot(ax=ax, color="white", edgecolor="black")
    ax.axis("off")

    # Convert plot to image mask
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, transparent=True)
    buf.seek(0)
    mask = Image.open(buf).convert("L")

    # Resize flag to mask
    flag_img = flag_img.resize(mask.size)

    # Composite: keep flag only where mask is white
    result = Image.composite(flag_img, Image.new("RGBA", flag_img.size, (0, 0, 0, 0)), mask)
    return result

# -------------------------------
# Game Logic
# -------------------------------
countries = get_countries()
world = get_world_geojson()

if "country" not in st.session_state:
    st.session_state.country = random.choice(countries)
    st.session_state.tries = 0
    st.session_state.score = 0

country = st.session_state.country
st.title("🌍 Guess the Country (API Version)")

# Get shape
country_shape = get_country_shape(world, country["code"])
if country_shape is not None:
    painted_map = overlay_flag_on_shape(country["flag"], country_shape)
    st.image(painted_map, caption="Guess which country this is!", use_container_width=True)
else:
    st.warning("Country shape not found, skipping map rendering.")

# Input for guess
guess = st.text_input("Enter your guess:").strip()

if st.button("Submit Guess"):
    if guess.lower() == country["name"].lower():
        st.success(f"✅ Correct! It was {country['name']}.")
        st.session_state.score += 1
        st.session_state.tries = 0
        st.session_state.country = random.choice(countries)
    else:
        st.session_state.tries += 1
        if st.session_state.tries >= 3:
            st.error(f"❌ Out of tries! It was {country['name']}.")
            st.session_state.tries = 0
            st.session_state.country = random.choice(countries)
        else:
            st.warning(f"Wrong! Try again ({3 - st.session_state.tries} attempts left).")

# Show score
st.metric("Score", st.session_state.score)
st.button("Next Country", on_click=lambda: st.session_state.update({
    "country": random.choice(countries),
    "tries": 0
}))