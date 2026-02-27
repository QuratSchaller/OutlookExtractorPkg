"""
Monitoring Module for Outlook VTT Extractor v2.0
Handles email folder monitoring, filtering, and approval workflow
"""

import time
import threading
import pythoncom
import win32com.client
from datetime import datetime
import tkinter as tk
from tkinter import ttk


class EmailMonitor:
    """Monitors Outlook folder for new emails matching pattern"""
    
    def __init__(self, config_manager, log_callback, approval_callback, process_callback):
        """Initialize the email monitor
        
        Args:
            config_manager: ConfigManager instance
            log_callback: Function to call for logging
            approval_callback: Function to call to get user approval
            process_callback: Function to call to process approved email
        """
        self.config = config_manager
        self.log = log_callback
        self.request_approval = approval_callback
        self.process_email = process_callback
        
        self.monitoring_active = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start the monitoring thread"""
        if self.monitoring_active:
            self.log("Monitoring already active")
            return False
        
        self.monitoring_active = True
        
        # Initialize check time if not set (ignore existing emails)
        if not self.config.get_last_check_time():
            self.config.update_last_check_time()
            self.log("Initialized monitoring - processing emails from now on")
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        return True
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        return True
    
    def _monitor_loop(self):
        """Main monitoring loop (runs in background thread)"""
        # Initialize COM for this thread
        pythoncom.CoInitialize()
        
        try:
            polling_interval = self.config.config['polling_interval_seconds']
            
            while self.monitoring_active:
                try:
                    # Check for new emails
                    new_emails = self._check_for_new_emails()
                    
                    # Process each new email
                    for email_data in new_emails:
                        if not self.monitoring_active:
                            break
                        
                        # Request user approval
                        approved = self.request_approval(email_data)
                        
                        if approved:
                            self.log(f"User approved: {email_data['subject'][:50]}")
                            # Process the email
                            self.process_email(email_data)
                        else:
                            self.log(f"User declined: {email_data['subject'][:50]}")
                            self.config.add_ignored_email(email_data['entry_id'])
                        
                        # Delay between processing
                        if self.monitoring_active:
                            delay = self.config.config['processing_delay_seconds']
                            self.log(f"Waiting {delay} seconds before next email...")
                            time.sleep(delay)
                
                except Exception as e:
                    self.log(f"Error in monitoring loop: {str(e)}")
                
                # Sleep until next poll (but check monitoring_active frequently)
                for _ in range(polling_interval):
                    if not self.monitoring_active:
                        break
                    time.sleep(1)
        
        finally:
            pythoncom.CoUninitialize()
            self.log("Monitoring stopped")
    
    def _check_for_new_emails(self):
        """Check for new emails matching the pattern
        
        Returns:
            List of email dictionaries
        """
        new_emails = []
        
        try:
            folder_name = self.config.config['monitored_folder']
            pattern = self.config.config['email_subject_pattern']
            last_check = self.config.get_last_check_time()
            
            if not last_check:
                last_check = datetime.now()
            
            # Connect to Outlook
            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")
            
            # Get the folder
            folder = self._get_folder(namespace, folder_name)
            if not folder:
                self.log(f"ERROR: Folder '{folder_name}' not found")
                return new_emails
            
            # Check for new emails
            items = folder.Items
            items.Sort("[ReceivedTime]", True)  # Sort by newest first
            
            self.log(f"Checking folder '{folder_name}' - {items.Count} total items")
            self.log(f"Pattern: '{pattern}'")
            self.log(f"Last check time: {last_check.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Check up to 50 most recent emails
            checked_count = 0
            pattern_matches = 0
            
            for i in range(1, min(50, items.Count) + 1):
                try:
                    item = items.Item(i)
                    checked_count += 1
                    
                    # Get received time
                    received_time = item.ReceivedTime
                    if hasattr(received_time, 'strftime'):
                        received_dt = received_time
                    else:
                        continue
                    
                    # Check subject pattern
                    subject = item.Subject or ""
                    if pattern.lower() not in subject.lower():
                        continue
                    
                    # Found matching pattern
                    pattern_matches += 1
                    self.log(f"  Found matching subject: '{subject[:60]}'")
                    self.log(f"    Received: {received_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # FOR TESTING: Process any unprocessed email regardless of received time
                    # In production, you may want to add back the time check:
                    # if received_dt <= last_check:
                    #     self.log(f"    ⚠ Email too old (before monitoring started)")
                    #     continue
                    
                    # Get entry ID
                    entry_id = item.EntryID
                    
                    # Skip if already handled
                    if self.config.is_email_handled(entry_id):
                        self.log(f"    ⚠ Already handled")
                        continue
                    
                    # Add to new emails list
                    self.log(f"    ✓ NEW email to process!")
                    new_emails.append({
                        'entry_id': entry_id,
                        'subject': subject,
                        'received_time': received_dt,
                        'body': item.HTMLBody if hasattr(item, 'HTMLBody') else item.Body
                    })
                
                except Exception as e:
                    # Skip problematic items
                    continue
            
            # Summary
            self.log(f"Poll summary: Checked {checked_count} items, {pattern_matches} matched pattern, {len(new_emails)} new to process")
            
            # Update last check time
            self.config.update_last_check_time()
            
            if new_emails:
                self.log(f"✓ Found {len(new_emails)} new email(s) to process!")
        
        except Exception as e:
            self.log(f"Error checking emails: {str(e)}")
        
        return new_emails
    
    def _get_folder(self, namespace, folder_name):
        """Get Outlook folder by name
        
        Args:
            namespace: Outlook MAPI namespace
            folder_name: Name of folder to find
            
        Returns:
            Folder object or None
        """
        try:
            # Check if it's Inbox
            if folder_name.lower() == "inbox":
                return namespace.GetDefaultFolder(6)  # 6 = Inbox
            
            # Search in inbox subfolders
            inbox = namespace.GetDefaultFolder(6)
            for subfolder in inbox.Folders:
                if subfolder.Name.lower() == folder_name.lower():
                    return subfolder
            
            # Search in root folders
            for root_folder in namespace.Folders:
                for subfolder in root_folder.Folders:
                    if subfolder.Name.lower() == folder_name.lower():
                        return subfolder
            
            return None
        
        except Exception as e:
            self.log(f"Error finding folder: {str(e)}")
            return None


class ApprovalDialog:
    """Shows approval dialog for new emails"""
    
    @staticmethod
    def show(root, email_data, timeout=300):
        """Show approval dialog and wait for response
        
        Args:
            root: Tkinter root window
            email_data: Email data dictionary
            timeout: Timeout in seconds (default 5 minutes)
            
        Returns:
            True if approved, False if declined or timeout
        """
        result = {'approved': False, 'done': False}
        
        def create_dialog():
            dialog = tk.Toplevel(root)
            dialog.title("New Recording Available")
            dialog.geometry("550x250")
            dialog.transient(root)
            dialog.grab_set()
            
            # Bring to front
            dialog.lift()
            dialog.focus_force()
            dialog.attributes('-topmost', True)
            dialog.after(100, lambda: dialog.attributes('-topmost', False))
            
            # Main frame
            main_frame = ttk.Frame(dialog, padding="20")
            main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            dialog.columnconfigure(0, weight=1)
            dialog.rowconfigure(0, weight=1)
            main_frame.columnconfigure(0, weight=1)
            
            # Title
            ttk.Label(main_frame, text="🎥 New Webex Recording Detected", 
                     font=('Arial', 14, 'bold')).grid(row=0, column=0, pady=(0, 15))
            
            # Meeting info
            ttk.Label(main_frame, text="Meeting:", 
                     font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W)
            
            # Subject text
            subject_frame = ttk.Frame(main_frame)
            subject_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 15))
            subject_frame.columnconfigure(0, weight=1)
            
            subject_text = tk.Text(subject_frame, height=3, width=60, wrap=tk.WORD, 
                                  font=('Arial', 10), bg='#f0f0f0', relief=tk.FLAT)
            subject_text.insert('1.0', email_data['subject'])
            subject_text.config(state='disabled')
            subject_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
            
            # Question
            ttk.Label(main_frame, text="Would you like to process this recording?", 
                     font=('Arial', 10)).grid(row=3, column=0, pady=(0, 20))
            
            # Buttons
            button_frame = ttk.Frame(main_frame)
            button_frame.grid(row=4, column=0)
            
            def on_yes():
                result['approved'] = True
                result['done'] = True
                dialog.destroy()
            
            def on_no():
                result['approved'] = False
                result['done'] = True
                dialog.destroy()
            
            yes_btn = ttk.Button(button_frame, text="✓ Yes, Process", 
                                command=on_yes, width=15)
            yes_btn.grid(row=0, column=0, padx=10)
            
            no_btn = ttk.Button(button_frame, text="✗ No, Skip", 
                               command=on_no, width=15)
            no_btn.grid(row=0, column=1, padx=10)
            
            # Handle window close
            def on_close():
                result['approved'] = False
                result['done'] = True
                dialog.destroy()
            
            dialog.protocol("WM_DELETE_WINDOW", on_close)
            
            # Wait for dialog
            dialog.wait_window()
        
        # Create dialog on main thread
        root.after(0, create_dialog)
        
        # Wait for response with timeout
        start_time = time.time()
        while not result['done']:
            if time.time() - start_time > timeout:
                return False
            time.sleep(0.1)
        
        return result['approved']
