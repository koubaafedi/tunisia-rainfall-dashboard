import streamlit as st
from .. import config

def apply_custom_css():
    """Injects high-end, premium CSS tokens and font-awesome icons."""
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
        
        html, body, [class*="css"] {{
            font-family: 'Poppins', sans-serif;
            color: {config.THEME_COLORS["text_main"]};
        }}
        
        .stApp {{
            background-color: {config.THEME_COLORS["background"]};
        }}
        
        /* Metric Card Premium Styling */
        div[data-testid="stMetric"] {{
            background: #ffffff;
            padding: 20px;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.04);
            border: 1px solid #f0f0f0;
            transition: transform 0.2s ease;
        }}
        
        div[data-testid="stMetric"]:hover {{
            transform: translateY(-2px);
            border-color: {config.THEME_COLORS["primary"]};
        }}
        
        /* Tab Styling */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 24px;
        }}
        
        /* Marker badges for map */
        .marker-badge {{
            background-color: white;
            border-radius: 50%;
            box-shadow: 0 4px 10px rgba(0,0,0,0.12);
            border: 2px solid #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            transition: all 0.2s ease;
        }}
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    """, unsafe_allow_html=True)
