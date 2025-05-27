import gspread
from google.oauth2.service_account import Credentials
from mti.mti_config import mticonfig

def get_gspread_client():
    keyfile = mticonfig.ini['Google']['ServiceAccountKeyFile']

    # Authenticate using the Service Account JSON key file
    creds = Credentials.from_service_account_file(keyfile,
        scopes=["https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"]
    )

    return gspread.authorize(creds)