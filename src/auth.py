
import os
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/calendar'
]

CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token.json'

def authenticate_user():
    """
    Authenticates the user via OAuth 2.0 Desktop Flow.
    Returns None if running in cloud environment without credentials.
    Returns:
        google.oauth2.credentials.Credentials or None: The authenticated credentials.
    """
    creds = None

    # Check if running in Streamlit Cloud (no interactive auth possible)
    # In cloud, NEVER attempt interactive authentication
    try:
        import streamlit
        # If streamlit is imported in a runtime context, we're in cloud
        if hasattr(streamlit, 'runtime'):
            logger.warning("Running in Streamlit Cloud - OAuth disabled.")
            return None
    except:
        pass

    # Also check if client secret file is missing
    if not os.path.exists(CLIENT_SECRET_FILE):
        logger.warning("No client_secret.json found - OAuth disabled.")
        return None

    # 1. Check for cached token
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            logger.info("Found cached credentials in token.json")
        except Exception as e:
            logger.warning(f"Cached token is invalid, refreshing: {e}")
            creds = None

    # 2. Refresh or Login if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("Token expired, refreshing...")
                creds.refresh(Request())
            except Exception as e:
                logger.warning(f"Failed to refresh token: {e}. Initiating new login.")
                creds = None

        if not creds:
            logger.info("Initiating new browser login flow...")
            if not os.path.exists(CLIENT_SECRET_FILE):
                 raise FileNotFoundError(f"Missing {CLIENT_SECRET_FILE}. Please download OAuth Client ID JSON from Google Cloud Console.")

            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # 3. Save new credentials
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            logger.info("Saved new credentials to token.json")

    return creds

if __name__ == "__main__":
    # Test execution
    try:
        creds = authenticate_user()
        print("Successfully authenticated!")
    except Exception as e:
        print(f"Authentication Failed: {e}")
