import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import requests
import time
from cachetools import TTLCache
import matplotlib.colors as mcolors

# Set Streamlit layout to wide
st.set_page_config(layout="wide")

# Set up a cache for routes (cache entries expire after 1 hour)
route_cache = TTLCache(maxsize=1000, ttl=3600)

# Throttle requests and cache the results
@st.cache_data(show_spinner=False)
def throttled_get_osrm_route(start_lat, start_lon, end_lat, end_lon):
    cache_key = (start_lat, start_lon, end_lat, end_lon)
    if cache_key in route_cache:
        return route_cache[cache_key]

    url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
    try:
        response = requests.get(url)
        if response.status_code == 429:
            # If rate-limited, wait a bit and retry
            time.sleep(1)
            response = requests.get(url)

        data = response.json()
        if data.get('routes'):
            route = data['routes'][0]['geometry']['coordinates']
            route_coords = [(lat, lon) for lon, lat in route]
            route_cache[cache_key] = route_coords
            return route_coords
        else:
            return None
    except Exception as e:
        st.error(f"Error fetching route: {e}")
        return None
    finally:
        # Throttle the requests
        time.sleep(1)

# Caching the uploaded CSV file
@st.cache_data(show_spinner=False)
def load_data(uploaded_file):
    return pd.read_csv(uploaded_file)

# Function to calculate color based on KSI count
def get_color(ksi_count, ksi_min, ksi_max):
    norm = mcolors.Normalize(vmin=ksi_min, vmax=ksi_max)
    cmap = mcolors.LinearSegmentedColormap.from_list("", ["yellow", "red"])
    return mcolors.to_hex(cmap(norm(ksi_count)))

# Streamlit app setup
st.title("OpenStreetMap + Streamlit Dashboard")

# Upload a CSV file with routes
uploaded_file = st.file_uploader("Upload your CSV file with latitude/longitude data", type=["csv"])

if uploaded_file:
    # Load the data using caching to avoid reloading on each rerun
    df = load_data(uploaded_file)

    # Check for required columns
    required_columns = ['latitude_S', 'longitude_S', 'Intermediate_Lat_Start', 'Intermediate_Lon_Start', 'Intermediate_Lat_End', 'Intermediate_Lon_End', 'KSI_Count', 'Speed_Limit', 'RoadNumber']
    if not all(col in df.columns for col in required_columns):
        st.error(f"CSV file must contain the following columns: {', '.join(required_columns)}")
    else:
        st.write("Data loaded successfully!")

        # Interactive Filters (KSI range, Road Numbers, and Speed Limits)
        with st.sidebar:
            # KSI count range
            ksi_min = int(df['KSI_Count'].min())
            ksi_max = int(df['KSI_Count'].max())
            selected_ksi_min, selected_ksi_max = st.slider(
                "Select KSI Count Range",
                min_value=ksi_min, max_value=ksi_max,
                value=(ksi_min, ksi_max)
            )

            # Road Numbers filter
            unique_road_numbers = df['RoadNumber'].unique().tolist()
            selected_road_numbers = st.multiselect(
                "Select Road Numbers",
                options=unique_road_numbers, default=unique_road_numbers
            )

            # Speed Limits filter
            unique_speed_limits = df['Speed_Limit'].unique().tolist()
            selected_speed_limits = st.multiselect(
                "Select Speed Limits",
                options=unique_speed_limits, default=unique_speed_limits
            )

        # Filter Data based on User Selection
        filtered_df = df[
            (df['KSI_Count'] >= selected_ksi_min) &
            (df['KSI_Count'] <= selected_ksi_max) &
            (df['RoadNumber'].isin(selected_road_numbers)) &
            (df['Speed_Limit'].isin(selected_speed_limits))
        ]

        # Optimize Data Display by limiting points
        if len(filtered_df) > 200:
            st.write("Large dataset, sampling 200 points for better performance.")
            filtered_df = filtered_df.sample(n=200)

        # Get min and max KSI for color mapping
        ksi_min = filtered_df['KSI_Count'].min()
        ksi_max = filtered_df['KSI_Count'].max()

        # Create a map centered on the filtered points using Folium
        if not filtered_df.empty:
            center_lat = filtered_df['latitude_S'].mean()
            center_lon = filtered_df['longitude_S'].mean()
            m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles='cartodbpositron')

            # Add Marker Cluster
            marker_cluster = MarkerCluster().add_to(m)

            # Plot data on the Folium map using CircleMarkers with colors based on KSI
            for _, row in filtered_df.iterrows():
                color = get_color(row['KSI_Count'], ksi_min, ksi_max)

                folium.CircleMarker(
                    location=[row['latitude_S'], row['longitude_S']],
                    radius=5 + (row['KSI_Count'] - ksi_min) / (ksi_max - ksi_min) * 10,  # Adjust size based on KSI count
                    color=color,
                    fill=True,
                    fill_opacity=0.7,
                    popup=f"KSI: {row['KSI_Count']} | Speed: {row['Speed_Limit']}",
                ).add_to(marker_cluster)

            # Display the map
            st_folium(m, width=1000, height=600)

        else:
            st.write("No data matches the selected filters.")
else:
    st.info("Please upload a CSV file to visualize the routes.")
