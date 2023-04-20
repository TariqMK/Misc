## Summary
These scripts allow for easy backups for entire directories. 

The Powershell Backup script is used on the backend to actually do the work, the reason we call the script using CMD on the frontend is to bypass any existing Policy Execution settings for this single script.

This way of using a frontend and backend means we do not have to change the system Policy Execution settings as a whole, and can bypass any restrictions just for this script specifically.

## Requirements
These scripts work on the Windows OS

## Intended Result
A directory of your choice will be compressed into a single file and sent to a destination of your choosing. The name this compressed file will have will contain the date of the backup in a sustainable format (`YYYY-MM-DD`) for long term ease of use.
