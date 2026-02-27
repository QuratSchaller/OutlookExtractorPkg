# Producto v3.0 - Build Instructions

This guide walks you through building Producto from source to a distributable installer.

---

## 📋 Prerequisites

### Required Software

1. **Python 3.11 or 3.13**
   - Download: https://www.python.org/downloads/
   - ✅ Install with "Add Python to PATH" checked

2. **Microsoft Outlook**
   - Required for COM automation
   - Must be installed and configured

3. **PyInstaller**
   - Installed via pip (see below)

4. **Inno Setup** (for installer creation)
   - Download: https://jrsoftware.org/isinfo.php
   - ✅ Install with default options

---

## 🔧 Setup Development Environment

### Step 1: Clone/Copy V3 Files

```powershell
# If you're starting fresh
cd "C:\Users\qschalle\Downloads\Outlook Items to Issues\Producto_v3"
```

### Step 2: Create Virtual Environment (Recommended)

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you get execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 3: Install Dependencies

```powershell
# Install required packages
pip install -r requirements.txt

# Verify installation
pip list
```

Expected packages:
- pywin32
- requests
- keyring
- pyinstaller

---

## 🏗️ Build Process

### Phase 1: Build Executable with PyInstaller

#### Option A: Using the spec file (Recommended)

```powershell
# Build using existing configuration
pyinstaller producto.spec

# Output: dist/Producto.exe
```

#### Option B: Manual PyInstaller command

```powershell
pyinstaller --name="Producto" `
            --windowed `
            --onefile `
            --add-data="assets;assets" `
            --hidden-import="keyring.backends.Windows" `
            --hidden-import="win32com" `
            --hidden-import="win32com.client" `
            --upx-dir="C:\upx" `
            producto.py
```

**Build Output:**
```
Producto_v3/
├── build/              # Temporary build files (can be deleted)
├── dist/
│   └── Producto.exe   # 🎯 THIS IS YOUR EXECUTABLE
└── producto.spec       # Build configuration
```

#### Test the Executable

```powershell
# Run the built executable
.\dist\Producto.exe

# Test on a different machine without Python installed
```

**Common Build Issues:**

1. **Missing module errors:**
   ```
   Solution: Add to hiddenimports in producto.spec
   ```

2. **File too large (>200 MB):**
   ```
   Solution: Enable UPX compression
   Download UPX: https://github.com/upx/upx/releases
   ```

3. **Antivirus blocking:**
   ```
   Solution: Add exclusion for build directory
   ```

---

### Phase 2: Create Installer with Inno Setup

#### Step 1: Open Inno Setup

```
1. Launch Inno Setup Compiler
2. Open: installer\producto_installer.iss
```

#### Step 2: Configure Installer (if needed)

Edit `producto_installer.iss`:
```inno
#define MyAppVersion "3.0.0"    ; Update version number
#define MyAppPublisher "Cisco Systems"  ; Your organization
#define MyAppContact "qschalle@cisco.com"  ; Support contact
```

#### Step 3: Compile Installer

```
1. In Inno Setup: Build > Compile
   OR
   Press Ctrl+F9

2. Wait for compilation (should take 10-30 seconds)

3. Output: installer\Output\ProductoInstaller_v3.0.0.exe
```

**Installer Output:**
```
Producto_v3/
└── installer/
    └── Output/
        └── ProductoInstaller_v3.0.0.exe  # 🎯 DISTRIBUTABLE INSTALLER
```

#### Test the Installer

```powershell
# Run installer in test mode
.\installer\Output\ProductoInstaller_v3.0.0.exe /SILENT /LOG="install_log.txt"

# Or interactive mode:
.\installer\Output\ProductoInstaller_v3.0.0.exe
```

**Test Checklist:**
- [ ] Installer runs without errors
- [ ] Application installs to Program Files
- [ ] Desktop shortcut created
- [ ] Start menu entry created
- [ ] Application launches successfully
- [ ] Uninstaller works correctly

---

## 🧪 Testing Strategy

### Test Environment 1: Clean Windows VM

**Purpose:** Verify installer works on fresh system

```
1. Create Windows 10/11 VM
2. Install Microsoft Outlook
3. Do NOT install Python
4. Run ProductoInstaller.exe
5. Complete setup wizard
6. Test all features
```

### Test Environment 2: Different User Profile

**Purpose:** Verify user-specific installations

