import gspread
from google.oauth2.service_account import Credentials
from mti.mti_config import mticonfig

#TODO: Is this best way to create a singleton client?
# Global variable to hold the gspread client instance
_gs_spread_client = None

def get_gspread_client():
    global _gs_spread_client
    if (_gs_spread_client == None):

        keyfile = mticonfig.ini['Google']['ServiceAccountKeyFile']

        # Authenticate using the Service Account JSON key file
        creds = Credentials.from_service_account_file(keyfile,
            scopes=["https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"]
        )

        _gs_spread_client = gspread.authorize(creds)

    return _gs_spread_client

def get_sheet(spreadsheet_name, info_log=True):
    client = get_gspread_client()

    if info_log:
        print(mticonfig.idtab, f"Sheet Name : {spreadsheet_name} ")
    
    # Open existing spreadsheet if it exists
    try:
        spreadsheet = client.open(spreadsheet_name) 
    
    # Create new one if it doesn't exist 
    except gspread.exceptions.SpreadsheetNotFound:
        print(mticonfig.idtab, f"Existing sheet not found, creating new one.")

        folder_id = mticonfig.ini['Google']['SharedDriveFolderID']
        spreadsheet = client.create(spreadsheet_name, folder_id) 

        # Share sheet with google user
        #spreadsheet.share('your-email@gmail.com', perm_type='user', role='writer')  

    if info_log:
        print(mticonfig.idtab, f"Sheet URL  : {spreadsheet.url} ")

    return spreadsheet  

def get_updater_actions_sheet(info_log=True):
    return get_sheet('Archiver Updates', info_log=info_log)

def get_archiver_report_sheet(coll_name=None):
    if coll_name is None:
        coll_name = mticonfig.coll_name        
    """
    Function to get the Archiver Report Sheet for the given collection

    Args:
        coll_name (str): Name of the collection, defaults to mticonfig.coll_name
    """
    return get_sheet('Archiver Report: ' + coll_name)

def get_catalog_sheet(coll_name=None, info_log=True):
    if coll_name is None:
        coll_name = mticonfig.coll_name
    return get_sheet('Catalog: ' + coll_name, info_log=info_log) 

def get_row_as_dict(worksheet, row_number):
        header = worksheet.row_values(1)
        row = worksheet.row_values(row_number)
        return dict(zip(header, row))
