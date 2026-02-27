"""
Configuration Manager for Outlook VTT Extractor v2.0
Handles persistent storage of settings and state
"""

import json
import os
from datetime import datetime


class ConfigManager:
    """Manages application configuration and state persistence"""
    
    def __init__(self, config_dir=None):
        """Initialize config manager"""
        if config_dir:
            self.config_dir = config_dir
        else:
            # Default to %APPDATA%\OutlookVTTExtractor
            appdata = os.getenv('APPDATA')
            self.config_dir = os.path.join(appdata, 'OutlookVTTExtractor')
        
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_file = os.path.join(self.config_dir, 'config_v2.json')
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        default_config = {
            'monitored_folder': 'Inbox',
            'last_check_time': None,
            'processed_emails': [],
            'ignored_emails': [],
            'polling_interval_seconds': 60,  # 60 seconds for testing
            'processing_delay_seconds': 60,  # 60 seconds between emails
            'email_subject_pattern': 'Your Webex meeting content is available:',
            'monitoring_enabled': False,
            'output_directory': os.path.join(os.path.expanduser("~"), "Downloads", "Outlook Items to Issues", "vtt_files"),
            'auto_create_tasks': True,
            'auto_send_to_webex': True,
            'enable_analysis': True,
            'bot_recipient_email': 'qschalle@cisco.com'  # Configurable Webex bot recipient
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    default_config.update(loaded)
            except Exception as e:
                print(f"Error loading config: {e}")
        
        return default_config
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def add_processed_email(self, email_id):
        """Mark an email as processed"""
        if email_id not in self.config['processed_emails']:
            self.config['processed_emails'].append(email_id)
            self.save_config()
    
    def add_ignored_email(self, email_id):
        """Mark an email as ignored"""
        if email_id not in self.config['ignored_emails']:
            self.config['ignored_emails'].append(email_id)
            self.save_config()
    
    def is_email_handled(self, email_id):
        """Check if email was already processed or ignored"""
        return email_id in self.config['processed_emails'] or email_id in self.config['ignored_emails']
    
    def update_last_check_time(self):
        """Update the last check timestamp to now"""
        self.config['last_check_time'] = datetime.now().isoformat()
        self.save_config()
    
    def get_last_check_time(self):
        """Get last check time as datetime object"""
        if self.config['last_check_time']:
            return datetime.fromisoformat(self.config['last_check_time'])
        return None
    
    def save_oauth_tokens(self, access_token, expires_in):
        """Save OAuth access token with expiry time"""
        from datetime import timedelta
        
        expiry_time = (datetime.now() + timedelta(seconds=expires_in - 300)).isoformat()  # 5 min buffer
        self.config['webex_access_token'] = access_token
        self.config['token_expiry'] = expiry_time
        self.save_config()
    
    def get_oauth_token(self):
        """Get stored OAuth access token if still valid"""
        token = self.config.get('webex_access_token')
        expiry = self.config.get('token_expiry')
        
        if not token or not expiry:
            return None
        
        # Check if token is still valid
        expiry_time = datetime.fromisoformat(expiry)
        if datetime.now() >= expiry_time:
            return None  # Token expired
        
        return token
    
    def clear_oauth_token(self):
        """Clear stored OAuth token"""
        if 'webex_access_token' in self.config:
            del self.config['webex_access_token']
        if 'token_expiry' in self.config:
            del self.config['token_expiry']
        self.save_config()
