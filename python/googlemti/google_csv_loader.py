import gspread
import pandas as pd
from mti.mti_config import MTIDataKey, mticonfig
from googlemti import gspread_client, google_util
from pathlib import Path

def load_csv_files():   
    last_idx_gen_dt		= mticonfig.exe_details.get(MTIDataKey.LAST_IDX_GEN_FILE_DT)
    last_idx_load_dt	= mticonfig.exe_details.get(MTIDataKey.LAST_IDX_LOAD_FILE_DT)
    last_idx_run_dt     = mticonfig.exe_details.get(MTIDataKey.LAST_INDEXER_RUN_DT)
    
    if (last_idx_gen_dt and last_idx_gen_dt == last_idx_run_dt):
        # Get file paths based on last index generated date
        file_prefix = f'{mticonfig.output_dir}/{mticonfig.archive_key}_{last_idx_gen_dt}'
        last_idx_output_file = Path(file_prefix + '_Index.csv')
        last_idx_error_file  = Path(file_prefix + '_Index_Error.csv')
        last_idx_new_file    = Path(file_prefix + '_Index_New.csv')
                
        print("Updating Google Sheet, please wait ...")

        # Get existing google sheet for collection
        spreadsheet = gspread_client.get_archiver_report_sheet()

        # If index was never loaded, load only the current index as new
        if (not last_idx_load_dt):
            tab_name    = mticonfig.doct_name + "-New"
            load_csv_file(spreadsheet, tab_name, last_idx_output_file)
        
        # If index was loaded, load the respective index and new files 
        # TODO: Remove the Index File, only do the new 
        # (will replace the Index File with the full inventory)
        else:
            #tab_name    = mticonfig.doct_name + "-Index"
            #load_csv_file(spreadsheet, tab_name, last_idx_output_file)
            tab_name    = mticonfig.doct_name + "-New"
            load_csv_file(spreadsheet, tab_name, last_idx_new_file)

        tab_name    = mticonfig.doct_name + "-Idx-Errors"
        load_csv_file(spreadsheet, tab_name, last_idx_error_file)

        update_summary_tab(spreadsheet, mticonfig.doct_name, last_idx_gen_dt)

        print(mticonfig.idtab, 
              f"Index Date : {last_idx_gen_dt} (Verify in Google Sheets Summary Tab) ")
        print(f"Google Sheet successfully updated.")

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

        # Find cell containig data for doctype
        cell = summary_sheet.find(doct_type, in_column=1)  
        if (cell):
            summary_sheet.update(f"A{cell.row}",[[doct_type, index_date]])        
        else:
            summary_sheet.insert_row([doct_type, index_date],2)        
    # Create sheet with date
    except gspread.exceptions.WorksheetNotFound:
        summary_sheet = sheet.add_worksheet(title="Summary", rows="100", cols="10")
        summary_sheet.update("A1", [["Index Type", "Index Date"]])
        summary_sheet.update("A2",[[doct_type, index_date]])

def update_catalog_sheet():
    #Get the load file dates
    last_google_load_dt = mticonfig.exe_details.get(MTIDataKey.LAST_GOOG_LOAD_FILE_DT)
    last_idx_load_dt    = mticonfig.exe_details.get(MTIDataKey.LAST_IDX_LOAD_FILE_DT)

    if (last_idx_load_dt and not last_google_load_dt==last_idx_load_dt):
        print("Updating Google Sheets ...")
        # Get existing collection sheet and fetch headers
        sheet = gspread_client.get_catalog_sheet()
        try:
            sheet = sheet.worksheet(mticonfig.doct_name) 
        except gspread.exceptions.WorksheetNotFound:
            sheet = sheet.add_worksheet(title=mticonfig.doct_name, rows="1000", cols="20")

        load_file_prefix = f'{mticonfig.output_dir}/{mticonfig.archive_key}_{last_idx_load_dt}'
        
        # Load CSV file into a DataFrame
        load_file  = Path( load_file_prefix + '_Loaded.csv')
        df = pd.read_csv(load_file, delimiter="|", dtype=str)

        # Convert dataframe to be able to load into sheet
        sheet_rows =  google_util.convert_df_to_sheet_rows(df, sheet)

        # Append data to Google Sheet
        sheet.append_rows(sheet_rows)

        # Upload Errors
        spreadsheet = gspread_client.get_archiver_report_sheet()
        tab_name    = mticonfig.doct_name + "-Load-Errors"
        load_error_file  = Path(load_file_prefix + '_Load_Error.csv')
        load_csv_file(spreadsheet, tab_name, load_error_file, delimiter="|")

        print("Updates complete.")

        mticonfig.exe_details[MTIDataKey.LAST_GOOG_LOAD_FILE_DT]  = last_idx_load_dt
        mticonfig.save_archiver_data()



    