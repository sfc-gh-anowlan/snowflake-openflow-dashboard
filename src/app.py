import streamlit as st
import pandas as pd
import plotly.express as px
from utils.snowflake_connector import SnowflakeConnector
from utils.backup_scheduler import BackupScheduler
import datetime
import pytz

# Page configuration
st.set_page_config(
    page_title="Snowflake OpenFlow Dashboard",
    page_icon="❄️",
    layout="wide"
)

# Initialize session state
if 'snowflake_connector' not in st.session_state:
    st.session_state.snowflake_connector = None
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None

def init_connection():
    """Initialize Snowflake connection"""
    if st.session_state.snowflake_connector is None:
        try:
            st.session_state.snowflake_connector = SnowflakeConnector()
        except Exception as e:
            st.error(f"Failed to connect to Snowflake: {str(e)}")
            return False
    return True

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Connector Status", "Backup Scheduler", "Settings"])

# Main content
st.title("Snowflake OpenFlow Dashboard")

if page == "Connector Status":
    st.header("Connector Status")
    
    # Add auto-refresh option
    auto_refresh = st.sidebar.checkbox("Auto-refresh", value=False)
    if auto_refresh:
        st.sidebar.number_input("Refresh interval (seconds)", min_value=30, value=60, key="refresh_interval")
        
    # Manual refresh button
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🔄 Refresh"):
            st.session_state.last_refresh = datetime.datetime.now()
    with col2:
        if st.session_state.last_refresh:
            st.text(f"Last refreshed: {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if init_connection():
        try:
            # Get connector status
            connectors = st.session_state.snowflake_connector.get_connector_status()
            
            if not connectors.empty:
                # Add search and filter options
                st.subheader("Search and Filter")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    search_term = st.text_input("Search connectors", "")
                with col2:
                    status_filter = st.multiselect(
                        "Filter by status",
                        options=connectors['STATUS'].unique().tolist(),
                        default=connectors['STATUS'].unique().tolist()
                    )
                with col3:
                    sort_by = st.selectbox(
                        "Sort by",
                        options=['CONNECTOR_NAME', 'STATUS', 'LAST_REFRESH_TIME', 'MODIFIED_ON'],
                        index=0
                    )
                
                # Apply filters
                filtered_df = connectors[
                    (connectors['STATUS'].isin(status_filter)) &
                    (connectors['CONNECTOR_NAME'].str.contains(search_term, case=False) |
                     connectors['STATUS'].str.contains(search_term, case=False))
                ]
                
                # Sort the dataframe
                filtered_df = filtered_df.sort_values(by=sort_by)
                
                # Display metrics
                st.subheader("Connector Metrics")
                metric1, metric2, metric3, metric4 = st.columns(4)
                with metric1:
                    st.metric("Total Connectors", len(connectors))
                with metric2:
                    running_count = len(connectors[connectors['STATUS'] == 'RUNNING'])
                    st.metric("Running", running_count)
                with metric3:
                    idle_count = len(connectors[connectors['STATUS'] == 'IDLE'])
                    st.metric("Idle", idle_count)
                with metric4:
                    error_count = len(connectors[connectors['STATUS'].str.contains('ERROR', case=False, na=False)])
                    st.metric("Errors", error_count)
                
                # Display connectors in a DataFrame
                st.subheader("Connector Details")
                st.dataframe(
                    filtered_df.style.apply(
                        lambda x: ['background-color: #90EE90' if v == 'RUNNING'
                                 else 'background-color: #FFB6C1' if 'ERROR' in str(v).upper()
                                 else 'background-color: #FFE4B5' for v in x],
                        subset=['STATUS']
                    ),
                    height=400
                )
                
                # Create visualizations
                col1, col2 = st.columns(2)
                with col1:
                    # Pie chart of connector statuses
                    fig1 = px.pie(
                        filtered_df,
                        names='STATUS',
                        title='Connector Status Distribution'
                    )
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    # Bar chart of connectors by last refresh time
                    fig2 = px.bar(
                        filtered_df,
                        x='CONNECTOR_NAME',
                        y='LAST_REFRESH_TIME',
                        title='Last Refresh Time by Connector',
                        height=400
                    )
                    fig2.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig2, use_container_width=True)
                
                # Display error messages if any
                error_connectors = filtered_df[filtered_df['ERROR_MESSAGE'].notna()]
                if not error_connectors.empty:
                    st.subheader("Error Messages")
                    for _, row in error_connectors.iterrows():
                        st.error(f"{row['CONNECTOR_NAME']}: {row['ERROR_MESSAGE']}")
                
            else:
                st.info("No connectors found")
        except Exception as e:
            st.error(f"Error fetching connector status: {str(e)}")

elif page == "Backup Scheduler":
    st.header("Backup Scheduler")
    if init_connection():
        scheduler = BackupScheduler(st.session_state.snowflake_connector)
        
        # Backup configuration form
        with st.form("backup_config"):
            connector_name = st.selectbox(
                "Select Connector",
                scheduler.get_available_connectors()
            )
            schedule_time = st.time_input(
                "Schedule Time (Daily)",
                datetime.time(0, 0)
            )
            stage_name = st.text_input(
                "Internal Stage Name",
                "OPENFLOW_BACKUP_STAGE"
            )
            submitted = st.form_submit_button("Schedule Backup")
            
            if submitted:
                try:
                    scheduler.schedule_backup(
                        connector_name,
                        schedule_time,
                        stage_name
                    )
                    st.success("Backup scheduled successfully!")
                except Exception as e:
                    st.error(f"Failed to schedule backup: {str(e)}")
        
        # Display existing schedules
        st.subheader("Existing Backup Schedules")
        schedules = scheduler.get_schedules()
        if schedules:
            st.dataframe(schedules)
        else:
            st.info("No backup schedules found")

else:  # Settings page
    st.header("Settings")
    with st.form("settings"):
        account = st.text_input("Snowflake Account")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        warehouse = st.text_input("Warehouse")
        database = st.text_input("Database")
        schema = st.text_input("Schema")
        
        if st.form_submit_button("Save Settings"):
            try:
                # Save settings and initialize connection
                st.session_state.snowflake_connector = SnowflakeConnector(
                    account=account,
                    user=username,
                    password=password,
                    warehouse=warehouse,
                    database=database,
                    schema=schema
                )
                st.success("Settings saved successfully!")
            except Exception as e:
                st.error(f"Failed to save settings: {str(e)}")

# Auto-refresh logic
if page == "Connector Status" and 'refresh_interval' in st.session_state and auto_refresh:
    st.experimental_rerun()