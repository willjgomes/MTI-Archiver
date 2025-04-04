import csv
from http.cookiejar import LoadError
import author_doc_scan, book_csv_reader, google_csv_loader
from wbg_book_post import WPGBook, WPGBookPostClient
from mti_config import MTIConfig, MTIDataKey
from pathlib import Path

class WPLoaderError(Exception):
   def __init__(self, message):
        self.message = message
        super().__init__(self.message)

def get_dates(mticonfig:MTIConfig):
    return (    
        mticonfig.exe_details.get(MTIDataKey.LAST_IDX_GEN_FILE_DT),
        MTIConfig.convert_to_datetime(mticonfig.exe_details.get(MTIDataKey.LAST_IDX_GEN_FILE_DT)),
        MTIConfig.convert_to_datetime(mticonfig.exe_details.get(MTIDataKey.LAST_IDX_LOAD_FILE_DT)),
    )

def get_file_paths(mticonfig:MTIConfig, last_idx_gen_dt):
    path_root = mticonfig.output_dir + '/' + mticonfig.archive_key + '_' + last_idx_gen_dt
    return (        
        Path(path_root + '_Index_New.csv'),
        Path(path_root + '_Loaded.csv'),
        Path(path_root + '_Load_Error.csv'),
    )

def get_wbg_client(mticonfig:MTIConfig):
    # Setup Book post client (TODO: Maybe only create this once per archiver instead of for every load event)
    wp_url      = mticonfig.ini['WordPress']['SiteURL']
    wp_username = mticonfig.ini['WordPress']['Username']
    wp_password = mticonfig.ini['WordPress']['Password']
    
    return WPGBookPostClient(wp_url, wp_username, wp_password)


def load(mticonfig:MTIConfig):
    # Setup needed date variables
    (last_idx_gen_dt, gen_datetime, load_datetime) = get_dates(mticonfig)
        
    if (not gen_datetime):
        print(f"Index for {mticonfig.coll_name} { mticonfig.doct_name} not found. Please run indexer first.")
    elif (load_datetime and (load_datetime == gen_datetime)):
        print(f"Index for {mticonfig.coll_name} { mticonfig.doct_name} dated {last_idx_gen_dt} has previously been loaded.")
    else:
        # Setup needed files for loading books
        (idx_new_file, loaded_file, load_error_file) = get_file_paths(mticonfig, last_idx_gen_dt)

        # Get configuration flags
        isDryRun    = mticonfig.bool_flag('WordPress','LoadDryRun')      
        uploadPDF   = mticonfig.bool_flag('WordPress','UploadPDF')

        # Print messages
        print('Wordpress loader started ...')
        print(mticonfig.idtab, f"Index File: {idx_new_file}")
        if (isDryRun):
            print('\n ===== Dry Run Output ==== \n')
            print('The following documents would have been loaded: \n')

        # Get the Wordpress Books Gallery (WBG) client
        wbgclient = get_wbg_client(mticonfig)

        # Intiialize book variables for loading books
        book_load_count     = 0
        book_error_count    = 0
        loadedbooks         = []
        loaderrors          = []
        loadtimestamp       = mticonfig.get_timestamp()
        
        try:
            for record in book_csv_reader.read_csv_file(idx_new_file):                
                (book_exists, post_ids) = wbgclient.check_book_exists(record['Book Title'])
                if (not book_exists):
                    book_load_count += 1
                    loadedbooks.append(load_book(isDryRun, wbgclient, record, uploadPDF, loadtimestamp))                
                else:
                    book_error_count += 1
                    loaderrors.append(log_book_exists(record, post_ids))

            # Save execution details and write file only if not dry run.
            if (not isDryRun):
                # Output loaded books to CSV file
                with open(loaded_file, "w", newline="", encoding="utf-8") as csvfile:                
                    fieldnames = ['Post ID', 'WBG Load Date'] + author_doc_scan.get_fieldnames('Book')
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter="|")
                    writer.writeheader()
                    writer.writerows(loadedbooks)
        
                with open(load_error_file, "w", newline="", encoding="utf-8") as csvfile:                
                    fieldnames = ['Error', 'Post IDs'] + author_doc_scan.get_fieldnames('Book')
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter="|")
                    writer.writeheader()
                    writer.writerows(loaderrors)

                # Save execution details checkpoint since wordpress loaded and loaded file created
                mticonfig.exe_details[MTIDataKey.LAST_IDX_LOAD_FILE_DT]  = last_idx_gen_dt
                mticonfig.exe_details[MTIDataKey.LAST_WP_LOADER_RUN_DT]  = loadtimestamp
                mticonfig.save_archiver_data()

        except FileNotFoundError:
            print(f"Error: File not found at {idx_new_file}")
#        except ValueError as ve:
#            print(f"Error: {ve}")
#        except Exception as e:
#            print(f"An unexpected error occurred: {e}")
        else:
            print(mticonfig.idtab, f"Documents loaded     {book_load_count}")
            print(mticonfig.idtab, f"Documents not loaded {book_error_count}")
            print('\nWordpress loader completed.\n')

        if (isDryRun):
            print('\n ===== Dry Run Output ==== \n')
       

def load_book(isDryRun, wbgclient, record, uploadPDF, loadtimestamp):
    new_book = WPGBook(
        record['Book Title'],
        "", 
        record['First Name'] + " " + record['Last Name'],
        record['Author Folder'],
        record['Book File'],
        record['Book Cover File'],
        record['Base Path']
    )
    
    if (not isDryRun):
        postid = wbgclient.createBook(new_book, uploadPDF)
        print("[Loaded]", record['Book Title'])
    else:
        print(new_book)

    record['WBG Load Date'] = loadtimestamp
    record['Post ID'] = postid

    return record

def log_book_exists(record, post_ids):
    record['Error']     = 'Book Already Exists'
    record['Post IDs']  = ','.join(str(pid) for pid in post_ids)

    print("[Exists]", record['Book Title'])

    return record
