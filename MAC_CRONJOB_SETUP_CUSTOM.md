# Email Skill mit Cronjob auf Mac einrichten
## 🎯 Pfad: /Users/timhuebner/tradingbot/skills/emailscanner

## 📋 Voraussetzungen:

✅ GMX App-Passwort erstellt (siehe GMX_APP_PASSWORD_SETUP.md)
✅ `email-skill-config.json` Datei vorbereitet
✅ Python 3 installiert (meist schon vorhanden)
✅ Verzeichnis existiert: `/Users/timhuebner/tradingbot/skills/emailscanner`

---

## Schritt 1: Terminal öffnen

1. **Spotlight Search öffnen:** `Cmd + Space`
2. Tippe: `terminal`
3. Drücke: `Enter`

Terminal öffnet sich.

---

## Schritt 2: Überprüfe Python Installation

Im Terminal tippe:

```bash
python3 --version
```

**Wenn Output:** `Python 3.x.x` → ✅ Perfekt!
**Wenn Error:** Mach weiter, wir installieren es

---

## Schritt 3: Gehe in dein Verzeichnis

```bash
# Navigiere zu deinem Skill-Verzeichnis
cd /Users/timhuebner/tradingbot/skills/emailscanner

# Überprüfe ob das Verzeichnis existiert
pwd
```

Du solltest sehen: `/Users/timhuebner/tradingbot/skills/emailscanner`

Falls das Verzeichnis nicht existiert, erstelle es:

```bash
mkdir -p /Users/timhuebner/tradingbot/skills/emailscanner
cd /Users/timhuebner/tradingbot/skills/emailscanner
```

---

## Schritt 4: Kopiere deine Config-Datei

1. Öffne **Finder**
2. Gehe zu **Dokumente** (oder wo du die Datei speicherst)
3. Finde `email-skill-config.json`
4. **Kopiere die Datei** (Cmd+C)
5. Navigiere zu: `/Users/timhuebner/tradingbot/skills/emailscanner`
6. **Füge ein** (Cmd+V)

Oder im Terminal:

```bash
# Wenn die Config-Datei in Dokumente ist:
cp ~/Documents/email-skill-config.json /Users/timhuebner/tradingbot/skills/emailscanner/

# Überprüfe ob sie da ist:
ls -la /Users/timhuebner/tradingbot/skills/emailscanner/
```

Du solltest sehen:
```
email-skill-config.json
```

---

## Schritt 5: Erstelle das Python-Script

Im Terminal (stelle sicher du im richtigen Verzeichnis bist):

```bash
cd /Users/timhuebner/tradingbot/skills/emailscanner
nano email-skill.py
```

Ein Editor öffnet sich. Kopiere diesen **kompletten Code**:

