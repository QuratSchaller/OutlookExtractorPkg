"""
Integrations Module for Outlook VTT Extractor v2.0
Handles Outlook Tasks, Webex Bot, and other external integrations
"""

import win32com.client
import requests
from datetime import datetime, timedelta


class OutlookTasksIntegration:
    """Creates and manages Outlook tasks (syncs to Microsoft To Do)"""
    
    def __init__(self, log_callback=None):
        self.log = log_callback or print
    
    def create_tasks_from_actions(self, actions, meeting_title):
        """Create Outlook tasks from action items
        
        Args:
            actions: List of action dictionaries from AI analysis
            meeting_title: Title of the meeting
            
        Returns:
            Number of tasks created
        """
        if not actions:
            self.log("No action items to create as tasks")
            return 0
        
        try:
            self.log(f"Creating {len(actions)} Outlook Task(s)...")
            outlook = win32com.client.Dispatch("Outlook.Application")
            
            created_count = 0
            for action in actions:
                try:
                    # Create task item
                    task = outlook.CreateItem(3)  # 3 = olTaskItem
                    
                    # Set subject
                    task.Subject = action.get('title', 'Untitled Task')
                    
                    # Build description
                    description = f"From meeting: {meeting_title}\n\n"
                    if action.get('description'):
                        description += f"{action['description']}\n\n"
                    if action.get('owner'):
                        description += f"Owner: {action['owner']}\n"
                    if action.get('related_decision'):
                        description += f"Related Decision: {action['related_decision']}\n"
                    
                    task.Body = description
                    
                    # Set due date (default 10 business days)
                    due_date = self.calculate_due_date(action.get('due_date_hint'))
                    task.DueDate = due_date
                    
                    # Set category for organization
                    task.Categories = "Webex Recording"
                    
                    # Set importance if urgent keywords detected
                    title_lower = action.get('title', '').lower()
                    if any(word in title_lower for word in ['urgent', 'asap', 'immediately', 'critical']):
                        task.Importance = 2  # High importance
                    
                    # Save task
                    task.Save()
                    created_count += 1
                    
                except Exception as e:
                    self.log(f"  Error creating task '{action.get('title', 'unknown')}': {str(e)}")
            
            self.log(f"✅ Created {created_count} Outlook Task(s) (will sync to Microsoft To Do)")
            return created_count
        
        except Exception as e:
            self.log(f"ERROR creating Outlook tasks: {str(e)}")
            return 0
    
    def calculate_due_date(self, due_date_hint):
        """Calculate due date - parses hints or defaults to 10 business days from now
        
        Args:
            due_date_hint: Optional hint from transcript (e.g., "tomorrow", "next week", "asap")
            
        Returns:
            datetime object for due date
        """
        current_date = datetime.now()
        
        # Parse due date hint if provided
        if due_date_hint:
            hint_lower = str(due_date_hint).lower()
            
            # Urgent/immediate keywords - 1 business day
            if any(word in hint_lower for word in ['asap', 'urgent', 'immediately', 'critical', 'today']):
                return self._add_business_days(current_date, 1)
            
            # Tomorrow - 1 business day
            elif 'tomorrow' in hint_lower:
                return self._add_business_days(current_date, 1)
            
            # This week / end of week - until Friday
            elif any(phrase in hint_lower for phrase in ['this week', 'end of week', 'end of the week', 'eow']):
                # Find next Friday
                days_until_friday = (4 - current_date.weekday()) % 7
                if days_until_friday == 0:  # Today is Friday
                    days_until_friday = 7
                return current_date + timedelta(days=days_until_friday)
            
            # Next week - 5 business days
            elif 'next week' in hint_lower:
                return self._add_business_days(current_date, 5)
            
            # Two weeks - 10 business days
            elif any(phrase in hint_lower for phrase in ['two weeks', '2 weeks', 'couple weeks']):
                return self._add_business_days(current_date, 10)
            
            # Next month / end of month - 15 business days
            elif any(phrase in hint_lower for phrase in ['next month', 'end of month', 'eom']):
                return self._add_business_days(current_date, 15)
        
        # Default: 10 business days
        return self._add_business_days(current_date, 10)
    
    def _add_business_days(self, start_date, business_days):
        """Helper to add business days (excluding weekends)
        
        Args:
            start_date: Starting datetime
            business_days: Number of business days to add
            
        Returns:
            datetime object
        """
        current = start_date
        days_added = 0
        
        while days_added < business_days:
            current += timedelta(days=1)
            # Monday = 0, Friday = 4 (weekdays)
            if current.weekday() < 5:
                days_added += 1
        
        return current


