import platform
from datetime import datetime
import time

def get_system_info() -> str:
    """Get current local date, time, weekday, and system status."""
    now = datetime.now()
    return f"""Current Date & Time Information:
- Current Time: {now.strftime('%I:%M:%S %p')}
- Current Date: {now.strftime('%A, %B %d, %Y')}
- Timezone / Offset: {time.strftime('%Z (UTC %z)')}
- Host OS: {platform.system()} {platform.release()}
- Python Runtime: {platform.python_version()}"""
