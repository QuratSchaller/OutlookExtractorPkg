"""
Producto V3 Configuration
Bundled credentials for packaged application
"""
import os
from token_store_v2 import TokenStore

class ProductoConfig:
    """
    Configuration management for Producto V3
    Handles both bundled credentials and per-user settings
    """
    
    # BUNDLED CREDENTIALS - These are compiled into the application
    # Replace with actual values before building the installer
    WEBEX_INTEGRATION_CLIENT_ID = os.getenv('WEBEX_INTEGRATION_CLIENT_ID', 'REPLACE_WITH_ACTUAL_CLIENT_ID')
    WEBEX_INTEGRATION_CLIENT_SECRET = os.getenv('WEBEX_INTEGRATION_CLIENT_SECRET', 'REPLACE_WITH_ACTUAL_CLIENT_SECRET')
    
    # Organization-wide credentials (can be bundled or loaded from env)
    # These will be automatically loaded and stored securely on first run
    _org_credentials_loaded = False
    
    @staticmethod
    def get_integration_credentials():
        """
        Get Webex Integration credentials (bundled with app)
        
        Returns:
            tuple: (client_id, client_secret)
        """
        return (
            ProductoConfig.WEBEX_INTEGRATION_CLIENT_ID,
            ProductoConfig.WEBEX_INTEGRATION_CLIENT_SECRET
        )
    
    @staticmethod
    def initialize_org_credentials():
        """
        Initialize organizational credentials on first run
        Checks in order:
        1. Windows Credential Manager (previously stored)
        2. Environment variables (first-time setup)
        3. Bundled defaults (if any)
        """
        if ProductoConfig._org_credentials_loaded:
            return  # Already initialized
        
        # Check if already in secure storage
        stored = TokenStore.get_org_credentials()
        has_stored = any([
            stored.get('webex_bot_token'),
            stored.get('chatai_client_id'),
            stored.get('chatai_client_secret'),
            stored.get('chatai_app_key')
        ])
        
        if has_stored:
            ProductoConfig._org_credentials_loaded = True
            return  # Already configured
        
        # Try loading from environment variables
        env_bot_token = os.getenv('WEBEX_BOT_TOKEN')
        env_chatai_id = os.getenv('CHATAI_CLIENT_ID')
        env_chatai_secret = os.getenv('CHATAI_CLIENT_SECRET')
        env_chatai_key = os.getenv('CHATAI_APP_KEY')
        
        # Save to secure storage if found
        if any([env_bot_token, env_chatai_id, env_chatai_secret, env_chatai_key]):
            TokenStore.save_org_credentials(
                webex_bot_token=env_bot_token,
                chatai_client_id=env_chatai_id,
                chatai_client_secret=env_chatai_secret,
                chatai_app_key=env_chatai_key
            )
            print("✓ Organizational credentials loaded from environment")
            ProductoConfig._org_credentials_loaded = True
    
    @staticmethod
    def get_org_credentials():
        """
        Get organizational credentials from secure storage
        
        Returns:
            dict: Organizational credentials
        """
        # Ensure initialized
        ProductoConfig.initialize_org_credentials()
        
        # Return from secure storage
        return TokenStore.get_org_credentials()
    
    @staticmethod
    def is_fully_configured():
        """
        Check if all required credentials are configured
        
        Returns:
            dict: Status of each credential type
        """
        integration_id, integration_secret = ProductoConfig.get_integration_credentials()
        org_creds = ProductoConfig.get_org_credentials()
        
        return {
            'webex_integration': bool(integration_id and integration_secret and 
                                     integration_id != 'REPLACE_WITH_ACTUAL_CLIENT_ID'),
            'webex_bot': bool(org_creds.get('webex_bot_token')),
            'chatai': all([
                org_creds.get('chatai_client_id'),
                org_creds.get('chatai_client_secret'),
                org_creds.get('chatai_app_key')
            ])
        }


# For V3 packaging: Update these before building
# Option 1: Set as environment variables during build
# Option 2: Replace these strings directly in this file before building
# Option 3: Use a build script to inject values

def print_config_status():
    """Helper to check configuration status"""
    print("=" * 60)
    print("Producto Configuration Status")
    print("=" * 60)
    print()
    
    client_id, client_secret = ProductoConfig.get_integration_credentials()
    print(f"Webex Integration Client ID: {client_id[:20] if client_id else '[NOT SET]'}...")
    print(f"Webex Integration Client Secret: {'[SET]' if client_secret else '[NOT SET]'}")
    print()
    
    status = ProductoConfig.is_fully_configured()
    print(f"Webex Integration: {'✓ Configured' if status['webex_integration'] else '✗ Not configured'}")
    print(f"Webex Bot Token: {'✓ Configured' if status['webex_bot'] else '✗ Not configured'}")
    print(f"Chat AI Credentials: {'✓ Configured' if status['chatai'] else '✗ Not configured'}")
    print()


if __name__ == "__main__":
    print_config_status()
