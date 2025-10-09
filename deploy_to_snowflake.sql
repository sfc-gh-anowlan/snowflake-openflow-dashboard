-- Snowflake OpenFlow Dashboard Deployment Script
-- Run this script in your Snowflake environment to deploy the Streamlit app

-- Step 1: Create the Streamlit app
CREATE OR REPLACE STREAMLIT openflow_dashboard
FROM 'streamlit_app.py'
MAIN_FILE = 'streamlit_app.py';

-- Step 2: Grant usage permissions (replace 'your_role' with your actual role)
GRANT USAGE ON STREAMLIT openflow_dashboard TO ROLE your_role;

-- Step 3: Optional - Create a stage for backups if it doesn't exist
CREATE STAGE IF NOT EXISTS OPENFLOW_BACKUP_STAGE;

-- Step 4: Grant permissions on the backup stage
GRANT READ, WRITE ON STAGE OPENFLOW_BACKUP_STAGE TO ROLE your_role;

-- Step 5: Verify the deployment
SHOW STREAMLITS;

-- To access your Streamlit app:
-- 1. Go to your Snowflake web interface
-- 2. Navigate to Streamlit apps
-- 3. Click on "openflow_dashboard"
