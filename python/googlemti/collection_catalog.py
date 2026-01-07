'''
This is used to read and manipulate the MTI Books Collections Catalog Google Sheets
'''

from googlemti import gspread_client
from gspread_dataframe import get_as_dataframe
from datetime import datetime
import pandas as pd

lookup_tab          = None      #TODO: Move this out of the Archiver Updates google spreadsheet
lookup_df           = None  
catalog_tabsdf_dict = None
catalog_tabs_dict   = None
is_initialized      = False

def __init__():
    #We must use global keyword since we will be reassigning these
    global lookup_tab 
    global lookup_df 
    global catalog_tabsdf_dict
    global catalog_tabs_dict
    global is_initialized
    
    catalog_tabsdf_dict = {}
    catalog_tabs_dict = {}

    updates_sheet  = gspread_client.get_updater_actions_sheet()

    lookup_tab  = updates_sheet.worksheet("Lookup")
    lookup_df   = get_as_dataframe(lookup_tab, evaluate_formulas=True, dtype=str)
    lookup_df.fillna("", inplace=True)  # Fill NaN with empty strings for consistency

    is_initialized = True

# Get the catalog entry for the document with given Post Id
def get_catalog_entry_by_post_id(post_id):

    c_book_entry    = None
    c_row_num       = None
    coll_name       = None
    doct_name       = None  


    matches = lookup_df.columns[(lookup_df == post_id).any()]

    lookup_val = matches[0] if not matches.empty else None

    if (lookup_val is not None):
        (coll_name, doct_name) = tuple(lookup_val.split(":"))
        # Get the related catalog entry details
        (c_book_entry, c_row_num) = get_catalog_entry(post_id, coll_name, doct_name)
    
    return c_book_entry, c_row_num, coll_name, doct_name

# Get the catalog entry for the document with given Post Id for the collection
def get_catalog_entry(post_id, coll_name, doct_name):
    # Get the catalog DataFrame for the given collection and document type
    doct_df = get_catalog_df(coll_name, doct_name)
    
    # Filter the row where the 'Post Id' column matches
    matching_rows = doct_df[doct_df["Post ID"] == post_id]

    # Get the first match as a dict, or None if no match
    c_book_entry = matching_rows.iloc[0].to_dict() if not matching_rows.empty else None
    c_row_num = matching_rows.index[0]

    return c_book_entry, c_row_num

# Get the Goolge Catalog Tab for Document Type as a Dataframe. The tab is loaded
# as a dataframe to minimize calls to the gspread API
def get_catalog_df(coll_name, doct_name):
    doct_df = catalog_tabsdf_dict.get((coll_name, doct_name))
    if doct_df is None:
        catalog_sheet = gspread_client.get_catalog_sheet(coll_name)
        doct_tab = catalog_sheet.worksheet(doct_name)
        doct_df = get_as_dataframe(doct_tab, evaluate_formulas=True, dtype=str)
        doct_df.fillna("", inplace=True)  # Fill NaN with empty strings for consistency
        
        catalog_tabsdf_dict[(coll_name, doct_name)] = doct_df
        catalog_tabs_dict[(coll_name, doct_name)] = doct_tab

    return doct_df

def update_catalog_entry(c_book_entry, coll_name, doct_name, c_row_num):

    # Update catalog entry (first rearrange c_book_entry to align with header cols)
    doct_tab = catalog_tabs_dict.get((coll_name, doct_name))

    header = doct_tab.row_values(1)
    c_row_values = [c_book_entry.get(col, "") for col in header]        
    
    google_row_num = c_row_num + 2  # gspread is 1-indexed and has header row
    doct_tab.update(f"A{google_row_num}", [c_row_values])

    #Also update the datafrane
    doct_df = catalog_tabsdf_dict.get((coll_name, doct_name))
    doct_df.loc[c_row_num, c_book_entry.keys()] = pd.Series(c_book_entry)

