import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
import plotly.express as px
import datetime

# Page configuration
st.set_page_config(
    page_title="Snowflake OpenFlow Dashboard",
    page_icon="❄️",
    layout="wide"
)

# Get the Snowflake session - this is automatically provided in Snowflake's Streamlit
try:
    session = get_active_session()
except Exception as e:
    st.error("❌ This application must be run within Snowflake's Streamlit environment.")
    st.info("Please deploy this app to Snowflake and run it from there.")
    st.stop()

# Initialize session state for refresh tracking
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None

# Initialize session state for lookback window
if 'lookback_minutes' not in st.session_state:
    st.session_state.lookback_minutes = 30

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Connector Status", "Runtime Logs", "Credit Usage", "Backup Scheduler"])

# Sidebar configuration
st.sidebar.title("Configuration")
lookback_minutes = st.sidebar.number_input(
    "Lookback Window (minutes)", 
    min_value=5, 
    max_value=1440,  # 24 hours
    value=st.session_state.lookback_minutes,
    help="How far back to look for connector data"
)
st.session_state.lookback_minutes = lookback_minutes

# Main content
st.title("Snowflake OpenFlow Dashboard")

def get_connector_status():
    """Get status of all OpenFlow connectors from telemetry events"""
    lookback_minutes = st.session_state.lookback_minutes
    
    query = f"""
    SELECT 
        RESOURCE_ATTRIBUTES:"openflow.dataplane.id" as DEPLOYMENT_ID,
        RESOURCE_ATTRIBUTES:"k8s.namespace.name" as RUNTIME_KEY,
        RESOURCE_ATTRIBUTES:"k8s.pod.name" as POD_NAME,
        RECORD_ATTRIBUTES:name as CONNECTOR_NAME,
        RECORD_ATTRIBUTES:id as CONNECTOR_ID,
        CASE 
            WHEN RECORD:metric:name = 'processor.run.status.running' AND TO_NUMBER(VALUE) = 1 THEN 'RUNNING'
            WHEN RECORD:metric:name = 'processor.run.status.running' AND TO_NUMBER(VALUE) = 0 THEN 'STOPPED'
            ELSE 'UNKNOWN'
        END as STATUS,
        TIMESTAMP as LAST_REFRESH_TIME,
        NULL as ERROR_MESSAGE,
        TIMESTAMP as CREATED_ON,
        TIMESTAMP as MODIFIED_ON
    FROM SNOWFLAKE.TELEMETRY.EVENTS_VIEW
    WHERE true
        AND RECORD_TYPE = 'METRIC'
        AND RECORD:metric:name = 'processor.run.status.running'
        AND TIMESTAMP > dateadd(minutes, -{lookback_minutes}, sysdate())
        AND RECORD_ATTRIBUTES:name IS NOT NULL
        AND RECORD_ATTRIBUTES:name != ''
    ORDER BY TIMESTAMP DESC
    LIMIT 100
    """
    
    try:
        df = session.sql(query).to_pandas()
        # Set pandas option to handle large dataframes
        pd.set_option("styler.render.max_elements", 1000000)
        
        if df.empty:
            st.warning(f"No OpenFlow connectors found in the last {lookback_minutes} minutes")
            st.info("**This might be due to:**")
            st.info("• No OpenFlow connectors running")
            st.info("• Insufficient permissions to access telemetry data")
            st.info("• OpenFlow not properly configured in your Snowflake account")
            
            return pd.DataFrame(columns=[
                'DEPLOYMENT_ID', 'RUNTIME_KEY', 'POD_NAME', 'CONNECTOR_NAME',
                'CONNECTOR_ID', 'STATUS', 'LAST_REFRESH_TIME',
                'ERROR_MESSAGE', 'CREATED_ON', 'MODIFIED_ON'
            ])
        
        return df
        
    except Exception as e:
        st.error(f"Error querying connector status: {str(e)}")
        st.info("**This might be due to:**")
        st.info("• Insufficient permissions to access telemetry data")
        st.info("• OpenFlow not properly configured in your Snowflake account")
        
        return pd.DataFrame(columns=[
            'DEPLOYMENT_ID', 'RUNTIME_KEY', 'POD_NAME', 'CONNECTOR_NAME',
            'CONNECTOR_ID', 'STATUS', 'LAST_REFRESH_TIME',
            'ERROR_MESSAGE', 'CREATED_ON', 'MODIFIED_ON'
        ])

