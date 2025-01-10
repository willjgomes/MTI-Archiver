# This script goes through all subdirectories in a target folder.
# If the subdirectory contains image files it will merge and convert
# all images to a PDF file.

$DocumentSource = 'C:\data\Bundle_2_on_right_side_of_White_Co-Workers_Folder'
$DocumentTarget = 'C:\data\generated\'

# This uses the Image Magick tool to combine and convert all jpg files in
# a given folder to a PDF file.
function CreatePDFFile {
	param (
		[string]$SourceFolderName,
		[string]$OutputFolderName,
		[string]$PDFName
	)

	$imageMagickPath = "C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"
	$sourcePath = $SourceFolderName + "\*.jpg"
	$outputPath = $DocumentTarget + "\" + $PDFName + ".pdf"
	
	# If the File name is too long, use default file name
	if ($outputPath.length -gt 260){
		$outputPath = $OutputFolderName + "\converted.pdf"
	}

	& $imageMagickPath $sourcePath $outputPath
}

# This function takes all the page*.jpg files and copies it into a temp Folder
# The purpose is to rename page_1 to page_9 files to page_01 to page_09, so the 
# proper order is preserved when the files are converted to PDF.
function CopyAndRenameImageFiles {
	param (
		[System.io.DirectoryInfo]$Folder
	)

	# Define the source folder and the working directory
	$sourceFolder = $Folder.FullName
	$workingDirectory = $sourceFolder + "\temp"

	# Create the working directory if it doesn't exist and copy the files
	If (-Not (Test-Path -Path $workingDirectory)) {

		Write-Host "`tCreating Temp Directory with Renamed Files"
		
		# Create the directory
		New-Item -ItemType Directory -Path $workingDirectory

		# Get the files from the source folder that match the naming pattern 'page_X'
		$files = Get-ChildItem -File $sourceFolder -Filter 'page_*'

		foreach ($file in $files) {
			# Extract the base name (e.g., "page_1") and file extension (e.g., ".txt")
			$baseName = $file.BaseName  # e.g., 'page_1'
			$extension = $file.Extension  # e.g., '.txt'

			# Extract the number from the file name (e.g., 1, 2, ..., 10)
			$fileNumber = $baseName -replace '^page_(\d+)$', '$1'

			# Check if the file name contains a single digit
			If ($fileNumber -match '^\d$') {
				# If it's a single digit, add a leading zero
				$newBaseName = 'page_' + $fileNumber.PadLeft(2, '0')
			} Else {
				# Otherwise, leave the name unchanged
				$newBaseName = $baseName
			}

			# Combine the new base name with the original file extension
			$newName = $newBaseName + $extension

			# Define the destination path
			$destinationPath = Join-Path -Path $workingDirectory -ChildPath $newName

			# Copy the file to the working directory with the new name
			Copy-Item -Path $file.FullName -Destination $destinationPath
			Write-Host "Copied and renamed $($file.Name) to $newName"
		}
	} Else {
		Write-Host "`tTemp files already created"
	}
}

function ProcessFolder {
	param (
		[System.io.DirectoryInfo]$Folder
	)

	Write-Host "$($Folder.Name)"
	$files = Get-ChildItem -File $Folder.FullName | Where-Object { $_.Extension -eq '.jpg' }
	If ($files) {
		Write-Host "`tTotal Files: `t$($files.count)"

		If ($files.count -gt 9) {
			CopyAndRenameImageFiles -Folder $Folder
			$TempFolderName = $Folder.FullName + "\temp"
			Write-Host $TempFolderName
			CreatePDFFile -SourceFolderName $TempFolderName -OutputFolderName $Folder.FullName -PDFName $Folder.Name
		} Else {
			foreach ($file in $files) {				
				Write-Host "`t$($file.Name)"
			}
			CreatePDFFile -SourceFolderName $Folder.FullName -OutputFolderName $Folder.FullName -PDFName $Folder.Name
		}

	} Else {
		Write-Host "`tThere are no files in $($Folder.Name)"
	}

	$SubFolders = Get-ChildItem -Directory $Folder.FullName
	If ($SubFolders) {
		Write-Host "`tTotal Sub-Folders: `t$($SubFolders.count)"
		foreach ($SubFolder in $SubFolders) {
			if ($SubFolder.Name -ne 'temp') {
				ProcessFolder -Folder $SubFolder
			}
		}
	}
}

####################################
# MAIN BLOXCK 
####################################

$Folders = Get-Childitem -Path $DocumentSource |
Where {$_.PSIsContainer} 

Write-Host "Processing: $($DocumentSource)"
If ($Folders) {
	foreach ($Folder in $Folders) {
		ProcessFolder -Folder $Folder
	} 
} Else {
	Write-Host "`tTarget folder is empty!"
}
