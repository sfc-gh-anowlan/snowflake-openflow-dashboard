import schedule
import time
import threading
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict
from .snowflake_connector import SnowflakeConnector

class BackupScheduler:
    def __init__(self, snowflake_connector: SnowflakeConnector):
        self.connector = snowflake_connector
        self.schedules = {}
        self._schedule_thread = None
        self._running = False

    def schedule_backup(self, connector_name: str, backup_time: datetime.time, stage_name: str) -> None:
        """Schedule a daily backup for a specific connector"""
        job_id = f"{connector_name}_{backup_time.strftime('%H:%M')}"
        
        # Remove existing schedule for this connector if it exists
        if job_id in self.schedules:
            schedule.cancel_job(self.schedules[job_id])
        
        # Create new schedule
        job = schedule.every().day.at(backup_time.strftime("%H:%M")).do(
            self.connector.backup_connector,
            connector_name=connector_name,
            stage_name=stage_name
        )
        
        self.schedules[job_id] = job
        
        # Start the scheduler thread if not already running
        if not self._running:
            self._start_scheduler()

    def get_schedules(self) -> pd.DataFrame:
        """Get all scheduled backups"""
        schedule_data = []
        for job_id, job in self.schedules.items():
            connector_name = job_id.split('_')[0]
            schedule_time = '_'.join(job_id.split('_')[1:])
            schedule_data.append({
                'connector_name': connector_name,
                'backup_time': schedule_time,
                'next_run': job.next_run
            })
        
        if schedule_data:
            return pd.DataFrame(schedule_data)
        return pd.DataFrame(columns=['connector_name', 'backup_time', 'next_run'])

    def get_available_connectors(self) -> List[str]:
        """Get list of available connectors"""
        return self.connector.get_available_connectors()

    def _start_scheduler(self) -> None:
        """Start the scheduler thread"""
        if self._schedule_thread is None or not self._schedule_thread.is_alive():
            self._running = True
            self._schedule_thread = threading.Thread(target=self._run_scheduler)
            self._schedule_thread.daemon = True
            self._schedule_thread.start()

    def _run_scheduler(self) -> None:
        """Run the scheduler loop"""
        while self._running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    def stop(self) -> None:
        """Stop the scheduler"""
        self._running = False
        if self._schedule_thread:
            self._schedule_thread.join()
        schedule.clear()
