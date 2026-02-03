from flask import Flask, request, redirect, send_file
from database import get_stats, get_recent_checks, get_all_incidents, get_overall_stats
import sqlite3
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.io as pio
from sites_config import load_sites, add_site, remove_site
from pdf_generator import generate_uptime_report
import io

app = Flask(__name__)

def get_all_sites_status():
    """Get current status for all monitored sites"""
    sites_data = []
    sites_to_monitor = load_sites()  # Load from config
    
    for url in sites_to_monitor:
        stats = get_stats(url)
        recent = get_recent_checks(url, limit=1)
        
        if recent:
            last_check = recent[0]
            last_status = last_check[1]
            last_time = last_check[4]
        else:
            last_status = "unknown"
            last_time = None
        
        sites_data.append({
            'url': url,
            'status': last_status,
            'uptime': stats['uptime_percentage'],
            'total_checks': stats['total_checks'],
            'avg_response': stats['avg_response_time'],
            'last_checked': last_time
        })
    
    return sites_data

def get_site_history(url, hours=24):
    """Get check history for a site"""
    conn = sqlite3.connect('monitor.db')
    cursor = conn.cursor()
    
    since = datetime.now() - timedelta(hours=hours)
    
    cursor.execute('''
        SELECT timestamp, status, response_time, status_code
        FROM checks
        WHERE url = ? AND timestamp > ?
        ORDER BY timestamp ASC
    ''', (url, since))
    
    results = cursor.fetchall()
    conn.close()
    
    return [{
        'timestamp': row[0],
        'status': row[1],
        'response_time': row[2],
        'status_code': row[3]
    } for row in results]

def create_response_time_chart(url):
    """Create a response time chart for the last 24 hours"""
    history = get_site_history(url, hours=24)
    
    if not history:
        return "<p style='color: #64748b; text-align: center;'>No data yet</p>"
    
    # Extract timestamps and response times
    timestamps = []
    response_times = []
    
    for check in history:
        if check['response_time'] is not None:
            timestamps.append(check['timestamp'])
            response_times.append(check['response_time'] * 1000)  # Convert to milliseconds
    
    if not response_times:
        return "<p style='color: #64748b; text-align: center;'>No successful checks yet</p>"
    
    # Create the chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=response_times,
        mode='lines+markers',
        name='Response Time',
        line=dict(color='#4f46e5', width=2),
        marker=dict(size=6),
        fill='tozeroy',
        fillcolor='rgba(79, 70, 229, 0.1)'
    ))
    
    fig.update_layout(
        title='Response Time (Last 24 Hours)',
        xaxis_title='Time',
        yaxis_title='Response Time (ms)',
        plot_bgcolor='rgba(15, 23, 42, 0.6)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0'),
        height=300,
        margin=dict(l=50, r=20, t=40, b=40),
        xaxis=dict(
            gridcolor='rgba(51, 65, 85, 0.3)',
            showgrid=True
        ),
        yaxis=dict(
            gridcolor='rgba(51, 65, 85, 0.3)',
            showgrid=True
        )
    )
    
    # Convert to HTML
    chart_html = pio.to_html(fig, include_plotlyjs='cdn', div_id=f'chart-{url}')
    return chart_html

