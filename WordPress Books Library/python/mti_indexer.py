import stat,subprocess, filecmp, difflib, os
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
		
			if (len(new_lines) >= len(file2_lines)):
				raise IndexerException("Issues detected indexing file. Please verify correct document folder for collection & type")

			return new_lines

	# This method starts the indexing process based on the current collection & document type selected
	@staticmethod
	def start(mticonfig: MTIConfig):
		folder_to_index = ""
		try:
			folder_to_index = mticonfig.ini[mticonfig.archive_sectkey]['DocumentFolder']
		except KeyError:
			raise IndexerException(f"{mticonfig.archive_sectkey} DocumentFolder not specified in settings.ini.")

		timestamp = mticonfig.get_timestamp()
		file_prefix = f'{mticonfig.archive_key}_{timestamp}'		
		index_output_file	= Path(mticonfig.output_dir + '/' + file_prefix + '_Index.csv')
		index_debug_file	= Path(mticonfig.output_dir + '/' + file_prefix + '_Index_Debug.txt')
		index_error_file	= Path(mticonfig.output_dir + '/' + file_prefix + '_Index_Error.csv')
	
		print("Indexing started")
		print(mticonfig.idtab, "Document Folder", folder_to_index)
	
		#Powershell command arguments for indexer script
		ps_command = f"& '{mticonfig.indexer_script}' -foldersPath '{folder_to_index}' -outputCSV '{index_output_file}' "
		ps_command += f"6> '{index_error_file}' "
		ps_command += f"-Debug 5> '{index_debug_file}' " if (mticonfig.ini['DEBUG']['indexer'].lower() == 'true') else ""	# Enable debug if set  

		#print(ps_command)

		result = subprocess.run([
			"powershell",
			"-ExecutionPolicy", "Bypass",
			"-Command", ps_command
		])

		# Update some archiver data
		mticonfig.exe_details[MTIDataKey.LAST_INDEXER_RUN_DT]	= timestamp		
		mticonfig.exe_summary[MTIDataKey.LAST_INDEXER_RUN_DT]	= timestamp
		mticonfig.exe_summary[MTIDataKey.LAST_IDXR_ARCHIVE_KEY] = mticonfig.archive_key

		# Check if current index generated is identical to last time index generated
		last_idx_identical = False
		last_idx_gen_dt	   = mticonfig.exe_details.get(MTIDataKey.LAST_IDX_GEN_FILE_DT)
		if last_idx_gen_dt:
			last_idx_output_file = Path(mticonfig.output_dir + '/' + mticonfig.archive_key + '_' + last_idx_gen_dt + '_Index.csv')
			last_idx_error_file  = Path(mticonfig.output_dir + '/' + mticonfig.archive_key + '_' + last_idx_gen_dt + '_Index_Error.csv')
			if (filecmp.cmp(index_output_file, last_idx_output_file, shallow=False) and
			   filecmp.cmp(index_error_file, last_idx_error_file, shallow=False)):
				last_idx_identical = True
				os.remove(index_output_file)
				os.remove(index_debug_file)
				os.remove(index_error_file)
				print(mticonfig.idtab, "No new documents found since last time indexed.")


		# Check for new items if current index is different from last time
		if not last_idx_identical:
			mticonfig.exe_details[MTIDataKey.LAST_IDX_GEN_FILE_DT] = timestamp
			last_idx_loaded_file		= last_idx_output_file
			newlines = MTIIndexer.find_new_lines(last_idx_loaded_file, index_output_file)

			print(mticonfig.idtab, 'New Documents Identified   :', len(newlines))

			# Print the new lines in file2
			for line in newlines:
				print(line.strip())
			
		mticonfig.save_archiver_data()



