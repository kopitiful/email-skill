#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import imaplib
import email
from email.header import decode_header
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8786126274:AAEWyu2yuOuPbsWkUaReIXphVk1U8-J63dQ")
TELEGRAM_CHANNEL = -1003995474645

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
    """Lade White/Blacklist"""
    if not list_path.exists():
        return {"whitelist": [], "blacklist": []}
    try:
        with open(list_path, 'r') as f:
            return json.load(f)
    except:
        return {"whitelist": [], "blacklist": []}

def save_lists(list_path, lists):
    """Speichere White/Blacklist"""
    os.makedirs(list_path.parent, exist_ok=True)
    with open(list_path, 'w') as f:
        json.dump(lists, f, indent=2)
    log(f"💾 Lists gespeichert", Colors.GREEN)

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

def extract_sender_email(from_addr):
    """Extrahiere Email-Adresse aus From-Header"""
    if '<' in from_addr and '>' in from_addr:
        return from_addr.split('<')[1].split('>')[0].lower()
    return from_addr.lower()

def extract_sender_domain(from_addr):
    """Extrahiere Domain aus From-Header"""
    email_part = extract_sender_email(from_addr)
    if '@' in email_part:
        return email_part.split('@')[1]
    return email_part

def categorize_email(email_data, lists):
    """Kategorisiere Email mit Whitelist/Blacklist"""
    
    from_addr = email_data['from'].lower()
    sender_email = extract_sender_email(from_addr)
    sender_domain = extract_sender_domain(from_addr)
    subject = email_data['subject'].lower()
    body = email_data['body'].lower()
    
    # Prüfe Whitelist (exakt + Domain)
    for item in lists['whitelist']:
        if item.lower() in [sender_email, sender_domain] or item.lower() in from_addr:
            return 'specific'
    
    # Prüfe Blacklist
    for item in lists['blacklist']:
        if item.lower() in [sender_email, sender_domain] or item.lower() in from_addr:
            return 'generic'
    
    # Standard Keywords
    generic_keywords = ['newsletter', 'unsubscribe', 'marketing', 'notification', 'alert', 'confirmation', 'receipt']
    for keyword in generic_keywords:
        if keyword in subject or keyword in body:
            return 'generic'
    
    action_keywords = ['please', 'can you', 'urgent', 'asap', 'bitte', 'dringend', 'review', 'approve']
    for keyword in action_keywords:
        if keyword in subject or keyword in body:
            return 'specific'
    
    return 'generic'

