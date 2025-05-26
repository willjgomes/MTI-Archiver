from google.oauth2.service_account import Credentials

class MTIGoogleClient:

    def create_google_client(keyfile):
        # Authenticate using the Service Account JSON key file
        creds = Credentials.from_service_account_file(keyfile,
            scopes=["https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"]
        )

        return gspread.authorize(creds)