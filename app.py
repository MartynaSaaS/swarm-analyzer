import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json

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
}

DIRECTION_ORIGINS = {
    "North": (52.5, 31.5),
    "Northwest": (52.0, 24.0),
    "Northeast": (52.5, 38.0),
    "East": (49.5, 40.5),
    "West": (50.0, 22.0),
    "South": (45.5, 33.0),
}

DRONE_COLORS = {
    "Shahed": "#ef4444",
    "Lancet": "#f97316",
    "FPV": "#eab308",
    "Ballistic": "#dc2626",
    "Missile": "#dc2626",
    "Kalibr": "#dc2626",
    "Kinzhal": "#dc2626",
    "UAV": "#6b7280",
}

@st.cache_data
def load_data():
    try:
        df = pd.read_csv("attacks.csv")
        df["date"] = pd.to_datetime(df["date"])
        return df
    except:
        return pd.DataFrame()

@st.cache_data
def load_live_attacks():
    try:
        with open("live_attacks.json") as f:
            return json.load(f)
    except:
        return []

def predict_target(direction, df):
    subset = df[df["direction"] == direction]
    if len(subset) == 0:
        return "Unknown", 0, {}
    target_counts = subset["target"].value_counts()
    top_target = target_counts.index[0]
    confidence = int((target_counts.iloc[0] / len(subset)) * 100)
    distribution = (target_counts / len(subset) * 100).round(1).to_dict()
    return top_target, confidence, distribution

def build_map(df, selected_direction, predicted_target, live_attacks, selected_types):
    m = folium.Map(location=[49.0, 32.0], zoom_start=6, tiles="CartoDB dark_matter")

    # Plot live attacks filtered by type
    for a in live_attacks:
        if a["drone_type"] not in selected_types:
            continue
        color = DRONE_COLORS.get(a["drone_type"], "#6b7280")
        folium.CircleMarker(
            [a["lat"], a["lon"]],
            radius=6 + min(a["drone_count"] / 10, 8),
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            tooltip=f"{a['drone_type']} x{a['drone_count']} — {a['city']} ({a['date']})"
        ).add_to(m)

    # Incoming threat vector
    if selected_direction in DIRECTION_ORIGINS:
        origin = DIRECTION_ORIGINS[selected_direction]
        folium.PolyLine(
            [origin, [49.0, 32.0]],
            color="#ef4444", weight=3, opacity=0.9, dash_array="8 4"
        ).add_to(m)
        folium.Marker(
            origin,
            icon=folium.DivIcon(html='<div style="color:#ef4444;font-size:22px">▼</div>')
        ).add_to(m)

    # City markers
    for city, coord in CITIES.items():
        is_predicted = city.lower() == predicted_target.lower()
        color = "#ef4444" if is_predicted else "#3b82f6"
        radius = 14 if is_predicted else 7
        folium.CircleMarker(
            coord, radius=radius, color=color,
            fill=True, fill_color=color, fill_opacity=0.7, tooltip=city
        ).add_to(m)
        if is_predicted:
            folium.Circle(coord, radius=80000, color="#ef4444", fill=False, weight=2, opacity=0.6, dash_array="6").add_to(m)
            folium.Marker(coord, icon=folium.DivIcon(
                html=f'<div style="color:#ef4444;font-weight:bold;font-size:13px;white-space:nowrap;margin-top:-22px">⚠ {city}</div>'
            )).add_to(m)
    return m

# Load data
df = load_data()
live_attacks = load_live_attacks()
all_types = list(set(a["drone_type"] for a in live_attacks))

# Sidebar
with st.sidebar:
    st.markdown("## 🎯 Swarm Analyzer")
    st.markdown("---")
    st.markdown("### Incoming threat")
    direction = st.selectbox("Approach direction", ["Northwest", "Northeast", "North", "East", "West", "South"])
    hour = st.slider("Time of attack (hour)", 0, 23, 2)
    drone_count = st.slider("Estimated drone count", 1, 200, 12)
    st.markdown("---")
    st.markdown("### Filter by drone type")
    selected_types = st.multiselect("Show on map", all_types, default=all_types)
    st.markdown("---")
    st.markdown(f'<div class="metric-box"><small>Attack records loaded</small><br><b style="font-size:18px">{len(live_attacks)}</b></div>', unsafe_allow_html=True)

predicted_target, confidence, distribution = predict_target(direction, df)

# Header
st.markdown('<h1 style="color:#ef4444;font-family:monospace;letter-spacing:3px">⚠ SWARM INTELLIGENCE ANALYZER</h1>', unsafe_allow_html=True)
st.markdown(f'<p style="color:#6b7280;font-family:monospace">{len(live_attacks)} ATTACK RECORDS — {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")} UTC</p>', unsafe_allow_html=True)

# Metrics
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
    m = build_map(df, direction, predicted_target, live_attacks, selected_types)
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

    st.markdown("### 📡 Attack log")
    recent = sorted(live_attacks, key=lambda x: x["date"], reverse=True)
    for a in recent[:8]:
        color = DRONE_COLORS.get(a["drone_type"], "#6b7280")
        st.markdown(f'<div class="metric-box" style="margin:3px 0;border-left:3px solid {color}"><span style="font-size:11px;color:{color}">{a["drone_type"]} x{a["drone_count"]} · {a["date"]}</span><br><span style="font-size:12px">{a["city"]} — {a["title"][:60]}</span></div>', unsafe_allow_html=True)