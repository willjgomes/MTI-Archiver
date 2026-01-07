
'''
This module is used to read all books in wordpress and synchronize with the Google Catalog sheets
to ensure all books are in the catalof files and ensure the book files exist in the file system.
'''
from wordpressmti.wbg_book_post import get_wbg_client
from mti.mti_config import MTIDataKey, mticonfig, MTIConfig
from googlemti import gspread_client
from pathlib import Path
import mti.mti_updater as mti_updater
from gspread_dataframe import get_as_dataframe


def get_catalog_entry(post_id):

    c_book_entry    = None

    # Find the Archive (Collection & Document Type) so we can get the 
    # details from the Catalog sheet
    cell = mti_updater.lookup_tab.find(post_id)

    if (cell):
        lookup_val = mti_updater.lookup_tab.cell(1, cell.col).value
        (coll_name, doct_name) = tuple(lookup_val.split(":"))

        # Get the related catalog entry details
        (c_book_entry, c_row_num) = mti_updater.get_catalog_entry(post_id, coll_name, doct_name)

    return c_book_entry

def get_catalog_entry(post_id,lookup_df):

    c_book_entry    = None

    matches = lookup_df.columns[(lookup_df == post_id).any()]

    lookup_val = matches[0] if not matches.empty else None

    if (lookup_val is not None):
        (coll_name, doct_name) = tuple(lookup_val.split(":"))
        # Get the related catalog entry details
        (c_book_entry, c_row_num) = mti_updater.get_catalog_entry(post_id, coll_name, doct_name)
    
    return c_book_entry


'''
This takes a WPGBook entry and checks to see if it can be found on the file system
'''
def check_book_exists_on_filesystem(book, c_book_entry):
    # Deterimine source book file path based on attributes about book derived from
    # values stored in Wordpress.  
    file_path = Path(f'{book.base_path}\\{book.folder}\\{book.file}')

    # IMPORTANT: Note the actual book base path, folder, file values can be found in 
    # the respective Google Catalog sheet. The goal here is to validate the books in
    # Wordpress with books stored in the file system, so we don't want to limit using
    # the catalog sheet data.
    
    # We will go through series checks until the book file is found. This is due to 
    # caveats in deriving value due to quirks in Wordpress and file system organization.
    
    # CHECK: Intiial derived values
    # =============================================
    is_book_file_found = file_path.exists()
    
    # CHECK: Extra spaces and special characters ()&' in title
    # ========================================================
    # TODO : Flag extra spaces as cleanup error, title should not have extra spaces.        
    if  (not is_book_file_found): 
        file_path = Path(f'{book.base_path}\\{book.folder}\\{book.get_filename_from_title()}')
        is_book_file_found = file_path.exists()

    # CHECK: Author sub-folders or special characters in author name
    # =============================================
    # Sub-folder data must comefrom catalog entry since Wordpress not store subfolder information
    if (not is_book_file_found):
        if (c_book_entry):
            author_folder = c_book_entry.get("Author Folder")
            file_path = Path(f'{book.base_path}\\{author_folder}\\{book.get_filename_from_title()}')
            is_book_file_found = file_path.exists()

            # Resort to using the filename from catalog if author name contains apostrophe
            # since wordpress gets rid of them.
            if (not is_book_file_found and book.author.find("'") != -1):
                file_name = c_book_entry.get(f'{book.book_type} File')
                file_path = Path(f'{book.base_path}\\{author_folder}\\{file_name}')
                is_book_file_found = file_path.exists()

    return (is_book_file_found, file_path)

'''
This queries Wordpress for all book entries and checks to see if the book exists on the file system
and in the catalog.
'''
def process_all_wordpress_book_entries():

    wbgclient = get_wbg_client()
    for page_counter in range(1, 15):
        books = wbgclient.get_books(page=page_counter)
        for book in books:
            # Check to see if book exists in catalog
            c_book_entry = get_catalog_entry(str(book.post_id),lookup_df)

            # Check to see if book file exists on file system, since it depends
            # on catalog entry data, perform check only if catalog entry found
            if (c_book_entry):
                (is_book_file_found, file_path_checked) = check_book_exists_on_filesystem(book, c_book_entry)

            should_report_missing = (
                not c_book_entry or 
                not is_book_file_found
            )

            if (should_report_missing):                
                print(f'{book.post_id} {book.title}')
                if  (not c_book_entry):
                    print("Missing catalog entry")
                
                if (not is_book_file_found):
                    print("Missing book file     : ",file_path_checked)
                print()


if (mti_updater.wbgclient == None):
    mti_updater.__init__()
        
lookup_df = get_as_dataframe(mti_updater.lookup_tab, evaluate_formulas=True, dtype=str)
lookup_df.fillna("", inplace=True)  # Fill NaN with empty strings for consistency

process_all_wordpress_book_entries()