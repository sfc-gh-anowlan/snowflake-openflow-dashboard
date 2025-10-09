# OpenFlow Credit Usage Page - Setup Guide

This guide will help you set up and use the new Credit Usage page in your Snowflake OpenFlow Dashboard.

## What Was Added

A comprehensive new page has been added to the Streamlit dashboard that visualizes OpenFlow credit usage with the following features:

### 1. Summary Metrics Dashboard
- **Total Credits Used**: Aggregate of all credit consumption
- **Total Runtimes**: Number of distinct runtime keys
- **Average Credits per Runtime**: Mean credit usage across runtimes
- **Total Active Days**: Sum of active days across all runtimes

### 2. Interactive Filters
- Search by runtime key (text search)
- Filter by usage category (multi-select)
- Filter by efficiency rating (multi-select)

### 3. Four Analysis Tabs

#### Tab 1: Overview
- **Top 10 Runtimes by Total Credits**: Bar chart showing the highest credit consumers, color-coded by efficiency rating
- **Usage Category Distribution**: Pie chart showing the breakdown of usage categories
- **Runtime vs Data Plane Credits**: Scatter plot comparing runtime and data plane credits with bubble size representing total credits

#### Tab 2: Cost Analysis
- **Runtime vs Data Plane Cost Percentage**: Stacked bar chart showing cost breakdown for top 20 runtimes
- **Cost Model Distribution**: Pie chart showing distribution across different cost models
- **Efficiency Rating Analysis**: Statistical summary grouped by efficiency rating

#### Tab 3: Usage Patterns
- **Usage Pattern Distribution**: Bar chart showing distribution of usage patterns
- **Credits Per Active Day**: Box plot showing credit distribution by usage pattern
- **Daily Credit Statistics**: Scatter plot showing average vs standard deviation of daily credits
- **Usage Timeline**: Timeline visualization showing when runtimes were first and last used

#### Tab 4: Detailed Data
- **Sortable Data Table**: Complete dataset with color-coded efficiency ratings
  - Green: Very Efficient
  - Teal: Efficient
  - Beige: Moderate
  - Pink: Inefficient
- **CSV Export**: Download button to export filtered data
- **Statistical Summary**: Descriptive statistics for key metrics

## Setup Instructions

### Step 1: Prepare Your Credit Usage Data

You need to create a view named `OPENFLOW_CREDIT_USAGE_VIEW` in your Snowflake account. This view should contain the following columns:

| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| RUNTIME_KEY | VARCHAR | Unique identifier for the runtime |
| DATA_PLANE_TYPE | VARCHAR | Type of data plane (e.g., SMALL, MEDIUM, LARGE) |
| ACTIVE_DAYS | NUMBER | Number of days the runtime was active |
| DATA_PLANES_USED | NUMBER | Number of data planes used |
| TOTAL_RUNTIME_CREDITS | NUMBER | Total credits for runtime operations |
| TOTAL_DATA_PLANE_CREDITS | NUMBER | Total credits for data plane operations |
| TOTAL_CREDITS | NUMBER | Total credits consumed |
| AVG_DAILY_CREDITS | NUMBER | Average credits per day |
| STDDEV_DAILY_CREDITS | FLOAT | Standard deviation of daily credits |
| MIN_DAILY_CREDITS | NUMBER | Minimum daily credits |
| MAX_DAILY_CREDITS | NUMBER | Maximum daily credits |
| CREDITS_PER_ACTIVE_DAY | NUMBER | Credits divided by active days |
| RUNTIME_COST_PERCENTAGE | NUMBER | Percentage of cost from runtime |
| DATA_PLANE_COST_PERCENTAGE | NUMBER | Percentage of cost from data plane |
| COST_MODEL | VARCHAR | Cost model identifier |
| USAGE_CATEGORY | VARCHAR | Category of usage (e.g., HIGH_USAGE, MEDIUM_USAGE, LOW_USAGE) |
| USAGE_PATTERN | VARCHAR | Pattern of usage (e.g., CONTINUOUS, FREQUENT, REGULAR, SPORADIC) |
| EFFICIENCY_RATING | VARCHAR | Efficiency rating (VERY_EFFICIENT, EFFICIENT, MODERATE, INEFFICIENT) |
| FIRST_USAGE_DATE | DATE | First date of usage |
| LAST_USAGE_DATE | DATE | Last date of usage |

### Step 2: Create the View

1. Open the `create_credit_usage_view.sql` file in this directory
2. Customize the SQL query to match your data source:
   - Replace `YOUR_CREDIT_USAGE_SOURCE_TABLE` with your actual table/view name
   - Adjust column mappings as needed
   - Modify the credit calculation logic if necessary