```
1. Create new Windows user account
2. Login as that user
3. Run ProductoInstaller.exe
4. Verify credentials are isolated
```

### Test Environment 3: Upgrade Scenario

**Purpose:** Verify upgrades work

```
1. Install previous version
2. Run new installer
3. Verify settings preserved
4. Verify credentials preserved
```

---

## 📦 Distribution

### Option 1: File Share (Internal Network)

```powershell
# Copy installer to network share
Copy-Item "installer\Output\ProductoInstaller_v3.0.0.exe" `
          -Destination "\\company-server\software\Producto\"
```

### Option 2: SCCM/Intune Deployment

```
1. Create application package
2. Set detection method (registry key)
3. Configure installation command:
   ProductoInstaller.exe /SILENT /NORESTART
4. Deploy to target computers
```

### Option 3: Self-Service Portal

Upload to internal software portal with:
- ProductoInstaller.exe
- README.md
- Quick Start Guide
- Release Notes

---

## 🔄 Update Process

### Building an Update

```powershell
# 1. Update version number
# Edit producto.py:
__version__ = "3.1.0"

# Edit producto_installer.iss:
#define MyAppVersion "3.1.0"

# 2. Update CHANGELOG.md with changes

# 3. Rebuild executable
pyinstaller producto.spec

# 4. Rebuild installer
# (Open in Inno Setup and compile)

# 5. Test thoroughly

# 6. Distribute new installer
```

### Version Numbering

```
MAJOR.MINOR.PATCH

3.0.0 - Initial production release
3.0.1 - Bug fix
3.1.0 - New feature
4.0.0 - Breaking changes
```

---

## 🐛 Troubleshooting Build Issues

### Issue: "Module not found" error in built executable

**Solution:**
```python
# Add to producto.spec hiddenimports:
hiddenimports=[
    'missing_module_name',
],
```

### Issue: Build is very slow

**Solution:**
```powershell
# Exclude unnecessary packages in producto.spec:
excludes=[
    'pytest', 'IPython', 'matplotlib', 'numpy', 'pandas',
],
```

### Issue: Antivirus flags executable as malware

**Solution:**
1. Add exclusion for build directory
2. Sign executable with code signing certificate
3. Submit to antivirus vendor for whitelisting

### Issue: Outlook COM not working in packaged app

**Solution:**
```python
# Ensure win32com is properly imported
import win32com.client
import pythoncom

# Use late binding
outlook = win32com.client.Dispatch("Outlook.Application")
```

### Issue: Keyring not working in packaged app

**Solution:**
```python
# Explicitly import Windows backend
import keyring
from keyring.backends import Windows
keyring.set_keyring(Windows.WinVaultKeyring())
```

---

## 📊 Build Metrics

### Expected Build Times

- PyInstaller build: 2-5 minutes
- Inno Setup compile: 10-30 seconds
- Total: ~5-10 minutes

### Expected File Sizes

- Uncompressed executable: ~150 MB
- With UPX compression: ~80 MB
- Final installer: ~85 MB

### Optimization Tips

1. **Enable UPX compression:** Reduces size by ~40%
2. **Exclude dev packages:** Reduces size by ~20 MB
3. **One-file mode:** Easier distribution
4. **Strip debug symbols:** Reduces size slightly

---

## ✅ Pre-Release Checklist

Before distributing V3:

- [ ] Version number updated in all files
- [ ] CHANGELOG.md updated
- [ ] All tests pass
- [ ] Executable built without errors
- [ ] Installer created successfully
- [ ] Tested on clean Windows VM
- [ ] Tested on different user profile
- [ ] Tested upgrade from previous version
- [ ] Documentation updated
- [ ] Release notes prepared
- [ ] Support team notified
- [ ] Rollback plan documented

---

## 📞 Build Support

**Build Issues:** [Your DevOps Team]
**PyInstaller Help:** https://pyinstaller.org/en/stable/
**Inno Setup Help:** https://jrsoftware.org/ishelp/

---

## 🚀 Quick Build Commands

```powershell
# Complete build process (one-liner)
cd Producto_v3
pyinstaller producto.spec
iscc installer\producto_installer.iss

# Output:
# - dist\Producto.exe
# - installer\Output\ProductoInstaller_v3.0.0.exe
```

---

**Document Version:** 1.0  
**Last Updated:** December 10, 2025  
**Maintained By:** Development Team
