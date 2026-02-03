import requests
import time
from datetime import datetime
from database import init_database, save_check, get_stats, get_recent_checks
from sites_config import load_sites
from email_config import send_email_alert, format_email_alert
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ===== TELEGRAM CONFIG =====
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# ===== SITES TO MONITOR =====
SITES_TO_MONITOR = load_sites()

CHECK_INTERVAL = 300  # Check every 5 minutes (300 seconds)

def send_telegram_alert(message):
    """Send alert via Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        requests.post(url, data=data)
        print("📱 Telegram alert sent")
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

def check_website(url, max_retries=3, retry_delay=2):
    """Check if a website is responding with retry logic"""
    # Headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    last_error = None
    last_status_code = None
    last_response_time = None
    
    # Try multiple times before giving up
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5, headers=headers, allow_redirects=True)
            response_time = response.elapsed.total_seconds()
            last_response_time = response_time
            
            if response.status_code == 200:
                print(f"✅ {url} is UP - Response time: {response_time}s")
                
                # Check if this is a recovery (was down before, now up)
                recent = get_recent_checks(url, limit=3)
                was_down = any(check[1] in ['down', 'warning'] for check in recent) if recent else False
                
                result = {
                    "url": url,
                    "status": "up",
                    "response_time": response_time,
                    "status_code": response.status_code,
                    "timestamp": datetime.now()
                }
                
                # Send recovery alert if site was previously down
                if was_down:
                    stats = get_stats(url)
                    recovery_message = f"""✅ <b>RECOVERY: Site Back Online</b>

🌐 <b>Site:</b> {url}
⏱ <b>Response Time:</b> {response_time:.2f}s
🕐 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 <b>Overall Uptime:</b> {stats['uptime_percentage']:.1f}%

