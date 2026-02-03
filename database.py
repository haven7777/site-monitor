import sqlite3
from datetime import datetime

DB_FILE = "monitor.db"

def init_database():
    """Create the database and tables if they don't exist"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create checks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            status TEXT NOT NULL,
            response_time REAL,
            status_code INTEGER,
            error TEXT,
            timestamp DATETIME NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

def save_check(check_result):
    """Save a check result to the database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO checks (url, status, response_time, status_code, error, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        check_result['url'],
        check_result['status'],
        check_result.get('response_time'),
        check_result.get('status_code'),
        check_result.get('error'),
        check_result['timestamp']
    ))
    
    conn.commit()
    conn.close()

def get_recent_checks(url, limit=10):
    """Get recent checks for a specific URL"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT url, status, response_time, status_code, timestamp
        FROM checks
        WHERE url = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (url, limit))
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_stats(url):
    """Get uptime statistics for a URL"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Total checks
    cursor.execute('SELECT COUNT(*) FROM checks WHERE url = ?', (url,))
    total = cursor.fetchone()[0]
    
    # Successful checks
    cursor.execute('SELECT COUNT(*) FROM checks WHERE url = ? AND status = "up"', (url,))
    successful = cursor.fetchone()[0]
    
    # Average response time
    cursor.execute('SELECT AVG(response_time) FROM checks WHERE url = ? AND status = "up"', (url,))
    avg_response = cursor.fetchone()[0]
    
    conn.close()
    
    if total > 0:
        uptime_percentage = (successful / total) * 100
    else:
        uptime_percentage = 0
    
    return {
        'total_checks': total,
        'successful_checks': successful,
        'uptime_percentage': uptime_percentage,
        'avg_response_time': avg_response if avg_response else 0
    }

def get_checks_by_date_range(url, start_date, end_date):
    """Get checks for a URL within a date range"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT timestamp, status, response_time, status_code, error
        FROM checks
        WHERE url = ? AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp DESC
    ''', (url, start_date, end_date))
    
    results = cursor.fetchall()
    conn.close()
    
    return results

def get_all_incidents(hours=168):
    """Get all incident events (status changes) across all sites"""
    from datetime import datetime, timedelta
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    since = datetime.now() - timedelta(hours=hours)
    
    # Get all checks ordered by time
    cursor.execute('''
        SELECT url, timestamp, status, status_code, error
        FROM checks
        WHERE timestamp > ?
        ORDER BY timestamp ASC
    ''', (since,))
    
    all_checks = cursor.fetchall()
    conn.close()
    
    if not all_checks:
        return []
    
    # Identify incidents (status changes)
    incidents = []
    site_previous_status = {}
    
    for check in all_checks:
        url, timestamp, status, status_code, error = check
        
        previous_status = site_previous_status.get(url)
        
        # Detect status change (skip first check for each site)
        if previous_status is not None and previous_status != status:
            incident = {
                'url': url,
                'timestamp': timestamp,
                'from_status': previous_status,
                'to_status': status,
                'status_code': status_code,
                'error': error
            }
            incidents.append(incident)
        
        site_previous_status[url] = status
    
    # Return most recent first
    return list(reversed(incidents))

def get_overall_stats():
    """Get overall statistics across all sites (current sites only)"""
    from sites_config import load_sites
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get currently monitored sites
    current_sites = load_sites()
    
    if not current_sites:
        conn.close()
        return {
            'total_checks': 0,
            'successful_checks': 0,
            'total_sites': 0,
            'overall_uptime': 0,
            'avg_response_time': 0
        }
    
    # Build query to only include current sites
    placeholders = ','.join(['?' for _ in current_sites])
    
    # Total checks for current sites only
    cursor.execute(f'SELECT COUNT(*) FROM checks WHERE url IN ({placeholders})', current_sites)
    total_checks = cursor.fetchone()[0]
    
    # Successful checks for current sites only
    cursor.execute(f'SELECT COUNT(*) FROM checks WHERE url IN ({placeholders}) AND status = "up"', current_sites)
    successful_checks = cursor.fetchone()[0]
    
    # Total sites monitored (current only)
    total_sites = len(current_sites)
    
    # Average response time for current sites only
    cursor.execute(f'SELECT AVG(response_time) FROM checks WHERE url IN ({placeholders}) AND status = "up"', current_sites)
    avg_response = cursor.fetchone()[0]
    
    conn.close()
    
    overall_uptime = (successful_checks / total_checks * 100) if total_checks > 0 else 0
    
    return {
        'total_checks': total_checks,
        'successful_checks': successful_checks,
        'total_sites': total_sites,
        'overall_uptime': overall_uptime,
        'avg_response_time': avg_response if avg_response else 0
    }