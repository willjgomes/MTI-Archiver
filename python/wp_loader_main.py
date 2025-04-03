import csv
import author_doc_scan, book_csv_reader, google_csv_loader
from wbg_book_post import WPGBook, WPGBookPostClient
from mti_config import MTIConfig, MTIDataKey
from pathlib import Path

class WPLoaderError(Exception):
   def __init__(self, message):
        self.message = message
        super().__init__(self.message)

def load(mticonfig:MTIConfig):
    last_idx_gen_dt = mticonfig.exe_details.get(MTIDataKey.LAST_IDX_GEN_FILE_DT)

    gen_datetime	= MTIConfig.convert_to_datetime(mticonfig.exe_details.get(MTIDataKey.LAST_IDX_GEN_FILE_DT))
    load_datetime   = MTIConfig.convert_to_datetime(mticonfig.exe_details.get(MTIDataKey.LAST_IDX_LOAD_FILE_DT))
        
    if (not gen_datetime):
        print("Index for {mticonfig.coll_name} { mticonfig.doct_name} not found. Please run indexer first.")
    elif (load_datetime and (load_datetime == gen_datetime)):
        print(f"Index for {mticonfig.coll_name} { mticonfig.doct_name} dated {last_idx_gen_dt} has previously been loaded.")
    else:
        print('Wordpress loader started ...')

        csv_file    = Path(mticonfig.output_dir + '/' + mticonfig.archive_key + '_' + last_idx_gen_dt + '_Index_New.csv')
        loaded_file = Path(mticonfig.output_dir + '/' + mticonfig.archive_key + '_' + last_idx_gen_dt + '_Loaded.csv')
        print(mticonfig.idtab, f"Index File: {csv_file}")

        isDryRun = mticonfig.bool_flag('WordPress', 'LoadDryRun')

        if (isDryRun):
            print('\n ===== Dry Run Output ==== \n')
            print('The following documents would have been loaded: \n')

        
        # Setup Book post client (TODO: Maybe only create this once per archiver instead of for every load event)
        wp_url      = mticonfig.ini['WordPress']['SiteURL']
        wp_username = mticonfig.ini['WordPress']['Username']
        wp_password = mticonfig.ini['WordPress']['Password']
        wpgclient   = WPGBookPostClient(wp_url, wp_username, wp_password)
        uploadPDF   = mticonfig.bool_flag('WordPress','UploadPDF')

        book_count  = 0
        loadedbooks = []
        loadtimestamp = mticonfig.get_timestamp()
        
        try:
            for record in book_csv_reader.read_csv_file(csv_file):
                book_count += 1
                loadedbooks.append(load_book(isDryRun, wpgclient, record, uploadPDF, loadtimestamp))                

            # Save execution details and write file only if not dry run.
            if (not isDryRun):
                # Output loaded books to CSV file
                with open(loaded_file, "w", newline="", encoding="utf-8") as csvfile:                
                    fieldnames = ['Post ID', 'WBG Load Date'] + author_doc_scan.get_fieldnames('Book')
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter="|")
                    writer.writeheader()
                    writer.writerows(loadedbooks)
        
                # Save execution details checkpoint since wordpress loaded and loaded file created
                mticonfig.exe_details[MTIDataKey.LAST_IDX_LOAD_FILE_DT]  = last_idx_gen_dt
                mticonfig.exe_details[MTIDataKey.LAST_WP_LOADER_RUN_DT]  = loadtimestamp
                mticonfig.save_archiver_data()

        except FileNotFoundError:
            print(f"Error: File not found at {csv_file}")
        except ValueError as ve:
            print(f"Error: {ve}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        else:
            print(mticonfig.idtab, f"Documents processed {book_count}")
            print('\nWordpress loader completed successfully.\n')

        if (isDryRun):
            print('\n ===== Dry Run Output ==== \n')
       

def load_book(isDryRun, wpgclient, record, uploadPDF, loadtimestamp):
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
        postid = wpgclient.createBook(new_book, uploadPDF)
        print("[Loaded]", record['Book Title'])
    else:
        print(new_book)

    record['WBG Load Date'] = loadtimestamp
    record['Post ID'] = postid

    return record

