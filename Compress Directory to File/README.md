## Summary
These scripts allow for easy (compressed) backups for entire directories. 

The Powershell Backup script is used on the backend to actually do the work, the reason we call the script using CMD on the frontend is to bypass any existing Policy Execution settings for this single script.

This way of using a frontend and backend means we do not have to change the system Policy Execution settings as a whole, and can bypass any restrictions just for this script specifically.

This is generally more secure.

## Requirements
These scripts work on Windows.

## How to Run
Open the CMD Frontend file with administrative privileges. Ensure all relevant parts of both scripts are filled in with the required information. 

## Intended Result
A directory of your choice will be compressed into a single file and sent to a destination of your choosing. The filename of this compressed file will contain the date of the backup in a sustainable format (`YYYY-MM-DD`) for long term ease of use.
