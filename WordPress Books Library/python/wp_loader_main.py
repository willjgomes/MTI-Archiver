import wpg_book_post
from wpg_book_post import WPGBook as WPGBook
import book_csv_reader
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

        csv_file = Path(mticonfig.output_dir + '/' + mticonfig.archive_key + '_' + last_idx_gen_dt + '_Index_New.csv')
        print(mticonfig.idtab, f"Index File: {csv_file}")

        if (mticonfig.ini['WordPress']['LoadDryRun']):
            print('\n ===== Dry Run Output ==== \n')
            print('The following documents would have been loaded: \n')

        book_count = 0
        
        try:
            for record in book_csv_reader.read_csv_file(csv_file):
                book_count += 1
                load_book(mticonfig, record)    

            # Save execution details, only if not dry run.
            if (not mticonfig.ini['WordPress']['LoadDryRun']):
                mticonfig.exe_details[MTIDataKey.LAST_IDX_LOAD_FILE_DT]  = last_idx_gen_dt
                mticonfig.exe_details[MTIDataKey.LAST_WP_LOADER_RUN_DT]  = mticonfig.get_timestamp()
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

        if (mticonfig.ini['WordPress']['LoadDryRun']):
            print('\n ===== Dry Run Output ==== \n')

def load_book(mticonfig:MTIConfig, record):
    new_book = WPGBook(
        record['Book Title'],
        "", 
        record['First Name'] + " " + record['Last Name'],
        record['Author Folder'],
        record['Book File'],
        record['Book Cover File'],
        record['Base Path']
        )
    
    if (not mticonfig.ini['WordPress']['LoadDryRun']):
        wpg_book_post.createBook(new_book)
    else:
        print(new_book)