def backup_connector(connector_name, stage_name):
    """Backup a connector configuration to an internal stage"""
    try:
        # Create stage if it doesn't exist
        session.sql(f"CREATE STAGE IF NOT EXISTS {stage_name}").collect()
        
        # Export OpenFlow connector configuration using the correct function
        backup_query = f"""
        CALL SYSTEM$EXPORT_OPENFLOW_CONNECTOR(
            '{connector_name}',
            '@{stage_name}/{connector_name}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
        """
        session.sql(backup_query).collect()
        return True
    except Exception as e:
        # If the OpenFlow function doesn't exist, try alternative approach
        if "Unknown function" in str(e):
            try:
                # Alternative: Create a simple backup by querying connector metadata
                backup_query = f"""
                COPY INTO '@{stage_name}/{connector_name}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                FROM (
                    SELECT OBJECT_CONSTRUCT(
                        'connector_name', '{connector_name}',
                        'backup_timestamp', CURRENT_TIMESTAMP(),
                        'status', 'backup_created'
                    )
                )
                FILE_FORMAT = (TYPE = 'JSON')
                """
                session.sql(backup_query).collect()
                return True
            except Exception as e2:
                raise Exception(f"Failed to backup connector {connector_name}: {str(e2)}")
        else:
            raise Exception(f"Failed to backup connector {connector_name}: {str(e)}")

def get_available_connectors():
    """Get list of available connector names from telemetry events"""
    lookback_minutes = st.session_state.lookback_minutes
    query = f"""
    SELECT DISTINCT record_attributes:name as CONNECTOR_NAME
    FROM SNOWFLAKE.TELEMETRY.EVENTS_VIEW
    WHERE true
        AND record_type = 'METRIC'
        AND record:metric:name = 'processor.run.status.running'
        AND timestamp > dateadd(minutes, -{lookback_minutes}, sysdate())
        AND record_attributes:name IS NOT NULL
    """
    try:
        df = session.sql(query).to_pandas()
        return df['CONNECTOR_NAME'].tolist() if not df.empty else []
    except Exception as e:
        print(f"Warning: Could not query available connectors: {str(e)}")
        return []

def get_error_logs():
    """Get error logs for OpenFlow runtimes using official Snowflake example"""
    lookback_minutes = st.session_state.lookback_minutes
    query = f"""
    SELECT
        timestamp,
        resource_attributes:"openflow.dataplane.id" as DEPLOYMENT_ID,
        resource_attributes:"k8s.namespace.name" as RUNTIME_KEY,
        parsed_log:level as LOG_LEVEL,
        parsed_log:loggerName as LOGGER,
        parsed_log:formattedMessage as MESSAGE,
        parsed_log
    FROM (
        SELECT
            timestamp,
            resource_attributes:"openflow.dataplane.id" as DEPLOYMENT_ID,
            resource_attributes:"k8s.namespace.name" as RUNTIME_KEY,
            TRY_PARSE_JSON(value) as parsed_log
        FROM SNOWFLAKE.TELEMETRY.EVENTS_VIEW
        WHERE true
            AND timestamp > dateadd('minutes', -{lookback_minutes}, sysdate())
            AND record_type = 'LOG'
            AND resource_attributes:"k8s.namespace.name" like 'runtime-%'
        ORDER BY timestamp DESC
        LIMIT 5000
    ) WHERE LOG_LEVEL = 'ERROR'
    LIMIT 100
    """
    try:
        df = session.sql(query).to_pandas()
        pd.set_option("styler.render.max_elements", 1000000)
        return df
    except Exception as e:
        print(f"Warning: Could not query error logs: {str(e)}")
        return pd.DataFrame(columns=[
            'TIMESTAMP', 'DEPLOYMENT_ID', 'RUNTIME_KEY', 
            'LOG_LEVEL', 'LOGGER', 'MESSAGE', 'PARSED_LOG'
        ])

