# GMX App-Passwort Setup für Email Skill

## Schritt 1: Gehe zu GMX Sicherheitseinstellungen

1. Öffne **gmx.de** und melde dich an
2. Klicke auf dein **Profil-Icon** (oben rechts)
3. Wähle **"Einstellungen"** oder **"Konto"**
4. Navigiere zu **"Sicherheit"** oder **"Sichere Anmeldung"**

## Schritt 2: Aktiviere App-Passwörter

1. Suche nach **"App-Passwort"** oder **"Anwendungsspezifische Passwörter"**
2. Klicke auf **"Neues App-Passwort erstellen"** oder **"Hinzufügen"**
3. Beschreibung eingeben: z.B. **"Email Skill Bot"**
4. GMX generiert dir ein **16-stelliges Passwort**
5. **KOPIERE DIESES PASSWORT** (du brauchst es gleich!)

## Schritt 3: Notiere deine Credentials

Speichere diese Informationen sicher ab (z.B. in einer Datei oder Password Manager):

```
EMAIL_PROVIDER: GMX
EMAIL: deine-email@gmx.de
EMAIL_PASSWORD: [16-stelliges App-Passwort aus Schritt 2]
IMAP_SERVER: imap.gmx.net
IMAP_PORT: 993
SSL_ENABLED: true
```

## ⚠️ WICHTIG - Sicherheit:

- **Speichere das App-Passwort NIE** im Plain-Text in deinen Dateien
- Verwende einen **Password Manager** (z.B. Bitwarden, 1Password, KeePass)
- Das App-Passwort ist **speziell für diese App** - dein echtes GMX-Passwort bleibt sicher
- Du kannst das App-Passwort jederzeit in GMX deaktivieren/löschen

## Schritt 4: Konfiguriere deinen Skill

Sobald du das App-Passwort hast, gehen wir zum nächsten Schritt!
