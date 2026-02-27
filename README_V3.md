# Producto v3.0 - Production Release Branch

**Status:** Production Packaging Branch  
**Base Version:** v2.0 (fully tested and working)  
**Purpose:** Package v2.0 for enterprise deployment

---

## 🎯 What is V3?

V3 is **not** a new version with new features. It is the **production packaging branch** of the fully working v2.0.

### Version Strategy:
- **V2 (Outlook File Extractor v2.0.py)** - Development & testing branch
  - Active development
  - Feature additions
  - Bug fixes
  - Experimentation

- **V3 (Producto_v3/)** - Production packaging branch
  - Stable v2.0 codebase
  - Production hardening
  - Packaging with PyInstaller
  - Installer creation
  - Enterprise deployment

---

## 📁 Directory Structure

```
Producto_v3/
├── producto.py                           # Main application (from v2.0)
├── outlook_extractor_v2_config.py        # Configuration management
├── outlook_extractor_v2_integrations.py  # Jira, Outlook, Webex integrations
├── outlook_extractor_v2_monitoring.py    # Email monitoring system
├── meeting_classifier_v2.py              # Meeting classification
├── meeting_prompts_v2.py                 # LLM prompts
├── requirements.txt                      # Python dependencies
├── producto.spec                         # PyInstaller specification
├── README_V3.md                          # This file
├── CHANGELOG.md                          # Version history
├── assets/                               # Icons, images
│   └── producto.ico                      # Application icon
├── installer/                            # Installer files
│   ├── producto_installer.iss            # Inno Setup script
│   └── README.md                         # Installer documentation
└── docs/                                 # Documentation
    ├── README.md                         # User guide
    ├── PRODUCTION_DEPLOYMENT_GUIDE.md    # IT deployment guide
    ├── QUICKSTART.md                     # Quick start guide
    └── TROUBLESHOOTING.md                # Common issues
```

---

## 🚀 Building V3 for Distribution

### Prerequisites

```bash
# Install packaging tools
pip install pyinstaller
pip install keyring
pip install -r requirements.txt
```

### Step 1: Build Executable

```bash
# Navigate to Producto_v3 directory
cd Producto_v3

# Build with PyInstaller
pyinstaller producto.spec

# Output: dist/Producto.exe
```

### Step 2: Create Installer

```bash
# Install Inno Setup (if not already installed)
# Download from: https://jrsoftware.org/isinfo.php

# Compile installer
iscc installer/producto_installer.iss

# Output: installer/Output/ProductoInstaller.exe
```

### Step 3: Test

```bash
# Test on clean Windows VM
# 1. Install Outlook
# 2. Run ProductoInstaller.exe
# 3. Complete setup wizard
# 4. Test all features
```

---

## 📝 Changes from V2 to V3

### Production Hardening (Planned)

- [ ] **Credential Manager Integration**
  - Replace environment variables with Windows Credential Manager
  - Secure storage for user-specific credentials

- [ ] **First-Run Wizard**
  - Welcome screen
  - Organization config detection
  - User credential input
  - Outlook connection test
  - Completion screen

- [ ] **Enhanced Error Handling**
  - User-friendly error messages
  - No credential leaks in logs
  - Graceful degradation

- [ ] **Logging Improvements**
  - File-based logging in %APPDATA%
  - Log rotation
  - Masked credentials in logs

- [ ] **Settings Management**
  - Settings UI in dedicated tab
  - Save/Load from Credential Manager
  - Test connection buttons

- [ ] **Auto-Update Check** (Future)
  - Check for updates on startup
  - Download new version
  - Prompt user to update

---

## 🔧 Development Workflow

### Making Changes

1. **Develop in V2**
   ```bash
   # Work on: Outlook File Extractor v2.0.py
   # Test thoroughly
   # When stable and ready for production...
   ```

2. **Sync to V3**
   ```bash
   # Copy updated files to Producto_v3/
   Copy-Item "Outlook File Extractor v2.0.py" -Destination "Producto_v3\producto.py"
   # Update version number in producto.py
   # Update CHANGELOG.md
   ```

3. **Build & Test V3**
   ```bash
   cd Producto_v3
   pyinstaller producto.spec
   # Test dist/Producto.exe
   ```

4. **Create Installer**
   ```bash
   iscc installer/producto_installer.iss
   # Test installer/Output/ProductoInstaller.exe
   ```

5. **Deploy**
   ```bash
   # Copy ProductoInstaller.exe to distribution location
   # Update release notes
   # Notify users
   ```

---

## 📦 Packaging Configuration

### PyInstaller Options

```python
# producto.spec
a = Analysis(
    ['producto.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=[
        'keyring.backends.Windows',
        'outlook_extractor_v2_config',
        'outlook_extractor_v2_integrations',
        'outlook_extractor_v2_monitoring',
        'meeting_classifier_v2',
        'meeting_prompts_v2',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
```

### File Size Optimization

- **Unoptimized:** ~150 MB
- **With UPX compression:** ~80 MB
- **One-file mode:** Single .exe (easier distribution)
- **One-folder mode:** Faster startup (more files)

**Recommendation:** Use one-file mode for easier distribution

---

## 🔒 Security Checklist

Before packaging for production:

- [ ] No hardcoded credentials in code
- [ ] All sensitive data uses Credential Manager
- [ ] HTTPS only for all API calls
- [ ] SSL certificate verification enabled
- [ ] Credentials masked in logs
- [ ] Error messages don't leak secrets
- [ ] Config files don't contain passwords
- [ ] Debug mode disabled
- [ ] Test with security scanner

---

## 📊 Version History

### v3.0.0 (Planned)
- Initial production packaging of v2.0
- Windows Credential Manager integration
- First-run setup wizard
- PyInstaller packaging
- Inno Setup installer

### v2.0.0 (Current Base)
- Email monitoring and automation
- Meeting classification
- Jira posting with approval
- Outlook Tasks creation
- Webex Bot integration
- Tabbed UI with Cisco branding
- Configurable bot recipient
- Smart due date parsing

---

## 🎯 Release Checklist

Before releasing V3:

- [ ] All tests pass
- [ ] Documentation complete
- [ ] CHANGELOG.md updated
- [ ] Version number updated
- [ ] Build successful (no errors)
- [ ] Installer tested on clean VM
- [ ] First-run wizard tested
- [ ] Credential Manager tested
- [ ] Outlook connection tested
- [ ] Jira posting tested
- [ ] Webex Bot tested
- [ ] Security scan passed
- [ ] IT deployment guide ready
- [ ] User quick start guide ready
- [ ] Support documentation ready

---

## 🤝 Support

**For Developers:**
- V2 Development: Continue in `Outlook File Extractor v2.0.py`
- V3 Packaging: Work in `Producto_v3/`

**For Users:**
- See `docs/QUICKSTART.md`
- See `docs/TROUBLESHOOTING.md`

**For IT:**
- See `docs/PRODUCTION_DEPLOYMENT_GUIDE.md`

---

## 📞 Contact

**Product Owner:** Quincy Schalle (qschalle@cisco.com)  
**Development:** AI-Assisted Development  
**Status:** In Production Hardening Phase

---

**Remember:** V2 is for development, V3 is for deployment. Keep them separate!
