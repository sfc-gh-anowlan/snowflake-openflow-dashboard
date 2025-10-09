import pandas as pd
import snowflake.connector
from typing import List, Optional
import os
from datetime import datetime

class SnowflakeConnector:
    def __init__(self, account: Optional[str] = None, user: Optional[str] = None, 
                 password: Optional[str] = None, warehouse: Optional[str] = None,
                 database: Optional[str] = None, schema: Optional[str] = None):
        """Initialize Snowflake connection"""
        self.account = account or os.getenv('SNOWFLAKE_ACCOUNT')
        self.user = user or os.getenv('SNOWFLAKE_USER')
        self.password = password or os.getenv('SNOWFLAKE_PASSWORD')
        self.warehouse = warehouse or os.getenv('SNOWFLAKE_WAREHOUSE')
        self.database = database or os.getenv('SNOWFLAKE_DATABASE')
        self.schema = schema or os.getenv('SNOWFLAKE_SCHEMA')
        
        if not all([self.account, self.user, self.password, self.warehouse]):
            raise ValueError("Missing required Snowflake connection parameters")
        
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Establish connection to Snowflake"""
        try:
            self.connection = snowflake.connector.connect(
                account=self.account,
                user=self.user,
                password=self.password,
                warehouse=self.warehouse,
                database=self.database,
                schema=self.schema
            )
        except Exception as e:
            raise Exception(f"Failed to connect to Snowflake: {str(e)}")
    
    def get_connector_status(self) -> pd.DataFrame:
        """Get status of OpenFlow connectors from telemetry events"""
        query = """
        SELECT 
            resource_attributes:"openflow.dataplane.id" as DEPLOYMENT_ID,
            resource_attributes:"k8s.namespace.name" as RUNTIME_KEY,
            resource_attributes:"k8s.pod.name" as POD_NAME,
            record_attributes:name as CONNECTOR_NAME,
            record_attributes:id as CONNECTOR_ID,
            CASE 
                WHEN record:metric:name = 'processor.run.status.running' AND TO_NUMBER(value) = 1 THEN 'RUNNING'
                WHEN record:metric:name = 'processor.run.status.running' AND TO_NUMBER(value) = 0 THEN 'STOPPED'
                ELSE 'UNKNOWN'
            END as STATUS,
            timestamp as LAST_REFRESH_TIME,
            NULL as ERROR_MESSAGE,
            timestamp as CREATED_ON,
            timestamp as MODIFIED_ON
        FROM SNOWFLAKE.TELEMETRY.EVENTS_VIEW
        WHERE true
            AND record_type = 'METRIC'
            AND record:metric:name = 'processor.run.status.running'
            AND timestamp > dateadd(minutes, -30, sysdate())
            AND resource_attributes:"k8s.namespace.name" like 'runtime-%'
            AND record_attributes:name IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 1000
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            cursor.close()
            
            if data:
                df = pd.DataFrame(data, columns=columns)
                # Set pandas option to handle large dataframes
                pd.set_option("styler.render.max_elements", 1000000)
                return df
            else:
                # Return empty DataFrame with expected columns
                return pd.DataFrame(columns=[
                    'DEPLOYMENT_ID', 'RUNTIME_KEY', 'POD_NAME', 'CONNECTOR_NAME', 
                    'CONNECTOR_ID', 'STATUS', 'LAST_REFRESH_TIME', 
                    'ERROR_MESSAGE', 'CREATED_ON', 'MODIFIED_ON'
                ])
        except Exception as e:
            print(f"Warning: Could not query OpenFlow telemetry: {str(e)}")
            return pd.DataFrame(columns=[
                'DEPLOYMENT_ID', 'RUNTIME_KEY', 'POD_NAME', 'CONNECTOR_NAME', 
                'CONNECTOR_ID', 'STATUS', 'LAST_REFRESH_TIME', 
                'ERROR_MESSAGE', 'CREATED_ON', 'MODIFIED_ON'
            ])
    
    def get_available_connectors(self) -> List[str]:
        """Get list of available connector names from telemetry events"""
        query = """
        SELECT DISTINCT record_attributes:name as CONNECTOR_NAME
        FROM SNOWFLAKE.TELEMETRY.EVENTS_VIEW
        WHERE true
            AND record_type = 'METRIC'
            AND record:metric:name = 'processor.run.status.running'
            AND timestamp > dateadd(minutes, -30, sysdate())
            AND resource_attributes:"k8s.namespace.name" like 'runtime-%'
            AND record_attributes:name IS NOT NULL
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            data = cursor.fetchall()
            cursor.close()
            
            return [row[0] for row in data] if data else []
        except Exception as e:
            print(f"Warning: Could not query available connectors: {str(e)}")
            return []
    
    def get_error_logs(self) -> pd.DataFrame:
        """Get error logs for OpenFlow runtimes using official Snowflake example"""
        query = """
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
                AND timestamp > dateadd('minutes', -30, sysdate())
                AND record_type = 'LOG'
                AND resource_attributes:"k8s.namespace.name" like 'runtime-%'
            ORDER BY timestamp DESC
        ) WHERE LOG_LEVEL = 'ERROR'
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            cursor.close()
            
            if data:
                return pd.DataFrame(data, columns=columns)
            else:
                return pd.DataFrame(columns=[
                    'TIMESTAMP', 'DEPLOYMENT_ID', 'RUNTIME_KEY', 
                    'LOG_LEVEL', 'LOGGER', 'MESSAGE', 'PARSED_LOG'
                ])
        except Exception as e:
            print(f"Warning: Could not query error logs: {str(e)}")
            return pd.DataFrame(columns=[
                'TIMESTAMP', 'DEPLOYMENT_ID', 'RUNTIME_KEY', 
                'LOG_LEVEL', 'LOGGER', 'MESSAGE', 'PARSED_LOG'
            ])
    
    def get_stuck_flowfiles(self) -> pd.DataFrame:
        """Find stuck FlowFiles using official Snowflake example"""
        query = """
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
                AND timestamp > dateadd(minutes, -30, sysdate())
            GROUP BY 1, 2, 3, 4
            ORDER BY MAX_QUEUED_FILE_MINUTES DESC
        ) WHERE MAX_QUEUED_FILE_MINUTES > 30
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            cursor.close()
            
            if data:
                return pd.DataFrame(data, columns=columns)
            else:
                return pd.DataFrame(columns=[
                    'DEPLOYMENT_ID', 'RUNTIME_KEY', 'CONNECTION_NAME', 
                    'CONNECTION_ID', 'MAX_QUEUED_FILE_MINUTES'
                ])
        except Exception as e:
            print(f"Warning: Could not query stuck FlowFiles: {str(e)}")
            return pd.DataFrame(columns=[
                'DEPLOYMENT_ID', 'RUNTIME_KEY', 'CONNECTION_NAME', 
                'CONNECTION_ID', 'MAX_QUEUED_FILE_MINUTES'
            ])
    
    def backup_connector(self, connector_name: str, stage_name: str) -> None:
        """Backup a connector configuration to an internal stage"""
        # This is a placeholder implementation
        # In practice, you would need to use OpenFlow API or specific commands
        # to export connector configuration
        
        backup_query = f"""
        -- Create stage if it doesn't exist
        CREATE STAGE IF NOT EXISTS {stage_name};
        
        -- Note: Actual connector backup would require OpenFlow API calls
        -- This is a placeholder for the backup process
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(backup_query)
            cursor.close()
        except Exception as e:
            raise Exception(f"Failed to backup connector {connector_name}: {str(e)}")
    
    def close(self):
        """Close the Snowflake connection"""
        if self.connection:
            self.connection.close()