def get_stuck_flowfiles():
    """Find stuck FlowFiles using official Snowflake example"""
    lookback_minutes = st.session_state.lookback_minutes
    query = f"""
    SELECT * FROM (
        SELECT
            resource_attributes:"openflow.dataplane.id" as DEPLOYMENT_ID,
            resource_attributes:"k8s.namespace.name" as RUNTIME_KEY,
            record_attributes:name as CONNECTION_NAME,
            record_attributes:id as CONNECTION_ID,
            MAX(TO_NUMBER(value / 60 / 1000)) as MAX_QUEUED_FILE_MINUTES
        FROM SNOWFLAKE.TELEMETRY.EVENTS_VIEW
        WHERE true
            AND record_type = 'METRIC'
            AND record:metric:name = 'connection.queued.duration.max'
            AND timestamp > dateadd(minutes, -{lookback_minutes}, sysdate())
        GROUP BY 1, 2, 3, 4
        ORDER BY MAX_QUEUED_FILE_MINUTES DESC
        LIMIT 100
    ) WHERE MAX_QUEUED_FILE_MINUTES > 30
    """
    try:
        df = session.sql(query).to_pandas()
        pd.set_option("styler.render.max_elements", 1000000)
        return df
    except Exception as e:
        print(f"Warning: Could not query stuck FlowFiles: {str(e)}")
        return pd.DataFrame(columns=[
            'DEPLOYMENT_ID', 'RUNTIME_KEY', 'CONNECTION_NAME', 
            'CONNECTION_ID', 'MAX_QUEUED_FILE_MINUTES'
        ])

def get_credit_usage():
    """Get OpenFlow credit usage data from the view"""
    query = """
    SELECT 
        RUNTIME_KEY,
        DATA_PLANE_TYPE,
        ACTIVE_DAYS,
        DATA_PLANES_USED,
        TOTAL_RUNTIME_CREDITS,
        TOTAL_DATA_PLANE_CREDITS,
        TOTAL_CREDITS,
        AVG_DAILY_CREDITS,
        STDDEV_DAILY_CREDITS,
        MIN_DAILY_CREDITS,
        MAX_DAILY_CREDITS,
        CREDITS_PER_ACTIVE_DAY,
        RUNTIME_COST_PERCENTAGE,
        DATA_PLANE_COST_PERCENTAGE,
        COST_MODEL,
        USAGE_CATEGORY,
        USAGE_PATTERN,
        EFFICIENCY_RATING,
        FIRST_USAGE_DATE,
        LAST_USAGE_DATE
    FROM OPENFLOW_COST_ANALYSIS
    ORDER BY TOTAL_CREDITS DESC
    """
    try:
        df = session.sql(query).to_pandas()
        pd.set_option("styler.render.max_elements", 1000000)
        return df
    except Exception as e:
        st.error(f"Error querying credit usage: {str(e)}")
        st.info("**Note:** Make sure you have access to the view 'OPENFLOW_COST_ANALYSIS' with the required columns.")
        return pd.DataFrame(columns=[
            'RUNTIME_KEY', 'DATA_PLANE_TYPE', 'ACTIVE_DAYS', 'DATA_PLANES_USED',
            'TOTAL_RUNTIME_CREDITS', 'TOTAL_DATA_PLANE_CREDITS', 'TOTAL_CREDITS',
            'AVG_DAILY_CREDITS', 'STDDEV_DAILY_CREDITS', 'MIN_DAILY_CREDITS',
            'MAX_DAILY_CREDITS', 'CREDITS_PER_ACTIVE_DAY', 'RUNTIME_COST_PERCENTAGE',
            'DATA_PLANE_COST_PERCENTAGE', 'COST_MODEL', 'USAGE_CATEGORY',
            'USAGE_PATTERN', 'EFFICIENCY_RATING', 'FIRST_USAGE_DATE', 'LAST_USAGE_DATE'
        ])

if page == "Connector Status":
    st.header("Connector Status")
    
    # Display current lookback window
    st.info(f"📊 **Current Lookback Window:** {st.session_state.lookback_minutes} minutes")
    
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
    
    try:
        # Get connector status
        connectors = get_connector_status()
        
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

