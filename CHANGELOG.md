# Producto - Version History

All notable changes to the Producto project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] - v3.0.0 (Production Packaging)

### Added
- Windows Credential Manager integration for secure credential storage
- First-run setup wizard for easy onboarding
- Enhanced error handling and user-friendly error messages
- Credential masking in logs and error messages
- Settings save/load from Credential Manager
- Test connection buttons for all services
- Build configuration for PyInstaller packaging
- Inno Setup installer configuration
- Production deployment documentation

### Changed
- Renamed main file to `producto.py` for clarity
- Separated V2 (development) from V3 (production)
- Improved logging with credential masking
- Enhanced security posture

### Removed
- Direct environment variable dependency (moved to Credential Manager)
- Debug logging in production builds

### Security
- No plaintext credentials in environment variables
- OS-level encryption for stored credentials
- SSL certificate verification enforced
- Credential leak prevention in logs and errors

---

## [2.0.0] - 2025-12-10 (Base for V3)

### Added - Phase 1 (Core Automation)
- Automated email monitoring with configurable polling (60s for testing)
- Approval dialogs for new email processing
- Email pattern filtering: "Your Webex meeting content is available:"
- Persistent configuration management (JSON)
- Automatic Outlook Tasks creation (syncs to Microsoft To Do)
- Webex Bot integration (Producto) for team notifications
- Processing delay between emails (60s configurable)
- Email history tracking (processed & ignored)

### Added - Phase 2 (Intelligence & Integration)
- Meeting classification system (Refinement/General/Mixed)
  - Heuristic analysis of meeting title and transcript
  - Scoring system for refinement vs action keywords
  - Intelligent routing based on meeting type
- Jira posting with human approval
  - Parse issues from analysis
  - Checkbox selection UI
  - Batch posting to Jira
  - Custom field support (Work Type, Team, Acceptance Criteria)
- Configurable Webex Bot recipient email
- Smart due date parsing from transcript hints
  - "asap", "urgent" → 1 business day
  - "tomorrow" → 1 business day
  - "this week" → Next Friday
  - "next week" → 5 business days
  - "two weeks" → 10 business days
  - "next month" → 15 business days
  - Default → 10 business days
- Business days calculation (skips weekends)

### Added - UI Enhancements
- Tabbed interface for better organization
  - Tab 1: Connection & Monitoring
  - Tab 2: Credentials
  - Tab 3: Settings
  - Tab 4: Activity Log
- Cisco brand colors and styling
  - Navy/Blue color scheme
  - Gradient header background
  - Thicker section borders
  - Modern button styles
- Enhanced Activity Log
  - Full dedicated tab
  - White background for readability
  - Scrollable, expandable
- Analysis window improvements
  - Issue selection with checkboxes
  - Select All / Deselect All buttons
  - Copy Selected / Copy All buttons
  - Post to Jira button
  - Progress window for Jira posting

### Changed
- Window size increased to 1150x950 for better visibility
- Modular architecture (separate files for config, integrations, monitoring)
- Improved error handling and logging
- Enhanced Webex Bot messages with markdown formatting
- Configuration stored in `%APPDATA%\OutlookVTTExtractor\config_v2.json`

### Fixed
- Activity Log cut-off issues (dedicated tab)
- Webex Bot recipient now configurable
- Due date calculation now respects hints

---

## [1.0.0] - Initial MVP

### Added
- Manual email selection and processing
- Webex VTT file download
- Meeting transcript extraction
- AI analysis with Cisco Chat AI
- Meeting classification (Refinement/General/Mixed)
- Adaptive LLM prompts based on meeting type
- Jira issue posting with human approval
- User story and action item extraction
- Acceptance criteria parsing
- Custom Jira field support

### Features
- Outlook COM integration
- Webex API integration
- Chat AI (Cisco) integration
- Jira Cloud API integration
- Manual processing workflow
- Analysis display window
- Issue selection UI
- Clipboard copy functionality

---

## Version Numbering Strategy

### Semantic Versioning: MAJOR.MINOR.PATCH

- **MAJOR** (X.0.0): Breaking changes, major architecture changes
- **MINOR** (x.Y.0): New features, backward compatible
- **PATCH** (x.y.Z): Bug fixes, minor improvements

### Version Labels

- **v1.0** - MVP (Manual processing)
- **v2.0** - Automated monitoring & intelligence
- **v3.0** - Production packaging & deployment
- **v4.0** - (Future) Enterprise features (central management, SSO, etc.)

---

## Upgrade Path

### From V1 to V2
- No migration needed (separate codebase)
- Copy custom Jira field configurations if customized

### From V2 to V3
- Credentials migration from environment variables to Credential Manager
- First-run wizard guides through setup
- Configuration automatically migrated

---

## Known Issues

### V2.0
- Requires manual environment variable setup (fixed in v3.0)
- No auto-update mechanism (planned for v3.1)
- Webex OAuth not used (simplified to access token)

### V3.0 (Current)
- First-run wizard not yet implemented (in progress)
- Credential Manager integration not yet complete (in progress)
- No system tray support (planned for Phase 3)
- No Windows startup integration (planned for Phase 3)

---

## Roadmap

### v3.0 (Current) - Production Release
- [x] Create production branch (V3)
- [ ] Windows Credential Manager integration
- [ ] First-run setup wizard
- [ ] PyInstaller packaging
- [ ] Inno Setup installer
- [ ] Security audit
- [ ] Documentation for users & IT

### v3.1 - Refinements
- [ ] Auto-update mechanism
- [ ] Enhanced logging
- [ ] Performance optimizations
- [ ] Bug fixes from user feedback

### v4.0 - Enterprise Features
- [ ] Central configuration server
- [ ] Group Policy templates
- [ ] SSO integration
- [ ] Admin dashboard
- [ ] Usage analytics
- [ ] Multi-tenant support

### Phase 3 Features (Future)
- [ ] System tray icon and minimize
- [ ] Windows Task Scheduler integration
- [ ] Background service mode
- [ ] Notification improvements

---

**Current Version:** v3.0.0-dev  
**Last Updated:** December 10, 2025  
**Maintained By:** Quincy Schalle (qschalle@cisco.com)
