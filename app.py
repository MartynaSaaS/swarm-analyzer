import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import feedparser
import requests
from datetime import datetime
import re

st.set_page_config(page_title="Swarm Intelligence Analyzer", page_icon="🎯", layout="wide")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background-color: #0a0e1a; }
[data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #1f2937; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
h1, h2, h3, p, label { color: #e2e8f0 !important; }
.metric-box { background: #1a2235; border: 1px solid #2d3748; border-radius: 8px; padding: 12px 16px; margin: 6px 0; }
.threat-high { border-left: 4px solid #ef4444; }
.threat-med { border-left: 4px solid #f59e0b; }
.stButton>button { background: #1d4ed8; color: white; border: none; border-radius: 6px; width: 100%; padding: 10px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

CITIES = {
    "Kyiv": (50.4501, 30.5234),
    "Kharkiv": (49.9935, 36.2304),
    "Odesa": (46.4825, 30.7233),
    "Dnipro": (48.4647, 35.0462),
    "Zaporizhzhia": (47.8388, 35.1396),
    "Lviv": (49.8397, 24.0297),
    "Mykolaiv": (46.9750, 31.9946),
    "Kherson": (46.6354, 32.6169),
    "Poltava": (49.5883, 34.5514),
    "Sumy": (50.9077, 34.7981),
    "Kharkiv Oblast": (49.9935, 36.2304),
    "Kyiv Oblast": (50.4501, 30.5234),
}

DIRECTION_ORIGINS = {
    "North": (52.5, 31.5),
    "Northwest": (52.0, 24.0),
    "Northeast": (52.5, 38.0),
    "East": (49.5, 40.5),
    "West": (50.0, 22.0),
    "South": (45.5, 33.0),
}

DRONE_TYPES = {
    "shahed": "🔴 Shahed",
    "lancet": "🟠 Lancet",
    "fpv": "🟡 FPV",
    "orlan": "🟡 Orlan",
    "iskander": "🔴 Iskander",
    "kalibr": "🔴 Kalibr",
    "kinzhal": "🔴 Kinzhal",
    "geran": "🔴 Shahed/Geran",
    "baba yaga": "🟠 Baba Yaga",
    "ballistic": "🔴 Ballistic",
    "missile": "🔴 Missile",
    "drone": "⚪ UAV",
}

CITY_TO_DIRECTION = {
    "kharkiv": "Northeast", "sumy": "North", "kyiv": "North",
    "dnipro": "East", "zaporizhzhia": "East", "odesa": "South",
    "lviv": "West", "mykolaiv": "South", "kherson": "South",
    "poltava": "Northeast", "chernihiv": "North",
}

@st.cache_data(ttl=600)
def fetch_real_attacks():
    feeds = [
        "https://newsukraine.rbc.ua/rss.xml",
        "https://kyivindependent.com/feed/",
    ]
    attacks = []
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:50]:
                title = entry.get("title", "").lower()
                summary = entry.get("summary", "").lower()
                text = title + " " + summary
                attack_keywords = ["drone", "shahed", "missile", "strike", "attack", "uav", "ballistic", "geran"]
                if not any(k in text for k in attack_keywords):
                    continue
                drone_type = "⚪ UAV"
                for k, v in DRONE_TYPES.items():
                    if k in text:
                        drone_type = v
                        break
                target_city = "Unknown"
                direction = "North"
                for city, dir in CITY_TO_DIRECTION.items():
                    if city in text:
                        target_city = city.capitalize()
                        direction = dir
                        break
                drone_count = 1
                count_match = re.search(r'(\d+)\s*(drone|uav|shahed|missile)', text)
                if count_match:
                    drone_count = min(int(count_match.group(1)), 200)
                pub_date = entry.get("published", str(datetime.now()))[:10]
                attacks.append({
                    "date": pub_date,
                    "direction": direction,
                    "target": target_city,
                    "drone_count": drone_count,
                    "drone_type": drone_type,
                    "hour": datetime.now().hour,
                    "title": entry.get("title", "")[:100],
                    "lat": CITIES.get(target_city.capitalize(), (49.0, 32.0))[0],
                    "lon": CITIES.get(target_city.capitalize(), (49.0, 32.0))[1],
                })
        except Exception as e:
            pass
    return attacks

@st.cache_data
def load_data():
    try:
        df = pd.read_csv("attacks.csv")
        df["date"] = pd.to_datetime(df["date"])
        return df
    except:
        return pd.DataFrame()

def predict_target(direction, df):
    subset = df[df["direction"] == direction]
    if len(subset) == 0:
        return "Unknown", 0, {}
    target_counts = subset["target"].value_counts()
    top_target = target_counts.index[0]
    confidence = int((target_counts.iloc[0] / len(subset)) * 100)
    distribution = (target_counts / len(subset) * 100).round(1).to_dict()
    return top_target, confidence, distribution

def build_map(df, selected_direction, predicted_target, live_attacks):
    m = folium.Map(location=[49.0, 32.0], zoom_start=6, tiles="CartoDB dark_matter")

    # Historical attack lines
    DIRECTION_ORIGINS_MAP = DIRECTION_ORIGINS
    TARGET_CITY_MAP = {
        "Power station": "Kharkiv", "Bridge": "Dnipro",
        "Fuel depot": "Odesa", "Railway hub": "Kyiv", "Military base": "Zaporizhzhia",
    }
    for _, row in df.iterrows():
        origin = DIRECTION_ORIGINS_MAP.get(row["direction"])
        city = TARGET_CITY_MAP.get(row["target"])
        target_coord = CITIES.get(city)
        if origin and target_coord:
            folium.PolyLine([origin, target_coord], color="#374151", weight=0.6, opacity=0.2).add_to(m)

    # Live attack markers
    for attack in live_attacks[:20]:
        lat, lon = attack["lat"], attack["lon"]
        if lat and lon:
            folium.CircleMarker(
                [lat, lon],
                radius=8,
                color="#f59e0b",
                fill=True,
                fill_color="#f59e0b",
                fill_opacity=0.8,
                tooltip=f"{attack['drone_type']} — {attack['title'][:60]}"
            ).add_to(m)

    # Incoming threat vector
    if selected_direction in DIRECTION_ORIGINS:
        origin = DIRECTION_ORIGINS[selected_direction]
        folium.PolyLine([origin, [49.0, 32.0]], color="#ef4444", weight=3, opacity=0.9, dash_array="8 4").add_to(m)
        folium.Marker(origin, icon=folium.DivIcon(html='<div style="color:#ef4444;font-size:22px">▼</div>')).add_to(m)

    # City markers
    for city, coord in CITIES.items():
        is_predicted = city.lower() in predicted_target.lower()
        color = "#ef4444" if is_predicted else "#3b82f6"
        radius = 14 if is_predicted else 6
        folium.CircleMarker(coord, radius=radius, color=color, fill=True, fill_color=color, fill_opacity=0.7, tooltip=city).add_to(m)
        if is_predicted:
            folium.Circle(coord, radius=80000, color="#ef4444", fill=False, weight=2, opacity=0.6, dash_array="6").add_to(m)
            folium.Marker(coord, icon=folium.DivIcon(html=f'<div style="color:#ef4444;font-weight:bold;font-size:13px;white-space:nowrap;margin-top:-22px">⚠ {city}</div>')).add_to(m)

    return m

# Sidebar
with st.sidebar:
    st.markdown("## 🎯 Swarm Analyzer")
    st.markdown("---")
    st.markdown("### Incoming threat")
    direction = st.selectbox("Approach direction", ["Northwest", "Northeast", "North", "East", "West", "South"])
    hour = st.slider("Time of attack (hour)", 0, 23, 2)
    drone_count = st.slider("Estimated drone count", 1, 200, 12)
    st.markdown("---")
    st.markdown("### 🔴 Live data")
    live_attacks = fetch_real_attacks()
    st.markdown(f'<div class="metric-box threat-high"><small>Live reports fetched</small><br><b style="font-size:18px">{len(live_attacks)}</b></div>', unsafe_allow_html=True)

df = load_data()
predicted_target, confidence, distribution = predict_target(direction, df)

st.markdown('<h1 style="color:#ef4444;font-family:monospace;letter-spacing:3px">⚠ SWARM INTELLIGENCE ANALYZER</h1>', unsafe_allow_html=True)
st.markdown(f'<p style="color:#6b7280;font-family:monospace">LIVE FEED ACTIVE — {len(live_attacks)} REAL REPORTS — {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")} UTC</p>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="metric-box threat-high"><small>Predicted target</small><br><b style="font-size:18px">{predicted_target}</b></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-box threat-med"><small>Confidence</small><br><b style="font-size:18px">{confidence}%</b></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric-box"><small>Drone count</small><br><b style="font-size:18px">{drone_count}</b></div>', unsafe_allow_html=True)
with col4:
    night = "Yes 🌙" if hour < 6 or hour > 21 else "No ☀️"
    st.markdown(f'<div class="metric-box"><small>Night attack</small><br><b style="font-size:18px">{night}</b></div>', unsafe_allow_html=True)

map_col, report_col = st.columns([2, 1])

with map_col:
    m = build_map(df, direction, predicted_target, live_attacks)
    st_folium(m, width=None, height=540)

with report_col:
    st.markdown("### Intelligence report")
    st.markdown(f'<div class="metric-box threat-high"><b>THREAT ASSESSMENT</b><br><br>Direction: <b>{direction}</b><br>Time: <b>{hour:02d}:00</b><br>Drones: <b>{drone_count}</b><br>Type: <b>{"Night raid" if hour < 6 or hour > 21 else "Daylight strike"}</b></div>', unsafe_allow_html=True)

    st.markdown("**Target probability**")
    for target, pct in sorted(distribution.items(), key=lambda x: -x[1]):
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        color = "#ef4444" if target == predicted_target else "#6b7280"
        st.markdown(f'<div style="font-size:12px;color:{color};margin:3px 0">{target[:16]:<16} {bar} {pct:.0f}%</div>', unsafe_allow_html=True)

    if not df.empty:
        same_dir = df[df["direction"] == direction]
        st.markdown(f'<div class="metric-box" style="margin-top:8px"><small>Based on <b>{len(same_dir)}</b> historical attacks<br>Avg drones: <b>{same_dir["drone_count"].mean():.0f}</b></small></div>', unsafe_allow_html=True)

    st.markdown("### 📡 Live reports")
    if live_attacks:
        for a in live_attacks[:8]:
            st.markdown(f'<div class="metric-box" style="margin:3px 0"><span style="font-size:11px">{a["drone_type"]} · {a["date"]}</span><br><span style="font-size:12px">{a["title"][:75]}</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="metric-box"><small>Fetching live reports...</small></div>', unsafe_allow_html=True)