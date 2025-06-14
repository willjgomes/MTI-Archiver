# This will read a google sheet of update actions, such as Rename Title

from titlecase import titlecase
from googlemti import gspread_client
from mti.mti_config import MTIDataKey, mticonfig
from wordpressmti.wbg_book_post import *
from datetime import datetime
import os

def get_updater_actions_sheet():
    return gspread_client.get_sheet('Archiver Updates')
 
wbgclient = None
actions_tab = None
lookup_tab  = None
history_tab = None
errors_tab  = None

def __init__():
    # Get the Wordpress Books Gallery (WBG) client
    global wbgclient
    global actions_tab 
    global lookup_tab  
    global history_tab 
    global errors_tab  

    wbgclient = get_wbg_client()
    
    updates_sheet  = get_updater_actions_sheet()
    actions_tab    = updates_sheet.worksheet("Update Actions")
    lookup_tab     = updates_sheet.worksheet("Lookup")
    history_tab    = updates_sheet.worksheet("Update History")
    errors_tab     = updates_sheet.worksheet("Update Errors")

def start():
    print("Updating started")
    print("================")

    if (wbgclient == None):
        __init__()
   
    rows = actions_tab.get_all_values()
    for row in rows[1:]:            
        post_id = row[0]
        action = row[1]
        value = row[2]

        history_row = [post_id, action, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]

        # Find the Archive (Collection & Document Type) so we can get the 
        # details from the Catalog sheet
        cell = lookup_tab.find(post_id)
        lookup_val = lookup_tab.cell(1, cell.col).value
        (coll_name, doct_name) = tuple(lookup_val.split(":"))
        
        # Get the related catalog entry details
        catalog_sheet = gspread_client.get_catalog_sheet(coll_name)
        doct_tab = catalog_sheet.worksheet(doct_name)
        book_cell = doct_tab.find(post_id)       
        c_book_entry = gspread_client.get_row_as_dict(doct_tab, book_cell.row)

        # Process the action
        w_book = wbgclient.get_book(post_id)
        if not w_book:
            print(f"Post ID {post_id} not found in the current collection.")
        else :
            if action == "Rename Title":                    
                process_rename_action(w_book, c_book_entry, doct_name[0:-1], value, history_row)
            else:
                print(f"Unknown action '{action}' for post ID {post_id}. Skipping.")

        history_tab.insert_row(history_row, 2)   
        actions_tab.delete_rows(2)

        # Update catalog entry
        header = doct_tab.row_values(1)
        c_row_values = [c_book_entry.get(col, "") for col in header]
        doct_tab.update(f"A{book_cell.row}", [c_row_values])
    
def process_rename_action(w_book, c_book_entry, doct_name, new_title, history_row):
    old_title = c_book_entry[f"{doct_name} Title"]
    new_title = titlecase(new_title.strip())

    history_row.append('Old Title: ' + old_title)
    history_row.append('New Title: ' + new_title)

    # Get the old files from catalog entry
    old_book_file   = c_book_entry[f"{doct_name} File"]
    old_cover_file  = c_book_entry[f"{doct_name} Cover File"]

    # Get the folder paths from catalog entry
    w_book.folder       = c_book_entry.get("Author Folder")
    w_book.base_path    = c_book_entry.get("Base Path")

    # Rename book file using new title
    w_book.file = process_book_file(w_book, old_book_file, old_title, new_title)
    
    # Rename cover file using new title
    w_book.cover_file = process_cover_file(w_book, old_cover_file, old_title, new_title)
    
    # Capture the new itle
    w_book.title        = new_title
    
    # Reset author to None to prevent overriding since retrieve not working
    w_book.author       = None    

    # Update WordPress with new book details
    wbgclient.create_book(w_book, uploadPDF=True, post_id=w_book.post_id)

    # Update the catalog entry fields with new book details
    c_book_entry[f"{doct_name} Title"]      = w_book.title
    c_book_entry[f"{doct_name} File"]       = w_book.file
    c_book_entry[f"{doct_name} Cover File"] = w_book.cover_file
    c_book_entry['WBG Update Date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def process_book_file(w_book, old_file, old_title, new_title):
    return process_file(w_book.base_path, w_book.folder, old_file, 
                        old_title, new_title, w_book.file_id)

def process_cover_file(w_book, old_file, old_title, new_title):
    return process_file(w_book.base_path, w_book.folder, old_file, 
                        old_title, new_title, w_book.cover_file_id)

def process_file(base, folder, old_file, old_title, new_title, media_id):
    new_file = old_file.replace(old_title.replace(" ","-"), new_title.replace(" ","-"))
    
    os.rename(os.path.join(base, folder, old_file), os.path.join(base, folder, new_file))
    print(f"Renamed file: {old_file} -> {new_file}")

    wbgclient.delete_media(media_id)
    print("Deleted old file from WordPress:", media_id)

    return new_file
    





