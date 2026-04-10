#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import imaplib
import email
from email.header import decode_header
import requests
import re

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8786126274:AAEWyu2yuOuPbsWkUaReIXphVk1U8-J63dQ")
TELEGRAM_CHANNEL = -1003995474645

FRUUX_EMAIL = "tilohue@gmx.de"
FRUUX_PASSWORD = os.getenv("FRUUX_PASSWORD", "")
FRUUX_CALENDAR = "Calendar"
FRUUX_URL = "https://fruux.com/remote.php/dav/calendars/tilohue@gmx.de/Calendar/"

class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'

def log(message, color=Colors.BLUE):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{color}[{timestamp}] {message}{Colors.END}")

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHANNEL, "text": message, "parse_mode": "HTML"}
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception as e:
        log(f"⚠️  Telegram Fehler: {str(e)}", Colors.YELLOW)
        return False

def load_config(config_path):
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        log("✅ Config geladen", Colors.GREEN)
        return config
    except FileNotFoundError:
        log(f"❌ Config nicht gefunden: {config_path}", Colors.RED)
        sys.exit(1)
    except json.JSONDecodeError:
        log("❌ Config ist kein gültiges JSON", Colors.RED)
        sys.exit(1)

def load_lists(list_path):
    if not list_path.exists():
        return {"whitelist": [], "blacklist": []}
    try:
        with open(list_path, 'r') as f:
            return json.load(f)
    except:
        return {"whitelist": [], "blacklist": []}

def get_credentials(config):
    email_address = os.getenv("EMAIL_ADDRESS", config['email_config']['email_address'])
    app_password = os.getenv("EMAIL_APP_PASSWORD", config['email_config']['app_password'])
    if not email_address or not app_password:
        log("❌ Email oder Passwort nicht konfiguriert!", Colors.RED)
        sys.exit(1)
    return email_address, app_password

def connect_to_imap(email_address, app_password, config):
    try:
        imap_server = config['email_config']['imap_server']
        imap_port = config['email_config']['imap_port']
        log(f"🔗 Verbinde zu {imap_server}:{imap_port}...", Colors.BLUE)
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(email_address, app_password)
        log(f"✅ Angemeldet als {email_address}", Colors.GREEN)
        return mail
    except Exception as e:
        log(f"❌ Verbindungsfehler: {str(e)}", Colors.RED)
        sys.exit(1)

def fetch_emails(mail, folder='INBOX'):
    try:
        mail.select(folder)
        status, messages = mail.search(None, 'UNSEEN')
        if status != 'OK':
            return []
        email_ids = messages[0].split()
        log(f"📧 Found {len(email_ids)} neue Emails", Colors.BLUE)
        emails_data = []
        for email_id in email_ids[-20:]:
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            if status == 'OK':
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                emails_data.append({'id': email_id, 'message': email_message})
        return emails_data
    except Exception as e:
        log(f"❌ Fehler: {str(e)}", Colors.RED)
        return []

def parse_email(email_message):
    try:
        from_addr = email_message.get('From', 'Unknown')
        subject = email_message.get('Subject', 'No Subject')
        if isinstance(subject, bytes):
            subject = subject.decode('utf-8', errors='ignore')
        body = ""
        if email_message.is_multipart():
            for part in email_message.get_payload():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
        else:
            body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
        return {'from': from_addr, 'subject': subject, 'body': body[:500]}
    except Exception as e:
        log(f"⚠️  Fehler: {str(e)}", Colors.YELLOW)
        return None

