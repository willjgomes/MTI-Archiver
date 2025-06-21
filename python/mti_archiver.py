#---------------------------------------------------------------------------------------
# This is the main MTI Archving Progam. It is primarily a menu driven program to run
# variaous archiving tasks.  
# 
# The program also be run using command line arguments to bypass the menu, such as
# -qlaunch for quick launch of menu items
#---------------------------------------------------------------------------------------

import os, traceback, argparse
from pathlib import Path
from consolemenu import ConsoleMenu, SelectionMenu
from consolemenu.items import FunctionItem, SubmenuItem
from mti.mti_indexer import MTIIndexer
import mti.mti_updater as MTIUpdater
from mti.mti_config import MTIConfig, MTIDataKey, mticonfig
from wordpressmti.wbg_book_post import WPGBookAPIException
from wordpressmti import wp_loader_main
from googlemti import google_csv_loader

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


# Indexer option to scan and index documents in the archive folder
def launch_indexer():
	try:
		# Setup directories for archiver
		os.makedirs(mticonfig.output_dir, exist_ok=True)	

		# Run the indexer to index the archive folder
		MTIIndexer.start()
		update_menu_text()

		# Load index to google (TODO: Check Google Load flag)
		google_csv_loader.load_csv_files()

		#TODO: Figure out how to use console-menu promput utils
		input("\nIndexing successfull! Press enter to continue.")	
	except Exception as ie:
		print("\nUnable to run Indexer!\n    !!! ", ie)
		print_error_details()

# Loader function to load the new indexed documents to WordPress Books Gallery Plugin
def launch_wp_loader():
	try:
		# Run the loader to load documents/books to Wordpress
		wp_loader_main.load()

		# Update the catalog sheet with loaded books
		google_csv_loader.update_catalog_sheet()

		input("Press enter to continue.")
	except WPGBookAPIException as e:
		e.print_details()
		print_error_details()
	except Exception as e:
		print("\nUnexpected Error occured running Word Press Loader!\n")
		print_error_details()

# Updater function to make changes to loaded documents
def launch_updater():
	try:
		# Run the loader to load documents/books to Wordpress
		MTIUpdater.start()

		input("Press enter to continue.")
	except WPGBookAPIException as e:
		e.print_details()
		print_error_details()
	except Exception as e:
		print("\nUnexpected Error occured running Word Press Updater!\n")
		print_error_details()


def get_collection():
	coll_idx = SelectionMenu.get_selection(mticonfig.coll_list, 
		f"Collection [{mticonfig.coll_name}]", "Select to change:")
	
	if (coll_idx < len(mticonfig.coll_list)):
		mticonfig.coll_idx = coll_idx
		MenuItem.collection_settings.text	= f"Collection   : [{mticonfig.coll_name}]"
		update_menu_text()

def get_doc_type():
	doct_idx = SelectionMenu.get_selection(mticonfig.doct_list, 
		f"Document Type [{mticonfig.doct_name}]", "Select to change:")
	
	if (doct_idx < len(mticonfig.doct_list)):
		mticonfig.doct_idx = doct_idx
		MenuItem.doc_type_settings.text		= f"Document Type: [{mticonfig.doct_name}]"
		update_menu_text()

def get_settings_menu():
	menu = ConsoleMenu("Select Archive Folder")

	MenuItem.collection_settings.function	= get_collection
	MenuItem.collection_settings.text		= f"Collection Folder : [{mticonfig.coll_name}]"
	
	MenuItem.doc_type_settings.function		= get_doc_type
	MenuItem.doc_type_settings.text			= f"Document Folder: [{mticonfig.doct_name}]"

	menu.append_item(MenuItem.collection_settings)
	menu.append_item(MenuItem.doc_type_settings)

	return menu

def update_menu_text():
	menu.epilogue_text = f"Active Archive Folder [ {mticonfig.archive_sectkey} ]\n" 

	if (len(mticonfig.exe_details) == 0):
		menu.epilogue_text += "Last processed on [ Never ]\n"
	else:
		menu.epilogue_text += f"Last processed on [ {mticonfig.exe_details.get(MTIDataKey.LAST_INDEXER_RUN_DT)} ]"

def create_main_menu():
	menu = ConsoleMenu("Archiving Main Menu", clear_screen=not mticonfig.debug_flag('menu'))
	
	menu.append_item(SubmenuItem("Open Archive Folder", get_settings_menu(), menu=menu))
	menu.append_item(FunctionItem("Run Indexer", launch_indexer))
	menu.append_item(FunctionItem("Run WordPress Loader", launch_wp_loader))
	menu.append_item(FunctionItem("Run Updater", launch_updater))

	return menu

def quick_launch(qlaunch):
	qlaunch = qlaunch.upper()
	print("Running in quick launch mode")
	match qlaunch:
		case "INDEXER":
			launch_indexer()
		case "LOADER":
			launch_wp_loader()
		case "UPDATER":
			launch_updater()

def get_args():
	parser = argparse.ArgumentParser()
	parser.add_argument(
		'-qlaunch', metavar="MenuItemName", help='Quick launch the menu option')
		
	return parser.parse_args()

# BEGIN PROGRAM ------------------------------------------------------------------------

try:
	# Get Command line arguments
	args = get_args()

	# shutil.rmtree(temp_dir)						# Delete Existing Temp Directory??
	os.makedirs(mticonfig.temp_dir, exist_ok=True)	# Temporary Working Directory

	if args.qlaunch is not None:
		quick_launch(args.qlaunch)
	else:
		# Create the application menu
		menu = create_main_menu()
		update_menu_text()

		# Show the main menu
		menu.show()

	mticonfig.save_archiver_data()
except Exception as e:
	print("\nAn unxpected error occured running the Archiver Program!\n\n")
	print_error_details()


# END PROGRAM --------------------------------------------------------------------------------------------