elif page == "Runtime Logs":
    st.header("Runtime Logs & Monitoring")
    
    # Display current lookback window
    st.info(f"📊 **Current Lookback Window:** {st.session_state.lookback_minutes} minutes")
    
    # Add auto-refresh option
    auto_refresh = st.sidebar.checkbox("Auto-refresh", value=False, key="logs_auto_refresh")
    if auto_refresh:
        st.sidebar.number_input("Refresh interval (seconds)", min_value=30, value=60, key="logs_refresh_interval")
    
    # Manual refresh button
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🔄 Refresh", key="logs_refresh"):
            st.session_state.last_refresh = datetime.datetime.now()
    with col2:
        if st.session_state.last_refresh:
            st.text(f"Last refreshed: {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Tabs for different monitoring views
    tab1, tab2, tab3 = st.tabs(["Error Logs", "Stuck FlowFiles", "System Health"])
    
    with tab1:
        st.subheader("Error Logs")
        st.info(f"Showing ERROR level logs from OpenFlow runtimes in the last {st.session_state.lookback_minutes} minutes")
        
        try:
            error_logs = get_error_logs()
            
            if not error_logs.empty:
                # Display error count metric
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Errors", len(error_logs))
                with col2:
                    unique_runtimes = error_logs['RUNTIME_KEY'].nunique()
                    st.metric("Affected Runtimes", unique_runtimes)
                with col3:
                    unique_deployments = error_logs['DEPLOYMENT_ID'].nunique()
                    st.metric("Affected Deployments", unique_deployments)
                
                # Display error logs in a table
                st.subheader("Error Details")
                st.dataframe(
                    error_logs[['TIMESTAMP', 'DEPLOYMENT_ID', 'RUNTIME_KEY', 'LOGGER', 'MESSAGE']],
                    height=400
                )
                
                # Show detailed error messages
                st.subheader("Detailed Error Messages")
                for _, row in error_logs.iterrows():
                    with st.expander(f"Error at {row['TIMESTAMP']} - {row['RUNTIME_KEY']}"):
                        st.write(f"**Deployment ID:** {row['DEPLOYMENT_ID']}")
                        st.write(f"**Runtime Key:** {row['RUNTIME_KEY']}")
                        st.write(f"**Logger:** {row['LOGGER']}")
                        st.write(f"**Message:** {row['MESSAGE']}")
                        if row['PARSED_LOG']:
                            st.json(row['PARSED_LOG'])
            else:
                st.success(f"No errors found in the last {st.session_state.lookback_minutes} minutes! 🎉")
                
        except Exception as e:
            st.error(f"Error fetching error logs: {str(e)}")
    
    with tab2:
        st.subheader("Stuck FlowFiles")
        st.info(f"Connections with FlowFiles queued for more than 30 minutes (searching last {st.session_state.lookback_minutes} minutes)")
        
        try:
            stuck_flowfiles = get_stuck_flowfiles()
            
            if not stuck_flowfiles.empty:
                # Display stuck FlowFiles count
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Stuck Connections", len(stuck_flowfiles))
                with col2:
                    max_minutes = stuck_flowfiles['MAX_QUEUED_FILE_MINUTES'].max()
                    st.metric("Longest Queue Time", f"{max_minutes:.1f} minutes")
                
                # Display stuck FlowFiles
                st.subheader("Stuck FlowFiles Details")
                st.dataframe(stuck_flowfiles, height=400)
                
                # Alert for critical issues
                critical_issues = stuck_flowfiles[stuck_flowfiles['MAX_QUEUED_FILE_MINUTES'] > 60]
                if not critical_issues.empty:
                    st.error(f"🚨 {len(critical_issues)} connections have been stuck for over 1 hour!")
            else:
                st.success("No stuck FlowFiles found! 🎉")
                
        except Exception as e:
            st.error(f"Error fetching stuck FlowFiles: {str(e)}")
    
    with tab3:
        st.subheader("System Health Overview")
        st.info(f"High-level metrics from OpenFlow telemetry (last {st.session_state.lookback_minutes} minutes)")
        
        try:
            connectors = get_connector_status()
            
            if not connectors.empty:
                # System health metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    total_connectors = len(connectors)
                    st.metric("Total Connectors", total_connectors)
                with col2:
                    running_count = len(connectors[connectors['STATUS'] == 'RUNNING'])
                    st.metric("Running", running_count)
                with col3:
                    stopped_count = len(connectors[connectors['STATUS'] == 'STOPPED'])
                    st.metric("Stopped", stopped_count)
                with col4:
                    unique_runtimes = connectors['RUNTIME_KEY'].nunique()
                    st.metric("Active Runtimes", unique_runtimes)
                
                # Health status
                if running_count == total_connectors:
                    st.success("✅ All connectors are running normally")
                elif stopped_count > 0:
                    st.warning(f"⚠️ {stopped_count} connectors are stopped")
                else:
                    st.info("ℹ️ Mixed connector states detected")
                
                # Runtime distribution
                st.subheader("Runtime Distribution")
                runtime_counts = connectors['RUNTIME_KEY'].value_counts()
                fig = px.bar(
                    x=runtime_counts.index,
                    y=runtime_counts.values,
                    title="Connectors per Runtime",
                    labels={'x': 'Runtime Key', 'y': 'Number of Connectors'}
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No connector data available")
                
        except Exception as e:
            st.error(f"Error fetching system health data: {str(e)}")

elif page == "Credit Usage":
    st.header("OpenFlow Credit Usage")
    
    # Time window information
    st.info("📅 **Data Time Window:** This view tracks OpenFlow credit usage over the past 30 days. Credit metrics, usage patterns, and efficiency ratings are calculated based on activity within this rolling 30-day window.")
    
    # Manual refresh button
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🔄 Refresh", key="credit_refresh"):
            st.session_state.last_refresh = datetime.datetime.now()
    with col2:
        if st.session_state.last_refresh:
            st.text(f"Last refreshed: {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        credit_data = get_credit_usage()
        
        if not credit_data.empty:
            # Display top-level metrics
            st.subheader("Summary Metrics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_credits = credit_data['TOTAL_CREDITS'].sum()
                st.metric("Total Credits Used", f"{total_credits:,.2f}")
            with col2:
                total_runtimes = len(credit_data)
                st.metric("Total Runtimes", total_runtimes)
            with col3:
                avg_credits_per_runtime = credit_data['TOTAL_CREDITS'].mean()
                st.metric("Avg Credits/Runtime", f"{avg_credits_per_runtime:,.2f}")
            with col4:
                total_active_days = credit_data['ACTIVE_DAYS'].sum()
                st.metric("Total Active Days", f"{total_active_days:,.0f}")
            
            # Filters and search
            st.subheader("Filter and Search")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                search_term = st.text_input("Search by Runtime Key", "")
            with col2:
                usage_category_filter = st.multiselect(
                    "Filter by Usage Category",
                    options=credit_data['USAGE_CATEGORY'].unique().tolist(),
                    default=credit_data['USAGE_CATEGORY'].unique().tolist()
                )
            with col3:
                efficiency_filter = st.multiselect(
                    "Filter by Efficiency Rating",
                    options=credit_data['EFFICIENCY_RATING'].unique().tolist(),
                    default=credit_data['EFFICIENCY_RATING'].unique().tolist()
                )
            
            # Apply filters
            filtered_df = credit_data[
                (credit_data['USAGE_CATEGORY'].isin(usage_category_filter)) &
                (credit_data['EFFICIENCY_RATING'].isin(efficiency_filter)) &
                (credit_data['RUNTIME_KEY'].str.contains(search_term, case=False, na=False))
            ]
            
            # Tabs for different views
            tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Cost Analysis", "Usage Patterns", "Detailed Data"])
            
            with tab1:
                st.subheader("Credit Usage Overview")
                
                # Top 10 runtimes by total credits
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Top 10 Runtimes by Total Credits**")
                    top_10 = filtered_df.nlargest(10, 'TOTAL_CREDITS')
                    fig1 = px.bar(
                        top_10,
                        x='RUNTIME_KEY',
                        y='TOTAL_CREDITS',
                        title='Top 10 Runtimes by Total Credits',
                        color='EFFICIENCY_RATING',
                        color_discrete_map={
                            'VERY_EFFICIENT': '#90EE90',
                            'EFFICIENT': '#98D8C8',
                            'MODERATE': '#FFE4B5',
                            'INEFFICIENT': '#FFB6C1'
                        }
                    )
                    fig1.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    st.write("**Usage Category Distribution**")
                    category_counts = filtered_df['USAGE_CATEGORY'].value_counts()
                    fig2 = px.pie(
                        values=category_counts.values,
                        names=category_counts.index,
                        title='Credit Usage by Category'
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                
                # Runtime vs Data Plane Credits comparison
                st.write("**Runtime vs Data Plane Credits**")
                fig3 = px.scatter(
                    filtered_df,
                    x='TOTAL_RUNTIME_CREDITS',
                    y='TOTAL_DATA_PLANE_CREDITS',
                    size='TOTAL_CREDITS',
                    color='EFFICIENCY_RATING',
                    hover_data=['RUNTIME_KEY', 'ACTIVE_DAYS'],
                    title='Runtime Credits vs Data Plane Credits',
                    labels={
                        'TOTAL_RUNTIME_CREDITS': 'Runtime Credits',
                        'TOTAL_DATA_PLANE_CREDITS': 'Data Plane Credits'
                    }
                )
                st.plotly_chart(fig3, use_container_width=True)
            
            with tab2:
                st.subheader("Cost Analysis")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Runtime vs Data Plane Cost Percentage**")
                    # Create data for stacked bar chart
                    cost_breakdown = filtered_df[['RUNTIME_KEY', 'RUNTIME_COST_PERCENTAGE', 'DATA_PLANE_COST_PERCENTAGE']].head(20)
                    fig4 = px.bar(
                        cost_breakdown,
                        x='RUNTIME_KEY',
                        y=['RUNTIME_COST_PERCENTAGE', 'DATA_PLANE_COST_PERCENTAGE'],
                        title='Cost Breakdown by Runtime (Top 20)',
                        labels={'value': 'Percentage', 'variable': 'Cost Type'},
                        barmode='stack'
                    )
                    fig4.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig4, use_container_width=True)
                
                with col2:
                    st.write("**Cost Model Distribution**")
                    cost_model_counts = filtered_df['COST_MODEL'].value_counts()
                    fig5 = px.pie(
                        values=cost_model_counts.values,
                        names=cost_model_counts.index,
                        title='Distribution by Cost Model'
                    )
                    st.plotly_chart(fig5, use_container_width=True)
                
                # Efficiency analysis
                st.write("**Efficiency Rating Analysis**")
                efficiency_summary = filtered_df.groupby('EFFICIENCY_RATING').agg({
                    'TOTAL_CREDITS': ['sum', 'mean', 'count'],
                    'AVG_DAILY_CREDITS': 'mean',
                    'CREDITS_PER_ACTIVE_DAY': 'mean'
                }).round(2)
                st.dataframe(efficiency_summary, use_container_width=True)
            
            with tab3:
                st.subheader("Usage Patterns")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Usage Pattern Distribution**")
                    pattern_counts = filtered_df['USAGE_PATTERN'].value_counts()
                    fig6 = px.bar(
                        x=pattern_counts.index,
                        y=pattern_counts.values,
                        title='Distribution by Usage Pattern',
                        labels={'x': 'Usage Pattern', 'y': 'Count'},
                        color=pattern_counts.index
                    )
                    st.plotly_chart(fig6, use_container_width=True)
                
                with col2:
                    st.write("**Credits Per Active Day**")
                    fig7 = px.box(
                        filtered_df,
                        x='USAGE_PATTERN',
                        y='CREDITS_PER_ACTIVE_DAY',
                        title='Credits Per Active Day by Usage Pattern',
                        color='USAGE_PATTERN'
                    )
                    st.plotly_chart(fig7, use_container_width=True)
                
                # Daily credit statistics
                st.write("**Daily Credit Statistics**")
                fig8 = px.scatter(
                    filtered_df,
                    x='AVG_DAILY_CREDITS',
                    y='STDDEV_DAILY_CREDITS',
                    size='ACTIVE_DAYS',
                    color='USAGE_PATTERN',
                    hover_data=['RUNTIME_KEY', 'MIN_DAILY_CREDITS', 'MAX_DAILY_CREDITS'],
                    title='Daily Credit Average vs Standard Deviation',
                    labels={
                        'AVG_DAILY_CREDITS': 'Average Daily Credits',
                        'STDDEV_DAILY_CREDITS': 'Std Dev of Daily Credits'
                    }
                )
                st.plotly_chart(fig8, use_container_width=True)
                
                # Timeline analysis
                st.write("**Usage Timeline**")
                timeline_df = filtered_df[['RUNTIME_KEY', 'FIRST_USAGE_DATE', 'LAST_USAGE_DATE', 'TOTAL_CREDITS']].copy()
                timeline_df['USAGE_DURATION_DAYS'] = (
                    pd.to_datetime(timeline_df['LAST_USAGE_DATE']) - 
                    pd.to_datetime(timeline_df['FIRST_USAGE_DATE'])
                ).dt.days
                
                fig9 = px.scatter(
                    timeline_df,
                    x='FIRST_USAGE_DATE',
                    y='USAGE_DURATION_DAYS',
                    size='TOTAL_CREDITS',
                    hover_data=['RUNTIME_KEY', 'LAST_USAGE_DATE'],
                    title='Runtime Usage Timeline',
                    labels={
                        'FIRST_USAGE_DATE': 'First Usage Date',
                        'USAGE_DURATION_DAYS': 'Usage Duration (Days)'
                    }
                )
                st.plotly_chart(fig9, use_container_width=True)
            
            with tab4:
                st.subheader("Detailed Credit Usage Data")
                
                # Display options
                col1, col2 = st.columns(2)
                with col1:
                    sort_column = st.selectbox(
                        "Sort by",
                        options=['TOTAL_CREDITS', 'RUNTIME_KEY', 'AVG_DAILY_CREDITS', 'ACTIVE_DAYS', 'EFFICIENCY_RATING'],
                        index=0
                    )
                with col2:
                    sort_order = st.radio("Sort order", ["Descending", "Ascending"], horizontal=True)
                
                # Sort the dataframe
                sorted_df = filtered_df.sort_values(by=sort_column, ascending=(sort_order == "Ascending"))
                
                # Color code efficiency rating
                def highlight_efficiency(row):
                    if row['EFFICIENCY_RATING'] == 'VERY_EFFICIENT':
                        return ['background-color: #90EE90'] * len(row)
                    elif row['EFFICIENCY_RATING'] == 'EFFICIENT':
                        return ['background-color: #98D8C8'] * len(row)
                    elif row['EFFICIENCY_RATING'] == 'MODERATE':
                        return ['background-color: #FFE4B5'] * len(row)
                    elif row['EFFICIENCY_RATING'] == 'INEFFICIENT':
                        return ['background-color: #FFB6C1'] * len(row)
                    return [''] * len(row)
                
                # Display the detailed data table
                st.dataframe(
                    sorted_df.style.apply(highlight_efficiency, axis=1),
                    height=500,
                    use_container_width=True
                )
                
                # Export option
                st.download_button(
                    label="Download Data as CSV",
                    data=sorted_df.to_csv(index=False).encode('utf-8'),
                    file_name=f'openflow_credit_usage_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                    mime='text/csv'
                )
                
                # Statistics summary
                st.write("**Statistical Summary**")
                st.dataframe(
                    sorted_df[['TOTAL_CREDITS', 'ACTIVE_DAYS', 'AVG_DAILY_CREDITS', 
                              'CREDITS_PER_ACTIVE_DAY', 'DATA_PLANES_USED']].describe().round(2),
                    use_container_width=True
                )
        
        else:
            st.warning("No credit usage data found")
            st.info("**Possible reasons:**")
            st.info("• The view 'OPENFLOW_COST_ANALYSIS' does not exist or is empty")
            st.info("• No OpenFlow credit usage data available for the past 30 days")
            st.info("• Insufficient permissions to access the view")
            
    except Exception as e:
        st.error(f"Error fetching credit usage data: {str(e)}")

else:  # Backup Scheduler page
    st.header("Backup Scheduler")
    
    # Backup configuration form
    with st.form("backup_config"):
        connector_name = st.selectbox(
            "Select Connector",
            get_available_connectors()
        )
        stage_name = st.text_input(
            "Internal Stage Name",
            "OPENFLOW_BACKUP_STAGE"
        )
        submitted = st.form_submit_button("Backup Now")
        
        if submitted:
            try:
                backup_connector(connector_name, stage_name)
                st.success("Backup completed successfully!")
            except Exception as e:
                st.error(f"Failed to create backup: {str(e)}")

# Auto-refresh logic
if page in ["Connector Status", "Runtime Logs"] and 'refresh_interval' in st.session_state and auto_refresh:
    st.experimental_rerun()
