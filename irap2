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

# Step 1: Set up a cache for routes (cache entries expire after 1 hour)
route_cache = TTLCache(maxsize=1000, ttl=3600)

# Function to throttle requests (1 request per second)
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
        time.sleep(1)  # 1 second delay between requests to comply with rate limits

# Step 2: Caching the data to avoid reloading the same file repeatedly
@st.cache_data
def load_data(uploaded_file):
    df = pd.read_csv(uploaded_file)
    return df

# Function to calculate color based on KSI count
def get_color(ksi_count, ksi_min, ksi_max):
    norm = mcolors.Normalize(vmin=ksi_min, vmax=ksi_max)
    cmap = mcolors.LinearSegmentedColormap.from_list("", ["yellow", "red"])
    return mcolors.to_hex(cmap(norm(ksi_count)))

# Step 3: Streamlit app setup
st.title("OpenStreetMap + Streamlit Dashboard")

# Step 4: Upload a CSV file with routes (latitude and longitude data)
uploaded_file = st.file_uploader("Upload your CSV file with latitude/longitude data", type=["csv"])

if uploaded_file is not None:
    # Load the data using caching to avoid reloading on each rerun
    df = load_data(uploaded_file)

    # Check for required columns
    required_columns = ['latitude_S', 'longitude_S', 'Intermediate_Lat_Start', 'Intermediate_Lon_Start', 'Intermediate_Lat_End', 'Intermediate_Lon_End', 'KSI_Count', 'Speed_Limit', 'RoadNumber']
    if not all(col in df.columns for col in required_columns):
        st.error(f"CSV file must contain the following columns: {', '.join(required_columns)}")
    else:
        st.write("Data loaded successfully!")

        # Step 5: Interactive Filters (KSI range, Road Numbers, and Speed Limits)
        with st.sidebar:
            # Generate KSI count range in steps of 10
            ksi_min = int(df['KSI_Count'].min())
            ksi_max = int(df['KSI_Count'].max())
            ksi_range_options = list(range(ksi_min, ksi_max + 10, 10))

            # Selectbox for min KSI count
            selected_ksi_min = st.selectbox("Select Minimum KSI Count", options=ksi_range_options, index=0)

            # Selectbox for max KSI count
            selected_ksi_max = st.selectbox("Select Maximum KSI Count", options=ksi_range_options, index=len(ksi_range_options) - 1)

            # Ensure that selected min KSI is less than or equal to max KSI
            if selected_ksi_min > selected_ksi_max:
                st.warning("Minimum KSI count should be less than or equal to the maximum KSI count.")
                st.stop()

            # Checkbox to "Select All" for Road Numbers
            unique_road_numbers = df['RoadNumber'].unique().tolist()
            select_all_roads = st.checkbox("Select All Road Numbers")

            # Multiselect for road numbers
            if select_all_roads:
                selected_road_numbers = st.multiselect("Select Road Numbers", options=unique_road_numbers, default=unique_road_numbers)
            else:
                selected_road_numbers = st.multiselect("Select Road Numbers", options=unique_road_numbers, default=[])

            # Checkbox to "Select All" for speed limits
            unique_speed_limits = df['Speed_Limit'].unique().tolist()
            select_all_speeds = st.checkbox("Select All Speed Limits")

            # Multiselect for speed limits
            if select_all_speeds:
                selected_speed_limits = st.multiselect("Select Speed Limits", options=unique_speed_limits, default=unique_speed_limits)
            else:
                selected_speed_limits = st.multiselect("Select Speed Limits", options=unique_speed_limits, default=[])

        # Step 6: Filter Data based on User Selection
        filtered_df = df[(df['KSI_Count'] >= selected_ksi_min) &
                         (df['KSI_Count'] <= selected_ksi_max) &
                         (df['RoadNumber'].isin(selected_road_numbers)) &
                         (df['Speed_Limit'].isin(selected_speed_limits))]

        # Step 7: Optimize Data Display by limiting points
        if len(filtered_df) > 200:
            st.write("Large dataset, sampling 200 points for better performance.")
            filtered_df = filtered_df.sample(n=200)

        # Get min and max KSI for color mapping
        ksi_min = filtered_df['KSI_Count'].min()
        ksi_max = filtered_df['KSI_Count'].max()

        # Step 8: Create a map centered on the filtered points using Folium
        if not filtered_df.empty:
            center_lat = filtered_df['latitude_S'].mean()
            center_lon = filtered_df['longitude_S'].mean()
            m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles='cartodbpositron')  # Using a lighter tile

            # Add Marker Cluster
            marker_cluster = MarkerCluster().add_to(m)

            # Step 9: Plot data on the Folium map using CircleMarkers with colors based on KSI
            for _, row in filtered_df.iterrows():
                color = get_color(row['KSI_Count'], ksi_min, ksi_max)

                # Add CircleMarker for each data point
                folium.CircleMarker(
                    location=[row['latitude_S'], row['longitude_S']],
                    radius=5 + (row['KSI_Count'] - ksi_min) / (ksi_max - ksi_min) * 10,  # Adjust size based on KSI count
                    color=color,
                    fill=True,
                    fill_opacity=0.7,
                    popup=f"KSI: {row['KSI_Count']} | Speed: {row['Speed_Limit']}",
                ).add_to(marker_cluster)  # Add to marker cluster

            # Step 10: Display the map
            st_folium(m, width=1000, height=600)

        else:
            st.write("No data matches the selected filters.")
else:
    st.info("Please upload a CSV file to visualize the routes.")