The site is responding normally again."""
                    
                    send_telegram_alert(recovery_message)
                    
                    email_subject = f"✅ RECOVERY: {url} is back online"
                    email_body = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; padding: 20px;">
                        <div style="background: #10b981; color: white; padding: 20px; border-radius: 10px;">
                            <h2>✅ Site Recovered</h2>
                            <p><strong>{url}</strong> is back online!</p>
                        </div>
                        <div style="margin-top: 20px; padding: 15px; background: #f9fafb; border-radius: 8px;">
                            <p><strong>Response Time:</strong> {response_time:.2f}s</p>
                            <p><strong>Overall Uptime:</strong> {stats['uptime_percentage']:.1f}%</p>
                            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                        </div>
                    </body>
                    </html>
                    """
                    send_email_alert(email_subject, email_body)
                
                return result
                
            else:
                # Non-200 status code - might be temporary, retry
                last_status_code = response.status_code
                
                if attempt < max_retries - 1:
                    print(f"⚠️ {url} returned {response.status_code}, retrying ({attempt + 1}/{max_retries})...")
                    time.sleep(retry_delay)
                    continue
                
                # Still failing after retries
                print(f"⚠️ {url} returned status code: {response.status_code} (after {max_retries} attempts)")
                
                stats = get_stats(url)
                recent = get_recent_checks(url, limit=3)
                consecutive_failures = sum(1 for check in recent if check[1] != "up") if recent else 0
                
                # DEBUG
                print(f"   🐛 DEBUG: recent checks = {len(recent) if recent else 0}")
                print(f"   🐛 DEBUG: consecutive_failures = {consecutive_failures}")
                
                # Only alert if 2+ consecutive failures (this would be the 2nd+ failure)
                if consecutive_failures >= 1:
                    message = f"""⚠️ <b>WARNING: Unusual Status Code</b>

🌐 <b>Site:</b> {url}
📊 <b>Status Code:</b> {response.status_code}
⏱ <b>Response Time:</b> {response_time:.2f}s
🕐 <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}
🔄 <b>Retries:</b> {max_retries} attempts made

📈 <b>Recent Performance:</b>
   • Uptime: {stats['uptime_percentage']:.1f}%
   • Consecutive failures: {consecutive_failures + 1}

This is <b>not a complete failure</b>, but the site returned an error code after multiple attempts."""
                    
                    send_telegram_alert(message)
                    
                    email_subject, email_body = format_email_alert(
                        url, 
                        status_code=response.status_code, 
                        stats={'uptime': stats['uptime_percentage'], 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    )
                    send_email_alert(email_subject, email_body)
                else:
                    print(f"   ⏸️  Not alerting yet - this is the first failure (need 2+ consecutive)")
                
                return {
                    "url": url,
                    "status": "warning",
                    "response_time": response_time,
                    "status_code": response.status_code,
                    "timestamp": datetime.now()
                }
                
        except requests.exceptions.RequestException as e:
            last_error = e
            
            # Retry on connection errors
            if attempt < max_retries - 1:
                print(f"❌ {url} failed (attempt {attempt + 1}/{max_retries}): {str(e)[:80]}")
                print(f"   🔄 Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
    
    # All retries failed
    print(f"❌ {url} is DOWN after {max_retries} attempts - Error: {str(last_error)[:80]}")
    
    stats = get_stats(url)
    recent = get_recent_checks(url, limit=3)
    consecutive_failures = sum(1 for check in recent if check[1] != "up") if recent else 0
    
    # DEBUG
    print(f"   🐛 DEBUG: recent checks = {len(recent) if recent else 0}")
    print(f"   🐛 DEBUG: consecutive_failures = {consecutive_failures}")
    
    # Only alert if 2+ consecutive failures (this would be the 2nd+ failure)
    if consecutive_failures >= 1:
        recent_checks = get_recent_checks(url, limit=5)
        recent_failures = sum(1 for check in recent_checks if check[1] != "up") if recent_checks else 0
        
        message = f"""🚨 <b>ALERT: Site Down</b>

🌐 <b>Site:</b> {url}
❌ <b>Error:</b> {str(last_error)[:100]}
🕐 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔄 <b>Retries:</b> {max_retries} attempts made

📊 <b>Historical Context:</b>
   • Previous Uptime: {stats['uptime_percentage']:.1f}%
   • Total Checks: {stats['total_checks']}
   • Consecutive failures: {consecutive_failures + 1}
   • Recent Failures: {recent_failures + 1}/6 checks

{'🔴 <b>RECURRING ISSUE</b>' if recent_failures >= 2 else '⚡ Confirmed failure after retries'}

━━━━━━━━━━━━━━━━━━━━
Monitor will check again in {CHECK_INTERVAL//60} minutes."""
        
        send_telegram_alert(message)
        
        email_subject, email_body = format_email_alert(
            url, 
            error=str(last_error), 
            stats={'uptime': stats['uptime_percentage'], 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        )
        send_email_alert(email_subject, email_body)
    else:
        print(f"   ⏸️  Not alerting yet - this is the first failure (need 2+ consecutive)")
    
    return {
        "url": url,
        "status": "down",
        "response_time": None,
        "error": str(last_error),
        "timestamp": datetime.now()
    }

def check_all_sites():
    """Check all monitored sites"""
    print(f"\n{'='*50}")
    print(f"🔍 Checking sites at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")
    
    results = []
    for site in SITES_TO_MONITOR:
        result = check_website(site)
        results.append(result)
        
        # Save to database
        save_check(result)
        
        time.sleep(1)  # Wait 1 second between checks to be polite
    
    return results

def run_monitor():
    """Main monitoring loop"""
    global SITES_TO_MONITOR
    
    # Initialize database first
    init_database()
    
    print("🚀 Site Monitor Started!")
    print(f"Monitoring {len(SITES_TO_MONITOR)} sites")
    print(f"Check interval: {CHECK_INTERVAL} seconds ({CHECK_INTERVAL/60} minutes)")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        while True:
            # Reload sites in case they changed
            SITES_TO_MONITOR = load_sites()
            
            check_all_sites()
            print(f"\n💤 Sleeping for {CHECK_INTERVAL} seconds...")
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitor stopped by user")
        
        # Show stats before exiting
        print("\n📊 Final Statistics:")
        for site in SITES_TO_MONITOR:
            stats = get_stats(site)
            print(f"\n{site}")
            print(f"  Total checks: {stats['total_checks']}")
            print(f"  Uptime: {stats['uptime_percentage']:.2f}%")
            print(f"  Avg response: {stats['avg_response_time']:.3f}s")

# Run it
if __name__ == "__main__":
    run_monitor()