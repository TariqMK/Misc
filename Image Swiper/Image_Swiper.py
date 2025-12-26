import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import os
from pathlib import Path
import winshell
import random
from datetime import datetime
import piexif
import sqlite3

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
        self.root.title("Image Organizer - Swipe to Decide")
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
        
        # Database setup - stored next to script
        script_dir = Path(__file__).parent
        self.db_path = script_dir / "OnThisDay_cache.db"
        self.init_database()
        
        # Supported image formats (expanded)
        self.image_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif', 
            '.ico', '.heic', '.heif', '.jfif', '.ppm', '.pgm', '.pbm', '.pnm',
            '.svg', '.raw', '.cr2', '.nef', '.arw', '.dng', '.orf'
        }
        
        self.setup_ui()
        self.bind_keys()
    
    def init_database(self):
        """Initialize SQLite database for caching image metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS image_cache (
                filepath TEXT PRIMARY KEY,
                date_taken TEXT,
                file_size INTEGER,
                last_modified REAL
            )
        ''')
        conn.commit()
        conn.close()
        print(f"Database initialized at: {self.db_path}")
    
    def get_cached_date(self, img_path):
        """Get date from cache, or extract and cache it if not found"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if file exists in cache and hasn't been modified
        cursor.execute('SELECT date_taken, last_modified FROM image_cache WHERE filepath = ?', 
                      (str(img_path),))
        result = cursor.fetchone()
        
        current_mtime = img_path.stat().st_mtime
        
        # If cached and file hasn't changed, use cached date
        if result and result[1] == current_mtime:
            conn.close()
            if result[0]:
                return datetime.fromisoformat(result[0])
            return None
        
        # Otherwise, extract date and update cache
        img_date = self.extract_image_date(img_path)
        file_size = img_path.stat().st_size
        
        cursor.execute('''
            INSERT OR REPLACE INTO image_cache (filepath, date_taken, file_size, last_modified)
            VALUES (?, ?, ?, ?)
        ''', (str(img_path), 
              img_date.isoformat() if img_date else None,
              file_size,
              current_mtime))
        
        conn.commit()
        conn.close()
        
        return img_date
    
    def extract_image_date(self, img_path):
        """Extract date from EXIF data, fall back to file modification date"""
        try:
            # Try EXIF data first
            exif_data = piexif.load(str(img_path))
            if piexif.ExifIFD.DateTimeOriginal in exif_data['Exif']:
                date_str = exif_data['Exif'][piexif.ExifIFD.DateTimeOriginal].decode()
                return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
        except:
            pass
        
        # Fall back to file modification date
        try:
            return datetime.fromtimestamp(img_path.stat().st_mtime)
        except:
            return None
    
    def matches_this_day(self, img_date, reference_date=None):
        """Check if image was taken on this day in any year"""
        if img_date is None:
            return False
        if reference_date is None:
            reference_date = datetime.now()
        return img_date.month == reference_date.month and img_date.day == reference_date.day
        
    def setup_ui(self):
        # Top bar with folder selection and counter
        top_frame = tk.Frame(self.root, bg='#2b2b2b', pady=10)
        top_frame.pack(fill=tk.X)
        
        tk.Button(
            top_frame, 
            text="Select Folder", 
            command=self.select_folder,
            bg='#4CAF50',
            fg='white',
            font=('Arial', 12, 'bold'),
            padx=20,
            pady=5,
            cursor='hand2'
        ).pack(side=tk.LEFT, padx=10)
        
        self.counter_label = tk.Label(
            top_frame,
            text="No images loaded",
            bg='#2b2b2b',
            fg='white',
            font=('Arial', 12)
        )
        self.counter_label.pack(side=tk.LEFT, padx=20)
        
        # Random mode checkbox
        self.random_var = tk.BooleanVar(value=False)
        self.random_check = tk.Checkbutton(
            top_frame,
            text="Random Order",
            variable=self.random_var,
            command=self.toggle_random_mode,
            bg='#2b2b2b',
            fg='white',
            selectcolor='#1a1a1a',
            font=('Arial', 10),
            cursor='hand2'
        )
        self.random_check.pack(side=tk.LEFT, padx=10)
        
        # Include subdirectories checkbox
        self.subdirs_var = tk.BooleanVar(value=True)
        self.subdirs_check = tk.Checkbutton(
            top_frame,
            text="Include Subdirectories",
            variable=self.subdirs_var,
            command=self.toggle_subdirs,
            bg='#2b2b2b',
            fg='white',
            selectcolor='#1a1a1a',
            font=('Arial', 10),
            cursor='hand2'
        )
        self.subdirs_check.pack(side=tk.LEFT, padx=10)
        
        # On This Day checkbox
        self.this_day_var = tk.BooleanVar(value=False)
        self.this_day_check = tk.Checkbutton(
            top_frame,
            text="📅 On This Day",
            variable=self.this_day_var,
            command=self.toggle_this_day,
            bg='#2b2b2b',
            fg='#FFD700',
            selectcolor='#1a1a1a',
            font=('Arial', 10, 'bold'),
            cursor='hand2'
        )
        self.this_day_check.pack(side=tk.LEFT, padx=10)
        
        # Stats label
        self.stats_label = tk.Label(
            top_frame,
            text="Processed: 0 | Deleted: 0 | Saved: 0 MB",
            bg='#2b2b2b',
            fg='#888888',
            font=('Arial', 9)
        )
        self.stats_label.pack(side=tk.LEFT, padx=20)
        
        # Image display area
        self.canvas = tk.Canvas(
            self.root,
            bg='#1a1a1a',
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Date label (shows when photo was taken)
        self.date_label = tk.Label(
            self.root,
            text="",
            bg='#2b2b2b',
            fg='#FFD700',
            font=('Arial', 10, 'bold')
        )
        self.date_label.pack(pady=(5, 0))
        
        # Filename label
        self.path_label = tk.Label(
            self.root,
            text="",
            bg='#2b2b2b',
            fg='#888888',
            font=('Arial', 9)
        )
        self.path_label.pack(pady=(5, 0))
        
        self.filename_label = tk.Label(
            self.root,
            text="",
            bg='#2b2b2b',
            fg='#cccccc',
            font=('Arial', 10)
        )
        self.filename_label.pack(pady=(0, 5))
        
        # Button frame
        button_frame = tk.Frame(self.root, bg='#2b2b2b', pady=20)
        button_frame.pack()
        
        # Delete button (Q key)
        self.delete_btn = tk.Button(
            button_frame,
            text="✕ DELETE\n(Q)",
            command=self.delete_image,
            bg='#f44336',
            fg='white',
            font=('Arial', 14, 'bold'),
            width=15,
            height=3,
            cursor='hand2',
            state=tk.DISABLED
        )
        self.delete_btn.pack(side=tk.LEFT, padx=20)
        
        # Undo button
        self.undo_btn = tk.Button(
            button_frame,
            text="↶ UNDO\n(Backspace)",
            command=self.undo_delete,
            bg='#FF9800',
            fg='white',
            font=('Arial', 14, 'bold'),
            width=15,
            height=3,
            cursor='hand2',
            state=tk.DISABLED
        )
        self.undo_btn.pack(side=tk.LEFT, padx=20)
        
        # Keep button (W key)
        self.keep_btn = tk.Button(
            button_frame,
            text="✓ KEEP\n(W)",
            command=self.keep_image,
            bg='#4CAF50',
            fg='white',
            font=('Arial', 14, 'bold'),
            width=15,
            height=3,
            cursor='hand2',
            state=tk.DISABLED
        )
        self.keep_btn.pack(side=tk.LEFT, padx=20)
        
        # Instructions
        instructions = tk.Label(
            self.root,
            text="Keyboard shortcuts: Q = Delete | W = Keep | ← = Previous | → = Next | Backspace = Undo",
            bg='#2b2b2b',
            fg='#888888',
            font=('Arial', 9)
        )
        instructions.pack(pady=5)
        
    def bind_keys(self):
        self.root.bind('<Left>', lambda e: self.previous_image())
        self.root.bind('<Right>', lambda e: self.next_image())
        self.root.bind('q', lambda e: self.delete_image())
        self.root.bind('Q', lambda e: self.delete_image())
        self.root.bind('w', lambda e: self.keep_image())
        self.root.bind('W', lambda e: self.keep_image())
        self.root.bind('<BackSpace>', lambda e: self.undo_delete())
        
    def select_folder(self):
        folder = filedialog.askdirectory(title="Select folder with images")
        if folder:
            self.processed_count = 0
            self.deleted_count = 0
            self.space_saved_mb = 0
            self.stats_label.config(text="Processed: 0 | Deleted: 0 | Saved: 0 MB")
            self.load_images(folder)
    
    def toggle_subdirs(self):
        self.include_subdirs = self.subdirs_var.get()
    
    def toggle_this_day(self):
        """Toggle On This Day mode and reload images if folder is already selected"""
        self.on_this_day_mode = self.this_day_var.get()
        # If images are already loaded, re-filter them
        if hasattr(self, 'current_folder') and self.current_folder:
            self.load_images(self.current_folder)
            
    def load_images(self, folder):
        self.current_folder = folder
        self.images = []
        path = Path(folder)
        
        # Show loading message for On This Day mode
        if self.on_this_day_mode:
            self.counter_label.config(text="Scanning for 'On This Day' photos...")
            self.root.update()
        
        # Recursively or non-recursively find image files based on checkbox
        if self.include_subdirs:
            for ext in self.image_extensions:
                self.images.extend(path.rglob(f'*{ext}'))
                self.images.extend(path.rglob(f'*{ext.upper()}'))
        else:
            for ext in self.image_extensions:
                self.images.extend(path.glob(f'*{ext}'))
                self.images.extend(path.glob(f'*{ext.upper()}'))
        
        # Remove duplicates and sort
        self.images = sorted(list(set(self.images)))
        
        # Filter by "On This Day" if enabled
        if self.on_this_day_mode:
            total_images = len(self.images)
            filtered_images = []
            for i, img in enumerate(self.images):
                # Update progress every 100 images
                if i % 100 == 0:
                    self.counter_label.config(text=f"Scanning {i}/{total_images}...")
                    self.root.update()
                
                img_date = self.get_cached_date(img)
                if self.matches_this_day(img_date):
                    filtered_images.append((img, img_date))
            
            # Sort by year (oldest first) to show progression over years
            filtered_images.sort(key=lambda x: x[1] if x[1] else datetime.min)
            self.images = [img for img, date in filtered_images]
            
            if not self.images:
                today = datetime.now().strftime('%B %d')
                messagebox.showinfo("No Memories", f"No photos found from {today} in previous years.")
                self.counter_label.config(text="No images loaded")
                return
        
        if not self.images:
            messagebox.showinfo("No Images", "No images found in the selected folder.")
            return
        
        # Apply random order if enabled (but not in On This Day mode)
        if self.random_mode and not self.on_this_day_mode:
            random.shuffle(self.images)
            
        self.current_index = 0
        self.show_current_image()
        self.delete_btn.config(state=tk.NORMAL)
        self.keep_btn.config(state=tk.NORMAL)
    
    def toggle_random_mode(self):
        self.random_mode = self.random_var.get()
        # If images are already loaded, reshuffle or resort
        if self.images:
            if self.random_mode:
                random.shuffle(self.images)
            else:
                self.images = sorted(self.images)
            self.current_index = 0
            self.show_current_image()
        
    def show_current_image(self):
        if not self.images or self.current_index >= len(self.images):
            messagebox.showinfo("Done!", "All images have been reviewed!")
            self.delete_btn.config(state=tk.DISABLED)
            self.keep_btn.config(state=tk.DISABLED)
            self.counter_label.config(text="All done!")
            self.canvas.delete("all")
            self.path_label.config(text="")
            self.filename_label.config(text="")
            self.date_label.config(text="")
            return
            
        img_path = self.images[self.current_index]
        
        try:
            # Check if file exists (may have been deleted)
            if not img_path.exists():
                if self.current_index < len(self.images) - 1:
                    self.current_index += 1
                    self.show_current_image()
                elif self.current_index > 0:
                    self.current_index -= 1
                    self.show_current_image()
                return
            
            # Load and resize image
            if img_path.suffix.lower() in ['.heic', '.heif']:
                import pillow_heif
                heif_file = pillow_heif.read_heif(str(img_path))
                img = Image.frombytes(
                    heif_file.mode,
                    heif_file.size,
                    heif_file.data,
                    "raw",
                )
            else:
                img = Image.open(img_path)
            
            # Get canvas size
            self.root.update()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # Calculate scaling
            img_width, img_height = img.size
            scale = min(canvas_width / img_width, canvas_height / img_height, 1)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            self.photo = ImageTk.PhotoImage(img)
            
            # Display on canvas (centered)
            self.canvas.delete("all")
            x = canvas_width // 2
            y = canvas_height // 2
            self.canvas.create_image(x, y, image=self.photo, anchor=tk.CENTER)
            
            # Update labels
            self.counter_label.config(
                text=f"Image {self.current_index + 1} of {len(self.images)}"
            )
            
            # Show date when photo was taken
            img_date = self.get_cached_date(img_path)
            if img_date:
                years_ago = datetime.now().year - img_date.year
                date_text = img_date.strftime('%B %d, %Y')
                if years_ago > 0:
                    date_text += f" ({years_ago} year{'s' if years_ago != 1 else ''} ago)"
                self.date_label.config(text=f"📅 {date_text}")
            else:
                self.date_label.config(text="")
            
            self.path_label.config(text=str(img_path.parent))
            self.filename_label.config(text=img_path.name)
            
        except Exception as e:
            error_msg = f"Could not load image: {img_path.name}\n\nError: {str(e)}\n\n"
            if img_path.suffix.lower() in ['.heic', '.heif']:
                error_msg += "This is a HEIC file. Make sure you have installed:\npip install pillow-heif\n\n"
            error_msg += "Skip to next image?"
            
            if messagebox.askyesno("Error Loading Image", error_msg):
                if self.current_index < len(self.images) - 1:
                    self.current_index += 1
                    self.show_current_image()
                else:
                    messagebox.showinfo("Done!", "No more images to display.")
            
    def delete_image(self):
        if not self.images or self.current_index >= len(self.images):
            return
            
        img_path = self.images[self.current_index]
        
        try:
            file_size_bytes = img_path.stat().st_size
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            winshell.delete_file(str(img_path), no_confirm=True, allow_undo=True)
            
            # Remove from database cache when deleted
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM image_cache WHERE filepath = ?', (str(img_path),))
            conn.commit()
            conn.close()
            
            self.last_deleted = img_path
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
            
            # Re-add to cache when restored
            img_date = self.extract_image_date(self.last_deleted)
            file_size = self.last_deleted.stat().st_size
            current_mtime = self.last_deleted.stat().st_mtime
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO image_cache (filepath, date_taken, file_size, last_modified)
                VALUES (?, ?, ?, ?)
            ''', (str(self.last_deleted), 
                  img_date.isoformat() if img_date else None,
                  file_size,
                  current_mtime))
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
            messagebox.showerror("Error", f"Could not restore file: {str(e)}\nYou may need to restore it manually from Recycle Bin.")
            
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
