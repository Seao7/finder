import streamlit as st
import pandas as pd
import requests
import time
import io
import base64
from tqdm.auto import tqdm
import os
from dotenv import load_dotenv


st.set_page_config(
    page_title="India Places Finder",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS for better appearance
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 1rem;
    }
    .subtitle {
        font-size: 1.2rem;
        color: #4B5563;
        margin-bottom: 2rem;
    }
    .stProgress > div > div > div > div {
        background-color: #1E3A8A;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .success {
        background-color: #D1FAE5;
        color: #065F46;
    }
    .info {
        background-color: #E0F2FE;
        color: #0369A1;
    }
    .warning {
        background-color: #FEF3C7;
        color: #92400E;
    }
</style>
""", unsafe_allow_html=True)

# App title and description
st.markdown('<div class="title">India Places Finder 🔍</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Search for any places across Indian cities and download detailed information</div>', unsafe_allow_html=True)

# Function to get places
def get_places(city, api_key, search_term, status_placeholder=None):
    """Fetch place names, addresses, and contact numbers for a given city with pagination."""
    query = f"{search_term} in {city}"
    
    if status_placeholder:
        status_placeholder.markdown(f"🔍 Searching for '{query}' in {city}...")
    search_url = "https://places.googleapis.com/v1/places:searchText"
    
    search_payload = {"textQuery": query}
    search_headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.id,nextPageToken"
    }
    results = []
    
    page_count = 1
    max_pages = 5  # Set a reasonable limit to avoid excessive API calls
    
    while page_count <= max_pages:
        try:
            if status_placeholder:
                status_placeholder.markdown(f"📄 Fetching page {page_count}...")
                
            search_response = requests.post(search_url, json=search_payload, headers=search_headers)
            search_data = search_response.json()
            
            if "places" not in search_data:
                if status_placeholder:
                    status_placeholder.markdown(f"❌ No results found for {city} or API error.")
                return results  # Return any previously fetched results
            
            place_count = len(search_data['places'])
            if status_placeholder:
                status_placeholder.markdown(f"📍 Found {place_count} places on page {page_count}. Fetching details...")
            
            for place in search_data["places"]:
                place_id = place["id"]
                name = place["displayName"]['text']
                address = place["formattedAddress"]
                # Fetch additional details
                details_url = f"https://places.googleapis.com/v1/places/{place_id}"
                details_headers = {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": "displayName,formattedAddress,nationalPhoneNumber,rating,userRatingCount,websiteUri,types"
                }
                
                details_response = requests.get(details_url, headers=details_headers)
                details_data = details_response.json()
                # Extract additional fields
                phone = details_data.get("nationalPhoneNumber", "N/A")
                rating = details_data.get("rating", 0)
                rating_count = details_data.get("userRatingCount", 0)
                website = details_data.get("websiteUri", "N/A")
                types = ", ".join(details_data.get("types", [])) if "types" in details_data else "N/A"
                results.append({
                    "City": city, 
                    "Name": name, 
                    "Address": address, 
                    "Phone": phone,
                    "Rating": rating,
                    "Rating Count": rating_count,
                    "Website": website,
                    "Types": types
                })
                time.sleep(0.5)  # To avoid hitting rate limits
            
            # Handle pagination
            next_page_token = search_data.get("nextPageToken")
            if not next_page_token:
                if status_placeholder:
                    status_placeholder.markdown(f"ℹ️ No more pages available after page {page_count}.")
                break  # No more results, exit loop
                
            page_count += 1
            if status_placeholder:
                status_placeholder.markdown(f"⏳ Waiting before fetching next page...")
            time.sleep(2)  # Required delay before making the next request with page token
            search_payload = {"textQuery": query, "pageToken": next_page_token}  # Create new payload with token
        
        except Exception as e:
            if status_placeholder:
                status_placeholder.markdown(f"❌ Error while processing page {page_count} for {city}: {str(e)}")
            break  # Stop processing in case of an error
    
    if status_placeholder:
        status_placeholder.markdown(f"✅ Successfully fetched {len(results)} places in {city} across {page_count} pages.")
    
    return results

# Function to create a download link for dataframe
def get_download_link(df, filename, text):
    """Generate a download link for a dataframe"""
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_buffer.seek(0)
    b64 = base64.b64encode(excel_buffer.read()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">{text}</a>'
    return href

# Sidebar for configuration
st.sidebar.header("Search Configuration")

# API Key input
api_key = st.sidebar.text_input("Google Places API Key", type="password", help="Enter your Google Places API key")

# Search term input with examples
st.sidebar.subheader("What are you looking for?")
search_examples = [
    "JEE Coaching", 
    "NEET Coaching", 
    "Restaurants", 
    "Cafes", 
    "Hotels", 
    "Hospitals", 
    "Schools", 
    "Colleges",
    "Shopping Malls",
    "Gyms",
    "Parks",
    "Movie Theaters"
]

# Display example search terms
# Display example search terms
st.sidebar.markdown("**Popular searches:**")
example_cols = st.sidebar.columns(2)

# Check if we need to initialize the selected example
if 'selected_example' not in st.session_state:
    st.session_state.selected_example = None

# Function to set selected example when a button is clicked
def set_example(example):
    st.session_state.selected_example = example
    st.session_state.search_term = example

# Create buttons for examples
for i, example in enumerate(search_examples):
    if i % 2 == 0:
        example_cols[0].button(example, key=f"example_{i}", on_click=set_example, args=(example,))
    else:
        example_cols[1].button(example, key=f"example_{i}", on_click=set_example, args=(example,))

# Use the selected example or user input for search term
if st.session_state.selected_example:
    default_search = st.session_state.selected_example
elif 'search_term' in st.session_state:
    default_search = st.session_state.search_term
else:
    default_search = "JEE Coaching"

search_term = st.sidebar.text_input("Search Term", value=default_search, 
                                   help="Enter what you want to search for")

# Update session state
st.session_state.search_term = search_term
# City selection with categories
st.sidebar.subheader("Select Cities")

# Pre-defined city lists
MAJOR_CITIES = ["Delhi", "Mumbai", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow"]
TIER_2_CITIES = ["Bhopal", "Indore", "Nagpur", "Chandigarh", "Patna", "Visakhapatnam", "Coimbatore", "Thiruvananthapuram", "Vadodara", "Ludhiana"]
EDUCATIONAL_HUBS = ["Kota", "Dehradun", "Vellore", "Manipal", "Pilani", "Roorkee", "Kharagpur", "Varanasi", "Aligarh", "Guwahati"]
TOURIST_PLACES = ["Jaisalmer", "Udaipur", "Goa", "Shimla", "Manali", "Darjeeling", "Ooty", "Rishikesh", "Agra", "Amritsar"]
OTHER_CITIES = ["Meerut", "Jodhpur", "Gwalior", "Ranchi", "Mysore", "Hubli", "Salem", "Guntur", "Thrissur", "Jalandhar", "Siliguri", "Bhubaneswar", "Noida"]

# City selection options
select_all = st.sidebar.checkbox("Select All Cities")
city_categories = [
    ("Major Cities", MAJOR_CITIES),
    ("Tier 2 Cities", TIER_2_CITIES),
    ("Educational Hubs", EDUCATIONAL_HUBS),
    ("Tourist Places", TOURIST_PLACES)
]

category_selections = {}
for category_name, _ in city_categories:
    category_selections[category_name] = st.sidebar.checkbox(f"Select {category_name}")

# Custom city input
custom_city = st.sidebar.text_input("Add Custom City")

# Create containers for the different sections
st.sidebar.subheader("Selected Cities")
city_container = st.sidebar.container()

# Initialize selected cities list
if 'selected_cities' not in st.session_state:
    st.session_state.selected_cities = []

# Update selected cities based on checkboxes
if select_all:
    all_cities = []
    for _, cities in city_categories:
        all_cities.extend(cities)
    all_cities.extend(OTHER_CITIES)
    st.session_state.selected_cities = all_cities
else:
    temp_cities = []
    for category_name, cities in city_categories:
        if category_selections[category_name]:
            temp_cities.extend(cities)
    st.session_state.selected_cities = temp_cities

# Add custom city if provided
if custom_city and custom_city not in st.session_state.selected_cities:
    st.session_state.selected_cities.append(custom_city)

# Display and let user modify selected cities
with city_container:
    # Convert to a set temporarily to remove duplicates
    unique_cities = list(set(st.session_state.selected_cities))
    unique_cities.sort()  # Sort for better UI
    
    # Get all possible cities
    all_possible_cities = []
    for _, cities in city_categories:
        all_possible_cities.extend(cities)
    all_possible_cities.extend(OTHER_CITIES)
    
    # Show multiselect with current selections
    selected = st.multiselect(
        "Manage selected cities:",
        options=unique_cities + [city for city in all_possible_cities if city not in unique_cities],
        default=unique_cities
    )
    
    # Update the session state
    st.session_state.selected_cities = selected

# Main search function
search_button = st.sidebar.button("Start Search", type="primary", disabled=not api_key or not st.session_state.selected_cities)

# Main content area
main_container = st.container()
results_container = st.container()

with main_container:
    if not api_key:
        st.markdown('<div class="status-box warning">⚠️ Please enter your Google Places API Key in the sidebar to continue.</div>', unsafe_allow_html=True)
    elif not st.session_state.selected_cities:
        st.markdown('<div class="status-box warning">⚠️ Please select at least one city to search.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="status-box info">🔍 Ready to search for "{search_term}" in {len(st.session_state.selected_cities)} cities.</div>', unsafe_allow_html=True)

# Initialize session state for results
if 'search_results' not in st.session_state:
    st.session_state.search_results = []

# Run search when button is clicked
if search_button:
    all_results = []
    status_placeholder = st.empty()
    progress_bar = st.progress(0)
    
    # Clear previous results
    st.session_state.search_results = []
    
    # Setup search
    total_cities = len(st.session_state.selected_cities)
    status_placeholder.markdown(f"🚀 Starting search for {search_term} in {total_cities} cities...")
    
    # Perform search for each city
    for i, city in enumerate(st.session_state.selected_cities):
        progress = (i) / total_cities
        progress_bar.progress(progress)
        
        city_results = get_places(city, api_key, search_term, status_placeholder)
        all_results.extend(city_results)
        
        # Update progress
        status_text = f"Processed {i+1}/{total_cities} cities. Found {len(all_results)} places so far."
        progress_bar.progress((i+1) / total_cities)
        
        # Small delay to avoid API rate limits
        time.sleep(1)
    
    # Update session state with results
    st.session_state.search_results = all_results
    
    # Show completion message
    status_placeholder.markdown(f"✅ Search completed! Found {len(all_results)} places across {total_cities} cities.")
    progress_bar.progress(1.0)

# Add filename customization
filename_base = search_term.lower().replace(" ", "_")

# Display results
with results_container:
    if st.session_state.search_results:
        st.subheader(f"Search Results: {len(st.session_state.search_results)} Places Found")
        
        # Create DataFrame from results
        df = pd.DataFrame(st.session_state.search_results)
        
        # Add filters
        filter_col1, filter_col2 = st.columns(2)
        
        with filter_col1:
            # City filter
            if len(df['City'].unique()) > 1:
                city_filter = st.multiselect("Filter by City:", options=sorted(df['City'].unique()), default=sorted(df['City'].unique()))
                if city_filter:
                    df = df[df['City'].isin(city_filter)]
        
        with filter_col2:
            # Rating filter
            if 'Rating' in df.columns and df['Rating'].dtype != object:
                min_rating = float(df['Rating'].min()) if not pd.isna(df['Rating'].min()) else 0
                max_rating = float(df['Rating'].max()) if not pd.isna(df['Rating'].max()) else 5
                rating_filter = st.slider("Minimum Rating:", min_value=0.0, max_value=5.0, value=min_rating, step=0.5)
                df = df[df['Rating'] >= rating_filter]
        
        # Sort options
        sort_col1, sort_col2 = st.columns(2)
        with sort_col1:
            sort_by = st.selectbox("Sort by:", options=["City", "Name", "Rating"])
        with sort_col2:
            sort_order = st.radio("Order:", options=["Ascending", "Descending"], horizontal=True)
        
        # Apply sorting
        if sort_by == "Rating" and "Rating" in df.columns:
            # Convert Rating to numeric for proper sorting
            df["Rating"] = pd.to_numeric(df["Rating"], errors='coerce')
        
        df = df.sort_values(by=sort_by, ascending=(sort_order == "Ascending"))
        
        # Display results
        st.dataframe(df, use_container_width=True)
        
        # Download options
        st.markdown("### Download Options")
        
        # Custom filename
        custom_filename = st.text_input("Filename (without extension):", value=f"{filename_base}_places")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Excel download
            excel_file = f"{custom_filename}.xlsx"
            excel_href = get_download_link(df, excel_file, "Download Excel File")
            st.markdown(excel_href, unsafe_allow_html=True)
        
        with col2:
            # CSV download
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            b64 = base64.b64encode(csv_buffer.getvalue().encode()).decode()
            csv_href = f'<a href="data:text/csv;base64,{b64}" download="{custom_filename}.csv">Download CSV File</a>'
            st.markdown(csv_href, unsafe_allow_html=True)
        
        # Show data summary
        if not df.empty:
            st.subheader("Data Summary")
            
            summary_col1, summary_col2 = st.columns(2)
            
            with summary_col1:
                st.metric("Total Places Found", len(df))
                st.metric("Cities Covered", len(df['City'].unique()))
                
            with summary_col2:
                if "Rating" in df.columns:
                    avg_rating = df["Rating"].mean() if not pd.isna(df["Rating"].mean()) else "N/A"
                    if isinstance(avg_rating, float):
                        st.metric("Average Rating", f"{avg_rating:.2f}")
                
                top_city = df['City'].value_counts().index[0] if not df['City'].value_counts().empty else "N/A"
                st.metric("Top City", f"{top_city} ({df['City'].value_counts().iloc[0]} places)")