class WebexBotIntegration:
    """Sends notifications to Webex bot in markdown format"""
    
    def __init__(self, bot_token, log_callback=None):
        self.bot_token = bot_token
        self.log = log_callback or print
    
    def send_analysis_summary(self, structured_data, meeting_title, recording_url='', recipient_email=None):
        """Send meeting analysis summary to Webex bot
        
        Args:
            structured_data: Dict with 'actions' and 'stories' from AI analysis
            meeting_title: Title of the meeting
            recording_url: URL to the recording (optional)
            recipient_email: Email address to send to (optional, defaults to qschalle@cisco.com)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.bot_token:
            self.log("Webex Bot Token not configured - skipping notification")
            return False
        
        try:
            # Use provided recipient or default
            recipient = recipient_email or 'qschalle@cisco.com'
            self.log(f"Sending summary to Webex bot (Producto) → {recipient}...")
            
            actions = structured_data.get('actions', [])
            stories = structured_data.get('stories', [])
            
            if not actions and not stories:
                self.log("No items to send to bot")
                return False
            
            # Build markdown message
            message = self._format_markdown_message(meeting_title, actions, stories, recording_url)
            
            # Send via Webex API
            headers = {
                'Authorization': f'Bearer {self.bot_token}',
                'Content-Type': 'application/json'
            }
            
            # Send to configured recipient
            payload = {
                'toPersonEmail': recipient,  # Configurable recipient
                'markdown': message[:7439]  # Webex message size limit
            }
            
            response = requests.post(
                'https://webexapis.com/v1/messages',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                self.log("✅ Sent summary to Webex bot")
                return True
            else:
                self.log(f"ERROR: Webex API returned {response.status_code}")
                self.log(f"Response: {response.text[:200]}")
                return False
        
        except Exception as e:
            self.log(f"ERROR sending to Webex bot: {str(e)}")
            return False
    
    def _format_markdown_message(self, meeting_title, actions, stories, recording_url):
        """Format the analysis into a markdown message
        
        Args:
            meeting_title: Title of the meeting
            actions: List of action items
            stories: List of user stories
            recording_url: URL to recording
            
        Returns:
            Formatted markdown string
        """
        message = f"📹 **Meeting Processed:** {meeting_title}\n\n"
        message += f"🕐 **Analyzed:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        # Add action items
        if actions:
            message += f"## ✅ Action Items ({len(actions)})\n\n"
            for idx, action in enumerate(actions, 1):
                message += f"**{idx}. {action.get('title', 'Untitled')}**\n"
                
                if action.get('owner'):
                    message += f"   - 👤 Owner: {action['owner']}\n"
                if action.get('due_date_hint'):
                    message += f"   - 📅 Due: {action['due_date_hint']}\n"
                if action.get('description'):
                    # Truncate long descriptions
                    desc = action['description'][:100]
                    if len(action['description']) > 100:
                        desc += "..."
                    message += f"   - 📝 {desc}\n"
                
                message += "\n"
        
        # Add user stories
        if stories:
            message += f"\n## 📝 User Stories ({len(stories)})\n\n"
            for idx, story in enumerate(stories, 1):
                message += f"**{idx}. {story.get('summary', 'Untitled')}**\n"
                
                if story.get('estimate_points'):
                    message += f"   - 🎯 Story Points: {story['estimate_points']}\n"
                if story.get('labels'):
                    message += f"   - 🏷️  Labels: {', '.join(story['labels'])}\n"
                
                message += "\n"
        
        # Add recording link
        if recording_url:
            message += f"\n[🔗 View Recording]({recording_url})\n"
        
        return message
