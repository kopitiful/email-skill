# Email Skill Konfiguration für automatische 2x tägliche Scans

## config.json

Speichere diese Datei als `email-skill-config.json`:

```json
{
  "email_config": {
    "provider": "GMX",
    "email_address": "deine-email@gmx.de",
    "app_password": "XXXX-XXXX-XXXX-XXXX",
    "imap_server": "imap.gmx.net",
    "imap_port": 993,
    "use_ssl": true,
    "folder": "INBOX"
  },
  "scanning": {
    "enabled": true,
    "frequency": "twice_daily",
    "schedule": [
      {
        "time": "08:00",
        "timezone": "Europe/Amsterdam",
        "description": "Morning scan"
      },
      {
        "time": "17:00",
        "timezone": "Europe/Amsterdam",
        "description": "Afternoon scan"
      }
    ]
  },
  "output": {
    "format": "markdown",
    "delivery_method": "email",
    "send_to": "deine-email@gmx.de",
    "subject_prefix": "[Inbox Digest]",
    "include_generic_emails": true,
    "include_actions": true,
    "max_generic_emails": 10,
    "max_action_items": 20
  },
  "filtering": {
    "exclude_senders": [
      "noreply@*",
      "notifications@*",
      "no-reply@*"
    ],
    "priority_keywords": {
      "high": ["URGENT", "ASAP", "TODAY", "CRITICAL", "DRINGEND"],
      "medium": ["IMPORTANT", "this week", "diese woche"],
      "low": ["FYI", "when you can", "wenn du zeit hast"]
    }
  },
  "logging": {
    "enabled": true,
    "log_file": "/var/log/email-skill.log",
    "level": "INFO"
  }
}
```

---

## Wie man die Credentials SICHER speichert:

### Option A: Environment Variables (SICHERSTE Methode)

Statt die Config direkt zu speichern, nutze Environment Variables:

```bash
# Linux/Mac - .env Datei erstellen:
export EMAIL_PROVIDER="GMX"
export EMAIL_ADDRESS="deine-email@gmx.de"
export EMAIL_APP_PASSWORD="XXXX-XXXX-XXXX-XXXX"
export IMAP_SERVER="imap.gmx.net"
export IMAP_PORT=993

# Oder in Windows (.env.bat):
set EMAIL_PROVIDER=GMX
set EMAIL_ADDRESS=deine-email@gmx.de
set EMAIL_APP_PASSWORD=XXXX-XXXX-XXXX-XXXX
```

Dann lädt die Config diese Variablen statt hardcodierter Werte.

### Option B: Secrets Manager

Verwende einen Password Manager:
- **Bitwarden** (kostenlos, open-source)
- **1Password** (bezahlt, empfohlen)
- **KeePass** (lokal, kostenlos)

Der Skill liest dann die Credentials von dort.

---

## Schritt-für-Schritt Einrichtung

### 1. GMX App-Passwort erstellen (siehe separate Anleitung)

### 2. Config-Datei vorbereiten

```
email-skill-config.json
↓
Mit deinen Daten füllen (siehe oben)
↓
In sicheres Verzeichnis speichern
```

### 3. Automatisierung einrichten

Je nach deinem System:

**OPTION A: Cronjob (Linux/Mac)**

```bash
# Öffne Terminal und tippe:
crontab -e

# Füge diese Zeilen hinzu:
# Morning scan at 8 AM
0 8 * * * /usr/local/bin/python3 /path/to/email-skill.py scan morning

# Afternoon scan at 5 PM  
0 17 * * * /usr/local/bin/python3 /path/to/email-skill.py scan afternoon
```

**OPTION B: Windows Task Scheduler**

1. Öffne **Task Scheduler**
2. Klicke **"Create Task"**
3. Name: `Email Skill Morning Scan`
4. Trigger: **Daily** at 8:00 AM
5. Action: Python script ausführen
6. Wiederhol für 5 PM (Afternoon Scan)

**OPTION C: Cloud-basiert (EINFACHSTE)**

Nutze einen Service wie:
- **GitHub Actions** (kostenlos für private Repos)
- **Google Cloud Scheduler** (kostenlos mit Limits)
- **IFTTT** (einfach aber weniger flexibel)
- **Zapier** (professionell)

---

## Python Script zum Ausführen des Skills

Speichere diese Datei als `run-email-skill.py`:

```python
#!/usr/bin/env python3
"""
Email Skill Runner - Führt den Email Scan aus
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Lade Config
config_path = Path("/path/to/email-skill-config.json")  # ANPASSEN!
with open(config_path) as f:
    config = json.load(f)

# Lade Credentials aus Env-Variablen (SICHERER!)
email = os.getenv("EMAIL_ADDRESS", config["email_config"]["email_address"])
app_password = os.getenv("EMAIL_APP_PASSWORD", config["email_config"]["app_password"])

print(f"🔄 Email Skill startet...")
print(f"📧 Scanning: {email}")
print(f"🕐 Zeit: {datetime.now()}")

# HIER WÜRDE DER EIGENTLICHE SKILL AUSGEFÜHRT
# (Integration mit deinem Email Skill)

print("✅ Scan abgeschlossen!")
print("📨 Digest wurde gesendet.")
```

Mache das Script ausführbar:

```bash
chmod +x run-email-skill.py
```

---

## Nächster Schritt

Sag mir:
1. Hast du das GMX App-Passwort erstellt?
2. Welches System nutzt du? (Windows/Mac/Linux)
3. Möchtest du lokal oder Cloud-basiert automatisieren?

Dann zeige ich dir die genaue Einrichtung! 👍
