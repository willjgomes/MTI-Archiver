import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from mti.mti_config import MTIConfig, MTIDataKey, mticonfig
from pathlib import Path

def load_csv_files():   
    last_idx_gen_dt		= mticonfig.exe_details.get(MTIDataKey.LAST_IDX_GEN_FILE_DT)
    last_idx_load_dt	= mticonfig.exe_details.get(MTIDataKey.LAST_IDX_LOAD_FILE_DT)
    last_idx_run_dt     = mticonfig.exe_details.get(MTIDataKey.LAST_INDEXER_RUN_DT)
    
    if (last_idx_gen_dt and last_idx_gen_dt == last_idx_run_dt):
        last_idx_output_file = Path(mticonfig.output_dir + '/' + mticonfig.archive_key + '_' + last_idx_gen_dt + '_Index.csv')
        last_idx_error_file  = Path(mticonfig.output_dir + '/' + mticonfig.archive_key + '_' + last_idx_gen_dt + '_Index_Error.csv')
        last_idx_new_file  = Path(mticonfig.output_dir + '/' + mticonfig.archive_key + '_' + last_idx_gen_dt + '_Index_New.csv')
                
        print("Updating Google Sheet, please wait ...")

        # Get existing google sheet for collection
        spreadsheet = get_indexer_output_sheet()

        # If index was never loaded, load only the current index as new
        if (not last_idx_load_dt):
            tab_name    = mticonfig.doct_name + "-New"
            load_csv_file(spreadsheet, tab_name, last_idx_output_file)
        
        # If index was loaded, load the respective index and new files 
        # TODO: Remove the Index File, only do the new (will replace the Index File with the full inventory)
        else:
            #tab_name    = mticonfig.doct_name + "-Index"
            #load_csv_file(spreadsheet, tab_name, last_idx_output_file)
            tab_name    = mticonfig.doct_name + "-New"
            load_csv_file(spreadsheet, tab_name, last_idx_new_file)

        tab_name    = mticonfig.doct_name + "-Idx-Errors"
        load_csv_file(spreadsheet, tab_name, last_idx_error_file)

        update_summary_tab(spreadsheet, mticonfig.doct_name, last_idx_gen_dt)

        print(mticonfig.idtab, f"Index Date : {last_idx_gen_dt} (Verify in Google Sheets Summary Tab) ")
        print(f"Google Sheet successfully updated.")


def get_indexer_output_sheet():
    return get_sheet('Archiver Report: ' + mticonfig.coll_name)

def get_collection_sheet():
    return get_sheet('Catalog: ' + mticonfig.coll_name)

def get_sheet(spreadsheet_name):
    client              = create_google_client(mticonfig.ini['Google']['ServiceAccountKeyFile'])

    print(mticonfig.idtab, f"Sheet Name : {spreadsheet_name} ")
    
    # Open existing spreadsheet for collection if it exists
    try:
        spreadsheet = client.open(spreadsheet_name) 
    
    # Create new one if it doesn't exist 
    except gspread.exceptions.SpreadsheetNotFound:
        print(mticonfig.idtab, f"Existing sheet not found, creating new one.")

        folder_id = mticonfig.ini['Google']['SharedDriveFolderID']
        spreadsheet = client.create(spreadsheet_name, folder_id) 
        #spreadsheet.share('your-email@gmail.com', perm_type='user', role='writer')  # Share sheet with google user

    print(mticonfig.idtab, f"Sheet URL  : {spreadsheet.url} ")

    return spreadsheet

def create_google_client(keyfile):
    # Authenticate using the Service Account JSON key file
    creds = Credentials.from_service_account_file(keyfile,
        scopes=["https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"]
    )

    return gspread.authorize(creds)
    

def load_csv_file(sheet, tab, file, delimiter=","):
    # Load CSV File into Pandas DataFrame
    df = pd.read_csv(file, dtype=str, delimiter=delimiter)

    # Replace NaN values with an empty string
    df.fillna("", inplace=True) 

    # Convert DataFrame to List of Lists & Upload to Google Sheets
    data = [df.columns.tolist()] + df.values.tolist()

    # Try to get existing sheet tab
    try:
        sheet = sheet.worksheet(tab) 
        #sheet = spreadsheet.sheet1

    # Create tab if it doesn't exist
    except gspread.exceptions.WorksheetNotFound:
        sheet = sheet.add_worksheet(title=tab, rows="1000", cols="20")

    sheet.clear()
    sheet.update(data)

def update_summary_tab(sheet, doct_type, index_date):
    # Update in existing sheet
    try:
        summary_sheet = sheet.worksheet('Summary')         

        cell = summary_sheet.find(doct_type, in_column=1)  # Find cell containig data for doctype
        if (cell):
            summary_sheet.update(f"A{cell.row}",[[doct_type, index_date]])        
        else:
            summary_sheet.insert_row([doct_type, index_date],2)        
    # Create sheet with date
    except gspread.exceptions.WorksheetNotFound:
        summary_sheet = sheet.add_worksheet(title="Summary", rows="100", cols="10")
        summary_sheet.update("A1", [["Index Type", "Index Date"]])
        summary_sheet.update("A2",[[doct_type, index_date]])

def update_collection_sheet():
    #Get the load file dates
    last_google_load_dt = mticonfig.exe_details.get(MTIDataKey.LAST_GOOG_LOAD_FILE_DT)
    last_idx_load_dt    = mticonfig.exe_details.get(MTIDataKey.LAST_IDX_LOAD_FILE_DT)

    if (last_idx_load_dt and not last_google_load_dt==last_idx_load_dt):
        print("Updating Google Sheets ...")
        # Get existing collection sheet and fetch headers
        sheet = get_collection_sheet(mticonfig)
        try:
            sheet = sheet.worksheet(mticonfig.doct_name) 
        except gspread.exceptions.WorksheetNotFound:
            sheet = sheet.add_worksheet(title=mticonfig.doct_name, rows="1000", cols="20")

        # Load CSV file into a DataFrame
        load_file  = Path(mticonfig.output_dir + '/' + mticonfig.archive_key + '_' + last_idx_load_dt + '_Loaded.csv')
        df = pd.read_csv(load_file, delimiter="|", dtype=str)

        # Replace NaN values with an empty string
        df.fillna("", inplace=True) 

        headers = sheet.row_values(1)
        if (headers):
            # Add cmpty fields to data frame for columns that only exist in google sheet
            for col in headers:
                if col not in df.columns:
                    df[col] = ""  # Add missing columns as empty
        else:
            # Add header row to sheet using the data frame columns
            headers = df.columns.tolist()
            sheet.insert_row(headers)

        # Reorder DataFrame columns to match the sheet
        df = df[headers]  # This ensures correct column alignment

        # Convert DataFrame to list of lists
        data_to_append = df.values.tolist()

        # Append data to Google Sheet
        sheet.append_rows(data_to_append)

        # Upload Errors
        spreadsheet = get_indexer_output_sheet()
        tab_name    = mticonfig.doct_name + "-Load-Errors"
        load_error_file  = Path(mticonfig.output_dir + '/' + mticonfig.archive_key + '_' + last_idx_load_dt + '_Load_Error.csv')
        load_csv_file(spreadsheet, tab_name, load_error_file, delimiter="|")

        print("Updates complete.")

        mticonfig.exe_details[MTIDataKey.LAST_GOOG_LOAD_FILE_DT]  = last_idx_load_dt
        mticonfig.save_archiver_data()



    