@app.route('/')
def index():
    sites = get_all_sites_status()
    overall_stats = get_overall_stats()
    
    # Build HTML directly in Python (no template)
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Site Monitor Dashboard</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                color: #e2e8f0;
                padding: 40px 20px;
                min-height: 100vh;
            }
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            
            h1 {
                text-align: center;
                font-size: 3rem;
                color: #f1f5f9;
                margin-bottom: 15px;
                text-shadow: 0 2px 10px rgba(0,0,0,0.3);
            }
            
            .subtitle {
                text-align: center;
                color: #94a3b8;
                font-size: 1.2rem;
                margin-bottom: 50px;
            }
            
            .overall-stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                max-width: 1000px;
                margin: 0 auto 40px;
            }
            
            .stat-box {
                background: rgba(30, 41, 59, 0.8);
                padding: 25px;
                border-radius: 16px;
                border: 2px solid #334155;
                text-align: center;
            }
            
            .stat-box .stat-label {
                color: #94a3b8;
                font-size: 0.9rem;
                margin-bottom: 10px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .stat-box .stat-value {
                font-size: 2.2rem;
                font-weight: 700;
                color: #f1f5f9;
            }
            
            .action-buttons {
                max-width: 600px;
                margin: 0 auto 20px;
                text-align: center;
            }
            
            .action-button {
                display: inline-block;
                padding: 12px 28px;
                background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                color: white;
                text-decoration: none;
                border-radius: 12px;
                font-weight: 600;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
            }
            
            .action-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4);
            }
            
            .add-site-section {
                max-width: 600px;
                margin: 0 auto 20px;
                background: rgba(30, 41, 59, 0.8);
                padding: 25px;
                border-radius: 16px;
                border: 2px solid #334155;
            }
            
            .add-site-form {
                display: flex;
                gap: 15px;
            }
            
            .url-input {
                flex: 1;
                padding: 12px 20px;
                background: rgba(15, 23, 42, 0.8);
                border: 2px solid #334155;
                border-radius: 10px;
                color: #e2e8f0;
                font-size: 1rem;
                transition: border-color 0.3s;
            }
            
            .url-input:focus {
                outline: none;
                border-color: #4f46e5;
            }
            
            .url-input::placeholder {
                color: #64748b;
            }
            
            .add-button {
                padding: 12px 24px;
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: 700;
                font-size: 1rem;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            
            .add-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 30px rgba(16, 185, 129, 0.4);
            }
            
            .download-section {
                max-width: 700px;
                margin: 0 auto 40px;
                text-align: center;
                background: rgba(30, 41, 59, 0.6);
                padding: 25px;
                border-radius: 16px;
                border: 2px solid #334155;
            }
            
            .download-section h3 {
                color: #94a3b8;
                margin-bottom: 15px;
                font-size: 1.1rem;
            }
            
            .download-buttons {
                display: flex;
                gap: 10px;
                justify-content: center;
                flex-wrap: wrap;
            }
            
            .download-button {
                display: inline-block;
                padding: 14px 32px;
                background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);
                color: white;
                text-decoration: none;
                border-radius: 12px;
                font-weight: 700;
                font-size: 1.05rem;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
            }
            
            .download-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(79, 70, 229, 0.4);
            }
            
            .download-button-small {
                display: inline-block;
                padding: 12px 24px;
                background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                color: white;
                text-decoration: none;
                border-radius: 10px;
                font-weight: 600;
                font-size: 0.95rem;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
            }
            
            .download-button-small:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4);
            }
            
            .sites-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
                gap: 30px;
            }
            
            .site-card {
                background: rgba(30, 41, 59, 0.8);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 30px;
                border: 2px solid #334155;
                transition: all 0.3s ease;
            }
            
            .site-card:hover {
                transform: translateY(-5px);
                border-color: #4f46e5;
                box-shadow: 0 20px 60px rgba(79, 70, 229, 0.3);
            }
            
            .site-url {
                font-size: 1.4rem;
                font-weight: 600;
                color: #f1f5f9;
                margin-bottom: 20px;
                word-break: break-word;
            }
            
            .status-badge {
                display: inline-block;
                padding: 10px 20px;
                border-radius: 25px;
                font-weight: 700;
                margin-bottom: 25px;
                text-transform: uppercase;
                font-size: 0.9rem;
                letter-spacing: 1px;
            }
            
            .status-up { 
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
            }
            
            .status-down { 
                background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
                animation: pulse 2s infinite;
            }
            
            .status-warning { 
                background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3);
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }
            
            .stats {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
            }
            
            .stat {
                background: rgba(15, 23, 42, 0.6);
                padding: 20px;
                border-radius: 12px;
                border: 1px solid rgba(51, 65, 85, 0.5);
            }
            
            .stat-label {
                color: #94a3b8;
                font-size: 0.85rem;
                margin-bottom: 8px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                font-weight: 600;
            }
            
            .stat-value {
                font-size: 2rem;
                font-weight: 700;
                color: #f1f5f9;
            }
            
            .chart-container {
                margin-top: 25px;
                background: rgba(15, 23, 42, 0.6);
                padding: 15px;
                border-radius: 12px;
                border: 1px solid rgba(51, 65, 85, 0.5);
                overflow: hidden;
            }
            
            .chart-container > div {
                max-width: 100%;
                overflow: hidden;
            }
            
            .remove-button {
                display: inline-block;
                padding: 8px 16px;
                background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 0.85rem;
                cursor: pointer;
                margin-top: 15px;
                transition: transform 0.2s;
            }
            
            .remove-button:hover {
                transform: scale(1.05);
            }
            
            .footer {
                text-align: center;
                margin-top: 60px;
                padding: 20px;
                color: #64748b;
                font-size: 0.95rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 Site Monitor Dashboard</h1>
            <p class="subtitle">Monitoring """ + str(len(sites)) + """ websites in real-time</p>
            
            <!-- Overall Stats -->
            <div class="overall-stats">
    """
    
    if overall_stats['total_checks'] > 0:
        html += f"""
                <div class="stat-box">
                    <div class="stat-label">Overall Uptime</div>
                    <div class="stat-value">{overall_stats['overall_uptime']:.1f}%</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Total Checks</div>
                    <div class="stat-value">{overall_stats['total_checks']}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Sites Monitored</div>
                    <div class="stat-value">{overall_stats['total_sites']}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Avg Response</div>
                    <div class="stat-value">{overall_stats['avg_response_time']:.2f}s</div>
                </div>
        """
    else:
        html += """
                <div class="stat-box">
                    <div class="stat-label">Status</div>
                    <div class="stat-value">Initializing...</div>
                </div>
        """
    
    html += """
            </div>
            
            <!-- Action Buttons -->
            <div class="action-buttons">
                <a href="/incidents" class="action-button incidents-btn">📅 View Incident Timeline</a>
            </div>
            
            <!-- Add Site Form -->
            <div class="add-site-section">
                <form method="POST" action="/add_site" class="add-site-form">
                    <input type="text" name="url" placeholder="Enter website URL (e.g., example.com)" class="url-input" required>
                    <button type="submit" class="add-button">➕ Add Site</button>
                </form>
            </div>
            
            <!-- Download Report Section -->
            <div class="download-section">
                <h3>Download PDF Report</h3>
                <div class="download-buttons">
                    <a href="/download_report?days=1" class="download-button">📄 Last 24 Hours</a>
                    <a href="/download_report?days=7" class="download-button">📥 Last 7 Days</a>
                    <a href="/download_report?days=30" class="download-button">📊 Last 30 Days</a>
                </div>
            </div>
            
            <div class="sites-grid">
    """
    
    # Add each site card
    for site in sites:
        status_class = f"status-{site['status']}"
        status_text = "✓ UP" if site['status'] == 'up' else ("✗ DOWN" if site['status'] == 'down' else "⚠ WARNING")
        
        chart_html = create_response_time_chart(site['url'])
        
        html += f"""
        <div class="site-card">
            <div class="site-url">{site['url']}</div>
            <span class="status-badge {status_class}">{status_text}</span>
            
            <div class="stats">
                <div class="stat">
                    <div class="stat-label">Uptime</div>
                    <div class="stat-value">{site['uptime']:.1f}%</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Total Checks</div>
                    <div class="stat-value">{site['total_checks']}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Avg Response</div>
                    <div class="stat-value">{site['avg_response']:.2f}s</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Last Check</div>
                    <div class="stat-value" style="font-size: 1.3rem;">
                        {site['last_checked'].split()[1].split('.')[0] if site['last_checked'] else 'Never'}
                    </div>
                </div>
            </div>
            
            <div class="chart-container">
                {chart_html}
            </div>
            
            <form method="POST" action="/remove_site" style="margin-top: 15px;">
                <input type="hidden" name="url" value="{site['url']}">
                <button type="submit" class="remove-button">🗑️ Remove Site</button>
            </form>
        </div>
        """
    
    html += """
            </div>
            <div class="footer">
                <p>⚡ Dashboard refreshes automatically every 60 seconds</p>
            </div>
        </div>
        <script>
            setTimeout(() => location.reload(), 60000);
        </script>
    </body>
    </html>
    """
    
    return html

@app.route('/incidents')
def incidents():
    """Incident timeline page"""
    incidents_list = get_all_incidents(hours=168)  # Last 7 days
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Incident Timeline - Site Monitor</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                color: #e2e8f0;
                padding: 40px 20px;
                min-height: 100vh;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            
            h1 {
                text-align: center;
                font-size: 2.5rem;
                color: #f1f5f9;
                margin-bottom: 15px;
            }
            
            .back-link {
                display: inline-block;
                margin-bottom: 30px;
                padding: 10px 20px;
                background: rgba(79, 70, 229, 0.2);
                color: #a5b4fc;
                text-decoration: none;
                border-radius: 8px;
                transition: all 0.3s;
            }
            
            .back-link:hover {
                background: rgba(79, 70, 229, 0.3);
            }
            
            .timeline {
                position: relative;
                padding-left: 40px;
            }
            
            .timeline::before {
                content: '';
                position: absolute;
                left: 15px;
                top: 0;
                bottom: 0;
                width: 2px;
                background: #334155;
            }
            
            .incident {
                position: relative;
                margin-bottom: 30px;
                padding: 20px;
                background: rgba(30, 41, 59, 0.8);
                border-radius: 12px;
                border-left: 4px solid #4f46e5;
            }
            
            .incident::before {
                content: '';
                position: absolute;
                left: -29px;
                top: 25px;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #4f46e5;
                border: 3px solid #0f172a;
            }
            
            .incident.recovery {
                border-left-color: #10b981;
            }
            
            .incident.recovery::before {
                background: #10b981;
            }
            
            .incident.failure {
                border-left-color: #ef4444;
            }
            
            .incident.failure::before {
                background: #ef4444;
            }
            
            .incident-time {
                color: #94a3b8;
                font-size: 0.9rem;
                margin-bottom: 10px;
            }
            
            .incident-url {
                font-size: 1.2rem;
                font-weight: 600;
                margin-bottom: 10px;
                color: #f1f5f9;
            }
            
            .incident-change {
                font-size: 1rem;
                padding: 10px;
                background: rgba(15, 23, 42, 0.6);
                border-radius: 8px;
            }
            
            .status-badge {
                display: inline-block;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 0.85rem;
                font-weight: 600;
                margin: 0 5px;
            }
            
            .status-up {
                background: #10b981;
                color: white;
            }
            
            .status-down {
                background: #ef4444;
                color: white;
            }
            
            .status-warning {
                background: #f59e0b;
                color: white;
            }
            
            .no-incidents {
                text-align: center;
                padding: 60px 20px;
                color: #64748b;
                font-size: 1.2rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/" class="back-link">← Back to Dashboard</a>
            <h1>📅 Incident Timeline</h1>
            <p style="text-align: center; color: #94a3b8; margin-bottom: 40px;">Last 7 days of status changes</p>
            
            <div class="timeline">
    """
    
    if incidents_list:
        for incident in incidents_list:
            # Determine incident type
            if incident['to_status'] == 'up':
                incident_class = 'recovery'
                icon = '✅'
            else:
                incident_class = 'failure'
                icon = '🚨'
            
            from_badge_class = f"status-{incident['from_status']}"
            to_badge_class = f"status-{incident['to_status']}"
            
            from_text = incident['from_status'].upper()
            to_text = incident['to_status'].upper()
            
            html += f"""
            <div class="incident {incident_class}">
                <div class="incident-time">{incident['timestamp']}</div>
                <div class="incident-url">{incident['url']}</div>
                <div class="incident-change">
                    {icon} Status changed: 
                    <span class="status-badge {from_badge_class}">{from_text}</span>
                    →
                    <span class="status-badge {to_badge_class}">{to_text}</span>
                </div>
            </div>
            """
    else:
        html += """
        <div class="no-incidents">
            <p>🎉 No incidents in the last 7 days!</p>
            <p style="margin-top: 10px; font-size: 1rem;">All monitored sites have been stable.</p>
        </div>
        """
    
    html += """
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

@app.route('/add_site', methods=['POST'])
def add_site_route():
    """Add a new site via form submission"""
    url = request.form.get('url', '').strip()
    
    if url:
        # Add https:// if not present
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
        
        add_site(url)
    
    return redirect('/')

@app.route('/remove_site', methods=['POST'])
def remove_site_route():
    """Remove a site via form submission"""
    url = request.form.get('url', '')
    
    if url:
        remove_site(url)
    
    return redirect('/')

@app.route('/download_report')
def download_report():
    """Generate and download PDF report with optional date range"""
    # Get optional days parameter (default: 7 days)
    days = request.args.get('days', 7, type=int)
    
    # Limit to reasonable range
    if days < 1:
        days = 1
    if days > 365:
        days = 365
    
    # Generate PDF
    pdf_data = generate_uptime_report(days=days)
    
    # Create filename with timestamp and period
    filename = f"uptime_report_{days}days_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    # Return PDF as download
    return send_file(
        io.BytesIO(pdf_data),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

if __name__ == '__main__':
    print("Starting server...")
    app.run(debug=True, port=5001)