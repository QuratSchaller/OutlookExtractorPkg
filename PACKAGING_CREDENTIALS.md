# Packaging Credentials for Producto V3

## 🎯 Overview

Producto V3 uses a hybrid credential management approach:
- **Application Credentials**: Bundled with the .exe (same for all users)
- **User Credentials**: Stored per-user in Windows Credential Manager

---

## 📦 Credential Types

### 1. Webex Integration Credentials (Bundled)
```
WEBEX_INTEGRATION_CLIENT_ID       ← Bundled in app
WEBEX_INTEGRATION_CLIENT_SECRET   ← Bundled in app
```
- **Purpose**: Application's identity with Webex
- **Scope**: Same for all installations
- **Storage**: Hardcoded in `producto_config.py`

### 2. Organizational Credentials (Auto-loaded)
```
WEBEX_BOT_TOKEN                   ← Loaded from env → Windows Credential Manager
CHATAI_CLIENT_ID                  ← Loaded from env → Windows Credential Manager
CHATAI_CLIENT_SECRET              ← Loaded from env → Windows Credential Manager
CHATAI_APP_KEY                    ← Loaded from env → Windows Credential Manager
```
- **Purpose**: Organization-wide services
- **Scope**: Same for all users in organization
- **Storage**: Windows Credential Manager (loaded from environment on first run)

### 3. User OAuth Tokens (Per-User)
```
User's Webex Access Token         ← Per user
User's Webex Refresh Token        ← Per user
```
- **Purpose**: User's personal Webex access
- **Scope**: Unique per user
- **Storage**: Windows Credential Manager (per Windows user account)

---

## 🔧 Build Process

### Step 1: Set Environment Variables
```powershell
# Set these BEFORE building the installer

# Application credentials (will be bundled)
$env:WEBEX_INTEGRATION_CLIENT_ID = "your_integration_client_id"
$env:WEBEX_INTEGRATION_CLIENT_SECRET = "your_integration_client_secret"

# Organizational credentials (will be in documentation for IT)
$env:WEBEX_BOT_TOKEN = "your_bot_token"
$env:CHATAI_CLIENT_ID = "your_chatai_client_id"
$env:CHATAI_CLIENT_SECRET = "your_chatai_client_secret"
$env:CHATAI_APP_KEY = "your_chatai_app_key"
```

### Step 2: Build with PyInstaller
```powershell
cd Producto_v3
python -m PyInstaller producto.spec
```

**What happens:**
- Integration credentials are read from environment and bundled into .exe
- `producto_config.py` contains these values

### Step 3: Build Installer
```powershell
# Open producto_installer.iss in Inno Setup
# Build → Compile
```

---

## 📋 Deployment Options

### Option A: Environment Variables (Recommended for Internal)

**IT Setup:**
```powershell
# On each machine or via Group Policy
[System.Environment]::SetEnvironmentVariable('WEBEX_BOT_TOKEN', 'your_token', 'Machine')
[System.Environment]::SetEnvironmentVariable('CHATAI_CLIENT_ID', 'your_id', 'Machine')
[System.Environment]::SetEnvironmentVariable('CHATAI_CLIENT_SECRET', 'your_secret', 'Machine')
[System.Environment]::SetEnvironmentVariable('CHATAI_APP_KEY', 'your_key', 'Machine')
```

**User Experience:**
1. Install Producto
2. Launch application
3. Org credentials automatically loaded from environment
4. Click "Connect to Webex" to authenticate personally
5. Done!

---

### Option B: Pre-configured Installation

**Build Process:**
1. Edit `producto_config.py` before building
2. Replace placeholder strings with actual values
3. Build installer
4. Distribute installer

**In `producto_config.py`:**
```python
# Change from:
WEBEX_INTEGRATION_CLIENT_ID = 'REPLACE_WITH_ACTUAL_CLIENT_ID'

# To:
WEBEX_INTEGRATION_CLIENT_ID = 'C1234567890abcdef'  # Actual value
```

**User Experience:**
1. Install Producto
2. Launch application (all creds already bundled!)
3. Click "Connect to Webex" to authenticate personally
4. Done!

⚠️ **Note**: Credentials visible if someone reverse-engineers the .exe

---

### Option C: Configuration File (Most Flexible)

Create installer that includes encrypted config file:

