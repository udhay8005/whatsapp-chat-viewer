#!/usr/bin/env python3
"""
WhatsApp Chat Viewer - Smart Chunked Loading (NO CORS)
Handles 1GB-10GB+ chats smoothly on mobile and desktop
Uses .js files instead of .json to avoid CORS errors
"""

import re
import os
import json
import html
import base64
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import hashlib

class WhatsAppSmartViewer:
    """Process WhatsApp chat with smart chunked loading"""
    
    def __init__(self, chat_file, media_folder):
        self.chat_file = Path(chat_file)
        self.media_folder = Path(media_folder)
        self.output_folder = self.media_folder / "chat_data"
        self.messages_by_month = defaultdict(list)
        self.statistics = {
            'total_messages': 0,
            'total_media': 0,
            'images': 0,
            'videos': 0,
            'audio': 0,
            'documents': 0,
            'participants': set(),
            'messages_by_sender': {}
        }
        # Build index of all media files in the folder (for universal file detection)
        self._build_media_index()
    
    # Known media extensions for file type classification
    MEDIA_EXTENSIONS = {
        # Images
        'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff', 'tif', 'svg', 'ico', 'heic', 'heif',
        # Videos
        'mp4', 'mkv', 'avi', 'mov', '3gp', 'm4v', 'webm', '3g2', 'rmvb', 'flv', 'wmv', 'ts', 'vob',
        # Audio
        'aac', 'amr', 'flac', 'm4a', 'm4r', 'mp3', 'ogg', 'opus', 'wav', 'wma',
        # Documents
        'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'pdf', 'txt', 'html', 'epub', 'zip', 'vcf',
        'csv', 'rtf', 'rar', '7z', 'tar', 'gz', 'apk', 'ics', 'json', 'xml',
        # Stickers
        'webp',
    }
    
    def _build_media_index(self):
        """Scan media folder and build an index of all media files.
        
        This enables universal file detection - ANY filename format is supported.
        We match by checking if a known filename appears in message content.
        Sorted longest-first to prevent partial matches.
        """
        self.known_media_files = []
        
        if not self.media_folder.exists():
            return
        
        for f in self.media_folder.iterdir():
            if not f.is_file():
                continue
            name = f.name
            # Get extension (handle double dots like file..xlsx)
            ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
            if ext in self.MEDIA_EXTENSIONS:
                self.known_media_files.append(name)
        
        # Sort longest first — prevents partial matches (e.g., "photo.jpg" matching before "my photo.jpg")
        self.known_media_files.sort(key=len, reverse=True)
        
        print(f"📁 Indexed {len(self.known_media_files)} media files in folder")
    
    def encode_file_to_base64(self, file_path):
        """Encode a file to base64"""
        try:
            with open(file_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            return None
    
    def create_thumbnail(self, file_path, max_size=200):
        """Create thumbnail for images"""
        try:
            from PIL import Image
            import io
            
            with Image.open(file_path) as img:
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=70, optimize=True)
                buffer.seek(0)
                return base64.b64encode(buffer.read()).decode('utf-8')
        except:
            return None
    
    def get_mime_type(self, filename):
        """Get MIME type based on file extension"""
        ext = filename.lower().split('.')[-1]
        mime_types = {
            # Images
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
            'gif': 'image/gif', 'webp': 'image/webp',
            # Videos
            'mp4': 'video/mp4', 'webm': 'video/webm', 'mkv': 'video/x-matroska',
            'avi': 'video/x-msvideo', 'mov': 'video/quicktime', '3gp': 'video/3gpp',
            'm4v': 'video/x-m4v', '3g2': 'video/3gpp2', 'rmvb': 'application/vnd.rn-realmedia-vbr',
            # Audio
            'opus': 'audio/ogg', 'mp3': 'audio/mpeg', 'wav': 'audio/wav',
            'm4a': 'audio/mp4', 'aac': 'audio/aac', 'amr': 'audio/amr',
            'flac': 'audio/flac', 'm4r': 'audio/x-m4r', 'ogg': 'audio/ogg',
            # Documents
            'pdf': 'application/pdf', 'txt': 'text/plain', 'zip': 'application/zip',
            'doc': 'application/msword', 'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel', 'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'ppt': 'application/vnd.ms-powerpoint', 'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'html': 'text/html', 'epub': 'application/epub+zip',
            # VCF
            'vcf': 'text/vcard'
        }
        return mime_types.get(ext, 'application/octet-stream')
    
    def get_file_type(self, filename):
        """Determine file type based on extension (not filename prefix)"""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        # Image extensions
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            return 'image'
        # Video extensions  
        elif ext in ['mp4', 'mkv', 'avi', 'mov', '3gp', 'm4v', 'webm', '3g2', 'rmvb']:
            return 'video'
        # Audio extensions
        elif ext in ['aac', 'amr', 'flac', 'm4a', 'm4r', 'mp3', 'ogg', 'opus', 'wav']:
            return 'audio'
        # Sticker (animated webp - treated as image but could be separate)
        # Document extensions
        elif ext in ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'pdf', 'txt', 'html', 'epub', 'zip', 'vcf']:
            return 'document'
        return 'document'
    
    def is_system_message(self, content):
        """Check if system message.

        Genuine WhatsApp group notices (created group, members added/removed,
        etc.) have no "Sender:" prefix and are already flagged structurally
        while parsing. This check only needs to catch system phrases that DO
        appear on a sender line (e.g. deleted messages), so we match specific
        phrases rather than bare words like "added"/"left"/"removed" — those
        occur in normal chat and previously caused false positives.
        """
        patterns = [
            r'created group', r'added you',
            r'changed the subject', r'changed this group\'s icon',
            r'Messages and calls are end-to-end encrypted',
            r'deleted this message', r'This message was deleted'
        ]
        return any(re.search(p, content, re.IGNORECASE) for p in patterns)
    
    def format_file_size(self, size):
        """Format file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def parse_chat_file(self):
        """Parse WhatsApp chat file"""
        print(f"📄 Reading: {self.chat_file.name}")
        
        with open(self.chat_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        current_message = None
        message_pattern = re.compile(r'^(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}(?:\s*[ap]m)?)\s*-\s*(.+?)(?::\s*(.*))?$', re.IGNORECASE)
        
        print(f"⏳ Parsing messages...")
        
        for line_num, line in enumerate(lines, 1):
            match = message_pattern.match(line.strip())
            
            if match:
                if current_message:
                    self._save_message(current_message)
                
                date_str, time_str, sender_or_content, message_content = match.groups()
                
                try:
                    fmt = '%d/%m/%Y' if len(date_str.split('/')[-1]) == 4 else '%d/%m/%y'
                    date_obj = datetime.strptime(date_str, fmt)
                    year_month = f"{date_obj.year}-{date_obj.month:02d}"
                except ValueError:
                    continue
                
                if message_content is None:
                    current_message = {
                        'id': hashlib.md5(f"{date_str}_{time_str}_{line_num}".encode()).hexdigest()[:12],
                        'date': date_str,
                        'time': time_str,
                        'sender': None,
                        'content': sender_or_content,
                        'is_system': True,
                        'attachments': [],
                        'year_month': year_month
                    }
                else:
                    current_message = {
                        'id': hashlib.md5(f"{date_str}_{time_str}_{line_num}".encode()).hexdigest()[:12],
                        'date': date_str,
                        'time': time_str,
                        'sender': sender_or_content,
                        'content': message_content or '',
                        'is_system': self.is_system_message(sender_or_content + ' ' + (message_content or '')),
                        'attachments': [],
                        'year_month': year_month
                    }
                    
                    if not current_message['is_system']:
                        self.statistics['participants'].add(sender_or_content)
                        self.statistics['messages_by_sender'][sender_or_content] = \
                            self.statistics['messages_by_sender'].get(sender_or_content, 0) + 1

                    self._extract_attachments(current_message)
            
            elif current_message and line.strip():
                current_message['content'] += '\n' + line.strip()
                self._extract_attachments(current_message)
        
        if current_message:
            self._save_message(current_message)
        
        print(f"✅ Parsed {self.statistics['total_messages']:,} messages")
        print(f"👥 Found {len(self.statistics['participants'])} participants")
    
    def _extract_attachments(self, message):
        """Extract file attachments — UNIVERSAL detection, ANY filename format.
        
        Strategy:
        1. Clean content of already-attached filenames (handles continuation lines)
        2. Extract via "(file attached)" marker — captures ANY text before .<ext>
        3. Match against known media files from disk — handles ALL filename formats
        """
        
        # Step 1: Clean content of any previously-attached filenames
        # WhatsApp often duplicates filename on a continuation line after "(file attached)"
        if message['attachments']:
            for att in message['attachments']:
                fn = att['filename']
                # Remove lines that are just the filename
                lines = message['content'].split('\n')
                lines = [l for l in lines if l.strip() != fn]
                message['content'] = '\n'.join(lines).strip()
            message['content'] = re.sub(r'\(file attached\)', '', message['content']).strip()
        
        # Handle <Media omitted> — media that WhatsApp did not include in the
        # export. Flag it so the viewer can show a "Media omitted" placeholder
        # instead of rendering an empty bubble.
        if '<Media omitted>' in message['content']:
            message['content'] = message['content'].replace('<Media omitted>', '').strip()
            message['media_omitted'] = True
        
        if not message['content']:
            return
        
        found_filenames = {}  # Map filename -> source ('marker', 'disk', 'heuristic')
        
        # Step 2: Extract via "(file attached)" marker
        # Pattern: <ANYTHING>.<ext> (file attached)
        # The ".+?" captures ANY characters (including spaces, special chars, etc.)
        attached_match = re.search(r'(.+?)\s*\(file attached\)', message['content'])
        if attached_match:
            candidate = attached_match.group(1).strip()
            # The candidate should end with a known extension
            if '.' in candidate:
                found_filenames[candidate] = 'marker'
        
        # Step 3: Match against known media files from disk
        # This is the UNIVERSAL detection — works with ANY filename format
        content = message['content']
        for known_file in self.known_media_files:
            if known_file in content:
                if known_file not in found_filenames:
                    found_filenames[known_file] = 'disk'

        # Step 4: Fallback - Heuristic detection for missing files (User Request)
        # "just look the extension... then identify the file"
        # If a line ENDS with a known extension, treat it as a filename
        # This captures "6J8A5144...chaitanya.jpg" even if file is missing and no marker
        lines = message['content'].split('\n')
        for line in lines:
            line_clean = line.strip()
            # Fast check: does it likely end with an extension?
            if '.' in line_clean and not line_clean.endswith('.'):
                 # Get extension
                parts = line_clean.rsplit('.', 1)
                if len(parts) == 2:
                    ext = parts[1].lower()
                    # Check against known media extensions (from Step 2's regex logic)
                    if ext in self.MEDIA_EXTENSIONS:
                         fname = line_clean
                         if fname not in found_filenames:
                              found_filenames[fname] = 'heuristic'

        
        # Process each found filename
        for filename, source in found_filenames.items():
            file_path = self.media_folder / filename
            file_exists = file_path.exists()
            
            # For files found ONLY via content matching (Step 3),
            # require the file to actually exist on disk to avoid false positives.
            # For 'marker' and 'heuristic' (Steps 2 & 4), we allow missing files.
            if source == 'disk' and not file_exists:
                continue
            
            # Skip if this file was already attached
            if any(a['filename'] == filename for a in message['attachments']):
                # Still clean content even for duplicates
                message['content'] = message['content'].replace(filename, '').strip()
                message['content'] = re.sub(r'\(file attached\)', '', message['content']).strip()
                lines = message['content'].split('\n')
                lines = [l for l in lines if l.strip()]
                message['content'] = '\n'.join(lines).strip()
                continue
            
            file_type = self.get_file_type(filename)
            
            if file_exists:
                file_size = file_path.stat().st_size
            else:
                file_size = 0
            
            attachment = {
                'filename': filename,
                'type': file_type,
                'size': file_size,
                'size_formatted': self.format_file_size(file_size) if file_exists else 'File not available',
                'mime_type': self.get_mime_type(filename),
                'full_path': filename,
                'missing': not file_exists  # Flag for UI to show placeholder
            }
            
            # Embed thumbnails/data for files that EXIST on disk
            if file_exists:
                if file_type == 'image':
                    thumbnail = self.create_thumbnail(file_path, max_size=200)
                    if thumbnail:
                        attachment['thumbnail'] = thumbnail
                
                elif file_type in ['video', 'audio']:
                    if file_size < 2 * 1024 * 1024:  # 2MB
                        encoded = self.encode_file_to_base64(file_path)
                        if encoded:
                            attachment['data'] = encoded
            
            # Update statistics
            if file_type == 'image':
                self.statistics['images'] += 1
            elif file_type == 'video':
                self.statistics['videos'] += 1
            elif file_type == 'audio':
                self.statistics['audio'] += 1
            else:
                self.statistics['documents'] += 1
            
            message['attachments'].append(attachment)
            self.statistics['total_media'] += 1
            
            # Clean content: remove filename and "(file attached)" text
            # Remove "filename (file attached)" as a whole if present
            fa_pattern = re.escape(filename) + r'\s*\(file attached\)'
            message['content'] = re.sub(fa_pattern, '', message['content']).strip()
            # Remove bare filename occurrences
            message['content'] = message['content'].replace(filename, '').strip()
            # Remove any leftover "(file attached)"
            message['content'] = re.sub(r'\(file attached\)', '', message['content']).strip()
            # Remove empty lines left after cleanup
            lines = message['content'].split('\n')
            lines = [l for l in lines if l.strip()]
            message['content'] = '\n'.join(lines).strip()
    
    def _save_message(self, message):
        """Save message"""
        # Strip the "edited" marker WhatsApp appends and flag it instead, so the
        # viewer can show a subtle "Edited" tag rather than literal marker text.
        if message.get('content') and '<This message was edited>' in message['content']:
            message['content'] = message['content'].replace('<This message was edited>', '').strip()
            message['edited'] = True
        self.messages_by_month[message['year_month']].append(message)
        self.statistics['total_messages'] += 1
    
    def write_month_files(self):
        """Write month data as .js files (no CORS issues!)"""
        print(f"\n📦 Creating month data files...")
        
        self.output_folder.mkdir(exist_ok=True)
        months_info = []
        
        for year_month in sorted(self.messages_by_month.keys()):
            messages = self.messages_by_month[year_month]
            year, month = year_month.split('-')
            
            # Create .js file instead of .json - THIS AVOIDS CORS!
            js_filename = f"{year}-{month}.js"
            js_filepath = self.output_folder / js_filename
            
            # Write as JavaScript variable
            with open(js_filepath, 'w', encoding='utf-8') as f:
                f.write(f"// Month data: {year}-{month}\n")
                f.write(f"window.CHAT_DATA_{year}_{month} = ")
                json.dump({
                    'month': year_month,
                    'count': len(messages),
                    'messages': messages
                }, f, ensure_ascii=False, indent=2)
                f.write(";\n")
            
            file_size_kb = js_filepath.stat().st_size / 1024
            
            months_info.append({
                'year': int(year),
                'month': int(month),
                'key': year_month,
                'filename': js_filename,
                'count': len(messages),
                'size_kb': file_size_kb
            })
            
            print(f"   ✓ {js_filename} ({len(messages)} msgs, {file_size_kb:.1f} KB)")
        
        print(f"✅ Created {len(months_info)} month files")
        return months_info
    
    def create_viewer_html(self, months_info):
        """Create main HTML viewer"""
        print(f"\n🌐 Creating viewer HTML...")
        
        chat_name = self.chat_file.stem
        safe_chat_name = html.escape(chat_name)

        def _js_safe(js):
            # Make a JSON string safe to embed inside an inline <script> block:
            # neutralise </script>, stray < > &, and the U+2028/U+2029 line
            # separators, while keeping the result valid JSON/JavaScript.
            return (js.replace('<', '\\u003c')
                      .replace('>', '\\u003e')
                      .replace('&', '\\u0026')
                      .replace(' ', '\\u2028')
                      .replace(' ', '\\u2029'))

        months_json = _js_safe(json.dumps(months_info, ensure_ascii=False))
        stats_data = {
            'chat_name': chat_name,
            'total_messages': self.statistics['total_messages'],
            'total_media': self.statistics['total_media'],
            'images': self.statistics['images'],
            'videos': self.statistics['videos'],
            'audio': self.statistics['audio'],
            'documents': self.statistics['documents'],
            'participant_count': len(self.statistics['participants']),
            'messages_by_sender': self.statistics.get('messages_by_sender', {}),
        }
        stats_json = _js_safe(json.dumps(stats_data, ensure_ascii=False))

        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{safe_chat_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --bg-primary: #0b141a;
            --bg-secondary: #202c33;
            --bg-chat: #0b141a;
            --text-primary: #e9edef;
            --text-secondary: #8696a0;
            --message-in: #202c33;
            --message-out: #005c4b;
            --accent: #00a884;
            --border: #2a3942;
            --shadow: rgba(0, 0, 0, 0.4);
        }}

        [data-theme="light"] {{
            --bg-primary: #f0f2f5;
            --bg-secondary: #ffffff;
            --bg-chat: #efeae2;
            --text-primary: #111111;
            --text-secondary: #667781;
            --message-in: #ffffff;
            --message-out: #d9fdd3;
            --accent: #00a884;
            --border: #e9edef;
            --shadow: rgba(0, 0, 0, 0.08);
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg-chat);
            color: var(--text-primary);
            overflow-x: hidden;
        }}

        .header {{
            background: var(--bg-secondary);
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 1px 2px var(--shadow);
        }}

        .header-left {{
            display: flex;
            align-items: center;
            gap: 1rem;
            flex: 1;
        }}

        .chat-avatar {{
            width: 2.5rem;
            height: 2.5rem;
            background: var(--accent);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
        }}

        .chat-info {{
            flex: 1;
        }}

        .chat-name {{
            font-size: 1rem;
            font-weight: 500;
        }}

        .chat-status {{
            font-size: 0.75rem;
            color: var(--text-secondary);
        }}

        .header-actions {{
            display: flex;
            gap: 0.5rem;
        }}

        .btn-icon {{
            background: transparent;
            color: var(--text-secondary);
            padding: 0.5rem;
            border-radius: 50%;
            border: none;
            cursor: pointer;
            font-size: 1.2rem;
            width: 2.5rem;
            height: 2.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .btn-icon:hover {{
            background: var(--border);
        }}

        .range-selector {{
            background: var(--bg-secondary);
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 0.75rem;
            flex-wrap: wrap;
            position: sticky;
            top: 65px;
            z-index: 99;
            transition: transform 0.3s ease, opacity 0.3s ease;
        }}

        .range-selector.hidden {{
            transform: translateY(-100%);
            opacity: 0;
            pointer-events: none;
        }}

        .range-selector.collapsed {{
            display: none;
        }}

        .range-label {{
            font-size: 0.75rem;
            color: var(--text-secondary);
        }}

        .range-select {{
            padding: 0.4rem 0.6rem;
            border: 1px solid var(--border);
            border-radius: 4px;
            background: var(--bg-primary);
            color: var(--text-primary);
            font-size: 0.8rem;
        }}

        .btn-load {{
            padding: 0.4rem 1rem;
            background: var(--accent);
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 500;
            cursor: pointer;
        }}

        .btn-load:hover {{
            opacity: 0.9;
        }}

        .btn-load:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}

        .chat-container {{
            max-width: 900px;
            margin: 0 auto;
        }}

        .messages {{
            padding: 1rem 0.5rem;
        }}

        .date-divider {{
            text-align: center;
            padding: 0.75rem 0;
            margin: 0.5rem 0;
        }}

        .date-badge {{
            display: inline-block;
            background: var(--message-in);
            padding: 0.35rem 0.75rem;
            border-radius: 5px;
            font-size: 0.75rem;
            box-shadow: 0 1px 1px var(--shadow);
        }}

        .message-wrapper {{
            margin: 0.2rem 0;
            display: flex;
            animation: slideIn 0.2s ease;
        }}

        @keyframes slideIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .message-bubble {{
            background: var(--message-in);
            padding: 0.4rem 0.6rem 0.5rem;
            border-radius: 7.5px;
            max-width: 75%;
            box-shadow: 0 1px 0.5px var(--shadow);
        }}

        .sender-name {{
            font-weight: 600;
            font-size: 0.85rem;
            color: var(--accent);
            margin-bottom: 0.2rem;
        }}

        .message-content {{
            color: var(--text-primary);
            line-height: 1.4;
            white-space: pre-wrap;
            font-size: 0.9rem;
            word-break: break-word;
        }}

        .message-meta {{
            font-size: 0.7rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
            text-align: right;
        }}

        .system-message {{
            text-align: center;
            padding: 0.5rem;
            margin: 0.25rem 0;
        }}

        .system-badge {{
            display: inline-block;
            background: var(--message-in);
            padding: 0.35rem 0.75rem;
            border-radius: 5px;
            font-size: 0.75rem;
            color: var(--text-secondary);
            box-shadow: 0 1px 1px var(--shadow);
        }}

        .attachment {{
            margin-top: 0.3rem;
            margin-bottom: 0.3rem;
        }}

        .attachment img {{
            max-width: 100%;
            height: auto;
            display: block;
            cursor: pointer;
            border-radius: 7.5px;
            transition: transform 0.2s;
        }}

        .attachment img:hover {{
            transform: scale(1.02);
        }}

        .attachment video {{
            max-width: 100%;
            display: block;
            border-radius: 7.5px;
        }}

        .media-omitted {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.4rem 0.7rem;
            margin: 0.3rem 0;
            background: rgba(0, 0, 0, 0.12);
            border-radius: 8px;
            font-size: 0.8rem;
            font-style: italic;
            color: var(--text-secondary);
        }}

        .doc-attachment {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.6rem 0.8rem;
            background: rgba(0, 0, 0, 0.1);
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.2s;
            text-decoration: none;
            color: inherit;
            margin: 0.3rem 0;
        }}

        .doc-attachment:hover {{
            background: rgba(0, 0, 0, 0.2);
        }}

        .doc-icon {{
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            flex-shrink: 0;
            font-weight: 700;
            color: white;
        }}

        .doc-icon.pdf {{ background: #E53935; }}
        .doc-icon.xls, .doc-icon.xlsx {{ background: #43A047; }}
        .doc-icon.doc, .doc-icon.docx {{ background: #1E88E5; }}
        .doc-icon.ppt, .doc-icon.pptx {{ background: #FB8C00; }}
        .doc-icon.txt {{ background: #78909C; }}
        .doc-icon.zip {{ background: #8E24AA; }}
        .doc-icon.vcf {{ background: #00ACC1; }}
        .doc-icon.html {{ background: #E65100; }}
        .doc-icon.epub {{ background: #6D4C41; }}
        .doc-icon.default {{ background: #546E7A; }}

        .doc-info {{
            flex: 1;
            overflow: hidden;
        }}

        .doc-name {{
            font-size: 0.85rem;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            color: var(--text-primary);
        }}

        .doc-size {{
            font-size: 0.7rem;
            color: var(--text-secondary);
            margin-top: 0.1rem;
        }}

        .doc-download {{
            font-size: 1.2rem;
            color: var(--text-secondary);
            flex-shrink: 0;
        }}

        .audio-player {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
            padding: 0.6rem;
            background: rgba(0, 0, 0, 0.15);
            border-radius: 20px;
            margin: 0.3rem 0;
        }}

        .audio-btn {{
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 50%;
            background: var(--accent);
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .audio-btn svg {{
            width: 1.2rem;
            height: 1.2rem;
            fill: white;
        }}

        .audio-progress {{
            flex: 1;
            font-size: 0.75rem;
            color: var(--text-secondary);
        }}

        .lightbox {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.95);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            flex-direction: column;
        }}

        .lightbox.active {{
            display: flex;
        }}

        .lightbox-container {{
            position: relative;
            width: 100%;
            height: 100%;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            touch-action: none;
        }}

        .lightbox-img {{
            max-width: 90%;
            max-height: 90%;
            object-fit: contain;
            transition: transform 0.1s ease-out;
            cursor: grab;
            user-select: none;
            -webkit-user-drag: none;
        }}

        .lightbox-img.dragging {{
            cursor: grabbing;
            transition: none;
        }}

        .lightbox-img.zoomed {{
            max-width: none;
            max-height: none;
        }}

        .lightbox-close {{
            position: absolute;
            top: 1rem;
            right: 1rem;
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 50%;
            font-size: 1.5rem;
            cursor: pointer;
            z-index: 1010;
            backdrop-filter: blur(4px);
        }}

        .lightbox-close:hover {{
            background: rgba(255, 255, 255, 0.3);
        }}

        .lightbox-controls {{
            position: absolute;
            bottom: 2rem;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 0.5rem;
            z-index: 1010;
            background: rgba(0, 0, 0, 0.6);
            padding: 0.5rem;
            border-radius: 25px;
            backdrop-filter: blur(4px);
        }}

        .zoom-btn {{
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 50%;
            border: none;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            font-size: 1.2rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .zoom-btn:hover {{
            background: rgba(255, 255, 255, 0.3);
        }}

        .zoom-level {{
            color: white;
            font-size: 0.875rem;
            min-width: 3rem;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .lightbox-loading {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-size: 1rem;
            z-index: 1005;
        }}

        .lightbox-loading.hidden {{
            display: none;
        }}

        .lightbox-hint {{
            position: absolute;
            bottom: 5rem;
            left: 50%;
            transform: translateX(-50%);
            color: rgba(255, 255, 255, 0.6);
            font-size: 0.75rem;
            text-align: center;
            pointer-events: none;
        }}

        .loading {{
            text-align: center;
            padding: 2rem;
            color: var(--text-secondary);
        }}

        .empty-state {{
            text-align: center;
            padding: 3rem 1rem;
            color: var(--text-secondary);
        }}

        .quick-btns {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}

        .quick-btn {{
            padding: 0.3rem 0.7rem;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: transparent;
            color: var(--text-primary);
            font-size: 0.75rem;
            cursor: pointer;
        }}

        .quick-btn:hover {{
            background: var(--accent);
            border-color: var(--accent);
            color: white;
        }}

        @media (max-width: 768px) {{
            .message-bubble {{
                max-width: 85%;
            }}
            
            .range-selector {{
                font-size: 0.7rem;
            }}
        }}

        .header-left {{
            cursor: pointer;
        }}

        /* ===== Search bar (WhatsApp-style, overlays the header) ===== */
        .search-bar {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            align-items: center;
            gap: 0.4rem;
            background: var(--bg-secondary);
            padding: 0.5rem 0.6rem;
            border-bottom: 1px solid var(--border);
            z-index: 103;
        }}

        .search-bar.active {{
            display: flex;
        }}

        .search-input {{
            flex: 1;
            min-width: 0;
            background: var(--bg-primary);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 0.5rem 0.9rem;
            color: var(--text-primary);
            font-size: 0.9rem;
            outline: none;
        }}

        .search-input::placeholder {{
            color: var(--text-secondary);
        }}

        .search-count {{
            font-size: 0.72rem;
            color: var(--text-secondary);
            min-width: 4.2rem;
            text-align: center;
            white-space: nowrap;
        }}

        .search-bar .btn-icon svg {{
            width: 1.15rem;
            height: 1.15rem;
            fill: var(--text-secondary);
        }}

        mark.search-hl {{
            background: #f7c948;
            color: #1a1a1a;
            border-radius: 2px;
            padding: 0 1px;
        }}

        mark.search-hl.current {{
            background: #ff8a00;
            color: #1a1a1a;
        }}

        /* ===== Chat-info / statistics panel (slides in from the right) ===== */
        .panel-overlay {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1100;
        }}

        .panel-overlay.active {{
            display: block;
        }}

        .stats-panel {{
            position: fixed;
            top: 0;
            right: 0;
            height: 100%;
            width: 380px;
            max-width: 90vw;
            background: var(--bg-secondary);
            z-index: 1101;
            transform: translateX(100%);
            transition: transform 0.25s ease;
            display: flex;
            flex-direction: column;
            box-shadow: -2px 0 14px var(--shadow);
        }}

        .stats-panel.open {{
            transform: translateX(0);
        }}

        .stats-header {{
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 0.85rem 1rem;
            border-bottom: 1px solid var(--border);
            font-weight: 500;
            flex-shrink: 0;
        }}

        .stats-body {{
            overflow-y: auto;
            padding: 1rem;
            flex: 1;
        }}

        .stats-id {{
            text-align: center;
            padding: 0.5rem 0 1.5rem;
            border-bottom: 1px solid var(--border);
            margin-bottom: 1rem;
        }}

        .stats-avatar {{
            width: 5rem;
            height: 5rem;
            border-radius: 50%;
            background: var(--accent);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.5rem;
            margin: 0 auto 0.75rem;
        }}

        .stats-name {{
            font-size: 1.2rem;
            font-weight: 600;
            word-break: break-word;
        }}

        .stats-sub {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
        }}

        .stats-section {{
            margin-bottom: 1.4rem;
        }}

        .stats-section-title {{
            font-size: 0.75rem;
            color: var(--accent);
            font-weight: 700;
            margin-bottom: 0.6rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        .stat-row {{
            display: flex;
            justify-content: space-between;
            gap: 0.75rem;
            padding: 0.4rem 0;
            font-size: 0.9rem;
        }}

        .stat-label {{
            color: var(--text-secondary);
        }}

        .stat-value {{
            font-weight: 500;
            text-align: right;
        }}

        .media-chips {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
        }}

        .media-chip {{
            background: var(--bg-primary);
            border-radius: 8px;
            padding: 0.6rem;
            text-align: center;
        }}

        .media-chip-n {{
            display: block;
            font-size: 1.05rem;
            font-weight: 600;
        }}

        .media-chip-l {{
            display: block;
            font-size: 0.7rem;
            color: var(--text-secondary);
            margin-top: 0.15rem;
        }}

        .stats-part {{
            width: 100%;
            background: transparent;
            border: none;
            cursor: pointer;
            padding: 0.5rem;
            text-align: left;
            color: inherit;
            border-radius: 6px;
            font-family: inherit;
        }}

        .stats-part:hover {{
            background: var(--bg-primary);
        }}

        .stats-part-top {{
            display: flex;
            justify-content: space-between;
            gap: 0.5rem;
            font-size: 0.85rem;
            margin-bottom: 0.3rem;
        }}

        .stats-part-name {{
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 70%;
        }}

        .stats-part-count {{
            color: var(--text-secondary);
            flex-shrink: 0;
        }}

        .stats-bar {{
            height: 5px;
            background: var(--bg-primary);
            border-radius: 3px;
            overflow: hidden;
        }}

        .stats-bar-fill {{
            height: 100%;
            background: var(--accent);
            border-radius: 3px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-left">
            <div class="chat-avatar">💬</div>
            <div class="chat-info">
                <div class="chat-name">{safe_chat_name}</div>
                <div class="chat-status" id="status">Select date range</div>
            </div>
        </div>
        <div class="header-actions">
            <button class="btn-icon" id="searchToggle" title="Search messages">🔍</button>
            <button class="btn-icon" id="rangeToggle" title="Change range">📅</button>
            <button class="btn-icon" id="statsToggle" title="Chat info & statistics">📊</button>
            <button class="btn-icon" id="themeToggle" title="Toggle theme">☀️</button>
        </div>
    </div>

    <div class="search-bar" id="searchBar">
        <button class="btn-icon" id="searchClose" title="Close search">
            <svg viewBox="0 0 24 24"><path d="M20 11H7.8l5.6-5.6L12 4l-8 8 8 8 1.4-1.4L7.8 13H20z"/></svg>
        </button>
        <input type="text" id="searchInput" class="search-input" placeholder="Search messages…" autocomplete="off" spellcheck="false">
        <span class="search-count" id="searchCount"></span>
        <button class="btn-icon" id="searchPrev" title="Previous match (Shift+Enter)">
            <svg viewBox="0 0 24 24"><path d="M7.4 15.4 12 10.8l4.6 4.6L18 14l-6-6-6 6z"/></svg>
        </button>
        <button class="btn-icon" id="searchNext" title="Next match (Enter)">
            <svg viewBox="0 0 24 24"><path d="M7.4 8.6 12 13.2l4.6-4.6L18 10l-6 6-6-6z"/></svg>
        </button>
    </div>

    <div class="range-selector" id="rangeSelector">
        <span class="range-label">From:</span>
        <select class="range-select" id="startMonth"></select>
        
        <span class="range-label">To:</span>
        <select class="range-select" id="endMonth"></select>

        <span class="range-label">Who:</span>
        <select class="range-select" id="participantFilter">
            <option value="">All participants</option>
        </select>

        <button class="btn-load" id="loadBtn">Load</button>
        
        <div class="quick-btns">
            <button class="quick-btn" data-range="last-1">Last Month</button>
            <button class="quick-btn" data-range="last-3">Last 3 Months</button>
            <button class="quick-btn" data-range="last-6">Last 6 Months</button>
            <button class="quick-btn" data-range="all">All Messages</button>
        </div>
    </div>

    <div class="chat-container">
        <div class="messages" id="messages"></div>
    </div>

    <div class="lightbox" id="lightbox">
        <button class="lightbox-close" onclick="closeLightbox(event)">✕</button>
        <div class="lightbox-loading" id="lightboxLoading">Loading full image...</div>
        <div class="lightbox-container" id="lightboxContainer">
            <img class="lightbox-img" id="lightboxImg" src="" alt="" draggable="false">
        </div>
        <div class="lightbox-hint" id="lightboxHint">Double-click or scroll to zoom • Drag to pan</div>
        <div class="lightbox-controls" id="lightboxControls">
            <button class="zoom-btn" onclick="zoomOut(event)" title="Zoom out">−</button>
            <span class="zoom-level" id="zoomLevel">100%</span>
            <button class="zoom-btn" onclick="zoomIn(event)" title="Zoom in">+</button>
            <button class="zoom-btn" onclick="resetZoom(event)" title="Reset">↻</button>
        </div>
    </div>

    <div class="panel-overlay" id="statsOverlay"></div>
    <div class="stats-panel" id="statsPanel">
        <div class="stats-header">
            <button class="btn-icon" id="statsClose" title="Close">✕</button>
            <span>Chat info</span>
        </div>
        <div class="stats-body" id="statsBody"></div>
    </div>

    <script>
        const MONTHS_INFO = {months_json};
        const CHAT_STATS = {stats_json};

        const STATE = {{
            theme: localStorage.getItem('theme') || 'dark',
            loadedMonths: new Set(),
            loadedScripts: new Set(),
            currentMessages: [],
            visibleMessages: [],
            participantFilter: null,
            searchTerm: '',
            searchMatches: [],
            searchIndex: -1
        }};

        function init() {{
            applyTheme(STATE.theme);
            populateDropdowns();
            populateParticipants();
            setupEvents();
        }}

        // Escape text before putting it into innerHTML, so message text and
        // file names containing < > & " ' render literally instead of being
        // interpreted as HTML.
        function escapeHtml(s) {{
            return String(s == null ? '' : s)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }}

        function populateDropdowns() {{
            const startSel = document.getElementById('startMonth');
            const endSel = document.getElementById('endMonth');
            
            const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

            MONTHS_INFO.forEach(m => {{
                const label = `${{monthNames[m.month - 1]}} ${{m.year}} (${{m.count}})`;
                startSel.add(new Option(label, m.key));
                endSel.add(new Option(label, m.key));
            }});

            if (MONTHS_INFO.length > 0) {{
                startSel.selectedIndex = Math.max(0, MONTHS_INFO.length - 1);
                endSel.selectedIndex = MONTHS_INFO.length - 1;
            }}
        }}

        async function loadMessages() {{
            const startVal = document.getElementById('startMonth').value;
            const endVal = document.getElementById('endMonth').value;
            
            if (!startVal || !endVal) return;

            document.getElementById('loadBtn').disabled = true;
            document.getElementById('messages').innerHTML = '<div class="loading">Loading...</div>';

            const selectedMonths = MONTHS_INFO.filter(m => 
                m.key >= startVal && m.key <= endVal
            );

            // Load month data files dynamically
            const allMessages = [];
            
            for (const month of selectedMonths) {{
                await loadMonthData(month);
                const [year, monthNum] = month.key.split('-');
                const dataKey = `CHAT_DATA_${{year}}_${{monthNum}}`;
                
                if (window[dataKey]) {{
                    allMessages.push(...window[dataKey].messages);
                }}
            }}

            STATE.currentMessages = allMessages;
            applyView();

            document.getElementById('loadBtn').disabled = false;
            document.getElementById('rangeSelector').classList.add('hidden');
        }}

        function loadMonthData(month) {{
            return new Promise((resolve) => {{
                if (STATE.loadedScripts.has(month.filename)) {{
                    resolve();
                    return;
                }}

                const script = document.createElement('script');
                script.src = `chat_data/${{month.filename}}`;
                script.onload = () => {{
                    STATE.loadedScripts.add(month.filename);
                    resolve();
                }};
                script.onerror = () => {{
                    console.error('Failed to load:', month.filename);
                    resolve();
                }};
                document.head.appendChild(script);
            }});
        }}

        function renderMessages(messages) {{
            const container = document.getElementById('messages');
            container.innerHTML = '';

            if (messages.length === 0) {{
                container.innerHTML = '<div class="empty-state">No messages</div>';
                return;
            }}

            let currentDate = '';

            messages.forEach(msg => {{
                if (msg.date !== currentDate) {{
                    currentDate = msg.date;
                    const divider = document.createElement('div');
                    divider.className = 'date-divider';
                    divider.innerHTML = `<span class="date-badge">${{msg.date}}</span>`;
                    container.appendChild(divider);
                }}

                if (msg.is_system) {{
                    const sys = document.createElement('div');
                    sys.className = 'system-message';
                    const text = msg.sender ? `${{msg.sender}}: ${{msg.content}}` : msg.content;
                    const sysBadge = document.createElement('div');
                    sysBadge.className = 'system-badge';
                    sysBadge.textContent = text;
                    sys.appendChild(sysBadge);
                    container.appendChild(sys);
                }} else {{
                    const wrapper = document.createElement('div');
                    wrapper.className = 'message-wrapper';
                    
                    const bubble = document.createElement('div');
                    bubble.className = 'message-bubble';
                    
                    if (msg.sender) {{
                        const sender = document.createElement('div');
                        sender.className = 'sender-name';
                        sender.textContent = msg.sender;
                        bubble.appendChild(sender);
                    }}

                    // Render attachments FIRST
                    msg.attachments.forEach(att => {{
                        const attDiv = document.createElement('div');
                        attDiv.className = 'attachment';
                        
                        // Handle missing files (detected from chat but not on disk)
                        if (att.missing) {{
                            const ext = att.filename.split('.').pop().toLowerCase();
                            const typeEmoji = att.type === 'image' ? '🖼️' : att.type === 'video' ? '🎬' : att.type === 'audio' ? '🎵' : '📄';
                            const iconMap = {{
                                'pdf': 'PDF', 'doc': 'DOC', 'docx': 'DOC',
                                'xls': 'XLS', 'xlsx': 'XLS',
                                'ppt': 'PPT', 'pptx': 'PPT',
                                'jpg': 'JPG', 'jpeg': 'JPG', 'png': 'PNG', 'gif': 'GIF', 'webp': 'WEBP',
                                'mp4': 'MP4', 'mkv': 'MKV', 'avi': 'AVI', 'mov': 'MOV',
                                'mp3': 'MP3', 'wav': 'WAV', 'ogg': 'OGG', 'opus': 'OPUS', 'm4a': 'M4A',
                                'txt': 'TXT', 'zip': 'ZIP', 'vcf': 'VCF'
                            }};
                            const iconLabel = iconMap[ext] || ext.toUpperCase();
                            const missingCard = document.createElement('div');
                            missingCard.className = 'doc-attachment';
                            missingCard.style.opacity = '0.7';
                            missingCard.innerHTML =
                                `<div class="doc-icon ${{escapeHtml(ext)}}">${{typeEmoji}} ${{escapeHtml(iconLabel)}}</div>` +
                                `<div class="doc-info">` +
                                    `<div class="doc-name">${{escapeHtml(att.filename)}}</div>` +
                                    `<div class="doc-size">File not available</div>` +
                                `</div>`;
                            attDiv.appendChild(missingCard);
                            bubble.appendChild(attDiv);
                            return;
                        }}
                        
                        if (att.type === 'image') {{
                            const img = document.createElement('img');
                            img.alt = att.filename;
                            img.loading = 'lazy';
                            
                            if (att.thumbnail) {{
                                img.src = 'data:image/jpeg;base64,' + att.thumbnail;
                            }} else if (att.data) {{
                                img.src = `data:${{att.mime_type}};base64,${{att.data}}`;
                            }}
                            
                            img.onclick = (e) => {{
                                e.stopPropagation();
                                openLightbox(att.full_path || img.src, img.src);
                            }};
                            
                            attDiv.appendChild(img);
                            
                        }} else if (att.type === 'video') {{
                            const video = document.createElement('video');
                            video.controls = true;
                            video.preload = 'metadata';
                            
                            const source = document.createElement('source');
                            if (att.full_path) {{
                                source.src = att.full_path;
                            }} else if (att.data) {{
                                source.src = `data:${{att.mime_type}};base64,${{att.data}}`;
                            }}
                            source.type = att.mime_type;
                            video.appendChild(source);
                            
                            attDiv.appendChild(video);
                            
                        }} else if (att.type === 'audio') {{
                            attDiv.className = 'audio-player';
                            const audioSrc = att.full_path || (att.data ? 'data:' + att.mime_type + ';base64,' + att.data : '');
                            attDiv.innerHTML = '<button class="audio-btn"><svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg></button>' +
                                '<div class="audio-progress"><div>🎵 ' + escapeHtml(att.filename) + '</div><div class="audio-time">0:00</div></div>' +
                                '<audio style="display:none;"><source src="' + escapeHtml(audioSrc) + '" type="' + escapeHtml(att.mime_type) + '"></audio>';
                        }} else if (att.type === 'document') {{
                            // Document attachment rendering
                            const ext = att.filename.split('.').pop().toLowerCase();
                            const iconMap = {{
                                'pdf': 'PDF', 'doc': 'DOC', 'docx': 'DOC',
                                'xls': 'XLS', 'xlsx': 'XLS',
                                'ppt': 'PPT', 'pptx': 'PPT',
                                'txt': 'TXT', 'zip': 'ZIP',
                                'vcf': 'VCF', 'html': 'HTML', 'epub': 'EPUB'
                            }};
                            const iconLabel = iconMap[ext] || ext.toUpperCase();
                            const iconClass = ext;
                            
                            const docLink = document.createElement('a');
                            docLink.className = 'doc-attachment';
                            docLink.href = att.full_path || '#';
                            docLink.target = '_blank';
                            docLink.onclick = (e) => {{ e.stopPropagation(); }};
                            docLink.innerHTML =
                                `<div class="doc-icon ${{escapeHtml(iconClass)}}">${{escapeHtml(iconLabel)}}</div>` +
                                `<div class="doc-info">` +
                                    `<div class="doc-name">${{escapeHtml(att.filename)}}</div>` +
                                    `<div class="doc-size">${{escapeHtml(att.size_formatted)}} · ${{escapeHtml(ext.toUpperCase())}}</div>` +
                                `</div>` +
                                `<div class="doc-download">📥</div>`;
                            attDiv.appendChild(docLink);
                        }}
                        
                        bubble.appendChild(attDiv);
                    }});

                    // Placeholder for media WhatsApp did not include in the export
                    if (msg.media_omitted) {{
                        const omitted = document.createElement('div');
                        omitted.className = 'media-omitted';
                        omitted.textContent = '📎 Media omitted';
                        bubble.appendChild(omitted);
                    }}

                    // Then render text content (if any and not just filename)
                    if (msg.content.trim()) {{
                        const content = document.createElement('div');
                        content.className = 'message-content';
                        content.textContent = msg.content;
                        bubble.appendChild(content);
                    }}

                    const meta = document.createElement('div');
                    meta.className = 'message-meta';
                    meta.textContent = (msg.edited ? 'Edited · ' : '') + msg.time;
                    bubble.appendChild(meta);
                    
                    wrapper.appendChild(bubble);
                    container.appendChild(wrapper);
                }}
            }});

            initAudioPlayers();
        }}

        function initAudioPlayers() {{
            document.querySelectorAll('.audio-player').forEach(container => {{
                const audio = container.querySelector('audio');
                const btn = container.querySelector('.audio-btn');
                const timeDisplay = container.querySelector('.audio-time');
                
                if (!audio || !btn) return;

                btn.onclick = (e) => {{
                    e.stopPropagation();
                    if (audio.paused) {{
                        audio.play();
                        btn.querySelector('svg').innerHTML = '<path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>';
                    }} else {{
                        audio.pause();
                        btn.querySelector('svg').innerHTML = '<path d="M8 5v14l11-7z"/>';
                    }}
                }};

                audio.ontimeupdate = () => {{
                    const current = Math.floor(audio.currentTime);
                    const duration = Math.floor(audio.duration) || 0;
                    const formatTime = (s) => {{
                        const m = Math.floor(s / 60);
                        const sec = s % 60;
                        return m + ':' + (sec < 10 ? '0' : '') + sec;
                    }};
                    timeDisplay.textContent = `${{formatTime(current)}} / ${{formatTime(duration)}}`;
                }};
            }});
        }}

        // ===== LIGHTBOX ZOOM SYSTEM =====
        const ZOOM = {{
            scale: 1,
            minScale: 0.5,
            maxScale: 5,
            step: 0.25,
            translateX: 0,
            translateY: 0,
            isDragging: false,
            startX: 0,
            startY: 0,
            lastX: 0,
            lastY: 0,
            pinchStartDist: 0,
            pinchStartScale: 1,
            fullImagePath: null,
            thumbnailSrc: null
        }};

        function openLightbox(fullPath, thumbnailSrc) {{
            const lightbox = document.getElementById('lightbox');
            const img = document.getElementById('lightboxImg');
            const loading = document.getElementById('lightboxLoading');
            const hint = document.getElementById('lightboxHint');
            
            // Reset zoom state
            ZOOM.scale = 1;
            ZOOM.translateX = 0;
            ZOOM.translateY = 0;
            ZOOM.fullImagePath = fullPath;
            ZOOM.thumbnailSrc = thumbnailSrc;
            
            // Show thumbnail first
            if (thumbnailSrc) {{
                img.src = thumbnailSrc;
            }}
            
            // Show lightbox
            lightbox.classList.add('active');
            updateZoomTransform();
            
            // Load full image if path exists
            if (fullPath && !fullPath.startsWith('data:')) {{
                loading.classList.remove('hidden');
                hint.style.opacity = '0';
                
                const fullImg = new Image();
                fullImg.onload = () => {{
                    img.src = fullPath;
                    loading.classList.add('hidden');
                    hint.style.opacity = '1';
                }};
                fullImg.onerror = () => {{
                    // Keep thumbnail if full image fails
                    loading.classList.add('hidden');
                    hint.textContent = 'Full image not available';
                    hint.style.opacity = '1';
                }};
                fullImg.src = fullPath;
            }} else {{
                loading.classList.add('hidden');
                hint.style.opacity = '1';
            }}
            
            // Setup event listeners
            setupLightboxEvents();
        }}

        function closeLightbox(e) {{
            if (e) e.stopPropagation();
            const lightbox = document.getElementById('lightbox');
            const img = document.getElementById('lightboxImg');
            
            lightbox.classList.remove('active');
            img.classList.remove('zoomed', 'dragging');
            
            // Reset zoom
            ZOOM.scale = 1;
            ZOOM.translateX = 0;
            ZOOM.translateY = 0;
            
            removeLightboxEvents();
        }}

        function updateZoomTransform() {{
            const img = document.getElementById('lightboxImg');
            img.style.transform = `translate(${{ZOOM.translateX}}px, ${{ZOOM.translateY}}px) scale(${{ZOOM.scale}})`;
            document.getElementById('zoomLevel').textContent = Math.round(ZOOM.scale * 100) + '%';
            
            if (ZOOM.scale > 1) {{
                img.classList.add('zoomed');
            }} else {{
                img.classList.remove('zoomed');
            }}
        }}

        function zoomIn(e) {{
            if (e) e.stopPropagation();
            ZOOM.scale = Math.min(ZOOM.maxScale, ZOOM.scale + ZOOM.step);
            updateZoomTransform();
        }}

        function zoomOut(e) {{
            if (e) e.stopPropagation();
            ZOOM.scale = Math.max(ZOOM.minScale, ZOOM.scale - ZOOM.step);
            if (ZOOM.scale <= 1) {{
                ZOOM.translateX = 0;
                ZOOM.translateY = 0;
            }}
            updateZoomTransform();
        }}

        function resetZoom(e) {{
            if (e) e.stopPropagation();
            ZOOM.scale = 1;
            ZOOM.translateX = 0;
            ZOOM.translateY = 0;
            updateZoomTransform();
        }}

        function handleWheel(e) {{
            e.preventDefault();
            e.stopPropagation();
            
            const delta = e.deltaY > 0 ? -ZOOM.step : ZOOM.step;
            ZOOM.scale = Math.max(ZOOM.minScale, Math.min(ZOOM.maxScale, ZOOM.scale + delta));
            
            if (ZOOM.scale <= 1) {{
                ZOOM.translateX = 0;
                ZOOM.translateY = 0;
            }}
            
            updateZoomTransform();
        }}

        function handleDoubleClick(e) {{
            e.preventDefault();
            e.stopPropagation();
            
            if (ZOOM.scale > 1) {{
                resetZoom();
            }} else {{
                ZOOM.scale = 2;
                updateZoomTransform();
            }}
        }}

        function handleMouseDown(e) {{
            if (ZOOM.scale <= 1) return;
            e.preventDefault();
            
            ZOOM.isDragging = true;
            ZOOM.startX = e.clientX - ZOOM.translateX;
            ZOOM.startY = e.clientY - ZOOM.translateY;
            
            document.getElementById('lightboxImg').classList.add('dragging');
        }}

        function handleMouseMove(e) {{
            if (!ZOOM.isDragging) return;
            e.preventDefault();
            
            ZOOM.translateX = e.clientX - ZOOM.startX;
            ZOOM.translateY = e.clientY - ZOOM.startY;
            updateZoomTransform();
        }}

        function handleMouseUp(e) {{
            ZOOM.isDragging = false;
            document.getElementById('lightboxImg').classList.remove('dragging');
        }}

        function handleTouchStart(e) {{
            if (e.touches.length === 2) {{
                // Pinch gesture start
                ZOOM.pinchStartDist = getTouchDistance(e.touches);
                ZOOM.pinchStartScale = ZOOM.scale;
            }} else if (e.touches.length === 1 && ZOOM.scale > 1) {{
                // Pan gesture start
                ZOOM.isDragging = true;
                ZOOM.startX = e.touches[0].clientX - ZOOM.translateX;
                ZOOM.startY = e.touches[0].clientY - ZOOM.translateY;
            }}
        }}

        function handleTouchMove(e) {{
            e.preventDefault();
            
            if (e.touches.length === 2) {{
                // Pinch gesture
                const dist = getTouchDistance(e.touches);
                const newScale = ZOOM.pinchStartScale * (dist / ZOOM.pinchStartDist);
                ZOOM.scale = Math.max(ZOOM.minScale, Math.min(ZOOM.maxScale, newScale));
                updateZoomTransform();
            }} else if (e.touches.length === 1 && ZOOM.isDragging) {{
                // Pan gesture
                ZOOM.translateX = e.touches[0].clientX - ZOOM.startX;
                ZOOM.translateY = e.touches[0].clientY - ZOOM.startY;
                updateZoomTransform();
            }}
        }}

        function handleTouchEnd(e) {{
            ZOOM.isDragging = false;
            if (ZOOM.scale <= 1) {{
                ZOOM.translateX = 0;
                ZOOM.translateY = 0;
                updateZoomTransform();
            }}
        }}

        function getTouchDistance(touches) {{
            const dx = touches[0].clientX - touches[1].clientX;
            const dy = touches[0].clientY - touches[1].clientY;
            return Math.sqrt(dx * dx + dy * dy);
        }}

        function handleContainerClick(e) {{
            // Close if clicking on container (not image or controls)
            if (e.target.id === 'lightboxContainer' && !ZOOM.isDragging) {{
                closeLightbox();
            }}
        }}

        function handleKeyDown(e) {{
            if (!document.getElementById('lightbox').classList.contains('active')) return;
            
            switch(e.key) {{
                case 'Escape':
                    closeLightbox();
                    break;
                case '+':
                case '=':
                    zoomIn();
                    break;
                case '-':
                    zoomOut();
                    break;
                case '0':
                    resetZoom();
                    break;
            }}
        }}

        function setupLightboxEvents() {{
            const container = document.getElementById('lightboxContainer');
            const img = document.getElementById('lightboxImg');
            
            container.addEventListener('wheel', handleWheel, {{ passive: false }});
            img.addEventListener('dblclick', handleDoubleClick);
            img.addEventListener('mousedown', handleMouseDown);
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
            container.addEventListener('touchstart', handleTouchStart, {{ passive: false }});
            container.addEventListener('touchmove', handleTouchMove, {{ passive: false }});
            container.addEventListener('touchend', handleTouchEnd);
            container.addEventListener('click', handleContainerClick);
            document.addEventListener('keydown', handleKeyDown);
        }}

        function removeLightboxEvents() {{
            const container = document.getElementById('lightboxContainer');
            const img = document.getElementById('lightboxImg');
            
            container.removeEventListener('wheel', handleWheel);
            img.removeEventListener('dblclick', handleDoubleClick);
            img.removeEventListener('mousedown', handleMouseDown);
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            container.removeEventListener('touchstart', handleTouchStart);
            container.removeEventListener('touchmove', handleTouchMove);
            container.removeEventListener('touchend', handleTouchEnd);
            container.removeEventListener('click', handleContainerClick);
            document.removeEventListener('keydown', handleKeyDown);
        }}

        // ===== Current view = loaded messages, optionally filtered by participant =====
        function applyView() {{
            let msgs = STATE.currentMessages;
            // Exclude system messages so the shown count matches the per-sender
            // count in the stats panel / dropdown label.
            if (STATE.participantFilter) {{
                msgs = msgs.filter(m => !m.is_system && m.sender === STATE.participantFilter);
            }}
            STATE.visibleMessages = msgs;

            const total = STATE.currentMessages.length;
            const status = document.getElementById('status');
            const container = document.getElementById('messages');

            if (msgs.length === 0) {{
                // Context-aware empty state so a filter/no-load never looks broken
                let note;
                if (total === 0) {{
                    note = STATE.participantFilter
                        ? 'Select a date range and press Load to see messages from ' + STATE.participantFilter
                        : 'Select a date range and press Load';
                }} else if (STATE.participantFilter) {{
                    note = 'No messages from ' + STATE.participantFilter + ' in this range';
                }} else {{
                    note = 'No messages';
                }}
                container.innerHTML = '';
                const es = document.createElement('div');
                es.className = 'empty-state';
                es.textContent = note;
                container.appendChild(es);
            }} else {{
                renderMessages(msgs);
            }}

            if (STATE.participantFilter) {{
                status.textContent = total
                    ? (msgs.length + ' / ' + total + ' messages · ' + STATE.participantFilter)
                    : ('Load a range · ' + STATE.participantFilter);
            }} else {{
                status.textContent = total ? (total + ' messages') : 'Select date range';
            }}

            if (STATE.searchTerm && STATE.searchTerm.trim()) {{
                runSearch(STATE.searchTerm, true);
            }}
        }}

        function populateParticipants() {{
            const sel = document.getElementById('participantFilter');
            const senders = Object.keys(CHAT_STATS.messages_by_sender)
                .map(k => [k, CHAT_STATS.messages_by_sender[k]])
                .sort((a, b) => b[1] - a[1]);
            senders.forEach(([name, count]) => sel.add(new Option(name + ' (' + count + ')', name)));
        }}

        // ===== Search (WhatsApp-style: highlight + navigate matches) =====
        function openSearch() {{
            document.getElementById('searchBar').classList.add('active');
            const inp = document.getElementById('searchInput');
            inp.focus();
            inp.select();
        }}

        function closeSearch() {{
            document.getElementById('searchBar').classList.remove('active');
            STATE.searchTerm = '';
            clearHighlights();
            STATE.searchMatches = [];
            STATE.searchIndex = -1;
            updateSearchCount();
        }}

        function clearHighlights() {{
            document.querySelectorAll('#messages [data-orig]').forEach(el => {{
                el.textContent = el.getAttribute('data-orig');
                el.removeAttribute('data-orig');
            }});
        }}

        function highlightInElement(el, term) {{
            let text = el.getAttribute('data-orig');
            if (text === null) {{
                text = el.textContent;
                el.setAttribute('data-orig', text);
            }}
            const lower = text.toLowerCase();
            const t = term.toLowerCase();
            if (t.length === 0) {{ el.textContent = text; return; }}  // guard: never loop forever
            let i = 0, idx, html = '';
            while ((idx = lower.indexOf(t, i)) !== -1) {{
                html += escapeHtml(text.slice(i, idx)) +
                        '<mark class="search-hl">' + escapeHtml(text.slice(idx, idx + t.length)) + '</mark>';
                i = idx + t.length;
            }}
            html += escapeHtml(text.slice(i));
            el.innerHTML = html;
        }}

        function runSearch(term, keepPosition) {{
            const prevIndex = STATE.searchIndex;
            STATE.searchTerm = term;
            clearHighlights();
            STATE.searchMatches = [];
            STATE.searchIndex = -1;
            if (term && term.trim()) {{
                const tl = term.toLowerCase();
                document.querySelectorAll('#messages .message-content').forEach(el => {{
                    if (el.textContent.toLowerCase().indexOf(tl) !== -1) {{
                        highlightInElement(el, term);
                    }}
                }});
                STATE.searchMatches = Array.from(document.querySelectorAll('#messages mark.search-hl'));
                if (STATE.searchMatches.length) {{
                    if (keepPosition) {{
                        // Re-highlight after a re-render (filter/load) without jumping
                        STATE.searchIndex = Math.min(Math.max(prevIndex, 0), STATE.searchMatches.length - 1);
                        focusMatch(true);
                    }} else {{
                        STATE.searchIndex = 0;
                        focusMatch(false);
                    }}
                }}
            }}
            updateSearchCount();
        }}

        function focusMatch(noScroll) {{
            STATE.searchMatches.forEach(m => m.classList.remove('current'));
            const m = STATE.searchMatches[STATE.searchIndex];
            if (m) {{
                m.classList.add('current');
                if (!noScroll) m.scrollIntoView({{ block: 'center', behavior: 'smooth' }});
            }}
            updateSearchCount();
        }}

        function nextMatch() {{
            if (!STATE.searchMatches.length) return;
            STATE.searchIndex = (STATE.searchIndex + 1) % STATE.searchMatches.length;
            focusMatch();
        }}

        function prevMatch() {{
            if (!STATE.searchMatches.length) return;
            STATE.searchIndex = (STATE.searchIndex - 1 + STATE.searchMatches.length) % STATE.searchMatches.length;
            focusMatch();
        }}

        function updateSearchCount() {{
            const c = document.getElementById('searchCount');
            if (!STATE.searchTerm || !STATE.searchTerm.trim()) {{ c.textContent = ''; return; }}
            if (!STATE.searchMatches.length) {{ c.textContent = 'No results'; return; }}
            c.textContent = (STATE.searchIndex + 1) + ' of ' + STATE.searchMatches.length;
        }}

        // ===== Chat-info / statistics panel =====
        function statRow(label, value) {{
            return '<div class="stat-row"><span class="stat-label">' + escapeHtml(label) +
                   '</span><span class="stat-value">' + escapeHtml(String(value)) + '</span></div>';
        }}

        function mediaChip(icon, label, n) {{
            return '<div class="media-chip"><span class="media-chip-n">' + icon + ' ' + escapeHtml(String(n)) +
                   '</span><span class="media-chip-l">' + escapeHtml(label) + '</span></div>';
        }}

        function openStats() {{
            const s = CHAT_STATS;
            const mn = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            let range = '';
            if (MONTHS_INFO.length) {{
                const a = MONTHS_INFO[0], b = MONTHS_INFO[MONTHS_INFO.length - 1];
                range = mn[a.month - 1] + ' ' + a.year;
                if (MONTHS_INFO.length > 1) range += ' – ' + mn[b.month - 1] + ' ' + b.year;
            }}
            const senders = Object.keys(s.messages_by_sender)
                .map(k => [k, s.messages_by_sender[k]])
                .sort((a, b) => b[1] - a[1]);
            const maxCount = senders.length ? senders[0][1] : 1;

            let html = '';
            html += '<div class="stats-id"><div class="stats-avatar">💬</div>' +
                    '<div class="stats-name">' + escapeHtml(s.chat_name) + '</div>' +
                    '<div class="stats-sub">' + s.participant_count + ' participants</div></div>';

            html += '<div class="stats-section"><div class="stats-section-title">Statistics</div>';
            html += statRow('Messages', s.total_messages.toLocaleString());
            html += statRow('Media', s.total_media.toLocaleString());
            if (range) html += statRow('Date range', range);
            html += '</div>';

            html += '<div class="stats-section"><div class="stats-section-title">Media</div><div class="media-chips">';
            html += mediaChip('🖼️', 'Images', s.images) + mediaChip('🎬', 'Videos', s.videos) +
                    mediaChip('🎵', 'Audio', s.audio) + mediaChip('📄', 'Documents', s.documents);
            html += '</div></div>';

            html += '<div class="stats-section"><div class="stats-section-title">Participants (' + senders.length + ')</div>';
            senders.forEach(([name, count]) => {{
                const pct = Math.round(count / maxCount * 100);
                html += '<button class="stats-part" data-sender="' + escapeHtml(name) + '">' +
                        '<div class="stats-part-top"><span class="stats-part-name">' + escapeHtml(name) +
                        '</span><span class="stats-part-count">' + count.toLocaleString() + '</span></div>' +
                        '<div class="stats-bar"><div class="stats-bar-fill" style="width:' + pct + '%"></div></div></button>';
            }});
            html += '</div>';

            const body = document.getElementById('statsBody');
            body.innerHTML = html;
            body.querySelectorAll('.stats-part').forEach(b => {{
                b.onclick = () => {{
                    const sender = b.getAttribute('data-sender');
                    document.getElementById('participantFilter').value = sender;
                    STATE.participantFilter = sender;
                    closeStats();
                    applyView();
                    if (!(STATE.searchTerm && STATE.searchTerm.trim())) window.scrollTo({{ top: 0 }});
                }};
            }});

            document.getElementById('statsOverlay').classList.add('active');
            document.getElementById('statsPanel').classList.add('open');
        }}

        function closeStats() {{
            document.getElementById('statsOverlay').classList.remove('active');
            document.getElementById('statsPanel').classList.remove('open');
        }}

        function applyTheme(theme) {{
            STATE.theme = theme;
            document.body.dataset.theme = theme;
            localStorage.setItem('theme', theme);
            document.getElementById('themeToggle').textContent = theme === 'dark' ? '☀️' : '🌙';
        }}

        function setupEvents() {{
            document.getElementById('themeToggle').onclick = () => {{
                applyTheme(STATE.theme === 'dark' ? 'light' : 'dark');
            }};
            
            document.getElementById('rangeToggle').onclick = () => {{
                document.getElementById('rangeSelector').classList.toggle('collapsed');
            }};
            
            // Auto-hide range selector on scroll
            let lastScrollY = 0;
            let ticking = false;
            
            window.addEventListener('scroll', () => {{
                if (!ticking) {{
                    window.requestAnimationFrame(() => {{
                        const rangeSelector = document.getElementById('rangeSelector');
                        const scrollY = window.scrollY;
                        
                        if (scrollY > 100) {{
                            rangeSelector.classList.add('hidden');
                        }} else {{
                            rangeSelector.classList.remove('hidden');
                        }}
                        
                        lastScrollY = scrollY;
                        ticking = false;
                    }});
                    ticking = true;
                }}
            }});
            
            document.getElementById('loadBtn').onclick = loadMessages;
            
            document.querySelectorAll('.quick-btn').forEach(btn => {{
                btn.onclick = () => {{
                    const range = btn.dataset.range;
                    const endSel = document.getElementById('endMonth');
                    const startSel = document.getElementById('startMonth');
                    
                    endSel.selectedIndex = endSel.options.length - 1;
                    
                    if (range === 'all') {{
                        startSel.selectedIndex = 0;
                    }} else if (range === 'last-1') {{
                        startSel.selectedIndex = Math.max(0, endSel.selectedIndex);
                    }} else if (range === 'last-3') {{
                        startSel.selectedIndex = Math.max(0, endSel.selectedIndex - 2);
                    }} else if (range === 'last-6') {{
                        startSel.selectedIndex = Math.max(0, endSel.selectedIndex - 5);
                    }}
                }};
            }});

            // Search controls
            document.getElementById('searchToggle').onclick = openSearch;
            document.getElementById('searchClose').onclick = closeSearch;
            let searchTimer = null;
            document.getElementById('searchInput').oninput = (e) => {{
                const v = e.target.value;
                clearTimeout(searchTimer);
                searchTimer = setTimeout(() => runSearch(v), 120);
            }};
            document.getElementById('searchInput').onkeydown = (e) => {{
                if (e.key === 'Enter') {{
                    e.preventDefault();
                    if (e.shiftKey) prevMatch(); else nextMatch();
                }} else if (e.key === 'Escape') {{
                    closeSearch();
                }}
            }};
            document.getElementById('searchPrev').onclick = prevMatch;
            document.getElementById('searchNext').onclick = nextMatch;

            // Participant filter
            document.getElementById('participantFilter').onchange = (e) => {{
                STATE.participantFilter = e.target.value || null;
                applyView();
                // Don't yank to top when a search is active (let it stay on the match)
                if (!(STATE.searchTerm && STATE.searchTerm.trim())) window.scrollTo({{ top: 0 }});
            }};

            // Chat-info / statistics panel
            document.getElementById('statsToggle').onclick = openStats;
            document.getElementById('statsClose').onclick = closeStats;
            document.getElementById('statsOverlay').onclick = closeStats;
            document.querySelector('.header-left').onclick = openStats;
            document.addEventListener('keydown', (e) => {{
                if (e.key === 'Escape' && document.getElementById('statsPanel').classList.contains('open')) {{
                    closeStats();
                }}
            }});
        }}

        init();
    </script>
</body>
</html>
'''
        
        output_file = self.media_folder / "chat_viewer.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Created: {output_file.name}")
        return output_file
    
    def process(self):
        """Main processing"""
        print("\n" + "=" * 70)
        print("🚀 WhatsApp Smart Viewer - Chunked Loading (NO CORS)")
        print("=" * 70)
        
        self.parse_chat_file()
        months_info = self.write_month_files()
        viewer_file = self.create_viewer_html(months_info)
        
        print("\n" + "=" * 70)
        print("🎉 SUCCESS!")
        print("=" * 70)
        print(f"\n📱 Usage:")
        print(f"   1. Double-click: {viewer_file.name}")
        print(f"   2. Select date range")
        print(f"   3. Click 'Load' button")
        print(f"   4. Change range anytime with 📅 button")
        print(f"\n💡 Features:")
        print(f"   ✅ No CORS errors (uses .js files)")
        print(f"   ✅ Works on mobile & desktop")
        print(f"   ✅ Handles huge chats (1-10GB+)")
        print(f"   ✅ Smart chunked loading")
        print(f"   ✅ Change ranges without closing")
        print(f"   ✅ WhatsApp-like UI")
        print(f"\n📊 Statistics:")
        print(f"   📨 Messages: {self.statistics['total_messages']:,}")
        print(f"   👥 Participants: {len(self.statistics['participants'])}")
        print(f"   📎 Media: {self.statistics['total_media']:,}")
        print("=" * 70 + "\n")


def main():
    print("\n" + "=" * 70)
    print("WhatsApp Smart Viewer - NO CORS Edition")
    print("=" * 70)
    
    folder_path = input("\n📂 Folder path (or Enter for current): ").strip()
    if not folder_path:
        folder_path = "."
    
    folder_path = Path(folder_path).resolve()
    
    if not folder_path.exists():
        print(f"❌ Not found: {folder_path}")
        return
    
    txt_files = list(folder_path.glob("*.txt"))
    
    if not txt_files:
        print("❌ No .txt files found!")
        return
    
    if len(txt_files) == 1:
        chat_file = txt_files[0]
        print(f"\n✅ Found: {chat_file.name}")
    else:
        print("\n📄 Multiple files:")
        for i, f in enumerate(txt_files, 1):
            print(f"   {i}. {f.name}")
        try:
            choice = int(input("\nSelect: ")) - 1
            chat_file = txt_files[choice]
        except (ValueError, IndexError):
            print("❌ Invalid")
            return
    
    print(f"\n⏳ Processing...")
    processor = WhatsAppSmartViewer(chat_file, folder_path)
    processor.process()


if __name__ == "__main__":
    main()