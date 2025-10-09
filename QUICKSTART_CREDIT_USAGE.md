# Quick Start: Credit Usage Page

## 🚀 Get Started in 5 Steps

### Step 1: Understand What You Have
A new **Credit Usage** page has been added to your Streamlit dashboard with comprehensive analytics:
- 📊 Summary metrics and KPIs
- 🎯 Interactive filters and search
- 📈 10+ visualizations across 4 tabs
- 💾 CSV export capability

### Step 2: Prepare Your Data Source
You need credit usage data with these key fields:
- Runtime identifiers (RUNTIME_KEY)
- Credit amounts (TOTAL_CREDITS, RUNTIME_CREDITS, DATA_PLANE_CREDITS)
- Usage metrics (ACTIVE_DAYS, dates)
- Classifications (USAGE_CATEGORY, EFFICIENCY_RATING, etc.)

**Don't have this data yet?** See "Option A" below for sample data.

### Step 3: Create the View

#### Option A: Test with Sample Data (Recommended for Testing)
```sql
-- Creates a view with 50 sample records for testing
CREATE OR REPLACE VIEW OPENFLOW_CREDIT_USAGE_VIEW AS
SELECT
    'runtime-' || SEQ4() AS RUNTIME_KEY,
    CASE WHEN UNIFORM(1, 3, RANDOM()) = 1 THEN 'SMALL'
         WHEN UNIFORM(1, 3, RANDOM()) = 2 THEN 'MEDIUM'
         ELSE 'LARGE' END AS DATA_PLANE_TYPE,
    UNIFORM(10, 90, RANDOM()) AS ACTIVE_DAYS,
    UNIFORM(1, 5, RANDOM()) AS DATA_PLANES_USED,
    UNIFORM(100.00, 1000.00, RANDOM()) AS TOTAL_RUNTIME_CREDITS,
    UNIFORM(50.00, 500.00, RANDOM()) AS TOTAL_DATA_PLANE_CREDITS,
    TOTAL_RUNTIME_CREDITS + TOTAL_DATA_PLANE_CREDITS AS TOTAL_CREDITS,
    (TOTAL_RUNTIME_CREDITS + TOTAL_DATA_PLANE_CREDITS) / ACTIVE_DAYS AS AVG_DAILY_CREDITS,
    UNIFORM(1.00, 20.00, RANDOM()) AS STDDEV_DAILY_CREDITS,
    UNIFORM(5.00, 50.00, RANDOM()) AS MIN_DAILY_CREDITS,
    UNIFORM(100.00, 200.00, RANDOM()) AS MAX_DAILY_CREDITS,
    AVG_DAILY_CREDITS AS CREDITS_PER_ACTIVE_DAY,
    (TOTAL_RUNTIME_CREDITS / TOTAL_CREDITS) * 100 AS RUNTIME_COST_PERCENTAGE,
    (TOTAL_DATA_PLANE_CREDITS / TOTAL_CREDITS) * 100 AS DATA_PLANE_COST_PERCENTAGE,
    'STANDARD' AS COST_MODEL,
    CASE WHEN TOTAL_CREDITS > 800 THEN 'HIGH_USAGE'
         WHEN TOTAL_CREDITS > 400 THEN 'MEDIUM_USAGE'
         ELSE 'LOW_USAGE' END AS USAGE_CATEGORY,
    CASE WHEN ACTIVE_DAYS > 60 THEN 'CONTINUOUS'
         WHEN ACTIVE_DAYS > 30 THEN 'FREQUENT'
         ELSE 'REGULAR' END AS USAGE_PATTERN,
    CASE WHEN CREDITS_PER_ACTIVE_DAY < 10 THEN 'VERY_EFFICIENT'
         WHEN CREDITS_PER_ACTIVE_DAY < 20 THEN 'EFFICIENT'
         WHEN CREDITS_PER_ACTIVE_DAY < 30 THEN 'MODERATE'
         ELSE 'INEFFICIENT' END AS EFFICIENCY_RATING,
    DATEADD('day', -ACTIVE_DAYS, CURRENT_DATE()) AS FIRST_USAGE_DATE,
    CURRENT_DATE() AS LAST_USAGE_DATE
FROM TABLE(GENERATOR(ROWCOUNT => 50));

-- Grant permissions
GRANT SELECT ON VIEW OPENFLOW_CREDIT_USAGE_VIEW TO ROLE YOUR_ROLE;
```

#### Option B: Use Your Actual Data (For Production)
1. Open `create_credit_usage_view.sql`
2. Replace `YOUR_CREDIT_USAGE_SOURCE_TABLE` with your actual table
3. Adjust column mappings to match your schema
4. Run the customized SQL in Snowflake

