'''
This module is used to do a full dry run report of all documents in file system to see if
they exist in wordpress.  It will report list of documents not found in wordpress, along
with ones that have multiple. 

The output can be checked to see what documents got missed, the action to take would be
to run the Wordpress Indexer and Loader function for the collection with issues.

Additionally once this is run, the wp_catalog_sync process can be run to ensure all items
in wordpress are also in the catalog.  

The two wp sync processes can be used to ensure consistency across the file system, wordpress
and the catalog sheets
'''
import os, tqdm
from datetime import datetime
from wordpressmti.wbg_book_post import get_wbg_client
from wordpressmti import wp_loader_main
from mti.mti_config import mticonfig
from mti.mti_logger import MTILogger
from mti import author_doc_scan, book_csv_reader
from pathlib import Path

# Global Variables
working_dir = None
logger = None
log = None
logc = None

# Intiialize module and setup gloabl variables
def __init__():
    global working_dir, logger, log, logc

    # Setup working directory
    datestamp = datetime.now().strftime("%Y-%m-%d")   
    working_dir = mticonfig.data_dir + '/wp_file_sync/' + datestamp + '/'
    os.makedirs(working_dir, exist_ok=True)
        
    # Setup logger and create shorthands for logging functions
    logger = MTILogger(working_dir, 'wp_file_sync')
    logc = logger.logc
    log = logger.log

# Check if this module has been initialized
def is_initialized():
    # Return true if working directory has been set
    return bool(working_dir)

'''
This processes the index file and checks to see if all documents indexed are
in Wordpress
'''
def process_index_file(doct_name, index_output_file):

    wbgclient = get_wbg_client()

    single_found_count = 0
    multiple_found_count = 0
    none_found_count = 0
    total_count = 0

    try:
        logc("\nChecking Wordpress for documents ...")

        doct_prefix = mticonfig.tosingular(doct_name)
        
        total_lines = sum(1 for _ in open(index_output_file, "r")) - 1
        pbar = tqdm(desc=" Processing:", total=total_lines)
        
        for record in book_csv_reader.read_csv_file(doct_prefix, index_output_file):
            total_count += 1
            pbar.update(1)
            book = wp_loader_main.record_to_book(record, doct_prefix)

            (book_exists, post_ids) = wbgclient.check_book_exists(book)
            if (not book_exists): 
                none_found_count +=1 
                log(f"Not Found: {book}")
            elif (book_exists):
                if (len(post_ids) > 1):
                    multiple_found_count +=1
                    log(f"Multiple : {post_ids}{book}")
                else:
                    single_found_count +=1
        pbar.close()

        logc("\nWordpress Check Summary")
        logc(f"{mticonfig.idtab} Total Book Count    : {total_count}")
        logc(f"{mticonfig.idtab} Single Found Count  : {single_found_count}")
        logc(f"{mticonfig.idtab} Multiple Found Count: {multiple_found_count}")
        logc(f"{mticonfig.idtab} None Found Count    : {none_found_count}")

    except Exception as e:
       logc(f"Error processing missing catalog entry: {e}")

    return

'''
This will process the document folder for the collection, index all the documents in 
the folder to an index file, then process the index file to check wordpress to see if
document has been loaded into wordpress.
'''
def process_document_folder(folder_to_index, coll_name, doct_name):
    
    archive_key = f'{coll_name}_{doct_name}'
    
    # Setup output filenames for indexer
    file_prefix = f'{archive_key}'        
    index_output_file   = Path(working_dir + file_prefix + '_Index.csv')
    index_debug_file    = Path(working_dir + file_prefix + '_Index_Debug.txt')
    index_error_file    = Path(working_dir + file_prefix + '_Index_Error.csv')

    logc(f'\nIndexing folder: {folder_to_index} ... \n')    
    num_processed = author_doc_scan.process_all_author_folders(
        folder_to_index, doct_name,
        index_output_file, index_debug_file, index_error_file, debug=True)
    
    if num_processed > 0:
        process_index_file(doct_name, index_output_file)
    else:
        logc(f'{mticonfig.idtab} Skipping...')

    return

'''
This will go through each collection and document folder specified in the settings file,
create a full index and check to see if all the books are in wordpress.
'''
def start():
    if not is_initialized():
        __init__()
    
    logc('Starting File System Sync Process ...', header='=')
  
    for coll_name in mticonfig.coll_list:
        for doct_name in mticonfig.doct_list:
            archive_sectkey = f'{coll_name}:{doct_name}'

            logc(f'Collection: {coll_name}:{mticonfig.toPlural(doct_name)}', header="+")

            try:   
                
                folder_to_index = mticonfig.ini[archive_sectkey]['DocumentFolder'].strip()
                if len(folder_to_index) <= 0: raise ValueError() 

                process_document_folder(folder_to_index, coll_name, mticonfig.tosingular(doct_name))
            except (KeyError, ValueError) as e:
                logc(f'{mticonfig.idtab} No folder path specified in settings ini file.')
                logc(f'{mticonfig.idtab} Skipping...')


def test_sync():
   archive_sectkey = 'Mother Teresa Collection:Dissertations'
   #archive_sectkey = 'MTI Library Collection:Dissertations'
   folder_to_index = mticonfig.ini[archive_sectkey]['DocumentFolder'].strip()

   process_document_folder(folder_to_index, "MTI Library Collection", "Dissertations")

