# This powershell script is used to index all the documents found a book cateogry type folder by author name and 
# documen(s) of the author.  The purpose of this indexing file is as follows:
#
# 1) Provide an index for the loader process to find and load all documents
# 2) Ensure the proper author formatting and file processing is followed
# 3) Use for comparison of folders processed between runs
#

#Input Parameters
param (
	[string]$foldersPath,		#Path to authors folder (empty folder processes current directory)
	[string]$outputCSV,			#Path to output filename
    [switch]$Debug				#Turn on debugging
)

# Set parameters for quick testing
# $foldersPath = "F:\3_Curated\MTI_Library\Books"	
# $outputCSV = "C:\data\local_booklist.csv"  # Path for the output CSV file

if ($Debug) {
    $DebugPreference = "Continue"
	Write-Debug "Debugging output for indexing process"
}

# Create an array to store the extracted data
$data = @()

# Initialize counts
$authorsProcessedCount = 0
$documentProcessedCount = 0
$authorsSkippedCount = 0
$documentSkippedCount = 0
$errorCount = 0

Write-Information "Author Directory, File Name, Error"

# Get all author folders
Get-ChildItem -Path $foldersPath -Directory | ForEach-Object {
    $authorFolder = $_
	Write-Debug "Processing Author Folder > [$($authorFolder.Name)]"
		
	# Author Name Regex Version 1: This does not handle De, De La, or Da for last name
	#if ($authorFolder.Name -match "^([A-Za-z0-9.-]+)(?:_([A-Za-z0-9.-]+))?_([A-Za-z0-9.'`-]+)$") {

	# Process Author Folders if it can be split into first, middle, and/or last name components 
	# allowing various formats (e.g., F.M._Last, F._Middle_last, Firs_Last, etc. allows hypens, apostropes in last name)
	if ($authorFolder.Name -match "^([A-Za-z0-9.-]+)(?:_([A-Za-z0-9.-]+))?_([A-Za-z0-9.'`-]+|D(?:a|e)_(?:[A-Za-z0-9.'`-]+|La_[A-Za-z0-9.'`-]+))$") {	
		$authorsProcessedCount++

		# Store the first, middle, and last parts
		$firstname = $matches[1]  # First word
		$middlename = if ($matches[2]) { $matches[2] } else { "" }  # Middle word (optional)
		$lastname = $matches[3]  # Last word (mandatory)
		
        # Get all book files within the author folder
        Get-ChildItem -Path $authorFolder.FullName -File | ForEach-Object {
			$bookFile = $_
			Write-Debug "== Processing File > [$($bookFile.Name)]"
			
            # Process book file if it conforms to book naming pattern
            if ($bookFile.Name -match '^(.*?)_' -and -not $bookFile.Name.contains("_cover")) {
				$documentProcessedCount++
                # Get the book title
				$bookTitle = $matches[1] -replace '-', ' '

				# Get the cover image file if it exists
				$bookCoverFileName = $matches[1] + "_cover"
				$bookCoverFile = Get-ChildItem -Path $bookFile.DirectoryName -File | Where-Object { $_.BaseName -eq $bookCoverFileName }
				
                # Add the extracted information to the data array that will be written to CSV
                $data += [PSCustomObject]@{
                    FirstName = $firstname
                    MiddleName = $middlename
                    LastName = $lastname
                    BookTitle = $bookTitle
					BookFile = $bookFile.Name
					BookCoverFile = $bookCoverFile.Name
					AuthorFolder = $authorFolder.Name
					BasePath = $foldersPath
                }
            }
			elseif (-not $bookFile.Name.contains("_cover")){				
				# Report an error only if it is not a cover image file
				Write-Debug "== Skipping File >>> [$($bookFile.Name)]: Name does not match regex pattern for book"
				Write-Information "$($bookFile.DirectoryName), $($bookFile.Name), File not properly named "
				$documentSkippedCount
				$errorCount++
			}
        }
    } else {
		$authorsSkippedCount++
		$errorCount++
		Write-Debug "Skipping Author Folder   > [$($authorFolder.Name)]: Name does not match regex pattern for author"
		Write-Information "$($authorFolder.Name), , Folder does not appear to be an author name "
	}
}

# Export the data to a CSV file
$data | Export-Csv -Path $outputCSV -NoTypeInformation

Write-Output "`Indexing Summary (Powershell) "
Write-Output "`t==> Index file created: at $outputCSV"
Write-Output "`t==> Author Folders Procssed: $authorsProcessedCount"
Write-Output "`t==> Author Folders Skipped : $authorsSkippedCount (Docs in these folder not procssed)"
Write-Output "`t==> Documents Identified   : $documentProcessedCount"
Write-Output "`t==> Documents Skipped      : $documentSkippedCount"
Write-Output "`t==> Document Errors        : $errorCount (See ...Index_Error.csv file)"