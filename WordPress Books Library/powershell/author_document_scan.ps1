#$foldersPath = "F:\3_Curated\MTI_Library\Books"  # Path to the root folder containing author folders
$foldersPath = "F:\2_Processing\MTC_Libarary_Temp"  # Path to the root folder containing author folders

$outputCSV = "F:\2_Processing\Script_Output\processing_booklist.csv"  # Path for the output CSV file

# Create an array to store the extracted data
$data = @()

# Initialize author folder counts
$authorsProcessedCount = 0
$authorsSkippedCount = 0

# Get all author folders
Get-ChildItem -Path $foldersPath -Directory | ForEach-Object {
    $authorFolder = $_
	#Write-Host "Processing Author Folder $($authorFolder.Name)"
		
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
			#Write-Host "Processing Book File $($bookFile.Name)"
			
            # Process book file if it conforms to book naming pattern
            if ($bookFile.Name -match '^(.*?)_' -and -not $bookFile.Name.contains("_cover")) {
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
					BookFile = $bookFile.FullName
					BookCoverFile = $bookCoverFile.FullName
                }
            }
			elseif (-not $bookFile.Name.contains("_cover")){				
				# Report an error only if it is not a cover image file
				Write-Host "Skipping Book File $($bookFile.Name): Name does not match regex pattern for book"					
			}
        }
    } else {
		$authorsSkippedCount++
		Write-Host "Skipping Author Folder $($authorFolder.Name): Name does not match regex pattern for author"		
	}
}

# Export the data to a CSV file
$data | Export-Csv -Path $outputCSV -NoTypeInformation

Write-Host "`nSummary: "
Write-Host "CSV file created at $outputCSV"
Write-Host "Author Folders Procssed: $authorsProcessedCount"
Write-Host "Author Folders Skipped : $authorsSkippedCount"