```python
#!/usr/bin/env python3
"""
Email Skill Runner - Automatischer Inbox Scanner für GMX
Pfad: /Users/timhuebner/tradingbot/skills/emailscanner
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
import imaplib
import email
from email.header import decode_header

# Farbige Terminal-Ausgabe
class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'

def log(message, color=Colors.BLUE):
    """Gebe eine Nachricht mit Zeitstempel aus"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{color}[{timestamp}] {message}{Colors.END}")

def load_config(config_path):
    """Lade die Konfigurationsdatei"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        log("✅ Config geladen", Colors.GREEN)
        return config
    except FileNotFoundError:
        log(f"❌ Config-Datei nicht gefunden: {config_path}", Colors.RED)
        sys.exit(1)
    except json.JSONDecodeError:
        log("❌ Config-Datei ist kein gültiges JSON", Colors.RED)
        sys.exit(1)

def get_credentials(config):
    """Hole Credentials aus Config oder Umgebungsvariablen"""
    email_address = os.getenv("EMAIL_ADDRESS", config['email_config']['email_address'])
    app_password = os.getenv("EMAIL_APP_PASSWORD", config['email_config']['app_password'])
    
    if not email_address or not app_password:
        log("❌ Email oder Passwort nicht konfiguriert!", Colors.RED)
        sys.exit(1)
    
    return email_address, app_password

def connect_to_imap(email_address, app_password, config):
    """Verbinde zu GMX IMAP Server"""
    try:
        imap_server = config['email_config']['imap_server']
        imap_port = config['email_config']['imap_port']
        
        log(f"🔗 Verbinde zu {imap_server}:{imap_port}...", Colors.BLUE)
        
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(email_address, app_password)
        
        log(f"✅ Erfolgreich angemeldet als {email_address}", Colors.GREEN)
        return mail
    
    except imaplib.IMAP4.error as e:
        log(f"❌ IMAP Fehler: {str(e)}", Colors.RED)
        sys.exit(1)
    except Exception as e:
        log(f"❌ Verbindungsfehler: {str(e)}", Colors.RED)
        sys.exit(1)

def fetch_emails(mail, folder='INBOX'):
    """Hole ungelesene Emails vom IMAP Server"""
    try:
        mail.select(folder)
        status, messages = mail.search(None, 'UNSEEN')
        
        if status != 'OK':
            log(f"Warnung: Konnte UNSEEN Emails nicht suchen", Colors.YELLOW)
            return []
        
        email_ids = messages[0].split()
        log(f"📧 Found {len(email_ids)} neue Emails", Colors.BLUE)
        
        emails_data = []
        for email_id in email_ids[-20:]:  # Letzte 20 Emails
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            if status == 'OK':
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                emails_data.append({
                    'id': email_id,
                    'message': email_message
                })
        
        return emails_data
    
    except Exception as e:
        log(f"❌ Fehler beim Abrufen von Emails: {str(e)}", Colors.RED)
        return []

def parse_email(email_message):
    """Parsze eine Email und extrahiere wichtige Infos"""
    try:
        from_addr = email_message.get('From', 'Unknown')
        subject = email_message.get('Subject', 'No Subject')
        
        # Dekodiere Subject wenn nötig
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
        
        return {
            'from': from_addr,
            'subject': subject,
            'body': body[:500]  # Erste 500 Zeichen
        }
    
    except Exception as e:
        log(f"⚠️  Fehler beim Parsen einer Email: {str(e)}", Colors.YELLOW)
        return None

def categorize_email(email_data):
    """Kategorisiere Email als generisch oder spezifisch"""
    
    generic_keywords = [
        'newsletter', 'unsubscribe', 'marketing', 'promotional',
        'notification', 'alert', 'confirmation', 'receipt',
        'weekly', 'daily', 'digest', 'report'
    ]
    
    subject = email_data['subject'].lower()
    body = email_data['body'].lower()
    
    # Prüfe auf generische Keywords
    for keyword in generic_keywords:
        if keyword in subject or keyword in body:
            return 'generic'
    
    # Prüfe auf Aktions-Keywords
    action_keywords = [
        'please', 'can you', 'could you', 'need', 'urgent',
        'asap', 'heute', 'morgen', 'deadline', 'review',
        'approve', 'sign', 'response needed', 'bitte'
    ]
    
    for keyword in action_keywords:
        if keyword in subject or keyword in body:
            return 'specific'
    
    # Standard: spezifisch wenn direkt adressiert
    if 'hi,' in body or 'hello,' in body:
        return 'specific'
    
    return 'generic'

def generate_report(specific_emails, generic_emails):
    """Generiere einen strukturierten Report"""
    
    report = []
    report.append("=" * 60)
    report.append("📧 EMAIL SKILL - TÄGLICHER REPORT")
    report.append(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 60)
    
    # Actions Required
    report.append("\n🎯 AKTIONEN ERFORDERLICH:")
    report.append("-" * 60)
    
    if specific_emails:
        for i, email in enumerate(specific_emails, 1):
            report.append(f"\n{i}. Von: {email['from']}")
            report.append(f"   Betreff: {email['subject']}")
            report.append(f"   Vorschau: {email['body'][:100]}...")
    else:
        report.append("✅ Keine Aktionen erforderlich")
    
    # Generic Emails
    report.append("\n\n📄 GENERISCHE EMAILS (FYI - Keine Aktion erforderlich):")
    report.append("-" * 60)
    
    if generic_emails:
        for i, email in enumerate(generic_emails, 1):
            report.append(f"\n{i}. Von: {email['from']}")
            report.append(f"   Betreff: {email['subject']}")
    else:
        report.append("✅ Keine generischen Emails")
    
    report.append("\n" + "=" * 60)
    
    return "\n".join(report)

def save_report(report, report_dir):
    """Speichere Report in Datei"""
    try:
        os.makedirs(report_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(report_dir, f"scan_{timestamp}.txt")
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        return report_file
    except Exception as e:
        log(f"⚠️  Fehler beim Speichern des Reports: {str(e)}", Colors.YELLOW)
        return None

def main():
    """Hauptfunktion"""
    
    # Bestimme Skript-Verzeichnis
    script_dir = Path(__file__).parent
    config_path = script_dir / 'email-skill-config.json'
    report_dir = script_dir / 'reports'
    
    log("=" * 60, Colors.BLUE)
    log("📧 EMAIL SKILL - AUTOMATISCHER INBOX SCANNER", Colors.BLUE)
    log(f"🕐 Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.BLUE)
    log(f"📁 Pfad: {script_dir}", Colors.BLUE)
    log("=" * 60, Colors.BLUE)
    
    # Lade Config
    config = load_config(config_path)
    
    # Hole Credentials
    email_address, app_password = get_credentials(config)
    
    # Verbinde zu IMAP
    mail = connect_to_imap(email_address, app_password, config)
    
    # Hole Emails
    emails = fetch_emails(mail, folder='INBOX')
    
    if not emails:
        log("ℹ️  Keine neuen Emails", Colors.YELLOW)
        mail.close()
        mail.logout()
        return
    
    # Kategorisiere und verarbeite
    specific_emails = []
    generic_emails = []
    
    log(f"\n📊 Verarbeite {len(emails)} Emails...\n", Colors.BLUE)
    
    for email_data in emails:
        parsed = parse_email(email_data['message'])
        if not parsed:
            continue
        
        category = categorize_email(parsed)
        
        if category == 'specific':
            specific_emails.append(parsed)
            log(f"📌 SPEZIFISCH: {parsed['subject'][:50]}", Colors.YELLOW)
        else:
            generic_emails.append(parsed)
            log(f"📄 GENERISCH: {parsed['subject'][:50]}", Colors.YELLOW)
    
    # Zusammenfassung
    log("\n" + "=" * 60, Colors.GREEN)
    log(f"✅ SCAN ABGESCHLOSSEN!", Colors.GREEN)
    log(f"📌 Spezifische Emails (Aktionen): {len(specific_emails)}", Colors.GREEN)
    log(f"📄 Generische Emails: {len(generic_emails)}", Colors.GREEN)
    log("=" * 60, Colors.GREEN)
    
    # Generiere und speichere Report
    report = generate_report(specific_emails, generic_emails)
    report_file = save_report(report, report_dir)
    
    if report_file:
        log(f"💾 Report gespeichert: {report_file}", Colors.GREEN)
    
    # Cleanup
    mail.close()
    mail.logout()
    log("✅ Verbindung geschlossen", Colors.GREEN)

if __name__ == "__main__":
    main()
```

