#!/usr/bin/env python
"""
Health check script for celery-beat service.
Checks if celery beat process is running by verifying the schedule file is being updated.
"""
import os
import sys
import time
from pathlib import Path

def check_celery_beat():
    """
    Check if celery beat is running by:
    1. Verifying the schedule file exists
    2. Checking if it's been updated recently (within last 5 minutes)
    """
    schedule_file = Path('/tmp/celerybeat-schedule')
    
    # Check if schedule file exists
    if not schedule_file.exists():
        # If file doesn't exist, beat might be starting up
        # Allow some time for initial startup (check if process exists as fallback)
        try:
            import subprocess
            # Try using pgrep if available, otherwise check /proc
            result = subprocess.run(
                ['pgrep', '-f', 'celery.*beat'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return 0  # Process exists, file will be created soon
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            # pgrep not available or failed - this is OK during startup
            # Return 0 to give beat time to create the schedule file
            # The health check start_period should handle initial startup
            pass
        # If file doesn't exist and we can't verify process, assume unhealthy
        # (but this might be OK during very first startup)
        return 1
    
    # Check if file has been modified recently (within last 5 minutes)
    try:
        file_mtime = schedule_file.stat().st_mtime
        current_time = time.time()
        time_diff = current_time - file_mtime
        
        # If file was modified within last 5 minutes, beat is healthy
        if time_diff < 300:  # 5 minutes
            return 0
        else:
            # File exists but hasn't been updated recently - might be stuck
            return 1
    except Exception as e:
        # If we can't check the file, assume unhealthy
        return 1

if __name__ == '__main__':
    sys.exit(check_celery_beat())

