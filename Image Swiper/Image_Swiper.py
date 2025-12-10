import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import os
from pathlib import Path
import winshell
import random

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
        self.last_deleted = None  # Track last deleted image for undo
        
        # Supported image formats (expanded)
        self.image_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif', 
            '.ico', '.heic', '.heif', '.jfif', '.ppm', '.pgm', '.pbm', '.pnm',
            '.svg', '.raw', '.cr2', '.nef', '.arw', '.dng', '.orf'
        }
        
        self.setup_ui()
        self.bind_keys()
        
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
        
        # Image display area
        self.canvas = tk.Canvas(
            self.root,
            bg='#1a1a1a',
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Filename label
        self.filename_label = tk.Label(
            self.root,
            text="",
            bg='#2b2b2b',
            fg='#cccccc',
            font=('Arial', 10)
        )
        self.filename_label.pack(pady=5)
        
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
            self.load_images(folder)
            
    def load_images(self, folder):
        self.images = []
        path = Path(folder)
        
        # Recursively find all image files
        for ext in self.image_extensions:
            self.images.extend(path.rglob(f'*{ext}'))
            self.images.extend(path.rglob(f'*{ext.upper()}'))
        
        # Remove duplicates and sort
        self.images = sorted(list(set(self.images)))
        
        if not self.images:
            messagebox.showinfo("No Images", "No images found in the selected folder.")
            return
        
        # Apply random order if enabled
        if self.random_mode:
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
            self.filename_label.config(text="")
            return
            
        img_path = self.images[self.current_index]
        
        try:
            # Load and resize image to fit canvas
            img = Image.open(img_path)
            
            # Get canvas size
            self.root.update()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # Calculate scaling to fit image in canvas
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
            self.filename_label.config(text=img_path.name)
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not load image: {str(e)}")
            self.current_index += 1
            self.show_current_image()
            
    def delete_image(self):
        if not self.images or self.current_index >= len(self.images):
            return
            
        img_path = self.images[self.current_index]
        
        try:
            # Move to recycle bin
            winshell.delete_file(str(img_path), no_confirm=True, allow_undo=True)
            self.last_deleted = img_path  # Store for undo
            self.undo_btn.config(state=tk.NORMAL)  # Enable undo button
            self.current_index += 1
            self.show_current_image()
        except Exception as e:
            messagebox.showerror("Error", f"Could not delete file: {str(e)}")
    
    def undo_delete(self):
        if not self.last_deleted:
            return
        
        try:
            # Restore from recycle bin using winshell
            winshell.undelete(str(self.last_deleted))
            messagebox.showinfo("Undo", f"Restored: {self.last_deleted.name}")
            self.last_deleted = None
            self.undo_btn.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("Error", f"Could not restore file: {str(e)}\nYou may need to restore it manually from Recycle Bin.")
            
    def keep_image(self):
        if not self.images or self.current_index >= len(self.images):
            return
            
        # Just move to next image (keeping the current one)
        self.current_index += 1
        self.show_current_image()
    
    def previous_image(self):
        if not self.images:
            return
        if self.current_index > 0:
            self.current_index -= 1
            self.show_current_image()
    
    def next_image(self):
        if not self.images:
            return
        if self.current_index < len(self.images) - 1:
            self.current_index += 1
            self.show_current_image()

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageOrganizer(root)
    root.mainloop()