**Speichern:** Drücke `Ctrl + O` → `Enter` → `Ctrl + X`

---

## Schritt 6: Mache das Script ausführbar

Im Terminal:

```bash
chmod +x /Users/timhuebner/tradingbot/skills/emailscanner/email-skill.py
```

---

## Schritt 7: Test das Script manuell

```bash
# Führe das Script direkt aus
/Users/timhuebner/tradingbot/skills/emailscanner/email-skill.py
```

**Du solltest sehen:**
```
[2026-04-09 08:15:32] ✅ Config geladen
[2026-04-09 08:15:33] 🔗 Verbinde zu imap.gmx.net:993...
[2026-04-09 08:15:34] ✅ Erfolgreich angemeldet als deine-email@gmx.de
[2026-04-09 08:15:35] 📧 Found 3 neue Emails
...
```

**Falls Fehler:** 
- Überprüfe ob `email-skill-config.json` korrekt ist
- Überprüfe ob App-Passwort korrekt eingetragen ist

---

## Schritt 8: Erstelle Cronjob - HAUPTSCHRITT!

Im Terminal:

```bash
# Öffne die Crontab
crontab -e
```

Ein Editor öffnet sich. Das ist dein Cronjob-Scheduler!

Kopiere diese 2 Zeilen am Ende:

