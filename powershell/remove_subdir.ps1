# This script removes all subdirectories from the 
# direcotires contained in the target folder.
$TargetFolder = 'F:\Temp'
$excludeFolders = @('testdir','testdir2')
$Folders = Get-Childitem -path $Targetfolder |
Where {$_.psIsContainer} 

If ($Folders) {

 foreach ($Folder in $Folders) {
   Write-Host "Processing Folder $($Folder.Name)"
   $items = Get-ChildItem -Path $Folder.FullName

 If ($items) {

	foreach ($item in $items) {
     Write-Host "Removing: $($item.FullName)"
     $item | Remove-Item -Recurse -Verbose
   } 
 } Else {
    Write-Host "There are no items to remove in $($Folder.Name)"
 }

   } 
 
}  Else {
	Write-Host "There are no folders to empty'"
}