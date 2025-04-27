import subprocess, filecmp, difflib, os, shutil
import author_doc_scan
from mti_config import MTIConfig, MTIDataKey
from pathlib import Path

class IndexerException(Exception):
   def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class MTIIndexer:
    
    @staticmethod
    def find_new_lines(file1, file2):
        with open(file1, 'r') as f1, open(file2, 'r') as f2:
            # Read both files
            file1_lines = f1.readlines()
            file2_lines = f2.readlines()

            # Get the differences between the files using unified_diff
            #diff = difflib.unified_diff(file1_lines, file2_lines, fromfile=str(file1), tofile=str(file2))
            diff = difflib.ndiff(file1_lines, file2_lines)
            #print('\n'.join(diff))
            #TODO: It appears once you process the diff, you can't read the same content from it again, it appears to become empty

            # Extract only the new lines that are in file2
            new_lines = [line[1:] for line in diff if line.startswith('+ ')]

            # Add header row from
            new_lines.insert(0, file1_lines[0])
        
            # Check if more new lines than files indexed (account for header row, hence -1)
            if ((len(new_lines) - 1) > len(file2_lines)):
                raise IndexerException("Issues detected: More new items found than total items indexed. Verify data files created for archive.")

            return new_lines

    # This method starts the indexing process based on the current collection & document type selected
    @staticmethod
    def start(mticonfig: MTIConfig):
        folder_to_index = ""
        try:                        
            folder_to_index = mticonfig.ini[mticonfig.archive_sectkey]['DocumentFolder'].strip()
            if len(folder_to_index) <= 0: raise ValueError() 
        except (KeyError, ValueError) as e:
            raise IndexerException(f"{mticonfig.archive_sectkey} DocumentFolder not specified in settings.ini.")

        # Setup output filenames for indexer
        timestamp = mticonfig.get_timestamp()
        file_prefix = f'{mticonfig.archive_key}_{timestamp}'        
        index_output_file   = Path(mticonfig.output_dir + '/' + file_prefix + '_Index.csv')
        index_debug_file    = Path(mticonfig.output_dir + '/' + file_prefix + '_Index_Debug.txt')
        index_error_file    = Path(mticonfig.output_dir + '/' + file_prefix + '_Index_Error.csv')
        index_new_file      = Path(mticonfig.output_dir + '/' + file_prefix + '_Index_New.csv')
    
        print("Indexing started")
        print("================")
        print("  Document Folder", folder_to_index)
    
        #run_powershell_author_doc_scan(mticonfig, folder_to_index, index_output_file, index_debug_file, index_error_file)
        run_python_author_doc_scan(mticonfig, folder_to_index, index_output_file, index_debug_file, index_error_file)

        # Update some archiver data
        mticonfig.exe_details[MTIDataKey.LAST_INDEXER_RUN_DT]   = timestamp     
        mticonfig.exe_summary[MTIDataKey.LAST_INDEXER_RUN_DT]   = timestamp
        mticonfig.exe_summary[MTIDataKey.LAST_IDXR_ARCHIVE_KEY] = mticonfig.archive_key     

        
        last_idx_gen_dt     = mticonfig.exe_details.get(MTIDataKey.LAST_IDX_GEN_FILE_DT)
        last_idx_load_dt    = mticonfig.exe_details.get(MTIDataKey.LAST_IDX_LOAD_FILE_DT)
        
        # Check current indexer output to output from last execution
        changes_found = False
        if last_idx_load_dt:
            last_idx_output_file = Path(mticonfig.output_dir + '/' + mticonfig.archive_key + '_' + last_idx_gen_dt + '_Index.csv')
            last_idx_error_file  = Path(mticonfig.output_dir + '/' + mticonfig.archive_key + '_' + last_idx_gen_dt + '_Index_Error.csv')
            

            # If last index output is same as current, no chances since las load, then
            # delete output, no need to keep them around
            if (filecmp.cmp(index_output_file, last_idx_output_file, shallow=False) and
               filecmp.cmp(index_error_file, last_idx_error_file, shallow=False)):
                os.remove(index_output_file)
                os.remove(index_debug_file)
                os.remove(index_error_file)
                print("No new documents found since last time indexed.")

            # Check for new items if current index is different from last time index loaded
            else:
                changes_found           = True              
                
                idx_comp_file = Path(mticonfig.output_dir + '/' + mticonfig.archive_key + '_' + last_idx_load_dt + '_Index.csv')
                
                # Find the new lines
                newlines = MTIIndexer.find_new_lines(idx_comp_file, index_output_file)              
                
                print(mticonfig.idtab, 'New Documents Identified   :', len(newlines)-1)
                with open(index_new_file, "w", encoding="utf-8") as file:
                    file.writelines(line for line in newlines)
        
        # The entire index is new as it has never been loaded
        else:
            changes_found = True
            #Copy the index file to new file
            shutil.copy(index_output_file, index_new_file)

        # Update the last generated file date, since new index contains changes
        if changes_found:
            mticonfig.exe_details[MTIDataKey.LAST_IDX_GEN_FILE_DT]  = timestamp
            print(f"\t==> Index file created: {index_new_file}")
        
        print()
        mticonfig.save_archiver_data()

def run_powershell_author_doc_scan(mticonfig:MTIConfig, folder_to_index, index_output_file, index_debug_file, index_error_file):
    #Powershell command arguments for indexer script
    ps_command = f"& '{mticonfig.indexer_script}' -foldersPath '{folder_to_index}' -outputCSV '{index_output_file}' "
    ps_command += f"6> '{index_error_file}' "
    ps_command += f"-Debug 5> '{index_debug_file}' " if mticonfig.debug_flag('indexer') else "" # Enable debug if set  

    #print(ps_command)

    result = subprocess.run([
        "powershell",
        "-ExecutionPolicy", "Bypass",
        "-Command", ps_command
    ])

    if (result.returncode != 0):
        raise IndexerException("Error encountered in Powershell script to process folder.")

def run_python_author_doc_scan(mticonfig:MTIConfig, folder_to_index, index_output_file, index_debug_file, index_error_file):
    author_doc_scan.process_author_folder(folder_to_index, mticonfig.doct_name, index_output_file, index_debug_file, index_error_file, mticonfig.debug_flag('indexer'))
