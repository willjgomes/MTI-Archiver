import os, csv, re

class DocError(Exception):
   def __init__(self, message):
        self.message = message
        super().__init__(self.message)

idx_debug = []

def process_author_folder(folders_path, doct_name, index_csv, idx_debug_file, index_error_csv, debug=False):
    idx_debug = []
    idx_data = []
    idx_error = []

    authors_processed_count = 0
    document_processed_count = 0
    authors_skipped_count = 0
    document_skipped_count = 0
    error_count = 0

    #Remove 's' from doc name if it has it
    if doct_name[-1].lower() == 's':
        doct_name = doct_name[:-1]
       
    for author_folder in os.scandir(folders_path):
        if author_folder.is_dir():
            
            idx_debug.append("==========================================================================================================================")
            idx_debug.append(f"Processing Author Folder > [{author_folder.name}]")
            idx_debug.append("==========================================================================================================================")
            
            match = re.match(r"^([A-Za-z0-9.-]+)(?:_([A-Za-z0-9.-]+))?_([A-Za-z0-9.'`-]+|D(?:a|e)_(?:[A-Za-z0-9.'`-]+|La_[A-Za-z0-9.'`-]+))$", author_folder.name)
            
            if match:
                authors_processed_count += 1
                
                firstname, middlename, lastname = match.groups()
                middlename = middlename if middlename else ""
                
                for doc_file in os.scandir(author_folder.path):
                    if doc_file.is_file():                        
                        debug_msg = f"==== Processing File ==> [{doc_file.name}]"
                        idx_debug.append(debug_msg)
                        debug_idx = len(idx_debug) - 1
                        
                        try:
                            doc_record = create_doc_record(folders_path, author_folder, doct_name, doc_file, firstname, middlename, lastname)                           

                            if (len(doc_record) > 0):
                                idx_data.append(doc_record)
                                document_processed_count += 1
                            
                            idx_debug[debug_idx] = debug_msg.replace("====", "[OK]")
                        except DocError as de:                                 
                            idx_debug.append(f"    <<<<<  ERROR!  >>>> {de.message}")
                            idx_error.append({"Author Directory":author_folder.name, "File Name":doc_file.name, "Error":de.message})
                            document_skipped_count += 1
                            error_count += 1
            else:
                authors_skipped_count += 1
                error_count += 1
                idx_debug.append(f"==    <<< FOLDER ERROR >>> [{author_folder.name}]: Name does not match regex pattern for author")
                idx_error.append({"Author Directory":author_folder.name,"Error":"Folder does not appear to be an author name"})
    
    with open(index_csv, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=get_fieldnames(doct_name))
        writer.writeheader()
        writer.writerows(idx_data)

    with open(index_error_csv, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["Author Directory", "File Name", "Error"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(idx_error)

    if debug:
        with open(idx_debug_file, "w", encoding="utf-8") as file:
            file.writelines(line + "\n" for line in idx_debug)
    
    print("\nIndexing Summary (Python)")
    print(f"\t==> Author Folders Processed: {authors_processed_count}")
    print(f"\t==>     Documents Identified: {document_processed_count}")
    print(f"\t==>        Documents Skipped: {document_skipped_count}")
    print(f"\t==>")
    print(f"\t==> Author Folders Skipped : {authors_skipped_count}")
    print(f"\t==> Errors Encountered     : {error_count}")


def get_fieldnames(doct_name):
    fieldnames = [
        'First Name', 
        'Middle Name',
        'Last Name',
        f'{doct_name} Title',
        f'{doct_name} File',
        f'{doct_name} Cover File',
        'Author Folder',
        'Base Path',
    ]
    if (doct_name == 'Article'):
        fieldnames[3:1] = [
            'Date',
            'Periodical'
        ]
    return fieldnames


def create_doc_record(folders_path, author_folder, doct_name, doc_file, firstname, middlename, lastname):
    doc_record = {}
    
    #match = re.match(r"^(.*?)_", book_file.name) #matches first '_'
    match = re.match(r"^(.+)_([^_]*)$", doc_file.name)
    if match and "_cover" not in doc_file.name:
                            
        title = match.group(1).replace('-', ' ')                            
        cover_file_name = match.group(1) + "_cover"
        cover_file = next((f.name for f in os.scandir(author_folder.path) if f.is_file() and f.name.startswith(cover_file_name)), "")
                            
        # Initialize doc details dictionary record
        doc_record = {
            "First Name": firstname,
            "Middle Name": middlename,
            "Last Name": lastname,
            f"{doct_name} Title": title,
            f"{doct_name} File": doc_file.name,
            f"{doct_name} Cover File": cover_file,
            "Author Folder": author_folder.name,
            "Base Path": folders_path
        }

        doc_record = add_doc_details(doct_name, doc_record)
    elif "_cover" not in doc_file.name:
        raise DocError(f"{doct_name} not properly named. Title does not match regex pattern.")

    return doc_record
    
def add_doc_details(doct_name, doc_record):
    if (doct_name == 'Article'):
        title = doc_record.get('Article Title')
        parts = title.split('_')

        if len(parts) > 3:
            raise DocError(f"{doct_name} file not properly named, too many underscores.")
        elif len(parts) < 3:
            raise DocError(f"{doct_name} file not properly named, too few underscores.")

        date, periodical, title, *_ = tuple(parts)

        doc_record.update({
            "Date":date.replace(" ", "-"),
            "Periodical":periodical,
            "Article Title":title
        })

    return doc_record
