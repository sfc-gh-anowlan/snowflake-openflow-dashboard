# Snowflake OpenFlow Dashboard

A native Snowflake Streamlit dashboard for monitoring and managing Snowflake OpenFlow connectors. This application provides real-time monitoring of connector status, runtime logs, and automated backup scheduling capabilities.

## Features

- **Real-time monitoring** of OpenFlow connector status
- **Runtime logs** and error monitoring
- **System health** overview with metrics
- **Stuck FlowFiles** detection
- **Credit usage tracking** with comprehensive analytics and visualizations
- **Automated backup scheduling** to internal Snowflake stages
- **User-friendly interface** with search and filtering
- **Native Snowflake integration** using `get_active_session()`

## Prerequisites

- Snowflake account with Streamlit enabled
- Appropriate permissions to access OpenFlow telemetry data
- Access to `SNOWFLAKE.TELEMETRY.EVENTS_VIEW`
- OpenFlow connectors running in your Snowflake account

## Deployment to Snowflake

### Method 1: Using Snowflake Web Interface

1. **Prepare the application:**
   - Copy the contents of `streamlit_app.py`
   - Ensure you have the required Python packages available in your Snowflake environment

2. **Create the Streamlit app in Snowflake:**
   ```sql
   CREATE STREAMLIT openflow_dashboard
   FROM 'streamlit_app.py'
   MAIN_FILE = 'streamlit_app.py';
   ```

3. **Grant permissions:**
   ```sql
   GRANT USAGE ON STREAMLIT openflow_dashboard TO ROLE your_role;
   ```

### Method 2: Using Snowflake CLI

1. **Install Snowflake CLI:**
   ```bash
   pip install snowflake-cli-labs
   ```

2. **Login to Snowflake:**
   ```bash
   snowflake login
   ```

3. **Deploy the Streamlit app:**
   ```bash
   snowflake streamlit deploy --name openflow_dashboard streamlit_app.py
   ```

## Usage

1. **Access the dashboard:**
   - Navigate to your Snowflake web interface
   - Go to Streamlit apps section
   - Click on "openflow_dashboard"

2. **Navigate through the dashboard:**
   - **Connector Status**: View real-time status of all connectors with filtering and search
   - **Runtime Logs**: Monitor error logs, stuck FlowFiles, and system health
   - **Credit Usage**: Track and analyze OpenFlow credit consumption with interactive visualizations
   - **Backup Scheduler**: Schedule automated backups of connector configurations

## Credit Usage Tracking

The Credit Usage page provides comprehensive analytics on OpenFlow credit consumption:

### Features
- **Summary Metrics**: Total credits used, number of runtimes, average credits per runtime, and total active days
- **Interactive Filters**: Search by runtime key, filter by usage category and efficiency rating
- **Four Analysis Tabs**:
  - **Overview**: Top consumers, category distribution, runtime vs data plane credit comparison
  - **Cost Analysis**: Cost breakdown by runtime, cost model distribution, efficiency rating analysis
  - **Usage Patterns**: Pattern distribution, credits per active day, daily credit statistics, usage timeline
  - **Detailed Data**: Sortable table with color-coded efficiency ratings, CSV export, statistical summary

### Setting Up Credit Usage View

Before using the Credit Usage page, you need to create the `OPENFLOW_CREDIT_USAGE_VIEW` in your Snowflake account:

1. **Review the template**: Check `create_credit_usage_view.sql` for the view structure
2. **Customize the query**: Update the source table/view to match your credit data source
3. **Create the view**: Run the SQL script in your Snowflake environment
4. **Grant permissions**: Ensure your role has SELECT access to the view

The view should include the following columns:
- RUNTIME_KEY, DATA_PLANE_TYPE, ACTIVE_DAYS, DATA_PLANES_USED
- TOTAL_RUNTIME_CREDITS, TOTAL_DATA_PLANE_CREDITS, TOTAL_CREDITS
- AVG_DAILY_CREDITS, STDDEV_DAILY_CREDITS, MIN_DAILY_CREDITS, MAX_DAILY_CREDITS
- CREDITS_PER_ACTIVE_DAY, RUNTIME_COST_PERCENTAGE, DATA_PLANE_COST_PERCENTAGE
- COST_MODEL, USAGE_CATEGORY, USAGE_PATTERN, EFFICIENCY_RATING
- FIRST_USAGE_DATE, LAST_USAGE_DATE

## Backup Scheduling

The backup scheduler allows you to:
- Schedule daily backups for specific connectors
- Choose backup time for each connector
- Store backups in Snowflake internal stages
- View all scheduled backups and their next run times

## Troubleshooting

### "No connector data available" Error

If you see "No connector data available" or "No connectors found", check the following:

1. **Permissions:**
   - Ensure your Snowflake user has access to `SNOWFLAKE.TELEMETRY.EVENTS_VIEW`
   - Verify you have the necessary roles to query OpenFlow data
   - Check that your role has `USAGE` permission on the Streamlit app

2. **Data Availability:**
   - Confirm that OpenFlow connectors are running and generating telemetry data
   - Check if there are any connectors in the last 30 minutes (the default time window)
   - Verify OpenFlow is properly configured in your Snowflake account

3. **Streamlit Environment:**
   - Ensure the app is running within Snowflake's Streamlit environment
   - Check that `get_active_session()` is working properly
   - Verify the app has access to the current Snowflake session

### Common Issues

- **Permission Denied**: Contact your Snowflake administrator for proper access to telemetry data
- **Empty Results**: Verify OpenFlow connectors are active and generating data
- **Session Errors**: Ensure the app is deployed correctly in Snowflake's Streamlit environment
- **Query Timeouts**: Check warehouse size and query complexity

## Security

- **Native Integration**: Uses Snowflake's built-in session management
- **No External Credentials**: No need to store or manage connection credentials
- **Secure Session**: Leverages Snowflake's secure session handling
- **Role-based Access**: Inherits permissions from your Snowflake role
- **Data Privacy**: All data processing happens within Snowflake's secure environment

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
