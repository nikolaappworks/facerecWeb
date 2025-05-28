from dotenv import load_dotenv
import os
import json
from typing import Dict, Optional, Tuple

load_dotenv()


class EmailTokenService:
    """Service for handling email-to-token mapping operations."""
    
    def __init__(self):
        """Initialize the service with email-to-key mapping and client tokens."""
        try:
            # CLIENTS_EMAILS mapira email -> key
            # {"rts@gmail.com": "rts", "hrt@gmail.com": "hrt", ...}
            self.clients_emails: Dict[str, str] = json.loads(
                os.getenv('CLIENTS_EMAILS', '{}')
            )
            
            # CLIENTS_TOKENS mapira token -> key  
            # {"dJfY7Aq4mycEYEtaHxAiY6Ok43Me5IT2QwD": "rts", ...}
            self.clients_tokens: Dict[str, str] = json.loads(
                os.getenv('CLIENTS_TOKENS', '{}')
            )
            
            # Kreiramo inverzni mapiranje: key -> token
            self.key_to_token: Dict[str, str] = {}
            for token, key in self.clients_tokens.items():
                self.key_to_token[key] = token
                
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"Invalid JSON configuration in environment variables: {str(e)}")
    
    def get_token_by_email(self, email: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get token for given email address.
        
        Args:
            email (str): Email address to look up
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (token, error_message)
            If successful, returns (token, None)
            If error, returns (None, error_message)
        """
        if not email or not isinstance(email, str):
            return None, "Email address is required and must be a valid string"
        
        email = email.strip().lower()
        
        # Check if email exists in CLIENTS_EMAILS
        if email not in self.clients_emails:
            return None, f"Email '{email}' not found in authorized users"
        
        # Get the key for this email
        key = self.clients_emails[email]
        
        # Check if the key exists in our key-to-token mapping
        if key not in self.key_to_token:
            return None, f"Token not found for key '{key}'. Please contact administrator"
        
        # Return the token
        return self.key_to_token[key], None
    
    def validate_email_exists(self, email: str) -> bool:
        """
        Check if email exists in the mapping.
        
        Args:
            email (str): Email address to validate
            
        Returns:
            bool: True if email exists, False otherwise
        """
        if not email or not isinstance(email, str):
            return False
        
        return email.strip().lower() in self.clients_emails
    
    def get_all_authorized_emails(self) -> list:
        """
        Get list of all authorized email addresses.
        
        Returns:
            list: List of authorized email addresses
        """
        return list(self.clients_emails.keys())
    
    def get_key_by_email(self, email: str) -> Optional[str]:
        """
        Get key for given email address.
        
        Args:
            email (str): Email address to look up
            
        Returns:
            Optional[str]: Key if found, None otherwise
        """
        if not email or not isinstance(email, str):
            return None
        
        email = email.strip().lower()
        return self.clients_emails.get(email)