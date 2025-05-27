# This is the main MTI Archving Progam that uses a menu based program to perform archiving tasks

import os
from pathlib import Path
from consolemenu import ConsoleMenu, SelectionMenu
from consolemenu.items import FunctionItem, SubmenuItem
from mti.mti_indexer import MTIIndexer
from mti.mti_config import MTIConfig, MTIDataKey, mticonfig
from wordpressmti.wbg_book_post import WPGBookAPIException
from wordpressmti import wp_loader_main
from googlemti import google_csv_loader
import traceback

def get_last_file(file_suffix):
	directory = Path(MTIConfig.output_dir)
	pattern = f'{mticonfig.archive_key}_*_{file_suffix}'
	files = list(directory.glob(pattern))

	return max(files, key=MTIConfig.extract_timestamp)

class MenuItem:
	def placeholder_func():
		print("Placeholder function for Menu Item")

	collection_settings = FunctionItem(f'Collection', placeholder_func)
	doc_type_settings	= FunctionItem(f'Document Type', placeholder_func)


def print_error_details():
	print("=========================================================================================================================")
	print("Error Trace:")
	print("=========================================================================================================================")
	traceback.print_exc()
	print("=========================================================================================================================\n")
	input("Press enter to continue.")	#TODO: Figure out how to use console-menu promput utils


# Indexer program/function to scan and index the archive folder
def launch_indexer():
	try:
		# Setup directories for archive
		os.makedirs(mticonfig.output_dir, exist_ok=True)		# Output Directory

		# Index the archive folder
		MTIIndexer.start()
		updateMenuText()

		# Load index to google (TODO: Check Google Load flag)
		google_csv_loader.load_csv_files()

		input("\nIndexing successfull! Press enter to continue.")	#TODO: Figure out how to use console-menu promput utils
	except Exception as ie:
		print("\nUnable to run Indexer!\n    !!! ", ie)
		input("Press enter to continue.")	#TODO: Figure out how to use console-menu promput utils

# WordPress loader program/function to load the new index output to WP Books Gallery Plugin
def launch_wp_loader():
	try:
		# Load wordpress
		wp_loader_main.load()

		# Update google sheet with loaded books
		google_csv_loader.update_collection_sheet()

		input("Press enter to continue.")
	except WPGBookAPIException as e:
		e.print_details()
		print_error_details()
	except Exception as e:
		print("\nUnexpected Error occured running Word Press Loader!\n")
		print_error_details()

def get_collection():
	coll_idx = SelectionMenu.get_selection(mticonfig.coll_list, f"Collection [{mticonfig.coll_name}]", "Select to change:")
	if (coll_idx < len(mticonfig.coll_list)):
		mticonfig.coll_idx = coll_idx
		MenuItem.collection_settings.text	= f"Collection   : [{mticonfig.coll_name}]"
		updateMenuText()

def get_doc_type():
	doct_idx = SelectionMenu.get_selection(mticonfig.doct_list, f"Document Type [{mticonfig.doct_name}]", "Select to change:")
	if (doct_idx < len(mticonfig.doct_list)):
		mticonfig.doct_idx = doct_idx
		MenuItem.doc_type_settings.text		= f"Document Type: [{mticonfig.doct_name}]"
		updateMenuText()

def get_settings_menu():
	menu = ConsoleMenu("Select Archive Folder")

	MenuItem.collection_settings.function	= get_collection
	MenuItem.collection_settings.text		= f"Collection Folder : [{mticonfig.coll_name}]"
	
	MenuItem.doc_type_settings.function		= get_doc_type
	MenuItem.doc_type_settings.text			= f"Document Folder: [{mticonfig.doct_name}]"

	menu.append_item(MenuItem.collection_settings)
	menu.append_item(MenuItem.doc_type_settings)

	return menu

def updateMenuText():
	menu.epilogue_text = f"Active Archive Folder [ {mticonfig.archive_sectkey} ]\n" 

	if (len(mticonfig.exe_details) == 0):
		menu.epilogue_text += "Last processed on [ Never ]\n"
	else:
		menu.epilogue_text += f"Last processed on [ {mticonfig.exe_details.get(MTIDataKey.LAST_INDEXER_RUN_DT)} ]"

def create_main_menu():
	menu = ConsoleMenu("Archiving Main Menu", clear_screen=not mticonfig.debug_flag('menu'))
	
	menu.append_item(SubmenuItem("Open Archive Folder", get_settings_menu(), menu=menu))
	menu.append_item(FunctionItem(f'Run Indexer', launch_indexer))
	menu.append_item(FunctionItem(f'Run WordPress Loader', launch_wp_loader))

	return menu

# BEGIN PROGRAM ---------------------------------------------------------------------------------------

try:

	# shutil.rmtree(temp_dir)								# Delete Existing Temp Directory??
	os.makedirs(mticonfig.temp_dir, exist_ok=True)			# Temporary Working Directory

	# Create the application menu
	menu = create_main_menu()
	updateMenuText()

	# Show the main menu
	menu.show()

	mticonfig.save_archiver_data()
except Exception as e:
	print("\nAn unxpected error occured running the Archiver Program!\n\n")
	print_error_details()


# END PROGRAM --------------------------------------------------------------------------------------------