def check_telegram_commands(script_dir, lists):
    """Prüfe auf Telegram-Befehle und verarbeite sie"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        response = requests.get(url, timeout=5)
        
        if response.status_code != 200:
            return
        
        data = response.json()
        if not data.get('result'):
            return
        
        for update in data['result']:
            if 'message' not in update:
                continue
            
            message = update['message']
            text = message.get('text', '').strip()
            
            if not text.startswith('/'):
                continue
            
            parts = text.split(' ', 1)
            command = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ''
            
            if command == '/whitelist' and arg:
                # Füge zu Whitelist hinzu
                item = arg.lower().strip()
                if item not in lists['whitelist']:
                    lists['whitelist'].append(item)
                    lists_path = script_dir / 'telegram-lists.json'
                    save_lists(lists_path, lists)
                    
                    msg = f"✅ <b>{item}</b> zur Whitelist hinzugefügt!\n\n"
                    msg += f"Whitelist ({len(lists['whitelist'])} Einträge):\n"
                    for i, w in enumerate(lists['whitelist'][-5:], 1):
                        msg += f"{i}. {w}\n"
                    send_telegram(msg)
                    log(f"✅ Whitelist: {item} hinzugefügt", Colors.GREEN)
                else:
                    send_telegram(f"ℹ️  <b>{item}</b> ist bereits auf der Whitelist")
            
            elif command == '/blacklist' and arg:
                # Füge zu Blacklist hinzu
                item = arg.lower().strip()
                if item not in lists['blacklist']:
                    lists['blacklist'].append(item)
                    lists_path = script_dir / 'telegram-lists.json'
                    save_lists(lists_path, lists)
                    
                    msg = f"🚫 <b>{item}</b> zur Blacklist hinzugefügt!\n\n"
                    msg += f"Blacklist ({len(lists['blacklist'])} Einträge):\n"
                    for i, b in enumerate(lists['blacklist'][-5:], 1):
                        msg += f"{i}. {b}\n"
                    send_telegram(msg)
                    log(f"✅ Blacklist: {item} hinzugefügt", Colors.GREEN)
                else:
                    send_telegram(f"ℹ️  <b>{item}</b> ist bereits auf der Blacklist")
            
            elif command == '/lists':
                # Zeige aktuelle Lists
                msg = f"📋 <b>Aktuelle Listen:</b>\n\n"
                msg += f"✅ <b>Whitelist ({len(lists['whitelist'])} Einträge):</b>\n"
                if lists['whitelist']:
                    for item in lists['whitelist']:
                        msg += f"  • {item}\n"
                else:
                    msg += "  (leer)\n"
                
                msg += f"\n🚫 <b>Blacklist ({len(lists['blacklist'])} Einträge):</b>\n"
                if lists['blacklist']:
                    for item in lists['blacklist']:
                        msg += f"  • {item}\n"
                else:
                    msg += "  (leer)\n"
                
                send_telegram(msg)
                log(f"📋 Lists angezeigt", Colors.GREEN)
            
            elif command == '/help':
                # Zeige Hilfe
                msg = """📚 <b>Verfügbare Befehle:</b>

/whitelist &lt;email/domain&gt;
  ➜ Sender zur Whitelist hinzufügen

/blacklist &lt;email/domain&gt;
  ➜ Sender zur Blacklist hinzufügen

/lists
  ➜ Aktuelle Whitelist & Blacklist anzeigen

/help
  ➜ Diese Nachricht anzeigen

<b>Beispiele:</b>
/whitelist boss@company.com
/whitelist company.com
/blacklist newsletter@spam.de
"""
                send_telegram(msg)
                log(f"📚 Hilfe gesendet", Colors.GREEN)
    
    except Exception as e:
        log(f"⚠️  Fehler beim Prüfen von Commands: {str(e)}", Colors.YELLOW)

def main():
    script_dir = Path(__file__).parent
    config_path = script_dir / 'email-skill-config.json'
    lists_path = script_dir / 'telegram-lists.json'
    
    log("=" * 60, Colors.BLUE)
    log("📧 EMAIL SKILL + TELEGRAM + LISTS", Colors.BLUE)
    log(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.BLUE)
    log("=" * 60, Colors.BLUE)
    
    # Prüfe auf Telegram-Befehle
    config = load_config(config_path)
    lists = load_lists(lists_path)
    check_telegram_commands(script_dir, lists)
    
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
    
    log(f"\n📊 Verarbeite {len(emails)} Emails...\n", Colors.BLUE)
    
    for email_data in emails:
        parsed = parse_email(email_data['message'])
        if not parsed:
            continue
        category = categorize_email(parsed, lists)
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
    log("=" * 60, Colors.GREEN)
    
    if specific_emails:
        telegram_msg = f"📧 <b>{len(specific_emails)} neue Aktionen!</b>\n\n"
        for i, email in enumerate(specific_emails[:5], 1):
            from_short = email['from'].split('<')[0].strip()[:30]
            subject_short = email['subject'][:45]
            telegram_msg += f"<b>{i}. {from_short}</b>\n{subject_short}\n\n"
        if len(specific_emails) > 5:
            telegram_msg += f"... und {len(specific_emails)-5} weitere"
        
        telegram_msg += "\n\n💡 /whitelist, /blacklist, /lists, /help"
        send_telegram(telegram_msg)
    
    mail.close()
    mail.logout()
    log("✅ Fertig", Colors.GREEN)

if __name__ == "__main__":
    main()
