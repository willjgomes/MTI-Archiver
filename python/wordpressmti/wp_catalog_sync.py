
'''
This module is used to read all books in wordpress and synchronize with the Google Catalog sheets
to ensure all books are in the catalof files and ensure the book files exist in the file system.
'''
import os
from wordpressmti import wp_loader_main
from wordpressmti.wbg_book_post import get_wbg_client
from mti.mti_config import MTIDataKey, mticonfig, MTIConfig
from mti import author_doc_scan, book_csv_reader
from googlemti import gspread_client, collection_catalog
from pathlib import Path
from tqdm import tqdm


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
def process_all_wordpress_book_entries(verbose=False):

    wbgclient = get_wbg_client()
    missing_results = {}
    max_page = 15

    for page_counter in tqdm(range(11, max_page), desc="Processing:"):
        books = wbgclient.get_books(page=page_counter)
        for book in tqdm(books, desc=f"Page {page_counter}", leave=False):
            # Check to see if book exists in catalog
            (c_book_entry, c_row_num, coll_name, doct_name) = (
                collection_catalog.get_catalog_entry_by_post_id(str(book.post_id))
            )

            (is_book_file_found, file_path_checked) = check_book_exists_on_filesystem(book, c_book_entry)

            should_report_missing = (
                not c_book_entry or 
                not is_book_file_found
            )

            if (should_report_missing): 
                missing_details = {"book":book}                           
                missing_details["isMissingCatalog"]   = (not c_book_entry)
                missing_details["isMissingBookFile"]  = (not is_book_file_found)
                missing_results[book.post_id] = missing_details
            
            if (verbose and should_report_missing):
                fstr = '[ ]' if is_book_file_found else '[F]'
                cstr = '[ ]' if c_book_entry else '[C]'
                tqdm.write(f'[NOT OK]{fstr}{cstr}{book.post_id:7} {book.author} - {book.title}')
                if (not is_book_file_found):
                    tqdm.write(f'       Checked File Path: {file_path_checked}')

    print(f'Total books with missing items: {len(missing_results)}')
    return missing_results


def index_missing_authors_in_collection(folder_to_index, missing_authors, coll_name, doct_name):
    
    archive_key = f'{coll_name}_{doct_name}'
    # Setup output filenames for indexer
    timestamp = mticonfig.get_timestamp()
    #file_prefix = f'{archive_key}_{timestamp}'        
    file_prefix = f'{archive_key}'        
    index_output_file   = Path(mticonfig.data_dir + '/temp/' + file_prefix + '_Index.csv')
    index_debug_file    = Path(mticonfig.data_dir + '/temp/' + file_prefix + '_Index_Debug.txt')
    index_error_file    = Path(mticonfig.data_dir + '/temp/' + file_prefix + '_Index_Error.csv')

    print("Processing folder: ", folder_to_index)    
    num_processed = author_doc_scan.process_selected_author_folders(
        folder_to_index, missing_authors, doct_name,
        index_output_file, index_debug_file, index_error_file, debug=True)
    
    entries = set()
    if num_processed > 0:
        entries.update(create_missing_catalog_entries(doct_name, index_output_file))
        if len(entries) == 0:
            print(mticonfig.idtab, "WARNING: Folder procssed but no catalog entries created.")
    else:
        print(mticonfig.idtab, "Skipping...")

    return entries

def index_missing_authors(missing_authors, missing_post_ids=None):
    
    entry_post_ids = set()
    for coll_name in mticonfig.coll_list:
        for doct_name in mticonfig.doct_list:
            archive_sectkey = f'{coll_name}:{doct_name}'

            print()
            print("=" * 125)
            print(f'Indexing missing authors for {archive_sectkey}')
            print()

            try:   
                
                folder_to_index = mticonfig.ini[archive_sectkey]['DocumentFolder'].strip()
                if len(folder_to_index) <= 0: raise ValueError() 

                entry_post_ids.update(index_missing_authors_in_collection(folder_to_index, missing_authors, coll_name, doct_name[:-1]))        
            except (KeyError, ValueError) as e:
                print(mticonfig.idtab, "No folder path specified in settings.ini. " )
                print(mticonfig.idtab, "Skipping...")

    print("Not   created:", missing_post_ids - entry_post_ids)
    print("Extra created:", entry_post_ids - missing_post_ids)
    print("Okay  created:", missing_post_ids & entry_post_ids)

def create_missing_catalog_entries(doct_prefix, idx_file):
    wbgclient = get_wbg_client()
    
    print()
    try:
        created_entries = set()
        for record in book_csv_reader.read_csv_file(doct_prefix, idx_file):
            new_book = wp_loader_main.record_to_book(record, doct_prefix)

            (book_exists, post_ids) = wbgclient.check_book_exists(new_book)

            if (len(post_ids) > 1):
                print('Multiple books found in wordpress:', {new_book.title} - {new_book.author})
            elif (len(post_ids) == 0):
                print('No book found in wordpress for:', {new_book.title} - {new_book.author})
            elif (len(post_ids) == 1):
                #Exactly one book found in wordpress
                post_id = post_ids[0]
                (c_book_entry, c_row_num, coll_name, doct_name) = (
                collection_catalog.get_catalog_entry_by_post_id(str(post_id))
                )
                
                # If catalog entry not found, create the missing entry
                if (not c_book_entry):
                    created_entries.add(post_id)
                    print(f'Creating catalog entry: {post_id} - {new_book.title} - {new_book.author}')
    except Exception as e:
       print(f"Error processing missing catalog entry: {e}")

    return created_entries


def start_sync():
    if (not collection_catalog.is_initialized):
        collection_catalog.__init__() 
        collection_catalog.show_info_logs = False       

    missing_results = process_all_wordpress_book_entries(verbose=True)

    missing_authors = set()
    missing_post_ids = set()
    for result in missing_results.values():
        book = result.get("book")
        missing_authors.add(book.author.replace("_","").replace("-","").replace(" ","").lower())


def test_sync():
    if (not collection_catalog.is_initialized):
        collection_catalog.__init__()
        collection_catalog.show_info_logs = False

    missing_authors = ['annspangler', 'kaifmahmood', 'adolphetanquerey', 'bradleyc.gregory', 'racheldavies', 'iuliumariusmorariu', 'alexandermaclaren', 'albanbutler', 'alfonsoroperoberzosa', 'briankolodiejchuk', 'paulchetcuti', 'michaelchampagne', 'jeanlafrance', 'anndoneganjohnson', 'anthonynicotera', 'amonkofmarimonabbey', 'jacquesphilippe', 'arpitabanerjee', 'jessicacoblentz', 'anthonychidiac', 'aroupchatterjee', 'a.huart', 'joeevans', 'cecilieendresen', 'alphonsusrodriguez', 'morihirooki', 'gezimalpion', 'sisternirmala', 'a.coviello']
    missing_post_ids = {641, 385, 131, 389, 135, 392, 393, 142, 149, 152, 1305, 155, 1308, 1311, 159, 1314, 1317, 165, 1320, 554, 1323, 299, 170, 1326, 560, 1329, 562, 304, 1332, 566, 587, 590, 595, 348, 350, 352, 613, 616, 362, 250, 620, 2286, 240, 243, 248, 378, 1403, 637}

    index_missing_authors(missing_authors, missing_post_ids)

start_sync()