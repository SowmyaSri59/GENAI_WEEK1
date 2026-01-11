import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests

# ================= PAGE CONFIG =================
st.set_page_config(page_title="IMDb Top 1000 Analyzer", layout="wide")
st.title("FILM FUSION DASHBOARD")

# ================= OMDb CONFIG =================
OMDB_API_KEY = "1868b4aa"
PLACEHOLDER_POSTER = "https://upload.wikimedia.org/wikipedia/commons/6/65/No-Image-Placeholder.svg"

# ================= POSTER FETCH =================
@st.cache_data(show_spinner=False)
def fetch_poster(title, year):
    try:
        response = requests.get(
            "https://www.omdbapi.com/",
            params={"t": title, "y": year, "apikey": OMDB_API_KEY},
            timeout=5
        )
        data = response.json()
        poster = data.get("Poster")
        if poster and poster != "N/A":
            return poster.replace("http://", "https://")
    except Exception:
        pass
    return PLACEHOLDER_POSTER

# ================= LOAD DATA =================
uploaded = st.file_uploader("Upload IMDb Top 1000 CSV file", type=["csv"])
if not uploaded:
    st.info("Please upload the IMDb Top 1000 CSV file.")
    st.stop()

@st.cache_data
def load_data(file):
    return pd.read_csv(file)

df = load_data(uploaded)

# ================= ROBUST COLUMN RENAMING =================
rename_map = {}
if "Series_Title" in df.columns:
    rename_map["Series_Title"] = "Movie_Title"
if "Released_Year" in df.columns:
    rename_map["Released_Year"] = "Year"
if "IMDB_Rating" in df.columns:
    rename_map["IMDB_Rating"] = "IMDb_Rating"

df.rename(columns=rename_map, inplace=True)

# ================= REQUIRED COLUMN CHECK =================
required_cols = ["Movie_Title", "Year", "IMDb_Rating", "Genre"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"Missing required columns: {missing}")
    st.stop()

# ================= CLEAN DATA =================
df = df.dropna(subset=["Movie_Title", "Year", "IMDb_Rating", "Genre"])
df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
df = df.dropna(subset=["Year"])
df["Year"] = df["Year"].astype(int)
df["IMDb_Rating"] = pd.to_numeric(df["IMDb_Rating"], errors="coerce")
df = df.dropna(subset=["IMDb_Rating"])

# ================= SIDEBAR FILTERS =================
st.sidebar.header("Filter Options")
year_min = int(df["Year"].min())
year_max = int(df["Year"].max())
year_range = st.sidebar.slider("Select Year Range", year_min, year_max, (year_min, year_max))

min_rating = st.sidebar.slider("Minimum IMDb Rating", 0.0, 10.0, 7.0, 0.1)

all_genres = sorted({g.strip() for genre in df["Genre"] for g in genre.split(",")})
selected_genres = st.sidebar.multiselect("Select Genres", all_genres)

search_query = st.sidebar.text_input("Search Movie by Title", placeholder="Enter movie name")

# ================= APPLY FILTERS =================
filtered = df[
    (df["Year"] >= year_range[0]) &
    (df["Year"] <= year_range[1]) &
    (df["IMDb_Rating"] >= min_rating)
]

if selected_genres:
    filtered = filtered[filtered["Genre"].apply(lambda g: any(x in g for x in selected_genres))]

if search_query:
    filtered = filtered[filtered["Movie_Title"].str.contains(search_query, case=False, na=False)]

st.subheader(f"{len(filtered)} movies found")

# ================= RAW DATA =================
if st.checkbox("Show Raw Data"):
    st.dataframe(filtered)

# ================= VISUALIZATIONS =================
if not filtered.empty and "IMDb_Rating" in filtered.columns:
    st.subheader("IMDb Rating Distribution")
    fig1, ax1 = plt.subplots(figsize=(6, 3))
    ax1.hist(filtered["IMDb_Rating"], bins=20, color="skyblue", edgecolor="black")
    ax1.set_xlabel("IMDb Rating")
    ax1.set_ylabel("Count")
    st.pyplot(fig1)

    st.subheader("Movies Per Year")
    fig2, ax2 = plt.subplots(figsize=(6, 3))
    year_counts = filtered["Year"].value_counts().sort_index()
    ax2.bar(year_counts.index, year_counts.values, color="lightgreen")
    ax2.set_xlabel("Year")
    ax2.set_ylabel("Number of Movies")
    st.pyplot(fig2)

    st.subheader("Top Genres")
    genre_counts = (
        filtered["Genre"]
        .str.split(",")
        .explode()
        .str.strip()
        .value_counts()
        .head(10)
    )
    st.bar_chart(genre_counts)

# ================= MOVIE CARDS =================
if not filtered.empty:
    st.subheader("Top Rated Movies")
    top_movies = filtered.sort_values("IMDb_Rating", ascending=False).head(6)
    cols = st.columns(3)
    for i, (_, row) in enumerate(top_movies.iterrows()):
        with cols[i % 3]:
            poster_url = fetch_poster(row["Movie_Title"], row["Year"])
            st.image(poster_url, width=250)
            director = row["Director"] if "Director" in row else "N/A"
            star1 = row["Star1"] if "Star1" in row else "N/A"
            st.markdown(
                f"""
                **{row['Movie_Title']}**  
                Rating: {row['IMDb_Rating']}  
                Director: {director}  
                Star: {star1}  
                Genre: {row['Genre']}  
                Year: {row['Year']}
                """
            )

# ================= DOWNLOAD =================
if not filtered.empty:
    st.download_button(
        "Download Filtered Dataset",
        filtered.to_csv(index=False),
        file_name="imdb_filtered_data.csv",
        mime="text/csv"
    )
