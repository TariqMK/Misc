_Disclaimer: This has been entirely coded using AI. **I have tested it a few times on my own pictures and it works without any noticable issues.** With all AI coded tools however, please exercise caution. I am not responsible for any problems._

## Purpose

On iOS there exist many apps which present to you photos one by one and you can decide to keep or delete them with a single swipe left or right respectively. Despite the long and rich history of development on Windows, I couldnt find any such tool. In fact the one that sounded like it had the closest thing to it cost $249 a YEAR.

So I 'made' this.

This script when run will present a GUI which allows us to then select a folder. All images within this folder will be presented individually and you have the option to delete (left arrow or 'd') or keep (right arrow or 'k') the image.

Images kept will remain untouched, images selected for deletion will be sent to the recycle bin.

##  Requirements

- You must have python installed on your machine
- The following packages must be installed for the script to work:

```
pip install Pillow pywin32 winshell pillow-heif piexif
```

## Usage

1. Open the script with python in the Windows Termainal (or Command Prompt directly) by entering:

```
python Image_Swiper.py
```

This will bring up the GUI

2. Press the 'Select Folder' button to select the directory with the images you want to sort. This will crawl through any subdirectories recursively too.

3. You can now start the culling process for any images you want to delete, or keep any photos you deem worthy:

<img width="1352" height="1098" alt="image" src="https://github.com/user-attachments/assets/e1c488a9-4081-4466-9a06-87599e6f3273" />

4. There is also a checkbox at the top of the application to randomise the order of photos presented for review

## Notes

- For future improvements I will consider adding video support