```bash
# Morning scan at 8:00 AM
0 8 * * * /usr/bin/python3 /Users/timhuebner/tradingbot/skills/emailscanner/email-skill.py >> /Users/timhuebner/tradingbot/skills/emailscanner/logs/morning.log 2>&1

# Afternoon scan at 5:00 PM
0 17 * * * /usr/bin/python3 /Users/timhuebner/tradingbot/skills/emailscanner/email-skill.py >> /Users/timhuebner/tradingbot/skills/emailscanner/logs/afternoon.log 2>&1
```

**Speichern:**
- Drücke `Esc`
- Tippe: `:wq`
- Drücke `Enter`

---

## Schritt 9: Erstelle Log-Verzeichnis

```bash
mkdir -p /Users/timhuebner/tradingbot/skills/emailscanner/logs
```

---

## Schritt 10: Erstelle Reports-Verzeichnis

```bash
mkdir -p /Users/timhuebner/tradingbot/skills/emailscanner/reports
```

---

## Schritt 11: Überprüfe ob Cronjob läuft

```bash
# Zeige alle Cronjobs
crontab -l
```

Du solltest sehen:
```
0 8 * * * /usr/bin/python3 /Users/timhuebner/tradingbot/skills/emailscanner/email-skill.py >> /Users/timhuebner/tradingbot/skills/emailscanner/logs/morning.log 2>&1
0 17 * * * /usr/bin/python3 /Users/timhuebner/tradingbot/skills/emailscanner/email-skill.py >> /Users/timhuebner/tradingbot/skills/emailscanner/logs/afternoon.log 2>&1
```

---

## 📊 Struktur deines Verzeichnisses nach Setup:

```
/Users/timhuebner/tradingbot/skills/emailscanner/
├── email-skill.py                    ← Das Python-Script
├── email-skill-config.json          ← Deine Email-Config
├── logs/
│   ├── morning.log                  ← Morning Scan Log
│   └── afternoon.log                ← Afternoon Scan Log
└── reports/
    ├── scan_20260409_080000.txt     ← Report Morning Scan
    ├── scan_20260409_170000.txt     ← Report Afternoon Scan
    └── ...
```

---

## 🔍 Logs & Reports anschauen

```bash
# Zeige den letzten Morning Log
cat /Users/timhuebner/tradingbot/skills/emailscanner/logs/morning.log

# Live Updates
tail -f /Users/timhuebner/tradingbot/skills/emailscanner/logs/morning.log

# Zeige alle Reports
ls -lah /Users/timhuebner/tradingbot/skills/emailscanner/reports/

# Öffne einen Report
cat /Users/timhuebner/tradingbot/skills/emailscanner/reports/scan_20260409_080000.txt
```

---

## ⚠️ Häufige Probleme auf Mac:

### Problem: "Command not found: python3"
**Lösung:** 
```bash
# Finde Python Pfad
which python3

# Nutze diesen Pfad statt /usr/bin/python3 in der Crontab
```

### Problem: "Permission denied"
**Lösung:**
```bash
chmod +x /Users/timhuebner/tradingbot/skills/emailscanner/email-skill.py
```

### Problem: Cronjob läuft nicht
**Lösung:**
1. Gib dem Cronjob Full Disk Access:
   - Systemeinstellungen → Sicherheit & Datenschutz → Vollzugriff auf Festplatte
   - Terminal hinzufügen

2. Überprüfe ob Mac im Energiesparmodus ist (verhindert Cronjobs)

3. Überprüfe Log:
```bash
cat /Users/timhuebner/tradingbot/skills/emailscanner/logs/morning.log
```

---

## ✅ Fertig!

Dein Cronjob läuft jetzt mit folgendem Setup:

**Pfad:** `/Users/timhuebner/tradingbot/skills/emailscanner`

**Zeitplan:**
- **8:00 AM** - Morning Scan
- **5:00 PM** - Afternoon Scan

**Output:**
- Logs: `/Users/timhuebner/tradingbot/skills/emailscanner/logs/`
- Reports: `/Users/timhuebner/tradingbot/skills/emailscanner/reports/`

---

**Fragen? Brauchst du Hilfe bei einem Schritt?** 👍