### Step 4: Deploy the Updated App
```sql
-- Redeploy the Streamlit app with the new Credit Usage page
CREATE OR REPLACE STREAMLIT openflow_dashboard
FROM 'streamlit_app.py'
MAIN_FILE = 'streamlit_app.py';

-- Grant usage
GRANT USAGE ON STREAMLIT openflow_dashboard TO ROLE YOUR_ROLE;
```

### Step 5: Access and Explore
1. Open your Snowflake web interface
2. Navigate to Streamlit Apps
3. Click on "openflow_dashboard"
4. Select **"Credit Usage"** from the left sidebar
5. Explore the four tabs:
   - **Overview**: See top consumers and distribution
   - **Cost Analysis**: Analyze cost breakdown
   - **Usage Patterns**: Identify trends
   - **Detailed Data**: View and export all data

---

## 📊 What You'll See

### Summary Metrics (Top of Page)
```
┌─────────────────────┬─────────────────┬──────────────────────┬─────────────────────┐
│ Total Credits Used  │ Total Runtimes  │ Avg Credits/Runtime  │ Total Active Days   │
│     12,345.67       │       50        │       246.91         │       2,500         │
└─────────────────────┴─────────────────┴──────────────────────┴─────────────────────┘
```

### Filters
```
┌──────────────────────┬────────────────────────┬──────────────────────────┐
│ Search by Runtime    │ Filter by Usage        │ Filter by Efficiency     │
│ [_____________]      │ [☑ HIGH   ☑ MEDIUM]   │ [☑ EFFICIENT  ☑ MODERATE]│
└──────────────────────┴────────────────────────┴──────────────────────────┘
```

### Tab Navigation
```
┌─────────┬───────────────┬───────────────┬──────────────┐
│ Overview│ Cost Analysis │ Usage Patterns│ Detailed Data│
└─────────┴───────────────┴───────────────┴──────────────┘
```

---

## 🎨 Visualizations Overview

### Overview Tab
1. **Bar Chart**: Top 10 runtimes by credits (color by efficiency)
2. **Pie Chart**: Distribution by usage category
3. **Scatter Plot**: Runtime vs data plane credits

### Cost Analysis Tab
4. **Stacked Bar**: Cost percentage breakdown (top 20)
5. **Pie Chart**: Cost model distribution
6. **Table**: Efficiency statistics

### Usage Patterns Tab
7. **Bar Chart**: Pattern distribution
8. **Box Plot**: Credits per active day
9. **Scatter Plot**: Daily credit variability
10. **Timeline**: First/last usage dates

### Detailed Data Tab
11. **Sortable Table**: All data with color coding
12. **Statistics**: Descriptive statistics
13. **Export Button**: Download as CSV

---

## 🔍 Quick Troubleshooting

### ❌ "No credit usage data found"
**Solution**: Verify the view exists and has data
```sql
-- Check if view exists
SHOW VIEWS LIKE 'OPENFLOW_CREDIT_USAGE_VIEW';

-- Check if it has data
SELECT COUNT(*) FROM OPENFLOW_CREDIT_USAGE_VIEW;
```

### ❌ "Error querying credit usage"
**Solution**: Check permissions
```sql
-- Grant SELECT permission
GRANT SELECT ON VIEW OPENFLOW_CREDIT_USAGE_VIEW TO ROLE YOUR_ROLE;
```

### ❌ Charts not loading
**Solution**: Verify data types match expected schema
```sql
-- Check column types
DESCRIBE VIEW OPENFLOW_CREDIT_USAGE_VIEW;
```

---

## 💡 Tips for Best Results

1. **Start with Sample Data**: Use Option A above to test the page first
2. **Customize Gradually**: Once working, replace with real data
3. **Check Date Ranges**: Ensure FIRST_USAGE_DATE and LAST_USAGE_DATE are populated
4. **Use Filters**: Large datasets load faster with active filters
5. **Export for Analysis**: Use CSV export for deeper analysis in other tools

---

## 📚 Additional Resources

- **Full Setup Guide**: See `CREDIT_USAGE_SETUP.md`
- **All Changes**: See `CHANGES_SUMMARY.md`
- **SQL Template**: See `create_credit_usage_view.sql`
- **Main Documentation**: See `README.md`

---

## 🎯 Success Checklist

- [ ] View `OPENFLOW_CREDIT_USAGE_VIEW` created
- [ ] View contains data (at least 1 row)
- [ ] Permissions granted to your role
- [ ] Streamlit app redeployed
- [ ] Can access "Credit Usage" page
- [ ] Summary metrics display correctly
- [ ] All four tabs load successfully
- [ ] Charts render properly
- [ ] CSV export works

**All checked?** 🎉 You're ready to analyze your OpenFlow credit usage!

---

## 🆘 Need Help?

1. Review error messages in the Streamlit UI
2. Check Snowflake query history for SQL errors
3. Verify your role has necessary permissions
4. Consult your Snowflake administrator
5. Review the detailed setup guide in `CREDIT_USAGE_SETUP.md`




