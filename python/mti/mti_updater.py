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
            process_file_update(action, w_book, c_book_entry, doct_name[0:-1], value, history_row)

        history_tab.insert_row(history_row, 2)   
        actions_tab.delete_rows(2)

        # Update catalog entry (first rearrange c_book_entry to align with header cols)
        header = doct_tab.row_values(1)
        c_row_values = [c_book_entry.get(col, "") for col in header]        
        doct_tab.update(f"A{book_cell.row}", [c_row_values])

# This Processs the update value for update and sets the w_book field accordingly
# based on update type. It also returns the part of the filename to replace as 
# (old, new)  tuple for later file renaming.
def process_update_value(u_type, w_book, c_book_entry, doct_name, value, history_row):
    if u_type == "Rename Title":
        old_title = c_book_entry[f"{doct_name} Title"]
        new_title = titlecase(value.strip())

        history_row.append('Old Title: ' + old_title)
        history_row.append('New Title: ' + new_title)

        # Capture the new title
        w_book.title =  c_book_entry[f"{doct_name} Title"] = new_title

        # Return the old and new title as the file part to replace
        return (old_title, new_title)
    
    elif u_type == "Update Author":
        firstname, middlename, lastname = (
            name_part.strip() for name_part in value.strip().split("|")
        )

        old_author = WPGBook.get_author(c_book_entry["First Name"],
                                        c_book_entry["Middle Name"],
                                        c_book_entry["Last Name"])
        new_author = WPGBook.get_author(firstname, middlename, lastname)

        history_row.append('Old Author: ' + old_author)
        history_row.append('New Author: ' + new_author)

        # Capture the author
        w_book.author = new_author
        c_book_entry["First Name"] = firstname
        c_book_entry["Middle Name"] = middlename
        c_book_entry["Last Name"] = lastname            

        # Get the new and old author parts of filename
        old_file = c_book_entry[f"{doct_name} File"]
        old_author_part = old_file.split("_")[-1].replace(".pdf", "")
        if (len(middlename) > 0):        
            new_author_part = f"{firstname[0].upper()}.{middlename[0].upper()}.-{lastname}"
        else:
            new_author_part = f"{firstname[0].upper()}.-{lastname}"
    
        return(old_author_part, new_author_part)

    else:
        print(f"Unknown action '{u_type}' for post ID {w_book.post_id}. Skipping.")



# This is used to process any update to a document that requires modifying the actual 
# name of the file (eg. title, author, publication, publication date)
def process_file_update(u_type, w_book, c_book_entry, doct_name, value, history_row):
    
    # Determine the old and new file parts to replace based on the update type and
    # update the respective w_book field for the update with the new value
    (old_f_part, new_f_Part) = process_update_value(
        u_type, w_book, c_book_entry, doct_name, value, history_row)

    # Get the old files from catalog entry
    old_book_file   = c_book_entry[f"{doct_name} File"]
    old_cover_file  = c_book_entry[f"{doct_name} Cover File"]

    # Get the existing folder paths from catalog entry
    w_book.folder       = c_book_entry.get("Author Folder")
    w_book.base_path    = c_book_entry.get("Base Path")

    # Rename book file and update using new value
    w_book.file = c_book_entry[f"{doct_name} File"] = (
        process_book_file(w_book, old_book_file, old_f_part, new_f_Part)
    )
    
    # Rename cover file and update using new value
    w_book.cover_file = c_book_entry[f"{doct_name} Cover File"] = (
        process_cover_file(w_book, old_cover_file, old_f_part, new_f_Part)
    )    

    # For author updates, move the files to new author folder
    if (u_type == "Update Author"):

        w_book.folder = c_book_entry["Author Folder"] = (            
            process_folder_move(w_book, value)
        )
    
    # Set author field to None for all non-author updates to preven upating author
    # field with bad value since fetching author values not working as expected.
    else:
        w_book.author = None

    # Update WordPress with new book details
    wbgclient.create_book(w_book, uploadPDF=True, post_id=w_book.post_id)

    c_book_entry['WBG Update Date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Partial application function to handle book file rename by pre-filling book file id
def process_book_file(w_book, old_file, old_part, new_part):
    return process_file(w_book.base_path, w_book.folder, old_file, 
                        old_part, new_part, w_book.file_id)

# Partial application function to handle cover file rename by pre-filling cover file id
def process_cover_file(w_book, old_file, old_part, new_part):
    return process_file(w_book.base_path, w_book.folder, old_file, 
                        old_part, new_part, w_book.cover_file_id)

# This renames a file by replacing the old_part of the filename with the new_part in 
# the file system and removes the file from WordPress so it can later be reloaded with 
# the new file name.
#
# The "part" of the file name is usually the component separated by an "_". This can be
# tht title, author, publication, etc.
def process_file(base, folder, old_file, old_part, new_part, media_id):
    new_file = old_file.replace(old_part.replace(" ","-"), new_part.replace(" ","-"))
    
    os.rename(os.path.join(base, folder, old_file), os.path.join(base, folder, new_file))
    print(f"Renamed file: {old_file} -> {new_file}")

    wbgclient.delete_media(media_id)
    print("Deleted old file from WordPress:", media_id)

    return new_file

def process_folder_move(w_book, author_value):
    # Get old and new author folders
    firstname, middlename, lastname = (
        name_part.strip() for name_part in author_value.strip().split("|")
    )
    if (len(middlename) > 0):
        new_folder = firstname + "_" + middlename + "_" + lastname
    else:
        new_folder = firstname + "_" + lastname
    new_folder = new_folder.replace(" ", "-")
    old_folder = w_book.folder
    
    # Get full paths for old and new folder
    base = w_book.base_path
    old_path = os.path.join(base, old_folder)
    new_path = os.path.join(base, new_folder)
    if not os.path.exists(new_path):
        os.makedirs(new_path, exist_ok=True)    

    # Move the file from old_path to new_path
    old_file_path = os.path.join(old_path, w_book.file)
    new_file_path = os.path.join(new_path, w_book.file)
    os.rename(old_file_path, new_file_path)

    print(f"Moved file: {old_file_path} -> {new_file_path}")

    # Move the cover file from old_path to new_path
    old_file_path = os.path.join(old_path, w_book.cover_file)
    new_file_path = os.path.join(new_path, w_book.cover_file)
    os.rename(old_file_path, new_file_path)

    print(f"Moved cover file: {old_file_path} -> {new_file_path}")

    # Delete old author folder if empty
    try:
        if os.path.isdir(old_path) and not os.listdir(old_path):
            os.rmdir(old_path)
            print(f"Deleted empty folder: {old_path}")
    except Exception as e:
        print(f"Could not delete folder {old_path}: {e}")

    return new_folder






