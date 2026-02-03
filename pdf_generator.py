from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime, timedelta
from database import get_stats, get_recent_checks, get_checks_by_date_range, get_overall_stats
from sites_config import load_sites
import io
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from io import BytesIO

def create_response_time_chart_image(url, days=7):
    """Create a response time chart as an image for PDF"""
    from datetime import datetime, timedelta
    import sqlite3
    
    # Get data for the specified period
    conn = sqlite3.connect('monitor.db')
    cursor = conn.cursor()
    
    since = datetime.now() - timedelta(days=days)
    
    cursor.execute('''
        SELECT timestamp, response_time
        FROM checks
        WHERE url = ? AND timestamp > ? AND status = 'up' AND response_time IS NOT NULL
        ORDER BY timestamp ASC
    ''', (url, since))
    
    results = cursor.fetchall()
    conn.close()
    
    if not results or len(results) < 2:
        return None
    
    # Extract data
    timestamps = [datetime.fromisoformat(row[0]) for row in results]
    response_times = [row[1] * 1000 for row in results]  # Convert to ms
    
    # Create chart
    fig, ax = plt.subplots(figsize=(6, 3), facecolor='white')
    
    ax.plot(timestamps, response_times, color='#4f46e5', linewidth=2, marker='o', markersize=3)
    ax.fill_between(timestamps, response_times, alpha=0.3, color='#4f46e5')
    
    ax.set_xlabel('Time', fontsize=9)
    ax.set_ylabel('Response Time (ms)', fontsize=9)
    ax.set_title(f'Response Time - Last {days} Days', fontsize=10, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.tick_params(labelsize=8)
    
    # Rotate x-axis labels
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    
    # Save to bytes
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
    img_buffer.seek(0)
    plt.close()
    
    return img_buffer

def generate_uptime_report(days=7):
    """Generate a comprehensive uptime report as PDF"""
    
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=26,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#334155'),
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )
    
    subheading_style = ParagraphStyle(
        'SubHeading',
        parent=styles['Heading3'],
        fontSize=13,
        textColor=colors.HexColor('#475569'),
        spaceAfter=10,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )
    
    normal_style = styles['Normal']
    
    # Title
    title = Paragraph("📊 Site Monitoring Report", title_style)
    elements.append(title)
    
    # Report metadata
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    metadata_text = f"""<b>Report Period:</b> {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}<br/>
    <b>Generated:</b> {end_date.strftime('%B %d, %Y at %H:%M:%S')}<br/>
    <b>Coverage:</b> Last {days} days"""
    
    metadata = Paragraph(metadata_text, normal_style)
    elements.append(metadata)
    elements.append(Spacer(1, 0.3*inch))
    
    # Overall statistics
    overall_stats = get_overall_stats()
    
    summary_heading = Paragraph("Executive Summary", heading_style)
    elements.append(summary_heading)
    
    summary_data = [
        ['Metric', 'Value'],
        ['Overall System Uptime', f"{overall_stats['overall_uptime']:.2f}%"],
        ['Total Sites Monitored', str(overall_stats['total_sites'])],
        ['Total Health Checks', str(overall_stats['total_checks'])],
        ['Successful Checks', str(overall_stats['successful_checks'])],
        ['Average Response Time', f"{overall_stats['avg_response_time']:.3f}s"],
    ]
    
    summary_table = Table(summary_data, colWidths=[3.5*inch, 2.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Individual site reports
    sites = load_sites()
    
    for idx, url in enumerate(sites):
        # Page break between sites (except first)
        if idx > 0:
            elements.append(PageBreak())
        
        stats = get_stats(url)
        
        # Site heading
        site_heading = Paragraph(f"Site Report: {url}", heading_style)
        elements.append(site_heading)
        
        # Site stats table
        site_data = [
            ['Metric', 'Value'],
            ['Uptime Percentage', f"{stats['uptime_percentage']:.2f}%"],
            ['Total Checks', str(stats['total_checks'])],
            ['Successful Checks', str(stats['successful_checks'])],
            ['Average Response Time', f"{stats['avg_response_time']:.3f}s"],
        ]
        
        site_table = Table(site_data, colWidths=[3*inch, 2*inch])
        site_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ]))
        
        elements.append(site_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Response time chart
        chart_subheading = Paragraph("Response Time Analysis", subheading_style)
        elements.append(chart_subheading)
        
        chart_img = create_response_time_chart_image(url, days=days)
        
        if chart_img:
            img = Image(chart_img, width=5.5*inch, height=2.75*inch)
            elements.append(img)
        else:
            no_data = Paragraph("<i>Insufficient data for chart generation</i>", normal_style)
            elements.append(no_data)
        
        elements.append(Spacer(1, 0.2*inch))
        
        # Recent check history
        history_subheading = Paragraph("Recent Check History", subheading_style)
        elements.append(history_subheading)
        
        recent = get_recent_checks(url, limit=10)
        
        if recent:
            history_data = [['Time', 'Status', 'Response Time', 'Status Code']]
            
            for check in recent:
                timestamp = check[4].split('.')[0] if check[4] else 'N/A'
                status = check[1].upper()
                response_time = f"{check[2]:.3f}s" if check[2] else 'N/A'
                status_code = str(check[3]) if check[3] else 'N/A'
                
                history_data.append([timestamp, status, response_time, status_code])
            
            history_table = Table(history_data, colWidths=[2*inch, 1*inch, 1.2*inch, 1*inch])
            history_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8b5cf6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ]))
            
            elements.append(history_table)
        else:
            no_history = Paragraph("<i>No check history available</i>", normal_style)
            elements.append(no_history)
    
    # Footer on last page
    elements.append(Spacer(1, 0.4*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#64748b'),
        alignment=TA_CENTER
    )
    footer = Paragraph(
        "Generated by Site Monitor Dashboard | Professional Infrastructure Monitoring",
        footer_style
    )
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data