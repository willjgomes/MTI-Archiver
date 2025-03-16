import configparser, json
from datetime import datetime
from pathlib import Path
import stat
from xml.sax.handler import property_declaration_handler

class MTIDataKey:
	LAST_INDEXER_RUN_DT	= "Index Run Date Time"
	LAST_IDX_GEN_DT		= "Last Index Generated"


class MTIConfig:

	idtab = "\t==>"

	# Script Paths
	script_dir		= Path(__file__).parent.parent
	temp_dir		= script_dir / 'temp'
	settings_file	= script_dir / 'settings' / 'archive.ini'
	data_file		= script_dir / 'settings' / 'mtiarchiver.dat'
	indexer_script	= script_dir / 'powershell' / 'author_document_scan.ps1'

	def __init__(self):
		# Get config from settings file
		self.ini = self.load_config()

		# Set some default config attributes
		self.output_dir		= self.ini['Settings']['ScriptDataFolder']
		self.coll_list	= [str.strip() for str in self.ini['Settings']['Collections'].split(",")]
		self.doct_list	= [str.strip() for str in self.ini['Settings']['DocumentTypes'].strip().split(",")]

		# Default the active Collection and DocumentType to 0 (TODO: Load from dat file)
		self.coll_idx	= 0
		self.doct_idx	= 0

		# Get the JSON data previous execution details and intialize default details for collection
		self.dat, self.exe_details = self.load_execution_details()

	# Define Active Collection and Document Type property to store active Settings during execution
	# This are defined this way to prevent setting of these properties directly, as it is controlled
	# by the index value of the selection and additional operations need to be performed for key and
	# name values when reset. Didn't use getter()/setter() function paradigm to keep it consistent 
	# with other config property access.
	#----------------------------------------------------------------------------------------------
	@property
	def coll_idx(self):
		return self._coll_idx

	@coll_idx.setter
	def coll_idx(self, new_value):
		self._coll_idx = new_value
		self._coll_key = MTIConfig.fileNameFormat(self.coll_list[self.coll_idx])

	@property
	def coll_name(self):
		return self.coll_list[self.coll_idx]

	@property
	def doct_idx(self):
		return self._coll_idx

	@doct_idx.setter
	def doct_idx(self, new_value):
		self._doct_idx = new_value
		self._doct_key = MTIConfig.fileNameFormat(self.doct_list[self.doct_idx])

	@property
	def doct_name(self):
		return self.doct_list[self.doct_idx]

	@property
	def coll_doct_key(self):
		return f'{self._coll_key}_{self._doct_key}'

	@property
	def coll_doct_sectkey(self):
		return f'{self.coll_name}:{self.doct_name}'

	#----------------------------------------------------------------------------------------------

	def load_config(self):
		_config_parser = configparser.ConfigParser()

		try:
			with open(MTIConfig.settings_file) as f:
				print("Settings File Detected:\n\t==>", MTIConfig.settings_file)
				_config_parser.read_file(f)
		except IOError:
			print("Settings file not found")

		return _config_parser

	def load_execution_details(self):
		data = {}
		details = {}
		# Load existing data
		try:
			with open(MTIConfig.data_file, 'r') as file:
				data = json.load(file)
			details = data[self.coll_doct_key]
		except IOError:
			print('WARNING: Missing previous execution data.')
	
		return data,details

	def save_execution_details(self):
		self.dat[self.coll_doct_key] = self.exe_details

		try:
			with open(MTIConfig.data_file, 'w') as file:
				json.dump(self.dat, file, indent=4)
		
			print("Program settings saved.")
		except IOError:
			print('ERROR Saving execution details. Please verify output and loading.')


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

