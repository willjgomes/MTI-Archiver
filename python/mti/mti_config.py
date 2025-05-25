import configparser, json
from datetime import datetime
from pathlib import Path
from typing import Self
from xml.sax.handler import property_declaration_handler

class MTIDataKey:
	LAST_INDEXER_RUN_DT		= "Last Indexer Run Date"
	LAST_WP_LOADER_RUN_DT	= "Last Wordpress Loader Run Date"
	LAST_IDX_GEN_FILE_DT	= "Last Index Generated File Date"
	LAST_IDX_LOAD_FILE_DT	= "Last Index File Loaded to Wordpress"
	LAST_GOOG_LOAD_FILE_DT	= "Last Load File Loaded to Google"
	SUMMARY_KEY				= "mti_archiver_summary"
	LAST_IDXR_ARCHIVE_KEY	= "Last Archive Indexed"
	PROGRAM_RUN_DT			= "Program Run Date"
	COLLECTION              = "Selected Collection"
	DOCUMENT_TYPE			= "Selected Document Type"

class MTIConfig:

	idtab = "\t==>"

	# Script Paths
	script_dir		= Path(__file__).parent.parent.parent
	settings_file	= script_dir / 'settings' / 'archive.ini'
	indexer_script	= script_dir / 'powershell' / 'author_document_scan.ps1'

	def __init__(self):

		# Load INI from archive.ini file
		self.load_ini()

		# Load DAT JSON file config attributes
		self.dat		= self.load_archiver_data()

		# Get the previous execution JSON summary object, intialize if it doesn't exist
		self.exe_summary	= self.dat.get(MTIDataKey.SUMMARY_KEY) if self.dat.get(MTIDataKey.SUMMARY_KEY) else {}
		
		# Load previous Collection and DocumentType or default to 0
		if self.exe_summary.get(MTIDataKey.COLLECTION):
			self.coll_idx	= self.coll_list.index(self.exe_summary[MTIDataKey.COLLECTION])
			self.doct_idx	= self.doct_list.index(self.exe_summary[MTIDataKey.DOCUMENT_TYPE])
		else:
			self.coll_idx	= 0
			self.doct_idx	= 0

		# Get the previous execution JSON detail objects, intialize details if they don't exist
		self.exe_details	= self.get_exe_details()		

	# Define Active Collection and Document Type property to store active Settings during execution
	# This are defined this way to prevent setting of these properties directly, as it is controlled
	# by the index value of the selection and additional operations need to be performed for key and
	# name values when reset. Didn't use getter()/setter() function paradigm to keep it consistent 
	# with other config property access.
	#----------------------------------------------------------------------------------------------
	@property
	def coll_idx(self):
		return self.__coll_idx

	@coll_idx.setter
	def coll_idx(self, new_value):
		if not hasattr(self,'__coll_idx') or self.__coll_idx != new_value:
			self.__coll_idx = new_value
			self.__coll_key = MTIConfig.fileNameFormat(self.coll_list[self.coll_idx])
			self.exe_details = self.get_exe_details()

	@property
	def coll_name(self):
		return self.coll_list[self.coll_idx]

	@property
	def doct_idx(self):
		return self.__doct_idx

	@doct_idx.setter
	def doct_idx(self, new_value):
		if (not hasattr(self,'__doct_idx') or self.__doct_idx != new_value):
			self.__doct_idx = new_value
			self.__doct_key = MTIConfig.fileNameFormat(self.doct_list[self.doct_idx])
			self.exe_details = self.get_exe_details()

	@property
	def doct_name(self):
		return self.doct_list[self.doct_idx]

	@property
	def archive_key(self):
		#Note in constructor doct_key may still not have been initialized
		return f'{self.__coll_key}_{self.__doct_key}' if hasattr(self,'_MTIConfig__doct_key') else ""

	@property
	def archive_sectkey(self):
		return f'{self.coll_name}:{self.doct_name}'

	#----------------------------------------------------------------------------------------------

	# This is overwritten since output_dir needs to be dynamically created based on archive selected
	@property
	def output_dir(self):
		return self.data_dir + "/" + self.archive_key


	def load_ini(self):
		# Intiialize ini to config parser
		self.ini = configparser.ConfigParser()

		# Load INI from file
		try:
			with open(MTIConfig.settings_file) as f:
				print("Settings File Detected:\n\t==>", MTIConfig.settings_file)
				self.ini.read_file(f)
		except IOError:
			print("Settings file not found")

		# Load INI config attributes
		self.data_dir	= self.ini['Settings']['ScriptDataFolder']
		self.coll_list	= [str.strip() for str in self.ini['Settings']['Collections'].split(",")]
		self.doct_list	= [str.strip() for str in self.ini['Settings']['DocumentTypes'].strip().split(",")]

		# Setup temp dir
		self.temp_dir		= Path(self.data_dir) / 'temp'
		self.data_file		= Path(self.data_dir) / 'mtiarchiver.json'

	def load_archiver_data(self):
		data = {}
		# Load existing data
		try:
			with open(self.data_file, 'r') as file:
				data = json.load(file)
		except IOError:
			print('WARNING: Missing previous execution data.')
	
		return data

	def save_archiver_data(self):
		self.exe_summary[MTIDataKey.PROGRAM_RUN_DT] = str(datetime.now())
		self.exe_summary[MTIDataKey.COLLECTION] = self.coll_name
		self.exe_summary[MTIDataKey.DOCUMENT_TYPE] = self.doct_name
		
		self.dat[self.archive_key]			= self.exe_details
		self.dat[MTIDataKey.SUMMARY_KEY]	= self.exe_summary
		
		try:
			print("Saving execution details ... .", end="")
			with open(self.data_file, 'w') as file:
				json.dump(self.dat, file, indent=4)
		
			print("done.")
		except IOError:
			print('ERROR occured. Please verify output and data.')

	def get_exe_details(self):
		return self.dat.get(self.archive_key) if self.dat.get(self.archive_key) else {}

	def debug_flag(self, key):
		return self.bool_flag('DEBUG',key)

	def bool_flag(self, section, key):
		return self.ini[section][key].lower() == 'true'


	@staticmethod
	def printini(configparser):
		for section in configparser.sections():
			print(f"[{section}]")
			for key, value in configparser.items(section):
				print(f"<{key}> = <{value}>")
			print()

	@staticmethod
	def extract_timestamp(file_name):
		# Split the filename and extract the timestamp part (yyyy-mm-dd_hh-mm)
		parts = file_name.stem.split('_')			# Split by underscores
		timestamp_str = parts[3] + '_' + parts[4]	# Concatenate the date and time part

		# Convert it to a datetime object
		return datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S")

	@staticmethod
	def fileNameFormat(str):
		return str.replace(' ','_').lower()

	@staticmethod
	def get_timestamp():
		return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

	@staticmethod
	def convert_to_datetime(timestamp_str):
		if (timestamp_str):
			return datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S")
		else:
			return None

	# Method to get singular form of a word
	@staticmethod
	def tosingular(str):
		#Remove 's' from doc name if it has it
		if (len(str) > 0 and str[-1].lower() == 's'):
			return str[:-1]
		else:
			return str
		
		
