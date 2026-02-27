#!/usr/bin/env python3
"""
Outlook to Webex VTT Extractor v2.0
MODULAR ARCHITECTURE VERSION

NEW IN v2.0:
- Automated folder monitoring with configurable polling
- Approval dialogs for new emails  
- Outlook Tasks integration (auto-syncs to Microsoft To Do)
- Webex bot integration for action items
- Persistent configuration and state management
- Modular code structure for maintainability

ARCHITECTURE:
- outlook_extractor_v2_config.py: Configuration management
- outlook_extractor_v2_monitoring.py: Email monitoring
- outlook_extractor_v2_integrations.py: External integrations
- This file: Main UI and orchestration

DEPENDENCIES (install with: pip install pywin32 beautifulsoup4 requests keyring):
pywin32
beautifulsoup4
requests
keyring
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import re
import os
import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import threading
import win32com.client
import pythoncom
import requests
import base64

# Import v2 modules
from outlook_extractor_v2_config import ConfigManager
from outlook_extractor_v2_monitoring import EmailMonitor, ApprovalDialog
from outlook_extractor_v2_integrations import OutlookTasksIntegration, WebexBotIntegration

# Import meeting classification system v2
from meeting_classifier_v2 import classify_meeting, MeetingClassification
from meeting_prompts_v2 import (
    SYSTEM_PROMPT,
    build_refinement_user_prompt,
    build_general_user_prompt,
    build_mixed_user_prompt
)

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False


class WebexOAuthManager:
    """Manages Webex OAuth2 Client Credentials flow for Service Apps"""
    
    def __init__(self, client_id, client_secret, service_app_id, config_manager, log_callback=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.service_app_id = service_app_id
        self.config_manager = config_manager
        self.log = log_callback if log_callback else print
        # Webex OAuth2 token endpoint for Service Apps
        self.token_url = 'https://webexapis.com/v1/access_token'
    
    def get_access_token(self):
        """Get valid access token, refreshing if necessary"""
        # Check for cached valid token
        cached_token = self.config_manager.get_oauth_token()
        if cached_token:
            self.log("  ✓ Using cached OAuth token")
            return cached_token
        
        # Need to get new token
        self.log("  Requesting new OAuth access token (Webex Service App)...")
        return self.refresh_access_token()
    
    def refresh_access_token(self):
        """
        Request new access token using OAuth2 Client Credentials Grant
        Follows Webex Meeting Service Apps authentication flow
        Reference: https://developer.webex.com/meeting/docs/service-apps
        """
        try:
            # Prepare request headers
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            # Request body with all required parameters
            # Webex Service Apps use a custom grant type
            data = {
                'grant_type': 'urn:cisco:webex:oauth2:grant-type:service_app',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'service_app_id': self.service_app_id
            }
            
            self.log(f"  Calling {self.token_url}...")
            self.log(f"  Service App ID: {self.service_app_id}")
            
            # Make request
            response = requests.post(self.token_url, headers=headers, data=data, timeout=30)
            
            # Handle errors
            if response.status_code == 400:
                self.log(f"  ✗ Bad Request - Invalid client credentials or grant_type")
                self.log(f"     Response: {response.text[:300]}")
                return None
            elif response.status_code == 401:
                self.log(f"  ✗ Unauthorized - Client ID or Secret is incorrect")
                return None
            elif response.status_code != 200:
                self.log(f"  ✗ OAuth token request failed: {response.status_code}")
                self.log(f"     Response: {response.text[:300]}")
                return None
            
            # Parse response
            token_data = response.json()
            access_token = token_data.get('access_token')
            token_type = token_data.get('token_type', 'Bearer')
            expires_in = token_data.get('expires_in', 1209600)  # Default 14 days
            refresh_token = token_data.get('refresh_token')  # May be present
            refresh_token_expires_in = token_data.get('refresh_token_expires_in', 0)
            
            if not access_token:
                self.log(f"  ✗ No access token in response")
                self.log(f"     Response: {token_data}")
                return None
            
            # Log token details
            self.log(f"  ✓ Got new OAuth token")
            self.log(f"     Token Type: {token_type}")
            self.log(f"     Expires In: {expires_in} seconds ({expires_in//3600} hours)")
            if refresh_token:
                self.log(f"     Refresh Token: Available (expires in {refresh_token_expires_in} seconds)")
            
            # Save token to cache
            self.config_manager.save_oauth_tokens(access_token, expires_in)
            
            return access_token
        
        except requests.exceptions.Timeout:
            self.log(f"  ✗ OAuth request timed out")
            return None
        except requests.exceptions.ConnectionError:
            self.log(f"  ✗ OAuth request connection error")
            return None
        except Exception as e:
            self.log(f"  ✗ OAuth error: {str(e)}")
            import traceback
            self.log(f"     {traceback.format_exc()[:300]}")
            return None


class OutlookWebexExtractorV2:
    """Main application class for v2.0"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Producto - Meeting Intelligence Assistant")
        self.root.geometry("1150x950")  # Increased size for better visibility
        self.root.minsize(1100, 900)  # Set minimum size to prevent cutting off content
        
        # Set modern styling
        self.setup_styles()
        
        # Core components
        self.outlook = None
        self.config_manager = ConfigManager()
        
        # Monitoring
        self.email_monitor = None
        
        # Setup UI
        self.setup_ui()
        
        # Auto-connect to Outlook
        self.root.after(500, self.auto_connect_outlook)
        
    def setup_styles(self):
        """Setup modern UI styling with Cisco brand colors"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Cisco brand colors from gradient
        cisco_navy = '#0D274D'        # Deep navy blue
        cisco_blue = '#049FD9'         # Cisco cyan/turquoise
        cisco_purple = '#7B3F8F'       # Purple from gradient
        # Dark ombre-inspired background (from provided image)
        cisco_light_bg = '#071B2E'     # App background (dark navy)
        cisco_text = '#E6EEF7'         # Light text for readability
        cisco_accent = '#00BCF2'       # Bright cyan accent
        success_green = '#00875A'      # Success color
        
        self.root.configure(bg=cisco_light_bg)
        
        # Custom styles with Cisco branding
        style.configure('Title.TLabel', font=('Segoe UI', 20, 'bold'), 
                       foreground=cisco_navy, background=cisco_light_bg)
        style.configure('Subtitle.TLabel', font=('Segoe UI', 10), 
                       foreground=cisco_text, background=cisco_light_bg)
        
        # Prominent section borders with thicker relief
        style.configure('Section.TLabelframe', 
                       font=('Segoe UI', 10, 'bold'),
                       foreground=cisco_blue, 
                       background=cisco_light_bg, 
                       bordercolor=cisco_blue,
                       borderwidth=3,  # Thicker border
                       relief='solid')
        style.configure('Section.TLabelframe.Label', 
                       font=('Segoe UI', 10, 'bold'),
                       foreground=cisco_blue, 
                       background=cisco_light_bg)
        
        # Bold action buttons
        style.configure('Action.TButton', 
                       font=('Segoe UI', 9, 'bold'),
                       background=cisco_blue, 
                       foreground='white',
                       borderwidth=2,
                       relief='raised')
        
        style.configure('TFrame', background=cisco_light_bg)
        style.configure('TLabel', background=cisco_light_bg, foreground=cisco_text)
        style.configure('TCheckbutton', background=cisco_light_bg, foreground=cisco_text)
        style.configure('TEntry', 
                       fieldbackground='white', 
                       bordercolor=cisco_blue,
                       borderwidth=2)

        # Notebook theming to match dark background
        style.configure('TNotebook', background=cisco_light_bg, borderwidth=0)
        style.configure('TNotebook.Tab', padding=[10, 6])
        style.map(
            'TNotebook.Tab',
            background=[('selected', cisco_navy), ('active', '#0E2F5A')],
            foreground=[('selected', 'white'), ('active', 'white')],
        )
        
        # Map hover effects with stronger colors
        style.map('Action.TButton',
                 background=[('active', cisco_accent), ('pressed', cisco_navy)],
                 relief=[('pressed', 'sunken')])
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="15", style='TFrame')
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)  # Tab notebook gets the weight
        
        # Header section with ombre background
        header_frame = tk.Frame(main_frame, bg='#071B2E', height=85)  # Ombre-inspired dark navy
        header_frame.grid(row=0, column=0, columnspan=2, pady=(0, 12), sticky=(tk.W, tk.E))
        header_frame.grid_propagate(False)
        
        # Create ombre effect with Canvas
        header_canvas = tk.Canvas(header_frame, height=85, bg='#071B2E', highlightthickness=0)
        header_canvas.pack(fill=tk.BOTH, expand=True)

        def _hex_to_rgb(h: str):
            h = h.lstrip('#')
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        def _rgb_to_hex(rgb):
            return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

        def _lerp(a: int, b: int, t: float) -> int:
            return int(a + (b - a) * t)

        def _draw_ombre_header():
            # Redraw on resize
            header_canvas.delete('ombre')

            w = max(1, header_canvas.winfo_width())
            h = 85

            # Multi-stop gradient approximating the provided image's ombre
            # (deep navy -> indigo/purple -> azure/blue -> deep navy)
            stops = [
                (0.00, '#071B2E'),
                (0.35, '#0D274D'),
                (0.55, '#3E2B63'),
                (0.78, '#1A63A8'),
                (1.00, '#0B2B4A'),
            ]

            # Draw as many vertical lines for a smooth gradient
            for x in range(w):
                p = x / (w - 1) if w > 1 else 0.0

                # Find stop segment
                for i in range(len(stops) - 1):
                    p0, c0 = stops[i]
                    p1, c1 = stops[i + 1]
                    if p0 <= p <= p1:
                        local_t = 0.0 if p1 == p0 else (p - p0) / (p1 - p0)
                        r0, g0, b0 = _hex_to_rgb(c0)
                        r1, g1, b1 = _hex_to_rgb(c1)
                        col = _rgb_to_hex((
                            _lerp(r0, r1, local_t),
                            _lerp(g0, g1, local_t),
                            _lerp(b0, b1, local_t),
                        ))
                        break
                else:
                    col = stops[-1][1]

                header_canvas.create_line(x, 0, x, h, fill=col, tags='ombre')

            # Subtle top-to-bottom darkening for depth (lightweight)
            shadow_steps = 12
            for i in range(shadow_steps):
                alpha_t = i / shadow_steps
                # Move from transparent-ish to darker at the top
                col = '#061528' if alpha_t < 0.6 else '#05101f'
                y0 = int(i * (h / shadow_steps))
                y1 = int((i + 1) * (h / shadow_steps))
                header_canvas.create_rectangle(0, y0, w, y1, fill=col, outline=col, tags='ombre')

            # Ensure text stays above the gradient
            header_canvas.tag_lower('ombre')

        header_canvas.bind('<Configure>', lambda _e: _draw_ombre_header())
        header_canvas.after(0, _draw_ombre_header)
        
        # Title with icon on gradient
        header_canvas.create_text(550, 30, text="🎯 Producto", 
                                 font=('Segoe UI', 20, 'bold'), fill='white', anchor=tk.CENTER)
        
        # Subtitle on gradient
        header_canvas.create_text(550, 58, 
                                 text="Meeting Intelligence Assistant - Transform Webex meetings into actionable insights",
                                 font=('Segoe UI', 9), fill='#C0D8E8', anchor=tk.CENTER)
        
        # Separator line (cyan accent)
        ttk.Separator(main_frame, orient='horizontal').grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 12))
        
        # Create tabbed notebook
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Tab 1: Connection & Monitoring
        tab1 = ttk.Frame(notebook, padding="15", style='TFrame')
        notebook.add(tab1, text="📬 Connection & Monitoring")
        
        # Tab 2: Credentials
        tab2 = ttk.Frame(notebook, padding="15", style='TFrame')
        notebook.add(tab2, text="🔐 Credentials")
        
        # Tab 3: Settings
        tab3 = ttk.Frame(notebook, padding="15", style='TFrame')
        notebook.add(tab3, text="⚙️ Settings")
        
        # Tab 4: Activity Log
        tab4 = ttk.Frame(notebook, padding="15", style='TFrame')
        notebook.add(tab4, text="📋 Activity Log")
        
        # === TAB 1: CONNECTION & MONITORING ===
        tab1.columnconfigure(0, weight=1)
        
        # Outlook connection status
        connection_frame = ttk.LabelFrame(tab1, text="📬 Outlook Connection", padding="12", style='Section.TLabelframe')
        connection_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        connection_frame.columnconfigure(1, weight=1)
        
        self.auth_status_label = ttk.Label(connection_frame, text="Not connected", 
                                           foreground="#E8112D")  # Cisco red
        self.auth_status_label.grid(row=0, column=0, sticky=tk.W, padx=5)
        
        self.auth_button = ttk.Button(connection_frame, text="Connect to Outlook", 
                                      command=self.connect_outlook, style='Action.TButton')
        self.auth_button.grid(row=0, column=1, sticky=tk.E, padx=5)
        
        # Monitoring section
        monitor_frame = ttk.LabelFrame(tab1, text="📧 Email Monitoring", padding="12", style='Section.TLabelframe')
        monitor_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 0))
        monitor_frame.columnconfigure(1, weight=1)
        
        ttk.Label(monitor_frame, text="Monitored Folder:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.folder_entry = ttk.Entry(monitor_frame, width=30)
        self.folder_entry.insert(0, self.config_manager.config['monitored_folder'])
        self.folder_entry.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        self.monitoring_status_label = ttk.Label(monitor_frame, text="⚫ Stopped", 
                                                  foreground="#E8112D", font=('Segoe UI', 10, 'bold'))
        self.monitoring_status_label.grid(row=0, column=2, padx=10)
        
        self.start_monitor_button = ttk.Button(monitor_frame, text="▶ Start Monitoring", 
                                               command=self.start_monitoring, state="disabled", 
                                               style='Action.TButton')
        self.start_monitor_button.grid(row=1, column=0, pady=5, padx=5, sticky=tk.W)
        
        self.stop_monitor_button = ttk.Button(monitor_frame, text="⏸ Stop Monitoring", 
                                              command=self.stop_monitoring, state="disabled",
                                              style='Action.TButton')
        self.stop_monitor_button.grid(row=1, column=1, pady=5, padx=5, sticky=tk.W)
        
        self.clear_history_button = ttk.Button(monitor_frame, text="🗑️ Clear History", 
                                               command=self.clear_processing_history,
                                               style='Action.TButton')
        self.clear_history_button.grid(row=1, column=2, pady=5, padx=5, sticky=tk.W)
        
        # === TAB 2: CREDENTIALS ===
        tab2.columnconfigure(0, weight=1)
        
        # Credentials section
        creds_frame = ttk.LabelFrame(tab2, text="🔐 API Credentials", padding="12", style='Section.TLabelframe')
        creds_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        creds_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # Webex Access Token
        ttk.Label(creds_frame, text="Webex Access Token:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.webex_token_entry = ttk.Entry(creds_frame, width=40, show="*")
        self.webex_token_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        webex_token = os.getenv('WEBEX_ACCESS_TOKEN')
        if webex_token:
            self.webex_token_entry.insert(0, webex_token)
        row += 1
        
        # Webex Bot Token
        ttk.Label(creds_frame, text="Webex Bot Token:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.bot_token_entry = ttk.Entry(creds_frame, width=40, show="*")
        self.bot_token_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        bot_token_env = os.getenv('WEBEX_BOT_TOKEN')
        if bot_token_env:
            self.bot_token_entry.insert(0, bot_token_env)
        row += 1
        
        # Chat AI credentials
        ttk.Label(creds_frame, text="Chat AI Client ID:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.chatai_client_id_entry = ttk.Entry(creds_frame, width=40)
        self.chatai_client_id_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        if os.getenv('CHATAI_CLIENT_ID'):
            self.chatai_client_id_entry.insert(0, os.getenv('CHATAI_CLIENT_ID'))
        row += 1
        
        ttk.Label(creds_frame, text="Chat AI Client Secret:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.chatai_client_secret_entry = ttk.Entry(creds_frame, width=40, show="*")
        self.chatai_client_secret_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        if os.getenv('CHATAI_CLIENT_SECRET'):
            self.chatai_client_secret_entry.insert(0, os.getenv('CHATAI_CLIENT_SECRET'))
        row += 1
        
        ttk.Label(creds_frame, text="Chat AI App Key:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.chatai_app_key_entry = ttk.Entry(creds_frame, width=40, show="*")
        self.chatai_app_key_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        if os.getenv('CHATAI_APP_KEY'):
            self.chatai_app_key_entry.insert(0, os.getenv('CHATAI_APP_KEY'))
        row += 1
        
        # Jira credentials
        ttk.Label(creds_frame, text="Jira URL:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.jira_url_entry = ttk.Entry(creds_frame, width=40)
        self.jira_url_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        if os.getenv('JIRA_URL'):
            self.jira_url_entry.insert(0, os.getenv('JIRA_URL'))
        row += 1
        
        ttk.Label(creds_frame, text="Jira Email:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.jira_email_entry = ttk.Entry(creds_frame, width=40)
        self.jira_email_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        if os.getenv('JIRA_EMAIL'):
            self.jira_email_entry.insert(0, os.getenv('JIRA_EMAIL'))
        row += 1
        
        ttk.Label(creds_frame, text="Jira API Token:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.jira_token_entry = ttk.Entry(creds_frame, width=40, show="*")
        self.jira_token_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        if os.getenv('JIRA_API_TOKEN'):
            self.jira_token_entry.insert(0, os.getenv('JIRA_API_TOKEN'))
        row += 1
        
        ttk.Label(creds_frame, text="Jira Project Key:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.jira_project_entry = ttk.Entry(creds_frame, width=40)
        self.jira_project_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        if os.getenv('JIRA_PROJECT_KEY'):
            self.jira_project_entry.insert(0, os.getenv('JIRA_PROJECT_KEY'))
        
        # === TAB 3: SETTINGS ===
        tab3.columnconfigure(0, weight=1)
        
        # Settings section
        settings_frame = ttk.LabelFrame(tab3, text="⚙️ Settings", padding="12", style='Section.TLabelframe')
        settings_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        settings_frame.columnconfigure(0, weight=1)
        
        self.enable_analysis_var = tk.BooleanVar(value=self.config_manager.config['enable_analysis'])
        ttk.Checkbutton(settings_frame, text="🤖 Enable AI Analysis", 
                       variable=self.enable_analysis_var).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        
        self.auto_create_tasks_var = tk.BooleanVar(value=self.config_manager.config['auto_create_tasks'])
        ttk.Checkbutton(settings_frame, text="✓ Auto-create Outlook Tasks (syncs to Microsoft To Do)", 
                       variable=self.auto_create_tasks_var).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        
        self.auto_send_webex_var = tk.BooleanVar(value=self.config_manager.config['auto_send_to_webex'])
        ttk.Checkbutton(settings_frame, text="📤 Auto-send to Webex Bot (Producto)", 
                       variable=self.auto_send_webex_var).grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(settings_frame, text="Bot Recipient Email:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.bot_recipient_entry = ttk.Entry(settings_frame, width=60)
        bot_recipient = self.config_manager.config.get('bot_recipient_email', 'qschalle@cisco.com')
        self.bot_recipient_entry.insert(0, bot_recipient)
        self.bot_recipient_entry.grid(row=4, column=0, sticky=(tk.W, tk.E), padx=5, pady=2)
        
        ttk.Label(settings_frame, text="Output Directory:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        self.output_entry = ttk.Entry(settings_frame, width=60)
        self.output_entry.insert(0, self.config_manager.config['output_directory'])
        self.output_entry.grid(row=6, column=0, sticky=(tk.W, tk.E), padx=5, pady=2)
        
        # === TAB 4: ACTIVITY LOG ===
        tab4.columnconfigure(0, weight=1)
        tab4.rowconfigure(0, weight=1)
        
        # Activity log - Full tab dedicated to log
        log_frame = ttk.LabelFrame(tab4, text="📋 Activity Log", padding="12", style='Section.TLabelframe')
        log_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Make log area prominent with white background for better readability
        self.log_text = scrolledtext.ScrolledText(log_frame, 
                                                  font=('Consolas', 9), wrap=tk.WORD,
                                                  bg='white', fg='#2C3E50',
                                                  relief='sunken', borderwidth=2)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=2, pady=2)
        
        # Initial log
        self.log("=" * 80)
        self.log("🎯 Producto - Meeting Intelligence Assistant v2.0")
        self.log("=" * 80)
        self.log(f"Config directory: {self.config_manager.config_dir}")
        self.log(f"Email pattern: '{self.config_manager.config['email_subject_pattern']}'")
        self.log(f"Polling interval: {self.config_manager.config['polling_interval_seconds']}s")
        self.log(f"Processing delay: {self.config_manager.config['processing_delay_seconds']}s")
        
        # DEBUG: Environment variables status
        self.log("=== Environment Variable Debug ===")
        webex_token = os.getenv('WEBEX_ACCESS_TOKEN')
        self.log(f"WEBEX_ACCESS_TOKEN: {'SET (length: ' + str(len(webex_token)) + ')' if webex_token else 'NOT SET'}")
        bot_token = os.getenv('WEBEX_BOT_TOKEN')
        self.log(f"WEBEX_BOT_TOKEN: {'SET (length: ' + str(len(bot_token)) + ')' if bot_token else 'NOT SET'}")
        self.log(f"CHATAI_CLIENT_ID: {'SET' if os.getenv('CHATAI_CLIENT_ID') else 'NOT SET'}")
        self.log(f"CHATAI_CLIENT_SECRET: {'SET' if os.getenv('CHATAI_CLIENT_SECRET') else 'NOT SET'}")
        self.log(f"CHATAI_APP_KEY: {'SET' if os.getenv('CHATAI_APP_KEY') else 'NOT SET'}")
        self.log(f"JIRA_URL: {'SET' if os.getenv('JIRA_URL') else 'NOT SET'}")
        self.log(f"JIRA_EMAIL: {'SET' if os.getenv('JIRA_EMAIL') else 'NOT SET'}")
        self.log(f"JIRA_API_TOKEN: {'SET' if os.getenv('JIRA_API_TOKEN') else 'NOT SET'}")
        self.log(f"JIRA_PROJECT_KEY: {'SET' if os.getenv('JIRA_PROJECT_KEY') else 'NOT SET'}")
        self.log("==================================")
        
        self.log("Ready to connect to Outlook...")
        
    def log(self, message):
        """Add message to log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def auto_connect_outlook(self):
        """Auto-connect to Outlook on startup"""
        self.connect_outlook()
    
    def connect_outlook(self):
        """Connect to Outlook"""
        self.log("Connecting to Outlook...")
        
        try:
            try:
                pythoncom.CoInitialize()
            except:
                pass
            
            self.outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = self.outlook.GetNamespace("MAPI")
            inbox = namespace.GetDefaultFolder(6)
            
            self.log(f"✓ Connected to Outlook! ({inbox.Items.Count} items in Inbox)")
            
            self.auth_status_label.config(text="Connected ✓", foreground="#00875A")  # Cisco green
            self.auth_button.config(text="Reconnect")
            self.start_monitor_button.config(state="normal")
            
        except Exception as e:
            self.log(f"✗ Failed to connect: {str(e)}")
            messagebox.showerror("Connection Error", f"Failed to connect to Outlook.\n\n{str(e)}")
    
    def start_monitoring(self):
        """Start email monitoring"""
        folder_name = self.folder_entry.get().strip()
        if not folder_name:
            messagebox.showerror("Error", "Please specify a folder to monitor")
            return
        
        # Save config
        self.config_manager.config['monitored_folder'] = folder_name
        self.config_manager.config['enable_analysis'] = self.enable_analysis_var.get()
        self.config_manager.config['auto_create_tasks'] = self.auto_create_tasks_var.get()
        self.config_manager.config['auto_send_to_webex'] = self.auto_send_webex_var.get()
        self.config_manager.config['bot_recipient_email'] = self.bot_recipient_entry.get()
        self.config_manager.config['output_directory'] = self.output_entry.get()
        self.config_manager.save_config()
        
        # Create email monitor
        self.email_monitor = EmailMonitor(
            config_manager=self.config_manager,
            log_callback=self.log,
            approval_callback=self.request_approval,
            process_callback=self.process_approved_email
        )
        
        # Start monitoring
        if self.email_monitor.start_monitoring():
            self.monitoring_status_label.config(text="🟢 Active", foreground="#00875A")  # Cisco green
            self.start_monitor_button.config(state="disabled")
            self.stop_monitor_button.config(state="normal")
            self.folder_entry.config(state="disabled")
            self.log(f"▶ Started monitoring folder: '{folder_name}'")
        else:
            self.log("✗ Failed to start monitoring")
    
    def stop_monitoring(self):
        """Stop email monitoring"""
        if self.email_monitor:
            self.email_monitor.stop_monitoring()
            self.email_monitor = None
        
        self.monitoring_status_label.config(text="⚫ Stopped", foreground="#E8112D")  # Cisco red
        self.start_monitor_button.config(state="normal")
        self.stop_monitor_button.config(state="disabled")
        self.folder_entry.config(state="normal")
        self.log("⏸ Monitoring stopped")
    
    def clear_processing_history(self):
        """Clear the list of processed/ignored emails"""
        # Confirm with user
        result = messagebox.askyesno(
            "Clear History",
            "This will clear the list of processed and ignored emails.\n\n"
            "All emails in the monitored folder will be considered 'new' again.\n\n"
            "Continue?",
            icon='warning'
        )
        
        if not result:
            return
        
        # Clear the lists
        processed_count = len(self.config_manager.config['processed_emails'])
        ignored_count = len(self.config_manager.config['ignored_emails'])
        
        self.config_manager.config['processed_emails'] = []
        self.config_manager.config['ignored_emails'] = []
        self.config_manager.save_config()
        
        self.log("=" * 60)
        self.log("🗑️ Processing history cleared!")
        self.log(f"   Removed {processed_count} processed emails")
        self.log(f"   Removed {ignored_count} ignored emails")
        self.log("   All emails will be considered 'new' on next poll")
        self.log("=" * 60)
        
        messagebox.showinfo(
            "History Cleared",
            f"Successfully cleared history:\n\n"
            f"• {processed_count} processed emails\n"
            f"• {ignored_count} ignored emails\n\n"
            f"Emails will be reprocessed on next poll."
        )
    
    def request_approval(self, email_data):
        """Request user approval for processing email"""
        return ApprovalDialog.show(self.root, email_data, timeout=300)
    
    def process_approved_email(self, email_data):
        """Process an approved email - full pipeline"""
        # Initialize COM for this thread
        pythoncom.CoInitialize()
        
        try:
            subject = email_data['subject']
            body = email_data['body']
            
            self.log(f"▶ Processing: {subject[:60]}...")
            
            # Extract Webex info
            webex_info = self.extract_webex_info_from_body(subject, body)
            
            # Check if transcript is embedded in email (no recording URL)
            has_embedded_transcript = self.check_for_embedded_transcript(body)
            
            if not webex_info and not has_embedded_transcript:
                self.log("  ✗ No Webex URL or embedded transcript found")
                self.config_manager.add_processed_email(email_data['entry_id'])
                return
            
            # Handle transcript-only emails (no recording)
            if not webex_info and has_embedded_transcript:
                self.log("  ℹ️ This is a transcript-only meeting (no recording)")
                self.process_transcript_only_email(email_data, subject, body)
                return
            
            # Download VTT using Webex Access Token
            output_dir = self.output_entry.get()
            os.makedirs(output_dir, exist_ok=True)
            
            # Get Webex access token from UI entry
            webex_access_token = self.webex_token_entry.get()
            
            if not webex_access_token:
                self.log("  ✗ Webex Access Token not configured")
                self.log("     Set WEBEX_ACCESS_TOKEN environment variable")
                self.config_manager.add_processed_email(email_data['entry_id'])
                return
            
            vtt_file = self.download_vtt_from_webex(webex_info, output_dir, subject, webex_access_token)
            
            if not vtt_file or not vtt_file.endswith('.vtt'):
                self.log("  ✗ Could not download VTT")
                self.config_manager.add_processed_email(email_data['entry_id'])
                return
            
            self.log(f"  ✓ Downloaded VTT: {vtt_file}")
            
            # Analyze with AI
            if self.enable_analysis_var.get():
                analysis_result = self.analyze_vtt_file(output_dir, vtt_file, subject)
                
                if analysis_result:
                    analysis_file, analysis_text, structured_data = analysis_result
                    self.log("  ✓ AI analysis complete")
                    
                    # Create Outlook Tasks
                    if self.auto_create_tasks_var.get() and structured_data:
                        actions = structured_data.get('actions', [])
                        if actions:
                            tasks_integration = OutlookTasksIntegration(log_callback=self.log)
                            tasks_integration.create_tasks_from_actions(actions, subject)
                    
                    # Send to Webex bot
                    self.log(f"  Checking Webex bot integration...")
                    self.log(f"    Auto-send enabled: {self.auto_send_webex_var.get()}")
                    self.log(f"    Has structured data: {bool(structured_data)}")
                    
                    if self.auto_send_webex_var.get() and structured_data:
                        bot_token = self.bot_token_entry.get()
                        self.log(f"    Bot token configured: {bool(bot_token)}")
                        
                        if bot_token:
                            webex_integration = WebexBotIntegration(bot_token, log_callback=self.log)
                            recipient_email = self.config_manager.config.get('bot_recipient_email', 'qschalle@cisco.com')
                            webex_integration.send_analysis_summary(
                                structured_data, subject, webex_info.get('url', ''), recipient_email
                            )
                        else:
                            self.log("  ⚠️ Webex Bot Token not configured - skipping bot notification")
                    else:
                        if not self.auto_send_webex_var.get():
                            self.log("  ℹ️ Auto-send to Webex Bot is disabled (check Settings)")
                        if not structured_data:
                            self.log("  ℹ️ No structured data to send to bot")
                    
                    # Display analysis
                    self.root.after(0, lambda: self.display_analysis_summary(analysis_text, subject))
            
            # Mark as processed
            self.config_manager.add_processed_email(email_data['entry_id'])
            self.log(f"✓ Completed: {subject[:60]}")
        
        except Exception as e:
            self.log(f"✗ Error: {str(e)}")
            import traceback
            self.log(traceback.format_exc()[:300])
        
        finally:
            pythoncom.CoUninitialize()
    
    # ===== EXTRACTION & ANALYSIS METHODS (from MVP) =====
    
    def check_for_embedded_transcript(self, body):
        """Check if email mentions transcript (will fetch from Webex API)"""
        # Look for transcript indicators AND Webex meeting links
        transcript_indicators = [
            'transcript',
            'meeting notes',
            'conversation summary',
            'meeting summary',
            'closed captions',
            'captions'
        ]
        
        body_lower = body.lower()
        has_transcript_mention = any(indicator in body_lower for indicator in transcript_indicators)
        
        # Also check for Webex meeting links (not recording links)
        has_webex_link = 'webex.com/meet/' in body_lower or 'webex.com/m/' in body_lower
        
        return has_transcript_mention or has_webex_link
    
    def process_transcript_only_email(self, email_data, subject, body):
        """Process email that has transcript but no recording"""
        try:
            self.log("  Fetching transcript from Webex...")
            
            # Get Webex access token from UI entry
            webex_access_token = self.webex_token_entry.get()
            
            if not webex_access_token:
                self.log("  ✗ Webex Access Token not configured")
                self.log("     Set WEBEX_ACCESS_TOKEN environment variable")
                self.config_manager.add_processed_email(email_data['entry_id'])
                return
            
            # Extract meeting ID from email
            meeting_id = self.extract_meeting_id_from_email(body)
            if not meeting_id:
                self.log("  ✗ Could not extract meeting ID from email")
                # Fallback: try to extract from email body text
                self.log("  Attempting to extract transcript from email body as fallback...")
                soup = BeautifulSoup(body, 'html.parser')
                text = soup.get_text()
                transcript_text = self.extract_transcript_from_email_text(text)
                
                if not transcript_text or len(transcript_text) < 100:
                    self.log("  ✗ No transcript found in email body either")
                    self.config_manager.add_processed_email(email_data['entry_id'])
                    return
            else:
                # Fetch transcript from Webex API
                transcript_text = self.fetch_transcript_from_webex(meeting_id, webex_access_token)
                
                if not transcript_text:
                    self.log("  ✗ Could not fetch transcript from Webex API")
                    self.config_manager.add_processed_email(email_data['entry_id'])
                    return
            
            self.log(f"  ✓ Retrieved {len(transcript_text)} characters of transcript")
            
            # Save transcript as text file
            output_dir = self.output_entry.get()
            os.makedirs(output_dir, exist_ok=True)
            
            safe_title = re.sub(r'[^\w\s-]', '', subject)[:50]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            txt_filename = f"{safe_title}_{timestamp}_transcript.txt"
            txt_filepath = os.path.join(output_dir, txt_filename)
            
            with open(txt_filepath, 'w', encoding='utf-8') as f:
                f.write(f"Meeting: {subject}\n")
                f.write(f"Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                f.write(transcript_text)
            
            self.log(f"  ✓ Saved transcript: {txt_filename}")
            
            # Analyze with AI if enabled
            if self.enable_analysis_var.get():
                self.log("  Analyzing transcript with AI...")
                analysis_result = self.analyze_transcript_text(transcript_text, subject, output_dir, safe_title)
                
                if analysis_result:
                    analysis_text, structured_data = analysis_result
                    self.log("  ✓ AI analysis complete")
                    
                    # Create Outlook Tasks
                    if self.auto_create_tasks_var.get() and structured_data:
                        actions = structured_data.get('actions', [])
                        if actions:
                            from outlook_extractor_v2_integrations import OutlookTasksIntegration
                            tasks_integration = OutlookTasksIntegration(log_callback=self.log)
                            tasks_integration.create_tasks_from_actions(actions, subject)
                    
                    # Send to Webex bot
                    self.log(f"  Checking Webex bot integration...")
                    self.log(f"    Auto-send enabled: {self.auto_send_webex_var.get()}")
                    self.log(f"    Has structured data: {bool(structured_data)}")
                    
                    if self.auto_send_webex_var.get() and structured_data:
                        bot_token = self.bot_token_entry.get()
                        self.log(f"    Bot token configured: {bool(bot_token)}")
                        
                        if bot_token:
                            from outlook_extractor_v2_integrations import WebexBotIntegration
                            webex_integration = WebexBotIntegration(bot_token, log_callback=self.log)
                            recipient_email = self.config_manager.config.get('bot_recipient_email', 'qschalle@cisco.com')
                            webex_integration.send_analysis_summary(structured_data, subject, '', recipient_email)
                        else:
                            self.log("  ⚠️ Webex Bot Token not configured - skipping bot notification")
                    else:
                        if not self.auto_send_webex_var.get():
                            self.log("  ℹ️ Auto-send to Webex Bot is disabled (check Settings)")
                        if not structured_data:
                            self.log("  ℹ️ No structured data to send to bot")
                    
                    # Display analysis
                    self.root.after(0, lambda: self.display_analysis_summary(analysis_text, subject))
            
            # Mark as processed
            self.config_manager.add_processed_email(email_data['entry_id'])
            self.log(f"✓ Completed: {subject[:60]}")
            
        except Exception as e:
            self.log(f"  Error processing transcript: {str(e)}")
            self.config_manager.add_processed_email(email_data['entry_id'])
    
    def extract_meeting_id_from_email(self, body):
        """Extract Webex meeting ID from email body"""
        # Look for meeting ID patterns in the email
        # Pattern 1: Meeting number
        meeting_patterns = [
            r'Meeting\s+(?:number|ID|#)[\s:]+(\d{9,15})',
            r'meetingKey["\']?\s*[:=]\s*["\']?([a-f0-9]{32})',
            r'webex\.com/meet/([a-zA-Z0-9\-_]+)',
            r'webex\.com/m/([a-zA-Z0-9\-_]+)',
            r'meetingUUID["\']?\s*[:=]\s*["\']?([a-f0-9\-]{36})',
        ]
        
        for pattern in meeting_patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                meeting_id = match.group(1)
                self.log(f"  Found meeting ID: {meeting_id[:20]}...")
                return meeting_id
        
        return None
    
    def fetch_transcript_from_webex(self, meeting_id, access_token):
        """Fetch transcript from Webex API using meeting ID"""
        try:
            self.log(f"  Calling Webex Meetings API...")
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Try to get meeting details first
            # Note: Webex transcript API may require specific scopes
            # This is a simplified approach - may need adjustment based on actual API
            
            # Option 1: Try meetings API
            meetings_url = f'https://webexapis.com/v1/meetings/{meeting_id}'
            response = requests.get(meetings_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                meeting_data = response.json()
                self.log(f"  ✓ Got meeting details")
                
                # Check if transcript is available
                # Note: Actual field names may vary
                transcript_url = meeting_data.get('transcriptUrl') or meeting_data.get('transcript')
                
                if transcript_url:
                    self.log(f"  Downloading transcript...")
                    transcript_response = requests.get(transcript_url, headers=headers, timeout=60)
                    if transcript_response.status_code == 200:
                        return transcript_response.text
            
            # Option 2: Try recordings API to find transcript
            self.log(f"  Trying recordings API...")
            recordings_url = f'https://webexapis.com/v1/recordings'
            
            # Search for recordings with this meeting ID
            # This is similar to the VTT download logic
            now = datetime.now(timezone.utc)
            search_from = (now - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
            search_to = now.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            params = {'max': 100, 'from': search_from, 'to': search_to}
            response = requests.get(recordings_url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                recordings = response.json().get('items', [])
                self.log(f"  Found {len(recordings)} recordings")
                
                for rec in recordings:
                    # Try to match by meeting ID
                    if str(meeting_id) in str(rec.get('meetingId', '')):
                        rec_id = rec.get('id')
                        self.log(f"  Found matching recording: {rec_id}")
                        
                        # Get recording details
                        detail_url = f'https://webexapis.com/v1/recordings/{rec_id}'
                        detail_response = requests.get(detail_url, headers=headers, timeout=30)
                        
                        if detail_response.status_code == 200:
                            rec_full = detail_response.json()
                            links = rec_full.get('temporaryDirectDownloadLinks', {})
                            transcript_link = links.get('transcriptDownloadLink')
                            
                            if transcript_link:
                                self.log(f"  Downloading transcript...")
                                transcript_response = requests.get(transcript_link, timeout=60)
                                if transcript_response.status_code == 200:
                                    # Convert VTT to plain text
                                    return self.extract_text_from_vtt(transcript_response.text)
            
            self.log(f"  ✗ No transcript found via API")
            return None
            
        except Exception as e:
            self.log(f"  Error fetching transcript: {str(e)}")
            return None
    
    def extract_transcript_from_email_text(self, text):
        """Extract transcript content from email plain text (fallback)"""
        # Remove excessive whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Try to find where transcript starts
        # Common headers: "Transcript:", "Meeting Notes:", etc.
        transcript_start_idx = 0
        for idx, line in enumerate(lines):
            if any(marker in line.lower() for marker in ['transcript', 'meeting notes', 'conversation']):
                transcript_start_idx = idx + 1
                break
        
        # Take everything after the header
        transcript_lines = lines[transcript_start_idx:]
        
        # Filter out common email footer junk
        filtered_lines = []
        for line in transcript_lines:
            # Skip lines that are likely email metadata
            if any(skip in line.lower() for skip in [
                'unsubscribe', 'privacy', 'cisco.com', 'copyright',
                'do not reply', 'automatic message', 'webex teams'
            ]):
                continue
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def analyze_transcript_text(self, transcript_text, meeting_title, output_dir, safe_title):
        """Analyze transcript text using Chat AI (similar to VTT analysis)"""
        try:
            client_id = self.chatai_client_id_entry.get()
            client_secret = self.chatai_client_secret_entry.get()
            app_key = self.chatai_app_key_entry.get()
            
            if not all([client_id, client_secret, app_key]):
                self.log("  ✗ Chat AI credentials not configured")
                return None
            
            # Classify meeting
            from meeting_classifier_v2 import classify_meeting
            classification = classify_meeting(meeting_title, transcript_text)
            self.log(f"  📊 Meeting Classification: {classification.meeting_type.upper()}")
            self.log(f"     Refinement Score: {classification.refinement_score:.2f} | Action Score: {classification.action_score:.2f}")
            
            # Intelligent routing based on classification
            if classification.meeting_type == "refinement":
                self.log(f"  🎯 Routing: Stories → Jira (with approval)")
            elif classification.meeting_type == "general":
                self.log(f"  🎯 Routing: Actions → Outlook Tasks (automatic)")
            else:  # mixed
                self.log(f"  🎯 Routing: Stories → Jira | Actions → Outlook Tasks")
            
            # Get SSO token
            sso_url = 'https://id.cisco.com/oauth2/default/v1/token'
            credentials = f"{client_id}:{client_secret}"
            encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            
            sso_response = requests.post(
                sso_url,
                headers={
                    'Authorization': f'Basic {encoded}',
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                data='grant_type=client_credentials',
                timeout=30
            )
            
            if sso_response.status_code != 200:
                self.log(f"  ✗ SSO authentication failed")
                return None
            
            access_token = sso_response.json().get('access_token')
            
            # Build prompt
            from meeting_prompts_v2 import (
                SYSTEM_PROMPT,
                build_refinement_user_prompt,
                build_general_user_prompt,
                build_mixed_user_prompt
            )
            
            if classification.meeting_type == "refinement":
                user_prompt = build_refinement_user_prompt(meeting_title, transcript_text)
            elif classification.meeting_type == "general":
                user_prompt = build_general_user_prompt(meeting_title, transcript_text)
            else:
                user_prompt = build_mixed_user_prompt(meeting_title, transcript_text)
            
            # Call Chat AI
            chatai_response = requests.post(
                'https://chat-ai.cisco.com/openai/deployments/gemini-2.5-flash/chat/completions',
                headers={'Content-Type': 'application/json', 'api-key': access_token},
                json={
                    'messages': [
                        {'role': 'system', 'content': SYSTEM_PROMPT},
                        {'role': 'user', 'content': user_prompt}
                    ],
                    'temperature': 0.2,
                    'max_tokens': 8000,
                    'user': f'{{"appkey": "{app_key}"}}'
                },
                timeout=180
            )
            
            if chatai_response.status_code != 200:
                self.log(f"  ✗ Chat AI API failed")
                return None
            
            llm_output = chatai_response.json()['choices'][0]['message']['content']
            
            # Parse JSON
            structured_data = None
            try:
                json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', llm_output, re.DOTALL)
                json_str = json_match.group(1) if json_match else llm_output
                structured_data = json.loads(json_str)
                
                if 'stories' in structured_data:
                    self.log(f"     {len(structured_data['stories'])} stories")
                if 'actions' in structured_data:
                    self.log(f"     {len(structured_data['actions'])} actions")
            except:
                pass
            
            # Save analysis
            if structured_data:
                json_filepath = os.path.join(output_dir, f"{safe_title}_analysis.json")
                with open(json_filepath, 'w', encoding='utf-8') as f:
                    json.dump(structured_data, f, indent=2)
            
            analysis_text = f"Meeting: {meeting_title}\nType: {classification.meeting_type}\n\n"
            if structured_data:
                analysis_text += json.dumps(structured_data, indent=2)
            else:
                analysis_text += llm_output
            
            txt_filepath = os.path.join(output_dir, f"{safe_title}_analysis.txt")
            with open(txt_filepath, 'w', encoding='utf-8') as f:
                f.write(analysis_text)
            
            return (analysis_text, structured_data)
        
        except Exception as e:
            self.log(f"  Analysis error: {str(e)}")
            return None
    
    def extract_webex_info_from_body(self, subject, body):
        """Extract Webex URL and password from email"""
        self.log("  Extracting Webex info from email body...")
        
        soup = BeautifulSoup(body, 'html.parser')
        text = soup.get_text()
        
        # Log first 500 chars of body for debugging
        body_preview = body[:500] if body else "(empty)"
        self.log(f"  Body preview (first 500 chars): {body_preview[:200]}...")
        
        webex_patterns = [
            r'https://[\w\-]+\.webex\.com/[\w\-]+/ldr\.php?[^\s"<>]+',
            r'https://[\w\-]+\.webex\.com/[\w\-]+/lsr\.php?[^\s"<>]+',
            r'https://[\w\-]+\.webex\.com/webappng/sites/[\w\-]+/recording/[^\s"<>]+',
            r'https://[\w\-]+\.webex\.com/recordingservice/sites/[\w\-]+/recording/playback/[^\s"<>]+',
        ]
        
        meeting_url = None
        for idx, pattern in enumerate(webex_patterns):
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                meeting_url = match.group(0)
                self.log(f"  ✓ Found URL with pattern {idx+1}: {meeting_url[:80]}...")
                break
        
        if not meeting_url:
            self.log("  ✗ No Webex URL found in email body")
            self.log(f"  Searched {len(webex_patterns)} patterns")
            return None
        
        password_patterns = [
            r'Password[\s:]+([a-zA-Z0-9]+)',
            r'password[\s:]+([a-zA-Z0-9]+)',
            r'Recording password[\s:]+([a-zA-Z0-9]+)',
        ]
        
        password = None
        for pattern in password_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                password = match.group(1).strip()
                self.log(f"  ✓ Found password: {password[:3]}***")
                break
        
        if not password:
            self.log("  ⚠ No password found (may not be required)")
        
        return {'url': meeting_url, 'password': password}
    
    def download_vtt_from_webex(self, webex_info, output_dir, subject, access_token):
        """Download VTT from Webex API - simplified version"""
        try:
            recording_url = webex_info['url']
            normalized_title = self.normalize_title(subject)
            
            self.log(f"  Recording URL: {recording_url[:80]}...")
            self.log(f"  Normalized title: {normalized_title}")
            
            rcid = self.extract_recording_id(recording_url)
            if not rcid:
                self.log("  ✗ Could not extract recording ID from URL")
                return None
            
            self.log(f"  Recording ID: {rcid}")
            
            headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
            self.log(f"  Using token length: {len(access_token)}")
            
            # Search last 30 days
            now = datetime.now(timezone.utc)
            search_from = (now - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
            search_to = now.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            # List recordings
            list_url = 'https://webexapis.com/v1/recordings'
            params = {'max': 100, 'from': search_from, 'to': search_to}
            self.log(f"  Calling Webex API to list recordings...")
            response = requests.get(list_url, headers=headers, params=params, timeout=30)
            
            self.log(f"  API Response: {response.status_code}")
            
            if response.status_code != 200:
                self.log(f"  ✗ API Error: {response.text[:200]}")
                return None
            
            recordings = response.json().get('items', [])
            self.log(f"  Found {len(recordings)} recordings in last 30 days")
            
            # Find best match (simplified - just use title matching)
            best_match = None
            best_score = 0
            
            self.log(f"  Searching for match to: '{normalized_title}'")
            
            for rec in recordings:
                score = 0
                topic = rec.get('topic', '').lower()
                title_words = set(normalized_title.lower().split())
                topic_words = set(topic.split())
                
                # Score by word overlap
                overlap = len(title_words.intersection(topic_words))
                if overlap > best_score:
                    best_score = overlap
                    best_match = rec
                    self.log(f"    Better match: '{rec.get('topic', 'N/A')}' (score: {overlap})")
            
            if not best_match or best_score < 1:
                self.log(f"  ✗ No good match found (best score: {best_score})")
                if recordings:
                    self.log(f"    Available recordings: {[r.get('topic', 'N/A')[:40] for r in recordings[:3]]}")
                return None
            
            self.log(f"  ✓ Best match: '{best_match.get('topic', 'N/A')}' (score: {best_score})")
            
            # Get VTT download link
            rec_id = best_match.get('id')
            detail_url = f'https://webexapis.com/v1/recordings/{rec_id}'
            self.log(f"  Getting recording details...")
            detail_response = requests.get(detail_url, headers=headers, timeout=30)
            
            if detail_response.status_code != 200:
                self.log(f"  ✗ Failed to get recording details: {detail_response.status_code}")
                return None
            
            rec_full = detail_response.json()
            links = rec_full.get('temporaryDirectDownloadLinks', {})
            vtt_url = links.get('transcriptDownloadLink')
            
            if not vtt_url:
                self.log(f"  ✗ No transcript download link available")
                self.log(f"    Available links: {list(links.keys())}")
                return None
            
            self.log(f"  ✓ Found transcript link")
            
            # Download VTT
            self.log(f"  Downloading VTT file...")
            vtt_response = requests.get(vtt_url, timeout=60)
            if vtt_response.status_code != 200:
                self.log(f"  ✗ VTT download failed: {vtt_response.status_code}")
                return None
            
            self.log(f"  ✓ Downloaded {len(vtt_response.content)} bytes")
            
            # Save
            safe_title = re.sub(r'[^\w\s-]', '', normalized_title)[:50]
            filename = f"{safe_title}_{rec_id}.vtt"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(vtt_response.content)
            
            return filename
        
        except Exception as e:
            self.log(f"  Error downloading VTT: {str(e)}")
            return None
    
    def normalize_title(self, subject):
        """Clean up email subject"""
        if not subject:
            return "Untitled"
        
        prefixes = ["Fw:", "Re:", "FW:", "RE:", "Fwd:", "Webex:", "Recording:", 
                   "Recording of", "Recording available:", "Your Webex meeting content is available:"]
        
        title = subject.strip()
        for prefix in prefixes:
            if title.lower().startswith(prefix.lower()):
                title = title[len(prefix):].strip()
        
        return ' '.join(title.split()) if title else "Untitled"
    
    def extract_recording_id(self, url):
        """Extract recording ID from URL"""
        patterns = [r'RCID=([a-f0-9\-]+)', r'/recording/([a-f0-9\-]+)', 
                   r'recordingId=([a-f0-9\-]+)', r'/playback/([a-f0-9\-]+)']
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def analyze_vtt_file(self, output_dir, vtt_filename, meeting_title):
        """Analyze VTT with Chat AI - simplified"""
        try:
            client_id = self.chatai_client_id_entry.get()
            client_secret = self.chatai_client_secret_entry.get()
            app_key = self.chatai_app_key_entry.get()
            
            if not all([client_id, client_secret, app_key]):
                return None
            
            # Read VTT
            vtt_filepath = os.path.join(output_dir, vtt_filename)
            with open(vtt_filepath, 'r', encoding='utf-8') as f:
                vtt_content = f.read()
            
            transcript_text = self.extract_text_from_vtt(vtt_content)
            
            if len(transcript_text) < 50:
                return None
            
            # Classify
            classification = classify_meeting(meeting_title, transcript_text)
            self.log(f"  📊 Meeting Classification: {classification.meeting_type.upper()}")
            self.log(f"     Refinement Score: {classification.refinement_score:.2f} | Action Score: {classification.action_score:.2f}")
            
            # Intelligent routing based on classification
            if classification.meeting_type == "refinement":
                self.log(f"  🎯 Routing: Stories → Jira (with approval)")
            elif classification.meeting_type == "general":
                self.log(f"  🎯 Routing: Actions → Outlook Tasks (automatic)")
            else:  # mixed
                self.log(f"  🎯 Routing: Stories → Jira | Actions → Outlook Tasks")
            
            # Get SSO token
            sso_url = 'https://id.cisco.com/oauth2/default/v1/token'
            credentials = f"{client_id}:{client_secret}"
            encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            
            sso_response = requests.post(
                sso_url,
                headers={
                    'Authorization': f'Basic {encoded}',
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                data='grant_type=client_credentials',
                timeout=30
            )
            
            if sso_response.status_code != 200:
                return None
            
            access_token = sso_response.json().get('access_token')
            
            # Build prompt
            if classification.meeting_type == "refinement":
                user_prompt = build_refinement_user_prompt(meeting_title, transcript_text)
            elif classification.meeting_type == "general":
                user_prompt = build_general_user_prompt(meeting_title, transcript_text)
            else:
                user_prompt = build_mixed_user_prompt(meeting_title, transcript_text)
            
            # Call Chat AI
            chatai_response = requests.post(
                'https://chat-ai.cisco.com/openai/deployments/gemini-2.5-flash/chat/completions',
                headers={'Content-Type': 'application/json', 'api-key': access_token},
                json={
                    'messages': [
                        {'role': 'system', 'content': SYSTEM_PROMPT},
                        {'role': 'user', 'content': user_prompt}
                    ],
                    'temperature': 0.2,
                    'max_tokens': 8000,
                    'user': f'{{"appkey": "{app_key}"}}'
                },
                timeout=180
            )
            
            if chatai_response.status_code != 200:
                return None
            
            llm_output = chatai_response.json()['choices'][0]['message']['content']
            
            # Parse JSON
            structured_data = None
            try:
                json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', llm_output, re.DOTALL)
                json_str = json_match.group(1) if json_match else llm_output
                structured_data = json.loads(json_str)
                
                if 'stories' in structured_data:
                    self.log(f"     {len(structured_data['stories'])} stories")
                if 'actions' in structured_data:
                    self.log(f"     {len(structured_data['actions'])} actions")
            except:
                pass
            
            # Save files
            base_filename = vtt_filename.replace('.vtt', '')
            
            if structured_data:
                json_filepath = os.path.join(output_dir, f"{base_filename}_analysis.json")
                with open(json_filepath, 'w', encoding='utf-8') as f:
                    json.dump(structured_data, f, indent=2)
            
            analysis_text = f"Meeting: {meeting_title}\nType: {classification.meeting_type}\n\n"
            if structured_data:
                analysis_text += json.dumps(structured_data, indent=2)
            else:
                analysis_text += llm_output
            
            txt_filepath = os.path.join(output_dir, f"{base_filename}_analysis.txt")
            with open(txt_filepath, 'w', encoding='utf-8') as f:
                f.write(analysis_text)
            
            return (f"{base_filename}_analysis.txt", analysis_text, structured_data)
        
        except Exception as e:
            self.log(f"  Analysis error: {str(e)}")
            return None
    
    def extract_text_from_vtt(self, vtt_content):
        """Extract text from VTT"""
        lines = vtt_content.split('\n')
        text_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith('WEBVTT') or line.startswith('NOTE'):
                i += 1
                continue
            if '-->' in line:
                i += 1
                if i < len(lines):
                    text = lines[i].strip()
                    if text:
                        text_lines.append(text)
                continue
            i += 1
        
        return ' '.join(text_lines)
    
    def parse_jira_issues(self, analysis_text):
        """Parse the analysis text into individual Jira issues"""
        import re
        
        # Find all issue headers (with or without numbering)
        issue_pattern = r'###\s+(?:\d+\.\s+)?\[(STORY|TASK)\]'
        matches = list(re.finditer(issue_pattern, analysis_text))
        
        if not matches:
            # If no issues found, return the whole text as one issue
            return [analysis_text]
        
        issues = []
        for i, match in enumerate(matches):
            start = match.start()
            # End is either the start of the next issue or end of text
            end = matches[i + 1].start() if i + 1 < len(matches) else len(analysis_text)
            issue_text = analysis_text[start:end].strip()
            issues.append(issue_text)
        
        return issues
    
    def post_issues_to_jira(self, issue_vars, issue_texts, parent_window):
        """Post selected issues to Jira Cloud"""
        # Get selected issues
        selected_issues = [(text, idx) for idx, (var, text) in enumerate(zip(issue_vars, issue_texts)) if var.get()]
        
        if not selected_issues:
            messagebox.showwarning("No Selection", "Please select at least one issue to post to Jira.")
            return
        
        # Get Jira credentials from main window
        jira_url = self.jira_url_entry.get().strip()
        jira_email = self.jira_email_entry.get().strip()
        jira_token = self.jira_token_entry.get().strip()
        jira_project = self.jira_project_entry.get().strip()
        
        if not all([jira_url, jira_email, jira_token, jira_project]):
            messagebox.showerror("Missing Credentials", 
                               "Please fill in all Jira credentials:\n"
                               "- Jira URL (e.g., https://your-domain.atlassian.net)\n"
                               "- Jira Email\n"
                               "- Jira API Token\n"
                               "- Jira Project Key")
            return
        
        # Hardcoded custom field values
        custom_field_values = {}
        
        # Work Type (customfield_10106) - RTB
        default_work_type = os.getenv('JIRA_DEFAULT_WORK_TYPE', 'RTB')
        custom_field_values['customfield_10106'] = {'value': default_work_type}
        self.log(f"  Setting Work Type to: {default_work_type}")
        
        # Team field (customfield_10001)
        default_team_id = os.getenv('JIRA_DEFAULT_TEAM_ID', '75ed17b2-21c7-405b-8534-57a2517f0dba-334')
        custom_field_values['customfield_10001'] = default_team_id
        self.log(f"  Setting Team field to: {default_team_id}")
        
        # Confirm before posting
        if not messagebox.askyesno("Confirm Post", 
                                   f"Post {len(selected_issues)} issue(s) to Jira project '{jira_project}'?"):
            return
        
        # Create progress window
        progress_window = tk.Toplevel(parent_window)
        progress_window.title("Posting to Jira")
        progress_window.geometry("400x150")
        progress_window.transient(parent_window)
        
        ttk.Label(progress_window, text="Posting issues to Jira...", 
                 font=('Arial', 12)).pack(pady=20)
        progress_label = ttk.Label(progress_window, text="")
        progress_label.pack(pady=10)
        
        # Post issues in a thread
        def post_thread():
            import base64
            auth_string = f"{jira_email}:{jira_token}"
            auth_bytes = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
            
            headers = {
                'Authorization': f'Basic {auth_bytes}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            api_url = f"{jira_url.rstrip('/')}/rest/api/3/issue"
            
            success_count = 0
            failed_issues = []
            
            for idx, (issue_text, original_idx) in enumerate(selected_issues, 1):
                progress_label.config(text=f"Posting issue {idx}/{len(selected_issues)}...")
                progress_window.update()
                
                try:
                    # Parse issue
                    issue_data = self.parse_issue_for_jira(issue_text, jira_project, custom_field_values)
                    
                    # Post to Jira
                    response = requests.post(api_url, json=issue_data, headers=headers, timeout=30)
                    
                    if response.status_code == 201:
                        success_count += 1
                        issue_key = response.json().get('key', 'Unknown')
                        self.log(f"  ✅ Posted to Jira: {issue_key}")
                    else:
                        failed_issues.append(f"Issue {original_idx + 1}: {response.status_code} - {response.text[:100]}")
                        self.log(f"  ✗ Failed to post issue {original_idx + 1}: {response.status_code}")
                
                except Exception as e:
                    failed_issues.append(f"Issue {original_idx + 1}: {str(e)}")
                    self.log(f"  ✗ Error posting issue {original_idx + 1}: {str(e)}")
            
            # Close progress window
            progress_window.destroy()
            
            # Show results
            if success_count == len(selected_issues):
                messagebox.showinfo("Success", 
                                  f"Successfully posted all {success_count} issue(s) to Jira!")
            elif success_count > 0:
                messagebox.showwarning("Partial Success", 
                                      f"Posted {success_count}/{len(selected_issues)} issue(s).\n\n"
                                      f"Failed:\n" + "\n".join(failed_issues[:3]))
            else:
                messagebox.showerror("Failed", 
                                   f"Failed to post any issues.\n\n" + "\n".join(failed_issues[:3]))
        
        thread = threading.Thread(target=post_thread, daemon=True)
        thread.start()
    
    def parse_issue_for_jira(self, issue_text, project_key, custom_field_values=None):
        """Parse issue text and create Jira API payload"""
        import re
        
        # Extract issue type and title
        header_match = re.search(r'###\s+(?:\d+\.\s+)?\[(STORY|TASK)\]\s+(.+?)(?:\n|$)', issue_text)
        
        if not header_match:
            raise ValueError("Could not parse issue header")
        
        issue_type = header_match.group(1)
        title = header_match.group(2).strip()
        
        # Extract sections
        summary_match = re.search(r'\*\*Summary:\*\*\s*\n(.+?)(?:\n\n|\*\*)', issue_text, re.DOTALL)
        description_match = re.search(r'\*\*Description:\*\*\s*\n(.+?)(?:\n\n\*\*|$)', issue_text, re.DOTALL)
        acceptance_criteria_match = re.search(r'\*\*Acceptance Criteria:\*\*\s*\n(.+?)(?:\n\n\*\*|$)', issue_text, re.DOTALL)
        
        summary = summary_match.group(1).strip() if summary_match else title
        description = description_match.group(1).strip() if description_match else issue_text
        
        # Build Jira payload
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": title[:255],  # Jira has a 255 char limit
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": description[:32000]  # Jira description limit
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {"name": "Story" if issue_type == "STORY" else "Task"}
            }
        }
        
        # Add acceptance criteria if present (hardcoded field ID)
        if acceptance_criteria_match:
            acceptance_criteria = acceptance_criteria_match.group(1).strip()
            # Hardcoded: customfield_10107 is the Acceptance Criteria field
            acceptance_criteria_field = os.getenv('JIRA_ACCEPTANCE_CRITERIA_FIELD', 'customfield_10107')
            # Format as ADF (Atlassian Document Format) like description
            payload["fields"][acceptance_criteria_field] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": acceptance_criteria
                            }
                        ]
                    }
                ]
            }
            self.log(f"  Adding Acceptance Criteria to field: {acceptance_criteria_field}")
        
        # Add custom fields if provided (skip internal keys)
        if custom_field_values:
            for key, value in custom_field_values.items():
                if not key.startswith('__'):  # Skip internal tracking keys
                    payload["fields"][key] = value
        
        return payload
    
    def display_analysis_summary(self, analysis_text, meeting_title):
        """Display analysis with Jira issue selection UI"""
        # Create new window
        analysis_window = tk.Toplevel(self.root)
        analysis_window.title(f"Analysis - {meeting_title[:50]}")
        analysis_window.geometry("1200x800")
        
        # Main frame
        main_frame = ttk.Frame(analysis_window, padding="10", style='TFrame')
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        analysis_window.columnconfigure(0, weight=1)
        analysis_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text=f"📊 Generated Issues for Review", 
                                font=('Segoe UI', 14, 'bold'), style='Title.TLabel')
        title_label.grid(row=0, column=0, pady=10, sticky=tk.W)
        
        # Parse issues from analysis text
        issues = self.parse_jira_issues(analysis_text)
        
        # Selection controls frame
        controls_frame = ttk.Frame(main_frame, style='TFrame')
        controls_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Select All / Deselect All buttons
        def select_all():
            for var in issue_vars:
                var.set(True)
        
        def deselect_all():
            for var in issue_vars:
                var.set(False)
        
        ttk.Button(controls_frame, text="✓ Select All", command=select_all, style='Action.TButton').grid(row=0, column=0, padx=5)
        ttk.Button(controls_frame, text="✗ Deselect All", command=deselect_all, style='Action.TButton').grid(row=0, column=1, padx=5)
        ttk.Label(controls_frame, text=f"Total Issues: {len(issues)}", font=('Segoe UI', 10, 'bold')).grid(row=0, column=2, padx=20)
        
        # Scrollable frame for issues
        canvas = tk.Canvas(main_frame, bg='#F5F7FA', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='TFrame')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=2, column=1, sticky=(tk.N, tk.S))
        
        # Create checkbox and text for each issue
        issue_vars = []
        issue_texts = []
        
        for idx, issue in enumerate(issues):
            # Frame for each issue
            issue_frame = ttk.Frame(scrollable_frame, relief="solid", borderwidth=2, style='TFrame')
            issue_frame.grid(row=idx, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
            issue_frame.columnconfigure(1, weight=1)
            
            # Checkbox
            var = tk.BooleanVar(value=True)
            issue_vars.append(var)
            issue_texts.append(issue)
            
            checkbox = ttk.Checkbutton(issue_frame, variable=var, style='TCheckbutton')
            checkbox.grid(row=0, column=0, sticky=tk.N, padx=5, pady=5)
            
            # Issue text
            text_widget = tk.Text(issue_frame, wrap=tk.WORD, height=10, width=100,
                                 font=('Consolas', 9), bg='white', fg='#2C3E50',
                                 relief='sunken', borderwidth=2)
            text_widget.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
            text_widget.insert('1.0', issue)
            text_widget.config(state='disabled')
        
        # Button frame
        button_frame = ttk.Frame(main_frame, style='TFrame')
        button_frame.grid(row=3, column=0, pady=10)
        
        # Copy selected issues to clipboard
        def copy_selected():
            selected_issues = [text for var, text in zip(issue_vars, issue_texts) if var.get()]
            if not selected_issues:
                messagebox.showwarning("No Selection", "Please select at least one issue to copy.")
                return
            
            combined_text = "\n\n" + "="*80 + "\n\n"
            combined_text = combined_text.join(selected_issues)
            
            analysis_window.clipboard_clear()
            analysis_window.clipboard_append(combined_text)
            messagebox.showinfo("Copied", f"Copied {len(selected_issues)} selected issue(s) to clipboard!")
        
        copy_button = ttk.Button(button_frame, text="📋 Copy Selected", 
                                command=copy_selected, style='Action.TButton')
        copy_button.grid(row=0, column=0, padx=5)
        
        # Copy all button
        def copy_all():
            analysis_window.clipboard_clear()
            analysis_window.clipboard_append(analysis_text)
            messagebox.showinfo("Copied", "All issues copied to clipboard!")
        
        copy_all_button = ttk.Button(button_frame, text="📄 Copy All", 
                                     command=copy_all, style='Action.TButton')
        copy_all_button.grid(row=0, column=1, padx=5)
        
        # Post to Jira button
        def post_to_jira():
            self.post_issues_to_jira(issue_vars, issue_texts, analysis_window)
        
        post_jira_button = ttk.Button(button_frame, text="🚀 Post Selected to Jira", 
                                      command=post_to_jira, style='Action.TButton')
        post_jira_button.grid(row=0, column=2, padx=5)
        
        # Close button
        close_button = ttk.Button(button_frame, text="❌ Close", 
                                 command=analysis_window.destroy, style='Action.TButton')
        close_button.grid(row=0, column=3, padx=5)


def main():
    root = tk.Tk()
    app = OutlookWebexExtractorV2(root)
    root.mainloop()


if __name__ == "__main__":
    main()