3. Run the SQL script in your Snowflake environment

**Example command:**
```sql
-- In Snowflake worksheet
USE DATABASE your_database;
USE SCHEMA your_schema;

-- Then run the contents of create_credit_usage_view.sql
```

### Step 3: Grant Permissions

Ensure your Snowflake role has SELECT permissions on the view:

```sql
GRANT SELECT ON VIEW OPENFLOW_CREDIT_USAGE_VIEW TO ROLE your_role;
```

### Step 4: Update Streamlit App (if needed)

If your view name is different from `OPENFLOW_CREDIT_USAGE_VIEW`, update the query in `streamlit_app.py`:

1. Find the `get_credit_usage()` function (around line 239)
2. Update the `FROM` clause to match your view name:
   ```python
   FROM YOUR_VIEW_NAME
   ```

### Step 5: Redeploy the Streamlit App

Redeploy the updated `streamlit_app.py` to Snowflake:

```sql
CREATE OR REPLACE STREAMLIT openflow_dashboard
FROM 'streamlit_app.py'
MAIN_FILE = 'streamlit_app.py';
```

## Using the Credit Usage Page

1. Navigate to your Snowflake Streamlit dashboard
2. Select "Credit Usage" from the left sidebar navigation
3. Use the filters to narrow down the data:
   - Type in the search box to find specific runtime keys
   - Select usage categories to focus on specific usage levels
   - Choose efficiency ratings to identify optimization opportunities
4. Explore the four tabs to gain insights:
   - **Overview**: Understand top consumers and credit distribution
   - **Cost Analysis**: Analyze cost breakdown and efficiency
   - **Usage Patterns**: Identify usage trends and patterns
   - **Detailed Data**: Examine individual runtime details and export data

## Common Data Sources for Credit Usage

Depending on your Snowflake environment, you might source credit data from:

1. **ACCOUNT_USAGE.METERING_HISTORY**: Snowflake's built-in metering view
2. **Custom Metering Tables**: Your organization's credit tracking tables
3. **Telemetry Data**: Aggregated from `SNOWFLAKE.TELEMETRY.EVENTS_VIEW`
4. **Third-party Monitoring Tools**: External cost tracking systems

## Troubleshooting

### "No credit usage data found"
- Verify the view `OPENFLOW_CREDIT_USAGE_VIEW` exists in your database
- Check that the view contains data (run `SELECT COUNT(*) FROM OPENFLOW_CREDIT_USAGE_VIEW`)
- Ensure your role has SELECT permissions on the view

### "Error querying credit usage"
- Check the error message for details
- Verify column names match the expected schema
- Ensure data types are compatible
- Check for null values in required columns

### Charts not displaying correctly
- Verify your data contains the expected columns
- Check for null or invalid values in numeric columns
- Ensure date columns are properly formatted

## Example View Creation

If you're starting from scratch, here's a simple example to get started:

```sql
CREATE OR REPLACE VIEW OPENFLOW_CREDIT_USAGE_VIEW AS
SELECT
    'runtime-001' AS RUNTIME_KEY,
    'SMALL' AS DATA_PLANE_TYPE,
    30 AS ACTIVE_DAYS,
    1 AS DATA_PLANES_USED,
    150.50 AS TOTAL_RUNTIME_CREDITS,
    75.25 AS TOTAL_DATA_PLANE_CREDITS,
    225.75 AS TOTAL_CREDITS,
    7.52 AS AVG_DAILY_CREDITS,
    2.15 AS STDDEV_DAILY_CREDITS,
    3.20 AS MIN_DAILY_CREDITS,
    12.80 AS MAX_DAILY_CREDITS,
    7.52 AS CREDITS_PER_ACTIVE_DAY,
    66.7 AS RUNTIME_COST_PERCENTAGE,
    33.3 AS DATA_PLANE_COST_PERCENTAGE,
    'STANDARD' AS COST_MODEL,
    'LOW_USAGE' AS USAGE_CATEGORY,
    'FREQUENT' AS USAGE_PATTERN,
    'VERY_EFFICIENT' AS EFFICIENCY_RATING,
    DATE('2024-10-01') AS FIRST_USAGE_DATE,
    DATE('2024-10-31') AS LAST_USAGE_DATE;
```

This will create a view with sample data that you can use to test the dashboard before connecting real credit data.

## Support

For questions or issues:
1. Check the main README.md for general troubleshooting
2. Review the SQL script comments in `create_credit_usage_view.sql`
3. Verify your Snowflake permissions and data sources
4. Contact your Snowflake administrator for assistance with credit tracking data




