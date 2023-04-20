# Set the Date format
$YourDate = Get-Date -Format "yyyy-MM-dd"

# Set the Source/Destination Path parameters and add the Date in the above format
Compress-Archive -Path "[SOURCE FOLDER PATH]" -Destination "[DESTINATION FOLDER PATH]\[FILENAME] - $YourDate.zip"
