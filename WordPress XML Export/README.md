# Wordpress XML Post Export

** NOTE: This Script was generated with AI **

## Intention

If you have a wordpress.com blog (i.e. it is hosted on WordPress), the way to backup your (text based) posts is to export your entire blog to an XML file.

Unfortunately I could not find any tools which allowed me to extract my posts individually, so I made a script with the help of ChatGPT.

## Usage

Place this script in the same folder as your WordPress .xml export. This script will look for any .xml files in the same directory and attempt to export posts from it. Be aware of this if you have multiple .xml files in the run directory.

Once complete, you should see a folder called 'output_files'. Inside this will be all your exported wordpress blog posts with the original date and time of posting at the top.
