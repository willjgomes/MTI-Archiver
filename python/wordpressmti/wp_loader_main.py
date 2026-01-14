import csv
from mti import book_csv_reader, author_doc_scan
from wordpressmti.wbg_book_post import *
from mti.mti_config import MTIConfig, MTIDataKey, mticonfig
from pathlib import Path

class WPLoaderError(Exception):
   def __init__(self, message):
        self.message = message
        super().__init__(self.message)

def get_dates():
    return (    
        mticonfig.exe_details.get(MTIDataKey.LAST_IDX_GEN_FILE_DT),
        MTIConfig.convert_to_datetime(mticonfig.exe_details.get(MTIDataKey.LAST_IDX_GEN_FILE_DT)),
        MTIConfig.convert_to_datetime(mticonfig.exe_details.get(MTIDataKey.LAST_IDX_LOAD_FILE_DT)),
    )

def get_file_paths(last_idx_gen_dt, loadManual):
    path_root = mticonfig.output_dir + '/' + mticonfig.archive_key + '_' + last_idx_gen_dt

    idx_new_file = ""
    if (loadManual):
        # If loading manually created index file, rename the file to manually dated
        # idexn new file
        manual_file = mticonfig.output_dir + '/' + mticonfig.archive_key + '_Manual.csv'
        idx_new_file = path_root + '_Manual_Index_New.csv'
        os.rename(manual_file, idx_new_file)
    else:
        idx_new_file = path_root + '_Index_New.csv'

    return (        
        Path(idx_new_file),
        Path(path_root + '_Loaded.csv'),
        Path(path_root + '_Load_Error.csv'),
    )

def load(loadManual=False):
    # Setup needed date variables
    (last_idx_gen_dt, gen_datetime, load_datetime) = get_dates()
        
    if (not gen_datetime and not loadManual):
        print(f"Index for {mticonfig.coll_name} { mticonfig.doct_name} not found. Please run indexer first.")
    elif (load_datetime and (load_datetime == gen_datetime) and not loadManual):
        print(f"Index for {mticonfig.coll_name} { mticonfig.doct_name} dated {last_idx_gen_dt} has previously been loaded.")
    else:
        # Setup needed files for loading books
        if (loadManual): last_idx_gen_dt = mticonfig.get_timestamp()
        (idx_new_file, loaded_file, load_error_file) = get_file_paths(last_idx_gen_dt, loadManual)

        # Get configuration flags
        isDryRun    = mticonfig.bool_flag('WordPress','LoadDryRun')      
        uploadMedia   = mticonfig.bool_flag('WordPress','UploadMedia')

        # Print messages
        print('Wordpress loader started ...')
        print(mticonfig.idtab, f"Index File: {idx_new_file}")
        if (isDryRun):
            print('\n ===== Dry Run Output ==== \n')
            print('The following documents would have been loaded: \n')

        # Get the Wordpress Books Gallery (WBG) client
        wbgclient = get_wbg_client()

        # Intiialize book variables for loading books
        book_load_count     = 0
        book_error_count    = 0
        loadedbooks         = []
        loaderrors          = []
        loadtimestamp       = mticonfig.get_timestamp()
        doct_prefix         = MTIConfig.tosingular(mticonfig.doct_name)
        
        try:
            for record in book_csv_reader.read_csv_file(doct_prefix, idx_new_file):
                new_book = record_to_book(record, doct_prefix)

                (book_exists, post_ids) = wbgclient.check_book_exists(new_book)
                if (not book_exists):
                    try:                    
                        loadedbooks.append(load_book(isDryRun, new_book, wbgclient, record, uploadMedia, loadtimestamp))            
                        book_load_count += 1
                    except WPGBookPostException as be:
                        book_error_count += 1
                        record['Error'] = str(be)
                        loaderrors.append(record)
                else:
                    book_error_count += 1
                    loaderrors.append(log_book_exists(doct_prefix, record, post_ids))

            # Save execution details and write file only if not dry run.
            if (not isDryRun):
                # Output loaded books to CSV file
                with open(loaded_file, "w", newline="", encoding="utf-8") as csvfile:                
                    fieldnames = ['Post ID', 'WBG Load Date'] + author_doc_scan.get_fieldnames(doct_prefix)
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter="|")
                    writer.writeheader()
                    writer.writerows(loadedbooks)
        
                with open(load_error_file, "w", newline="", encoding="utf-8") as csvfile:                
                    fieldnames = ['Error', 'Post IDs'] + author_doc_scan.get_fieldnames(doct_prefix)
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter="|")
                    writer.writeheader()
                    writer.writerows(loaderrors)

                # Save execution details checkpoint since wordpress loaded and loaded file created
                mticonfig.exe_details[MTIDataKey.LAST_IDX_LOAD_FILE_DT]  = last_idx_gen_dt
                mticonfig.exe_details[MTIDataKey.LAST_WP_LOADER_RUN_DT]  = loadtimestamp
                mticonfig.save_archiver_data()

        except FileNotFoundError as fe:
            print(f"Error: {fe}")
        except ValueError as ve:
            print(f"Error: {ve}")
        else:
            print(mticonfig.idtab, f"Documents loaded     {book_load_count}")
            print(mticonfig.idtab, f"Documents not loaded {book_error_count}")
            print('\nWordpress loader completed.\n')

        if (isDryRun):
            print('\n ===== Dry Run Output ==== \n')
       

def record_to_book(record, doct_prefix):
    new_book = WPGBook(
        title       = record[f"{doct_prefix} Title"],
        book_type        = doct_prefix,
        author      = WPGBook.get_author(
                            record['First Name'],
                            record['Middle Name'],
                            record['Last Name']
                        ),
        folder      = record['Author Folder'],
        file        = record[f"{doct_prefix} File"],
        cover_file  = record[f"{doct_prefix} Cover File"],
        base_path   = record['Base Path']
    )

    # Set book categories
    book_categories = mticonfig.ini[mticonfig.archive_sectkey]['BookCategories']
    # TODO: Find better way to handle this instead of hard-coding
    if (new_book.author == "Mother Teresa"):
        book_categories = book_categories.replace("letters-to-mt", "letters-by-mt")
    new_book.book_categories = [s.strip() for s in book_categories.split(",")]   

    # Add article specific fields
    if (doct_prefix == "Article" or doct_prefix == "Journal"):
        new_book.published_on   = record['Date']
        new_book.publisher      = record['Periodical']
    elif (doct_prefix == "Letter" or doct_prefix == "Dissertation"):
        new_book.published_on   = record['Date']

    return new_book


def load_book(isDryRun, new_book, wbgclient, record, uploadMedia, loadtimestamp):
    # Get Document Type Prefix (eg. Article, Book, etc)
    doct_prefix = MTIConfig.tosingular(mticonfig.doct_name)    

    if (not isDryRun):
        postid = wbgclient.create_book(new_book, uploadMedia)
        print("[Loaded]", record[f"{doct_prefix} Title"])
    else:
        print(new_book)
        postid = 'Dry Run'

    record['WBG Load Date'] = loadtimestamp
    record['Post ID'] = postid

    return record

def log_book_exists(doct_prefix, record, post_ids):
    record['Error']     = f"{doct_prefix} Already Exists"
    record['Post IDs']  = ','.join(str(pid) for pid in post_ids)

    print("[Exists]", record[f"{doct_prefix} Title"])

    return record
