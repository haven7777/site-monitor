cat > README.md << 'EOF'
# 🔍 Site Monitor Dashboard

A production-ready website monitoring system with real-time alerts, analytics dashboard, and comprehensive reporting.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## ✨ Features

- **Real-time Monitoring**: Checks website availability every 5 minutes
- **Smart Alerting**: 
  - 3-attempt retry logic with exponential backoff
  - Alerts only after 2+ consecutive failures
  - Recovery notifications when sites come back online
- **Multi-Channel Notifications**: Telegram + Email alerts
- **Web Dashboard**: Live status, response time charts, incident timeline
- **PDF Reports**: Generate reports with charts for any date range

## 🚀 Quick Start

### Installation

1. **Clone the repository**
```bash
   git clone https://github.com/haven7777/site-monitor.git
   cd site-monitor
```

2. **Install dependencies**
```bash
   pip install -r requirements.txt
```

3. **Configure environment variables**
   
   Copy the example file and fill in your credentials:
```bash
   cp .env.example .env
```
   
   Edit `.env` with your actual values:
   - Telegram bot token & chat ID
   - Gmail email & app password

4. **Add sites to monitor**
   
   Copy the example and add your sites:
```bash
   cp sites.json.example sites.json
```

5. **Run the application**
   
   Start monitoring:
```bash
   python checker.py
```
   
   Start web dashboard (separate terminal):
```bash
   python web_dashboard.py
```
   
   Visit: `http://localhost:5000`

## 📖 Setup Guide

### Telegram Bot Setup

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Create a new bot and get your token
3. Get your chat ID from [@userinfobot](https://t.me/userinfobot)
4. Add to `.env`

### Gmail Setup

1. Enable 2-factor authentication
2. Generate [App Password](https://myaccount.google.com/apppasswords)
3. Add to `.env`

## 🏗️ Project Structure
```
site-monitor/
├── checker.py              # Main monitoring script
├── database.py             # Database operations
├── web_dashboard.py        # Flask web interface
├── sites_config.py         # Site management
├── email_config.py         # Email alerts
├── pdf_generator.py        # PDF reports
├── requirements.txt        # Dependencies
├── .env.example           # Example environment variables
├── sites.json.example     # Example site list
└── README.md              # This file
```

## 🛠️ Technologies

- Python, Flask, SQLite
- Plotly & Matplotlib (visualizations)
- ReportLab (PDF generation)
- Telegram Bot API, SMTP

## 📝 License

MIT License - see LICENSE file for details.

## 👤 Author

GitHub: [@haven7777](https://github.com/haven7777)

---

⭐ Star this repo if you find it useful!
EOF