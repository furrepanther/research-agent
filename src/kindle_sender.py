import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from src.utils import logger, get_config

class KindleSender:
    def __init__(self, config=None):
        if config is None:
            config = get_config()
            
        self.email_config = config.get("email", {})
        self.smtp_server = self.email_config.get("smtp_server", "smtp.gmail.com")
        self.smtp_port = int(self.email_config.get("smtp_port", 587))
        self.smtp_user = self.email_config.get("smtp_user")
        self.smtp_password = self.email_config.get("smtp_password")
        
        # Security: Try keyring if password missing in config
        if not self.smtp_password and self.smtp_user:
            try:
                import keyring
                # Helper to get password
                pw = keyring.get_password("research_agent", self.smtp_user)
                if pw:
                    self.smtp_password = pw
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Keyring access failed: {e}")
                
        self.kindle_email = self.email_config.get("kindle_email") # Target address
        
    def validate_config(self):
        """Returns True if configuration is present."""
        if not self.smtp_user or not self.smtp_password or not self.kindle_email:
            return False, "Missing Email/SMTP configuration. Check config.yaml or run tools/setup_keys.py."
        return True, ""

    def send_file(self, file_path):
        """Sends the file to the Kindle email address."""
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"
            
        # Check size (limit ~50MB usually, play safe with 25MB or just warn)
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 50:
            return False, f"File too large ({size_mb:.1f}MB). Kindle limit is ~50MB."
            
        success, msg = self.validate_config()
        if not success:
            return False, msg

        filename = os.path.basename(file_path)
        
        try:
            # Create Email
            msg_root = MIMEMultipart()
            msg_root['Subject'] = "Convert" # 'Convert' triggers PDF conversion on Amazon's side if supported/needed
            msg_root['From'] = self.smtp_user
            msg_root['To'] = self.kindle_email
            
            # Body
            msg_root.attach(MIMEText(f"Sending document: {filename}", 'plain'))
            
            # Attachment
            with open(file_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=filename)
                
            part['Content-Disposition'] = f'attachment; filename="{filename}"'
            msg_root.attach(part)
            
            # Send
            logger.info(f"Connecting to SMTP: {self.smtp_server}:{self.smtp_port}")
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg_root)
            server.quit()
            
            logger.info(f"Sent {filename} to {self.kindle_email}")
            return True, "Sent successfully!"
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False, str(e)