**installer/producto_installer.iss additions:**
```iss
[Files]
Source: "..\config\org_credentials.enc"; DestDir: "{commonappdata}\Producto"; Flags: ignoreversion
```

**Application reads:**
```
C:\ProgramData\Producto\org_credentials.enc
```

**IT can update without repackaging!**

---

## 🎯 Recommended Approach for Your Organization

### For V3 Production Release:

**1. Bundle Integration Credentials** (Method B)
- Edit `producto_config.py` before building
- Hardcode `WEBEX_INTEGRATION_CLIENT_ID` and `WEBEX_INTEGRATION_CLIENT_SECRET`
- These are low-risk (just identify your app)

**2. Document Org Credentials for IT** (Method A)
- Create IT deployment guide
- Instruct IT to set environment variables organization-wide
- Or provide Group Policy template

**3. User OAuth is Automatic**
- Each user clicks "Connect to Webex" on first run
- Their token stored in their Windows account

---

## 📝 IT Deployment Guide Template

```markdown
# Producto IT Deployment Guide

## Prerequisites
Set these system-wide environment variables before users install Producto:

### Windows Environment Variables
1. Press Windows + R → Run: `sysdm.cpl`
2. Advanced → Environment Variables
3. Under "System variables" add:

| Variable | Value |
|----------|-------|
| WEBEX_BOT_TOKEN | [REDACTED - Get from admin] |
| CHATAI_CLIENT_ID | [REDACTED - Get from admin] |
| CHATAI_CLIENT_SECRET | [REDACTED - Get from admin] |
| CHATAI_APP_KEY | [REDACTED - Get from admin] |

### Or via PowerShell (Admin):
```powershell
[System.Environment]::SetEnvironmentVariable('WEBEX_BOT_TOKEN', 'VALUE', 'Machine')
[System.Environment]::SetEnvironmentVariable('CHATAI_CLIENT_ID', 'VALUE', 'Machine')
[System.Environment]::SetEnvironmentVariable('CHATAI_CLIENT_SECRET', 'VALUE', 'Machine')
[System.Environment]::SetEnvironmentVariable('CHATAI_APP_KEY', 'VALUE', 'Machine')
```

## Installation
1. Run `ProductoInstaller_v3.0.0.exe`
2. Follow installation wizard
3. Launch Producto from Start Menu

## First Run
Users must:
1. Click "Connect to Webex" in Credentials tab
2. Log in with their Cisco credentials
3. Click "Accept" to grant permissions
4. Application is now ready to use

## Support
- Application automatically uses organizational credentials
- Users only need to authenticate their personal Webex account once
- Tokens automatically refresh for 14 days
```

---

## 🔒 Security Considerations

### What's Protected:
- ✅ User OAuth tokens (encrypted in Windows Credential Manager)
- ✅ Org credentials (encrypted in Windows Credential Manager after first load)

### What's Somewhat Exposed:
- ⚠️ Integration Client ID/Secret (if bundled in .exe)
- **Risk**: Low - these just identify your app, not individual users
- **Mitigation**: OAuth flow still requires user authorization

### What's Secure:
- ✅ No credentials in config files
- ✅ No credentials visible in UI
- ✅ Tokens encrypted at rest
- ✅ Each user has their own token

---

## 🧪 Testing Packaged Application

### Test Scenario 1: Fresh Installation
```
1. Clean Windows VM (no env vars)
2. Install Producto
3. Launch app
4. Check Credentials tab:
   - Webex Integration: Should work (bundled)
   - Bot Token: Not configured (no env var)
   - Chat AI: Not configured (no env var)
5. Set env vars, restart app
6. Check again - should all be configured
```

### Test Scenario 2: Pre-configured Environment
```
1. Set env vars BEFORE installing
2. Install Producto
3. Launch app
4. Check Credentials tab - all should be "Configured ✓"
5. Click "Connect to Webex"
6. Authorize
7. Process test email
```

---

## ✅ Summary

**For V3 Production:**
1. Bundle Integration credentials in `producto_config.py`
2. Document org credentials for IT to set as env vars
3. Users authenticate themselves on first run
4. Everything else is automatic!

**Result:**
- ✅ Zero user configuration burden
- ✅ Secure credential storage
- ✅ Easy IT deployment
- ✅ Scalable across organization
