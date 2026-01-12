import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import os
from pathlib import Path
import winshell
import random
from datetime import datetime
import piexif
import sqlite3
import subprocess
import sys

# Register HEIC support
heic_support = False
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    heic_support = True
    print("HEIC support enabled")
except Exception as e:
    print(f"WARNING: HEIC support not available: {e}")

class ImageOrganizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Image & Video Organizer - Swipe to Decide")
        self.root.geometry("900x700")
        self.root.configure(bg='#2b2b2b')
        
        self.images = []
        self.current_index = 0
        self.photo = None
        self.random_mode = False
        self.include_subdirs = True
        self.on_this_day_mode = False
        self.last_deleted = None
        self.last_deleted_size = 0
        self.processed_count = 0
        self.deleted_count = 0
        self.space_saved_mb = 0
        self.current_file_is_video = False
        
        # Database setup
        script_dir = Path(__file__).parent
        self.db_path = script_dir / "OnThisDay_cache.db"
        self.thumbnails_dir = script_dir / "OnThisDay_thumbnails"
        self.thumbnails_dir.mkdir(exist_ok=True)
        self.init_database()
        
        # Check for ffmpeg
        self.ffmpeg_available = self.check_ffmpeg()
        if not self.ffmpeg_available:
            print("WARNING: ffmpeg not found. Video thumbnails will not be generated.")
            print("Install ffmpeg and add to PATH for video support.")
        
        # Supported formats
        self.image_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif', 
            '.ico', '.heic', '.heif', '.jfif', '.ppm', '.pgm', '.pbm', '.pnm',
            '.svg', '.raw', '.cr2', '.nef', '.arw', '.dng', '.orf'
        }
        
        self.video_extensions = {
            '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v',
            '.mpg', '.mpeg', '.3gp', '.m2ts', '.mts', '.ts', '.vob', '.ogv'
        }
        
        self.setup_ui()
        self.bind_keys()
    
    def check_ffmpeg(self):
        try:
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except:
            return False
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS image_cache (
                filepath TEXT PRIMARY KEY,
                date_taken TEXT,
                file_size INTEGER,
                last_modified REAL,
                is_video INTEGER,
                thumbnail_path TEXT
            )
        ''')
        
        # Migration: Add is_video and thumbnail_path columns if they don't exist
        try:
            cursor.execute("SELECT is_video FROM image_cache LIMIT 1")
        except sqlite3.OperationalError:
            print("Migrating database: adding is_video column...")
            cursor.execute("ALTER TABLE image_cache ADD COLUMN is_video INTEGER DEFAULT 0")
        
        try:
            cursor.execute("SELECT thumbnail_path FROM image_cache LIMIT 1")
        except sqlite3.OperationalError:
            print("Migrating database: adding thumbnail_path column...")
            cursor.execute("ALTER TABLE image_cache ADD COLUMN thumbnail_path TEXT")
        
        conn.commit()
        conn.close()
        print(f"Database initialized at: {self.db_path}")
    
    def get_video_date(self, video_path):
        if not self.ffmpeg_available:
            return datetime.fromtimestamp(video_path.stat().st_mtime)
        
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json', 
                 '-show_entries', 'format_tags=creation_time', str(video_path)],
                capture_output=True, text=True, timeout=5
            )
            
            import json
            data = json.loads(result.stdout)
            
            if 'format' in data and 'tags' in data['format']:
                creation_time = data['format']['tags'].get('creation_time')
                if creation_time:
                    # Parse ISO 8601 format and remove timezone info for consistency
                    dt = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
                    return dt.replace(tzinfo=None)  # Strip timezone
        except:
            pass
        
        return datetime.fromtimestamp(video_path.stat().st_mtime)
    
    def generate_video_thumbnail(self, video_path):
        if not self.ffmpeg_available:
            return None
        
        thumb_name = f"{hash(str(video_path))}.jpg"
        thumb_path = self.thumbnails_dir / thumb_name
        
        if thumb_path.exists():
            return thumb_path
        
        try:
            subprocess.run(
                ['ffmpeg', '-i', str(video_path), '-ss', '00:00:01', 
                 '-vframes', '1', '-q:v', '2', str(thumb_path)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=True
            )
            
            if thumb_path.exists():
                return thumb_path
        except:
            pass
        
        return None
    
    def get_cached_date(self, file_path):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT date_taken, last_modified FROM image_cache WHERE filepath = ?', (str(file_path),))
        result = cursor.fetchone()
        
        current_mtime = file_path.stat().st_mtime
        
        if result and result[1] == current_mtime:
            conn.close()
            if result[0]:
                return datetime.fromisoformat(result[0])
            return None
        
        is_video = file_path.suffix.lower() in self.video_extensions
        
        if is_video:
            file_date = self.get_video_date(file_path)
            thumbnail_path = self.generate_video_thumbnail(file_path)
        else:
            file_date = self.extract_image_date(file_path)
            thumbnail_path = None
        
        file_size = file_path.stat().st_size
        
        cursor.execute('''
            INSERT OR REPLACE INTO image_cache (filepath, date_taken, file_size, last_modified, is_video, thumbnail_path)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (str(file_path), file_date.isoformat() if file_date else None, file_size, current_mtime,
              1 if is_video else 0, str(thumbnail_path) if thumbnail_path else None))
        
        conn.commit()
        conn.close()
        
        return file_date
    
    def extract_image_date(self, img_path):
        try:
            exif_data = piexif.load(str(img_path))
            if piexif.ExifIFD.DateTimeOriginal in exif_data['Exif']:
                date_str = exif_data['Exif'][piexif.ExifIFD.DateTimeOriginal].decode()
                return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
        except:
            pass
        
        try:
            return datetime.fromtimestamp(img_path.stat().st_mtime)
        except:
            return None
    
    def matches_this_day(self, file_date, reference_date=None):
        if file_date is None:
            return False
        if reference_date is None:
            reference_date = datetime.now()
        return file_date.month == reference_date.month and file_date.day == reference_date.day
    
    def is_video_file(self, file_path):
        return file_path.suffix.lower() in self.video_extensions
        
    def setup_ui(self):
        top_frame = tk.Frame(self.root, bg='#2b2b2b', pady=10)
        top_frame.pack(fill=tk.X)
        
        tk.Button(top_frame, text="Select Folder", command=self.select_folder, bg='#4CAF50', fg='white',
                 font=('Arial', 12, 'bold'), padx=20, pady=5, cursor='hand2').pack(side=tk.LEFT, padx=10)
        
        tk.Button(top_frame, text="🧹 Clean Thumbnails", command=self.clean_thumbnails, bg='#9C27B0', fg='white',
                 font=('Arial', 10), padx=15, pady=5, cursor='hand2').pack(side=tk.LEFT, padx=5)
        
        self.counter_label = tk.Label(top_frame, text="No files loaded", bg='#2b2b2b', fg='white', font=('Arial', 12))
        self.counter_label.pack(side=tk.LEFT, padx=20)
        
        self.random_var = tk.BooleanVar(value=False)
        tk.Checkbutton(top_frame, text="Random Order", variable=self.random_var, command=self.toggle_random_mode,
                      bg='#2b2b2b', fg='white', selectcolor='#1a1a1a', font=('Arial', 10), cursor='hand2').pack(side=tk.LEFT, padx=10)
        
        self.subdirs_var = tk.BooleanVar(value=True)
        tk.Checkbutton(top_frame, text="Include Subdirectories", variable=self.subdirs_var, command=self.toggle_subdirs,
                      bg='#2b2b2b', fg='white', selectcolor='#1a1a1a', font=('Arial', 10), cursor='hand2').pack(side=tk.LEFT, padx=10)
        
        self.this_day_var = tk.BooleanVar(value=False)
        tk.Checkbutton(top_frame, text="📅 On This Day", variable=self.this_day_var, command=self.toggle_this_day,
                      bg='#2b2b2b', fg='#FFD700', selectcolor='#1a1a1a', font=('Arial', 10, 'bold'), cursor='hand2').pack(side=tk.LEFT, padx=10)
        
        self.stats_label = tk.Label(top_frame, text="Processed: 0 | Deleted: 0 | Saved: 0 MB",
                                    bg='#2b2b2b', fg='#888888', font=('Arial', 9))
        self.stats_label.pack(side=tk.LEFT, padx=20)
        
        self.canvas = tk.Canvas(self.root, bg='#1a1a1a', highlightthickness=0, cursor='hand2')
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.canvas.bind('<Button-1>', self.on_canvas_click)
        
        self.date_label = tk.Label(self.root, text="", bg='#2b2b2b', fg='#FFD700', font=('Arial', 10, 'bold'))
        self.date_label.pack(pady=(5, 0))
        
        self.media_type_label = tk.Label(self.root, text="", bg='#2b2b2b', fg='#00BFFF', font=('Arial', 9, 'italic'))
        self.media_type_label.pack(pady=(0, 5))
        
        self.path_label = tk.Label(self.root, text="", bg='#2b2b2b', fg='#888888', font=('Arial', 9))
        self.path_label.pack(pady=(5, 0))
        
        self.filename_label = tk.Label(self.root, text="", bg='#2b2b2b', fg='#cccccc', font=('Arial', 10))
        self.filename_label.pack(pady=(0, 5))
        
        button_frame = tk.Frame(self.root, bg='#2b2b2b', pady=20)
        button_frame.pack()
        
        self.delete_btn = tk.Button(button_frame, text="✕ DELETE\n(Q)", command=self.delete_image, bg='#f44336', fg='white',
                                    font=('Arial', 14, 'bold'), width=15, height=3, cursor='hand2', state=tk.DISABLED)
        self.delete_btn.pack(side=tk.LEFT, padx=20)
        
        self.undo_btn = tk.Button(button_frame, text="↶ UNDO\n(Backspace)", command=self.undo_delete, bg='#FF9800', fg='white',
                                  font=('Arial', 14, 'bold'), width=15, height=3, cursor='hand2', state=tk.DISABLED)
        self.undo_btn.pack(side=tk.LEFT, padx=20)
        
        self.keep_btn = tk.Button(button_frame, text="✓ KEEP\n(W)", command=self.keep_image, bg='#4CAF50', fg='white',
                                  font=('Arial', 14, 'bold'), width=15, height=3, cursor='hand2', state=tk.DISABLED)
        self.keep_btn.pack(side=tk.LEFT, padx=20)
        
        tk.Label(self.root, text="Keyboard: Q = Delete | W = Keep | ← = Previous | → = Next | Backspace = Undo | Click video to play",
                bg='#2b2b2b', fg='#888888', font=('Arial', 9)).pack(pady=5)
        
    def bind_keys(self):
        self.root.bind('<Left>', lambda e: self.previous_image())
        self.root.bind('<Right>', lambda e: self.next_image())
        self.root.bind('q', lambda e: self.delete_image())
        self.root.bind('Q', lambda e: self.delete_image())
        self.root.bind('w', lambda e: self.keep_image())
        self.root.bind('W', lambda e: self.keep_image())
        self.root.bind('<BackSpace>', lambda e: self.undo_delete())
    
    def on_canvas_click(self, event):
        if self.current_file_is_video and self.images and self.current_index < len(self.images):
            file_path = self.images[self.current_index]
            try:
                if sys.platform == 'win32':
                    os.startfile(str(file_path))
                elif sys.platform == 'darwin':
                    subprocess.run(['open', str(file_path)])
                else:
                    subprocess.run(['xdg-open', str(file_path)])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open video: {str(e)}")
    
    def clean_thumbnails(self):
        """Remove orphaned thumbnails for videos that no longer exist"""
        if not self.thumbnails_dir.exists():
            messagebox.showinfo("Clean Thumbnails", "No thumbnails folder found.")
            return
        
        try:
            # Get all thumbnail files
            thumbnail_files = list(self.thumbnails_dir.glob('*.jpg'))
            
            if not thumbnail_files:
                messagebox.showinfo("Clean Thumbnails", "No thumbnails to clean.")
                return
            
            # Get all video paths from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT filepath, thumbnail_path FROM image_cache WHERE is_video = 1')
            video_records = cursor.fetchall()
            conn.close()
            
            orphaned = []
            for thumb_file in thumbnail_files:
                # Check if this thumbnail belongs to an existing video
                is_orphaned = True
                for video_path, thumb_path in video_records:
                    if thumb_path and Path(thumb_path) == thumb_file:
                        # Check if the video still exists
                        if Path(video_path).exists():
                            is_orphaned = False
                            break
                
                if is_orphaned:
                    orphaned.append(thumb_file)
            
            if not orphaned:
                messagebox.showinfo("Clean Thumbnails", "No orphaned thumbnails found. All clean!")
                return
            
            # Ask for confirmation
            size_mb = sum(f.stat().st_size for f in orphaned) / (1024 * 1024)
            if messagebox.askyesno("Clean Thumbnails", 
                                  f"Found {len(orphaned)} orphaned thumbnail(s) ({size_mb:.1f} MB).\n\nDelete them?"):
                for thumb_file in orphaned:
                    thumb_file.unlink()
                
                messagebox.showinfo("Clean Thumbnails", 
                                   f"Deleted {len(orphaned)} orphaned thumbnail(s), freed {size_mb:.1f} MB.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not clean thumbnails: {str(e)}")
        
    def select_folder(self):
        folder = filedialog.askdirectory(title="Select folder with images and videos")
        if folder:
            self.processed_count = 0
            self.deleted_count = 0
            self.space_saved_mb = 0
            self.stats_label.config(text="Processed: 0 | Deleted: 0 | Saved: 0 MB")
            self.load_images(folder)
    
    def toggle_subdirs(self):
        self.include_subdirs = self.subdirs_var.get()
    
    def toggle_this_day(self):
        self.on_this_day_mode = self.this_day_var.get()
        if hasattr(self, 'current_folder') and self.current_folder:
            self.load_images(self.current_folder)
            
    def load_images(self, folder):
        self.current_folder = folder
        self.images = []
        path = Path(folder)
        
        if self.on_this_day_mode:
            self.counter_label.config(text="Scanning for 'On This Day' files...")
            self.root.update()
        
        all_extensions = self.image_extensions | self.video_extensions
        
        if self.include_subdirs:
            for ext in all_extensions:
                self.images.extend(path.rglob(f'*{ext}'))
                self.images.extend(path.rglob(f'*{ext.upper()}'))
        else:
            for ext in all_extensions:
                self.images.extend(path.glob(f'*{ext}'))
                self.images.extend(path.glob(f'*{ext.upper()}'))
        
        self.images = sorted(list(set(self.images)))
        
        if self.on_this_day_mode:
            total_files = len(self.images)
            filtered_files = []
            for i, file in enumerate(self.images):
                if i % 100 == 0:
                    self.counter_label.config(text=f"Scanning {i}/{total_files}...")
                    self.root.update()
                
                file_date = self.get_cached_date(file)
                if self.matches_this_day(file_date):
                    # Strip timezone if present for consistent sorting
                    if file_date and file_date.tzinfo is not None:
                        file_date = file_date.replace(tzinfo=None)
                    filtered_files.append((file, file_date))
            
            filtered_files.sort(key=lambda x: x[1] if x[1] else datetime.min)
            self.images = [file for file, date in filtered_files]
            
            if not self.images:
                today = datetime.now().strftime('%B %d')
                messagebox.showinfo("No Memories", f"No photos or videos found from {today} in previous years.")
                self.counter_label.config(text="No files loaded")
                return
        
        if not self.images:
            messagebox.showinfo("No Files", "No images or videos found in the selected folder.")
            return
        
        if self.random_mode and not self.on_this_day_mode:
            random.shuffle(self.images)
            
        self.current_index = 0
        self.show_current_image()
        self.delete_btn.config(state=tk.NORMAL)
        self.keep_btn.config(state=tk.NORMAL)
    
    def toggle_random_mode(self):
        self.random_mode = self.random_var.get()
        if self.images:
            if self.random_mode:
                random.shuffle(self.images)
            else:
                self.images = sorted(self.images)
            self.current_index = 0
            self.show_current_image()
    
    def create_play_overlay(self, img):
        draw = ImageDraw.Draw(img, 'RGBA')
        width, height = img.size
        
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 100))
        img = Image.alpha_composite(img.convert('RGBA'), overlay)
        
        center_x, center_y = width // 2, height // 2
        triangle_size = min(width, height) // 6
        
        draw = ImageDraw.Draw(img)
        points = [(center_x - triangle_size//2, center_y - triangle_size),
                 (center_x - triangle_size//2, center_y + triangle_size),
                 (center_x + triangle_size, center_y)]
        draw.polygon(points, fill=(255, 255, 255, 200))
        
        text = "Click to play in VLC"
        text_x = center_x - len(text) * 3
        text_y = center_y + triangle_size + 20
        draw.text((text_x, text_y), text, fill=(255, 255, 255, 230))
        
        return img.convert('RGB')
        
    def show_current_image(self):
        if not self.images or self.current_index >= len(self.images):
            messagebox.showinfo("Done!", "All files have been reviewed!")
            self.delete_btn.config(state=tk.DISABLED)
            self.keep_btn.config(state=tk.DISABLED)
            self.counter_label.config(text="All done!")
            self.canvas.delete("all")
            self.path_label.config(text="")
            self.filename_label.config(text="")
            self.date_label.config(text="")
            self.media_type_label.config(text="")
            return
            
        file_path = self.images[self.current_index]
        
        try:
            if not file_path.exists():
                if self.current_index < len(self.images) - 1:
                    self.current_index += 1
                    self.show_current_image()
                elif self.current_index > 0:
                    self.current_index -= 1
                    self.show_current_image()
                return
            
            self.current_file_is_video = self.is_video_file(file_path)
            
            if self.current_file_is_video:
                thumb_path = self.generate_video_thumbnail(file_path)
                if thumb_path and thumb_path.exists():
                    img = Image.open(thumb_path)
                    img = self.create_play_overlay(img)
                else:
                    img = Image.new('RGB', (800, 600), color='#1a1a1a')
                    draw = ImageDraw.Draw(img)
                    text = "Video Preview Unavailable\nClick to play in VLC"
                    draw.text((400, 300), text, fill='white', anchor='mm')
                
                self.media_type_label.config(text="🎬 VIDEO (click to play)")
            else:
                if file_path.suffix.lower() in ['.heic', '.heif']:
                    try:
                        import pillow_heif
                        heif_file = pillow_heif.read_heif(str(file_path))
                        img = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw")
                    except Exception as heic_error:
                        try:
                            img = Image.open(file_path)
                        except:
                            raise heic_error
                else:
                    img = Image.open(file_path)
                
                self.media_type_label.config(text="📷 IMAGE")
            
            self.root.update()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            img_width, img_height = img.size
            scale = min(canvas_width / img_width, canvas_height / img_height, 1)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            self.photo = ImageTk.PhotoImage(img)
            
            self.canvas.delete("all")
            x = canvas_width // 2
            y = canvas_height // 2
            self.canvas.create_image(x, y, image=self.photo, anchor=tk.CENTER)
            
            self.counter_label.config(text=f"File {self.current_index + 1} of {len(self.images)}")
            
            file_date = self.get_cached_date(file_path)
            if file_date:
                years_ago = datetime.now().year - file_date.year
                date_text = file_date.strftime('%B %d, %Y')
                if years_ago > 0:
                    date_text += f" ({years_ago} year{'s' if years_ago != 1 else ''} ago)"
                self.date_label.config(text=f"📅 {date_text}")
            else:
                self.date_label.config(text="")
            
            self.path_label.config(text=str(file_path.parent))
            self.filename_label.config(text=file_path.name)
            
        except Exception as e:
            error_msg = f"Could not load file: {file_path.name}\n\nError: {str(e)}\n\nSkip to next file?"
            if file_path.suffix.lower() in ['.heic', '.heif']:
                error_msg = f"HEIC Error: {str(e)}\nTry: pip install pillow-heif\n\nSkip?"
            
            if messagebox.askyesno("Error Loading File", error_msg):
                if self.current_index < len(self.images) - 1:
                    self.current_index += 1
                    self.show_current_image()
                else:
                    messagebox.showinfo("Done!", "No more files to display.")
            
    def delete_image(self):
        if not self.images or self.current_index >= len(self.images):
            return
            
        file_path = self.images[self.current_index]
        
        try:
            file_size_bytes = file_path.stat().st_size
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            winshell.delete_file(str(file_path), no_confirm=True, allow_undo=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM image_cache WHERE filepath = ?', (str(file_path),))
            conn.commit()
            conn.close()
            
            self.last_deleted = file_path
            self.last_deleted_size = file_size_mb
            self.undo_btn.config(state=tk.NORMAL)
            self.deleted_count += 1
            self.processed_count += 1
            self.space_saved_mb += file_size_mb
            self.stats_label.config(text=f"Processed: {self.processed_count} | Deleted: {self.deleted_count} | Saved: {self.space_saved_mb:.1f} MB")
            self.current_index += 1
            self.show_current_image()
        except Exception as e:
            messagebox.showerror("Error", f"Could not delete file: {str(e)}")
    
    def undo_delete(self):
        if not self.last_deleted:
            return
        
        try:
            winshell.undelete(str(self.last_deleted))
            
            is_video = self.is_video_file(self.last_deleted)
            
            if is_video:
                file_date = self.get_video_date(self.last_deleted)
                thumbnail_path = self.generate_video_thumbnail(self.last_deleted)
            else:
                file_date = self.extract_image_date(self.last_deleted)
                thumbnail_path = None
            
            file_size = self.last_deleted.stat().st_size
            current_mtime = self.last_deleted.stat().st_mtime
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO image_cache (filepath, date_taken, file_size, last_modified, is_video, thumbnail_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (str(self.last_deleted), file_date.isoformat() if file_date else None, file_size, current_mtime,
                  1 if is_video else 0, str(thumbnail_path) if thumbnail_path else None))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Undo", f"Restored: {self.last_deleted.name}")
            self.last_deleted = None
            self.undo_btn.config(state=tk.DISABLED)
            self.deleted_count -= 1
            self.processed_count -= 1
            self.space_saved_mb -= self.last_deleted_size
            self.last_deleted_size = 0
            self.stats_label.config(text=f"Processed: {self.processed_count} | Deleted: {self.deleted_count} | Saved: {self.space_saved_mb:.1f} MB")
        except Exception as e:
            messagebox.showerror("Error", f"Could not restore file: {str(e)}\nRestore manually from Recycle Bin.")
            
    def keep_image(self):
        if not self.images or self.current_index >= len(self.images):
            return
            
        self.processed_count += 1
        self.stats_label.config(text=f"Processed: {self.processed_count} | Deleted: {self.deleted_count} | Saved: {self.space_saved_mb:.1f} MB")
        self.current_index += 1
        self.show_current_image()
    
    def previous_image(self):
        if not self.images:
            return
        original_index = self.current_index
        while self.current_index > 0:
            self.current_index -= 1
            if self.images[self.current_index].exists():
                self.show_current_image()
                return
        self.current_index = original_index
    
    def next_image(self):
        if not self.images:
            return
        self.processed_count += 1
        self.stats_label.config(text=f"Processed: {self.processed_count} | Deleted: {self.deleted_count} | Saved: {self.space_saved_mb:.1f} MB")
        original_index = self.current_index
        while self.current_index < len(self.images) - 1:
            self.current_index += 1
            if self.images[self.current_index].exists():
                self.show_current_image()
                return
        self.current_index = original_index

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageOrganizer(root)
    root.mainloop()
