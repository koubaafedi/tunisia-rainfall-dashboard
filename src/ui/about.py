import streamlit as st
from .. import config

def render_about_page():
    """Renders the comprehensive project and technical documentation page."""
    
    st.markdown("""
        <div style='text-align: center; padding: 10px 0 30px 0;'>
            <h1 style='margin: 0;'>📖 Information Hub</h1>
            <p style='color: #666; font-size: 1.1rem;'>
                Project Overview, Technical Architecture, and Data Transparency
            </p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        with st.expander("🌟 Project Mission", expanded=True):
            st.write("""
                The **UK Groundwater Intelligence** platform is designed to provide real-time operational oversight 
                of the national groundwater network. By bridging the gap between raw sensors and actionable 
                intelligence, the dashboard enables stakeholders to monitor water level trends against 
                dynamic historical benchmarks.
                
                **Key Objectives:**
                - **Operational Visibility**: Real-time monitoring of 440+ stations across the UK.
                - **Trend Intelligence**: Identification of rising or falling levels through automated delta analysis.
                - **Data Integration**: Harmonizing disparate data sources from national monitoring bodies.
            """)

        with st.expander("🔍 Data Architecture & Endpoints", expanded=True):
            st.write(f"""
                This platform utilizes the **Environment Agency's Open Data APIs** to aggregate real-time 
                observations and historical snapshots.
                
                **Primary Endpoints:**
                - **Hydrology API**: Used for comprehensive station metadata, aquifer classifications, and 
                  historical records.
                    - `Endpoint`: [{config.HYDRO_STATIONS_URL.split('?')[0]}](https://environment.data.gov.uk/hydrology/doc/reference)
                - **Flood Monitoring API**: Used for real-time readings and measure definitions.
                    - `Endpoint`: [{config.FLOOD_MEASURES_URL.split('?')[0]}](https://environment.data.gov.uk/flood-monitoring/doc/reference)
                
                **Integration Logic:**
                The platform implements a **Multi-Key Matching Algorithm** that harmonizes `wiskiID`, 
                `stationReference`, and `notation` formats to ensure 100% metadata coverage for live readings.
            """)

        with st.expander("⚙️ Technical Excellence"):
            st.write("""
                The dashboard has undergone a rigorous **Professional Refactoring** to meet enterprise 
                standards for maintainability and scalability.
                
                **Architectural Features:**
                - **Modular Design**: Separation of concerns across `src/data` (fetching/processing) and `src/ui` (rendering).
                - **Resilience Patterns**: Automated fallback merging across APIs and standardized error handling.
                - **High-Resolution Fetching**: Configured to retrieve 10,000+ records to ensure national network coverage.
                - **Performance Optimization**: Efficient use of multi-layered caching (`@st.cache_data`) for metadata and snapshots.
            """)

    with col2:
        st.info("💡 **Did you know?**")
        st.write("""
            The "Period Delta" compares the latest reading with a baseline from your selected window 
            (e.g., 24h ago or 7 days ago). We apply a **2mm threshold** to filter out noise and 
            highlight significant geophysical trends.
        """)
        
        st.success("🛰️ **Network Scope**")
        st.write("""
            - **Stations**: 447 Active
            - **Layers**: Chalk, Limestone, Mudstone, etc.
            - **Coverage**: England & Wales
        """)

        st.warning("⚖️ **Disclaimer**")
        st.caption("""
            Data is provided by the Environment Agency's Open Data services. While we strive for 
            accuracy, this dashboard is for informational purposes and should be verified against 
            official flood warnings for critical safety decisions.
        """)

    st.markdown("---")
    st.caption("Developed with ❤️ by the Advanced Agentic Coding Team | UK Groundwater Dashboard v2.1")
