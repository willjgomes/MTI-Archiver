# This will read a google sheet of update actions, such as Rename Title

from titlecase import titlecase
from googlemti import gspread_client
from gspread_dataframe import get_as_dataframe
from mti.mti_config import MTIDataKey, mticonfig
from wordpressmti.wbg_book_post import *
from datetime import datetime
import os, re, pandas as pd

def get_updater_actions_sheet():
    return gspread_client.get_sheet('Archiver Updates')
 
wbgclient           = None
actions_tab         = None
lookup_tab          = None
history_tab         = None
errors_tab          = None
errors_tab          = None
catalog_tabsdf_dict = None
catalog_tabs_dict   = None

def __init__():
    # Get the Wordpress Books Gallery (WBG) client, we must use global keyword
    # since we will be reassigning these
    global wbgclient
    global actions_tab
    global lookup_tab  
    global history_tab 
    global errors_tab
    global catalog_tabsdf_dict
    global catalog_tabs_dict

    wbgclient = get_wbg_client()
    
    catalog_tabsdf_dict = {}
    catalog_tabs_dict = {}

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
        (post_id, action, value) = (row[0], row[1], row[2])

        history_row = [post_id, action, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]

        # Find the Archive (Collection & Document Type) so we can get the 
        # details from the Catalog sheet
        cell = lookup_tab.find(post_id)
        lookup_val = lookup_tab.cell(1, cell.col).value
        (coll_name, doct_name) = tuple(lookup_val.split(":"))
        
        # Get the related catalog entry details
        (c_book_entry, c_row_num) = get_catalog_entry(post_id, coll_name, doct_name)

        # Process the action
        w_book = wbgclient.get_book(post_id)
        if not w_book:
            print(f"Post ID {post_id} not found in the current collection.")
            continue    #TODO: Add better error handling for not found and other errros
        elif action == "Update Categories":
            process_category_updates(w_book, value, history_row)
        elif action == "Reload Details":
            # Note: This is currently here to fix mistakes due to API or code issues
            # such as missing publication fields, etc. 
            # TODO: May want to find better way to do this.
            reload_details(action, w_book, c_book_entry, doct_name[0:-1], value, history_row)
        else :
            # Process changes requiring file renames (eg. Rename Title, Update Author, Filenam Fix Spaces)
            process_file_update(action, w_book, c_book_entry, doct_name[0:-1], value, history_row)

        update_catalog_entry(c_book_entry, coll_name, doct_name, c_row_num)

        # Move action to history tab
        history_tab.insert_row(history_row, 2)   
        actions_tab.delete_rows(2)        

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
    #Set the update date time
    c_book_entry['WBG Update Date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Update catalog entry (first rearrange c_book_entry to align with header cols)
    doct_tab = catalog_tabs_dict.get((coll_name, doct_name))

    header = doct_tab.row_values(1)
    c_row_values = [c_book_entry.get(col, "") for col in header]        
    
    google_row_num = c_row_num + 2  # gspread is 1-indexed and has header row
    doct_tab.update(f"A{google_row_num}", [c_row_values])

    #Also update the datafrane
    doct_df = catalog_tabsdf_dict.get((coll_name, doct_name))
    doct_df.loc[c_row_num, c_book_entry.keys()] = pd.Series(c_book_entry)

def process_category_updates(w_book, value, history_row):
    if not cateogry_value_is_valid(value):
        raise Exception("Update category values is not formatted properly: ", value)

    value = value.replace(" ","");
    remove_str = re.search(r'\([^)]*\)', value)

    if (remove_str):
        remove_str = remove_str.group(0)
        add_str = value.replace(remove_str, "")
        remove_str = remove_str[1:-1]
    else:
        add_str = value.strip()

    categories_to_add = add_str.split(",") if add_str else []    
    categories_to_remove = remove_str.split(",") if remove_str else []
            
    wbgclient.update_categories(w_book.post_id, categories_to_add, categories_to_remove)

    history_row.append("Added: " + ",".join(categories_to_add))
    history_row.append("Removed: " + ",".join(categories_to_remove))

def cateogry_value_is_valid(value):
    pattern = re.compile(r"""
        ^\s*
        (                                                        # Case 1: Parens at start
            \(\s*[\w-]+(\s*,\s*[\w-]+)*\s*\)\s*,\s*               # (w1, w2, ..., wn),
            [\w-]+(\s*,\s*[\w-]+)*                                # word(s) after
        |
            [\w-]+(\s*,\s*[\w-]+)*                                # Case 2: word(s) first
            \s*,\s*\(\s*[\w-]+(\s*,\s*[\w-]+)*\s*\)               # ,(w1, w2, ..., wn)
        |
            \(\s*[\w-]+(\s*,\s*[\w-]+)*\s*\)                      # Only parens group
        |
            [\w-]+(\s*,\s*[\w-]+)*                                # Only non-parens words
        )
        \s*$
    """, re.VERBOSE)

    return pattern.fullmatch(value)


def reload_details(action, w_book, c_book_entry, doct_name, value, history_row):
    w_book.title = c_book_entry[f"{doct_name} Title"]
    w_book.author = None
    w_book.publisher = c_book_entry.get("Periodical")
    w_book.published_on = c_book_entry.get("Date")
    w_book.book_type = doct_name

    wbgclient.create_book(w_book, uploadMedia=False, post_id=w_book.post_id)


# This Processs the update value for update and sets the w_book field accordingly
# based on update type. It also returns the part of the filename to replace as 
# (old, new)  tuple for later file renaming.
def process_update_value(u_type, w_book, c_book_entry, doct_name, value, history_row):
    if u_type == "Fix Filename Spaces":
        old_file = c_book_entry[f"{doct_name} File"]

        history_row.append('Old Filename: ' + old_file)
        history_row.append('New Filename: ' + old_file.replace(" ", "-"))

        # No need to update w_book fields since only fixing spaces in filename

        # Return the old file name as both parts, the subsequent file rename will handle
        # replacing spaces with hyphens
        return (old_file, old_file)
    if u_type == "Rename Title":
        if not value and value.strip().length == 0:
            print(f"Blank update value for '{u_type}' for post ID {w_book.post_id}. Skipping.")

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
    wbgclient.create_book(w_book, uploadMedia=True, post_id=w_book.post_id)

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
    # Get new filename, properly handling hypens depanding on "Rename Title" or "Fix Filename Spaces"
    # for the latter, just use the old_file as both old and new parts
    new_file = re.sub(old_part.replace(" ","-") if not old_part == new_part else old_file, 
                      new_part.replace(" ","-") if not old_part == new_part else old_file.replace(" ","-"), 
                      old_file, flags=re.IGNORECASE)
    
    os.rename(os.path.join(base, folder, old_file), os.path.join(base, folder, new_file))
    print(f"Renamed file: {old_file} -> {new_file}")

    wbgclient.delete_media(media_id)
    print("Deleted old file from WordPress:", media_id)

    return new_file

def process_folder_move(w_book, author_value):
    # Get old author folder
    old_folder = w_book.folder
    
    # Get new author folder (account for sub-folder)
    firstname, middlename, lastname = (
        name_part.strip() for name_part in author_value.strip().split("|")
    )
    if (len(middlename) > 0):
        new_folder = firstname + "_" + middlename + "_" + lastname
    else:
        new_folder = firstname + "_" + lastname
    new_folder = new_folder.replace(" ", "-")
    if (old_folder.find("\\") > 0):
        _, tail = old_folder.split("\\", 1)
        new_folder = f"{new_folder}\\{tail}" 
    
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