def extract_dates(text):
    """Extrahiere Daten aus Text"""
    dates = []
    
    # Muster: "2026-04-15", "15.04.2026", "April 15", etc.
    patterns = [
        r'(\d{4})-(\d{1,2})-(\d{1,2})',  # 2026-04-15
        r'(\d{1,2})\.(\d{1,2})\.(\d{4})',  # 15.04.2026
        r'(\d{1,2})/(\d{1,2})/(\d{4})',  # 15/04/2026
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                if len(match[0]) == 4:  # YYYY-MM-DD
                    date_obj = datetime(int(match[0]), int(match[1]), int(match[2]))
                else:  # DD.MM.YYYY
                    date_obj = datetime(int(match[2]), int(match[1]), int(match[0]))
                if date_obj not in dates:
                    dates.append(date_obj)
            except:
                pass
    
    return dates

def add_to_fruux_calendar(event_title, event_date):
    """Füge Event zu Fruux Kalender hinzu"""
    try:
        if not FRUUX_PASSWORD:
            log("⚠️  FRUUX_PASSWORD nicht gesetzt", Colors.YELLOW)
            return False
        
        # ICS Event erstellen
        uid = f"{event_title}-{event_date.timestamp()}"
        ics_event = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Email Skill//EN
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}
DTSTART:{event_date.strftime('%Y%m%d')}
DTEND:{(event_date + timedelta(days=1)).strftime('%Y%m%d')}
SUMMARY:{event_title}
DESCRIPTION:Aus Email extrahiert
END:VEVENT
END:VCALENDAR"""
        
        # Zu Fruux hochladen
        url = f"{FRUUX_URL}{uid}.ics"
        response = requests.put(
            url,
            data=ics_event,
            auth=(FRUUX_EMAIL, FRUUX_PASSWORD),
            headers={"Content-Type": "text/calendar"},
            timeout=5
        )
        
        if response.status_code in [201, 204]:
            log(f"✅ Fruux: '{event_title}' am {event_date.strftime('%d.%m.%Y')} hinzugefügt", Colors.GREEN)
            return True
        else:
            log(f"⚠️  Fruux Fehler {response.status_code}: {event_title}", Colors.YELLOW)
            return False
    
    except Exception as e:
        log(f"⚠️  Fruux Fehler: {str(e)}", Colors.YELLOW)
        return False

def categorize_email(email_data, lists):
    from_addr = email_data['from'].lower()
    subject = email_data['subject'].lower()
    body = email_data['body'].lower()
    
    for item in lists['whitelist']:
        if item.lower() in from_addr or item.lower() in subject:
            return 'specific'
    
    for item in lists['blacklist']:
        if item.lower() in from_addr or item.lower() in subject:
            return 'generic'
    
    generic_keywords = ['newsletter', 'unsubscribe', 'marketing', 'notification', 'alert', 'confirmation', 'receipt']
    for keyword in generic_keywords:
        if keyword in subject or keyword in body:
            return 'generic'
    
    action_keywords = ['please', 'can you', 'urgent', 'asap', 'bitte', 'dringend', 'review', 'approve']
    for keyword in action_keywords:
        if keyword in subject or keyword in body:
            return 'specific'
    
    return 'generic'

def main():
    script_dir = Path(__file__).parent
    config_path = script_dir / 'email-skill-config.json'
    lists_path = script_dir / 'telegram-lists.json'
    
    log("=" * 60, Colors.BLUE)
    log("📧 EMAIL SKILL + TELEGRAM + FRUUX", Colors.BLUE)
    log(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.BLUE)
    log("=" * 60, Colors.BLUE)
    
    config = load_config(config_path)
    lists = load_lists(lists_path)
    
    email_address, app_password = get_credentials(config)
    mail = connect_to_imap(email_address, app_password, config)
    emails = fetch_emails(mail, folder='INBOX')
    
    if not emails:
        log("ℹ️  Keine neuen Emails", Colors.YELLOW)
        mail.close()
        mail.logout()
        return
    
    specific_emails = []
    generic_emails = []
    calendar_events = []
    
    log(f"\n📊 Verarbeite {len(emails)} Emails...\n", Colors.BLUE)
    
    for email_data in emails:
        parsed = parse_email(email_data['message'])
        if not parsed:
            continue
        
        category = categorize_email(parsed, lists)
        
        # Extrahiere Daten
        dates = extract_dates(parsed['subject'] + " " + parsed['body'])
        for date in dates:
            event_title = parsed['subject'][:50]
            added = add_to_fruux_calendar(event_title, date)
            if added:
                calendar_events.append({'title': event_title, 'date': date})
        
        if category == 'specific':
            specific_emails.append(parsed)
            log(f"📌 SPEZIFISCH: {parsed['subject'][:50]}", Colors.YELLOW)
        else:
            generic_emails.append(parsed)
            log(f"📄 GENERISCH: {parsed['subject'][:50]}", Colors.YELLOW)
    
    log("\n" + "=" * 60, Colors.GREEN)
    log(f"✅ SCAN ABGESCHLOSSEN!", Colors.GREEN)
    log(f"📌 Spezifisch: {len(specific_emails)}", Colors.GREEN)
    log(f"📄 Generisch: {len(generic_emails)}", Colors.GREEN)
    log(f"📅 Kalender-Events: {len(calendar_events)}", Colors.GREEN)
    log("=" * 60, Colors.GREEN)
    
    if specific_emails or calendar_events:
        telegram_msg = f"📧 <b>{len(specific_emails)} neue Aktionen!</b>\n"
        
        if calendar_events:
            telegram_msg += f"📅 <b>{len(calendar_events)} Events hinzugefügt:</b>\n"
            for event in calendar_events[:3]:
                telegram_msg += f"  • {event['title'][:40]} ({event['date'].strftime('%d.%m.%Y')})\n"
            if len(calendar_events) > 3:
                telegram_msg += f"  ... und {len(calendar_events)-3} weitere\n"
        
        telegram_msg += "\n"
        for i, email in enumerate(specific_emails[:5], 1):
            from_short = email['from'].split('<')[0].strip()[:30]
            subject_short = email['subject'][:45]
            telegram_msg += f"<b>{i}. {from_short}</b>\n{subject_short}\n\n"
        
        if len(specific_emails) > 5:
            telegram_msg += f"... und {len(specific_emails)-5} weitere"
        
        send_telegram(telegram_msg)
    
    mail.close()
    mail.logout()
    log("✅ Fertig", Colors.GREEN)

if __name__ == "__main__":
    main()
