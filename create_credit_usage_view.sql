-- SQL Script to create the OpenFlow Credit Usage View
-- This view provides comprehensive credit usage tracking for OpenFlow runtimes

-- Update this view definition based on your actual credit usage data source
-- You may need to adjust the source table/view name and column mappings

CREATE OR REPLACE VIEW OPENFLOW_CREDIT_USAGE_VIEW AS
SELECT 
    -- Runtime identification
    RUNTIME_KEY,
    DATA_PLANE_TYPE,
    
    -- Usage metrics
    ACTIVE_DAYS,
    DATA_PLANES_USED,
    
    -- Credit totals
    TOTAL_RUNTIME_CREDITS,
    TOTAL_DATA_PLANE_CREDITS,
    TOTAL_CREDITS,
    
    -- Daily credit statistics
    AVG_DAILY_CREDITS,
    STDDEV_DAILY_CREDITS,
    MIN_DAILY_CREDITS,
    MAX_DAILY_CREDITS,
    CREDITS_PER_ACTIVE_DAY,
    
    -- Cost breakdown percentages
    RUNTIME_COST_PERCENTAGE,
    DATA_PLANE_COST_PERCENTAGE,
    
    -- Classification and analysis
    COST_MODEL,
    USAGE_CATEGORY,
    USAGE_PATTERN,
    EFFICIENCY_RATING,
    
    -- Timeline
    FIRST_USAGE_DATE,
    LAST_USAGE_DATE
FROM 
    -- Replace this with your actual source table or computed view
    -- Example sources might be:
    -- - A dedicated credit tracking table
    -- - A materialized view from metering data
    -- - Results from ACCOUNT_USAGE.METERING_HISTORY
    YOUR_CREDIT_USAGE_SOURCE_TABLE
ORDER BY 
    TOTAL_CREDITS DESC;

-- Grant permissions (adjust role as needed)
GRANT SELECT ON VIEW OPENFLOW_CREDIT_USAGE_VIEW TO ROLE YOUR_ROLE;

-- Example: If you need to create a sample view from telemetry data
-- This is a template showing how you might compute credit metrics from raw data
/*
CREATE OR REPLACE VIEW OPENFLOW_CREDIT_USAGE_VIEW AS
WITH runtime_usage AS (
    SELECT 
        RESOURCE_ATTRIBUTES:"k8s.namespace.name"::VARCHAR AS RUNTIME_KEY,
        RESOURCE_ATTRIBUTES:"openflow.dataplane.type"::VARCHAR AS DATA_PLANE_TYPE,
        DATE_TRUNC('day', TIMESTAMP) AS USAGE_DATE,
        -- Add your credit calculation logic here
        COUNT(DISTINCT RESOURCE_ATTRIBUTES:"openflow.dataplane.id") AS DATA_PLANES_USED
    FROM SNOWFLAKE.TELEMETRY.EVENTS_VIEW
    WHERE RESOURCE_ATTRIBUTES:"k8s.namespace.name" LIKE 'runtime-%'
        AND RECORD_TYPE = 'METRIC'
        AND TIMESTAMP >= DATEADD('day', -90, CURRENT_DATE())
    GROUP BY 1, 2, 3
),
credit_aggregates AS (
    SELECT
        RUNTIME_KEY,
        DATA_PLANE_TYPE,
        COUNT(DISTINCT USAGE_DATE) AS ACTIVE_DAYS,
        MAX(DATA_PLANES_USED) AS DATA_PLANES_USED,
        -- Replace these with actual credit values from your metering source
        SUM(0) AS TOTAL_RUNTIME_CREDITS,
        SUM(0) AS TOTAL_DATA_PLANE_CREDITS,
        SUM(0) AS TOTAL_CREDITS,
        AVG(0) AS AVG_DAILY_CREDITS,
        STDDEV(0) AS STDDEV_DAILY_CREDITS,
        MIN(0) AS MIN_DAILY_CREDITS,
        MAX(0) AS MAX_DAILY_CREDITS,
        MIN(USAGE_DATE) AS FIRST_USAGE_DATE,
        MAX(USAGE_DATE) AS LAST_USAGE_DATE
    FROM runtime_usage
    GROUP BY 1, 2
)
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
    CASE 
        WHEN ACTIVE_DAYS > 0 THEN TOTAL_CREDITS / ACTIVE_DAYS 
        ELSE 0 
    END AS CREDITS_PER_ACTIVE_DAY,
    CASE 
        WHEN TOTAL_CREDITS > 0 THEN (TOTAL_RUNTIME_CREDITS / TOTAL_CREDITS) * 100 
        ELSE 0 
    END AS RUNTIME_COST_PERCENTAGE,
    CASE 
        WHEN TOTAL_CREDITS > 0 THEN (TOTAL_DATA_PLANE_CREDITS / TOTAL_CREDITS) * 100 
        ELSE 0 
    END AS DATA_PLANE_COST_PERCENTAGE,
    'STANDARD' AS COST_MODEL,
    CASE 
        WHEN TOTAL_CREDITS > 1000 THEN 'HIGH_USAGE'
        WHEN TOTAL_CREDITS > 100 THEN 'MEDIUM_USAGE'
        ELSE 'LOW_USAGE'
    END AS USAGE_CATEGORY,
    CASE 
        WHEN ACTIVE_DAYS > 60 THEN 'CONTINUOUS'
        WHEN ACTIVE_DAYS > 30 THEN 'FREQUENT'
        WHEN ACTIVE_DAYS > 7 THEN 'REGULAR'
        ELSE 'SPORADIC'
    END AS USAGE_PATTERN,
    CASE 
        WHEN CREDITS_PER_ACTIVE_DAY < 10 THEN 'VERY_EFFICIENT'
        WHEN CREDITS_PER_ACTIVE_DAY < 50 THEN 'EFFICIENT'
        WHEN CREDITS_PER_ACTIVE_DAY < 100 THEN 'MODERATE'
        ELSE 'INEFFICIENT'
    END AS EFFICIENCY_RATING,
    FIRST_USAGE_DATE,
    LAST_USAGE_DATE
FROM credit_aggregates
ORDER BY TOTAL_CREDITS DESC;
*/




