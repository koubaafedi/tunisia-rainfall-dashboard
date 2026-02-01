import streamlit as st
from .. import config

def render_about_page():
    """Renders the non-technical mission and overview page."""
    
    st.markdown("""
        <div style='text-align: center; padding: 20px 0 40px 0;'>
            <h1 style='margin: 0; color: #2c3e50;'>🌊 Information Hub</h1>
            <p style='color: #666; font-size: 1.2rem; font-weight: 300;'>
                Ensuring Water Security through Science and Intelligence
            </p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1.5, 1])

    with col1:
        st.markdown("### 🌟 Our Mission")
        st.write("""
            The **UK Groundwater Intelligence** project was founded with one primary objective: 
            **to safeguard the nation's most precious hidden resource.**
            
            Groundwater is the invisible lifeline of our ecosystem, providing drinking water, 
            supporting agriculture, and maintaining healthy river flows. This platform 
            transforms complex geospatial data into a simple, clear window into the 
            health of our aquifers.
        """)

        st.markdown("### 🧪 The Effective Recharge Approach")
        st.write("""
            Traditionally, monitoring focused solely on how much it rained. However, we know 
            that rainfall is only half the story. To truly understand groundwater, we must 
            account for **Evapotranspiration**—the water that returns to the atmosphere 
            through heat and plant life.
            
            Our model uses the **Effective Recharge Index**, which scientifically calculates 
            the water that actually reaches the deep groundwater layers. By subtracting 
            **Environment Agency scientific evaporation data (1km Grid)** from ground 
            rainfall, we provide a far more accurate prediction of our future water security.
        """)

    with col2:
        st.info("💡 **Did you know?**")
        st.write("""
            Over 30% of the UK’s public water supply comes from groundwater. In some regions 
            like the South East, it accounts for nearly 100%. Monitoring these levels is 
            not just data—it's disaster prevention.
        """)
        
        st.success("🛰️ **Project Scope**")
        st.write("""
            - **Stations**: 440+ Monitoring Points
            - **Methodology**: EA-Standard Hydraulic Balance
            - **Dataset**: PET 2025 (UK Operational)
        """)

        st.warning("⚖️ **Monitoring Integrity**")
        st.caption("""
            This platform uses verified national monitoring data. While our predictive 
            models are highly accurate, they are intended for strategic oversight. 
            Always refer to local water authorities for operational decisions.
        """)

    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #999; font-size: 0.9rem;'>
            Protecting the UK's Aquifers for Future Generations | v2.2 (Scientific Release)
        </div>
    """, unsafe_allow_html=True)
