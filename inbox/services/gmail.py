import base64
import json
import logging  # Make sure this is imported
from email.mime.text import MIMEText
from typing import List, Dict, Any, Optional
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache  # Add this import
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from ..models import GmailToken
import time  # Add this import at the top

# Add this logger configuration
logger = logging.getLogger(__name__)

# ——— Scopes ———
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid", 
    "https://www.googleapis.com/auth/userinfo.email",
]

def build_flow(redirect_uri: str) -> Flow:
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )

def _load_creds_from_db(user=None) -> Optional[Credentials]:
    token = GmailToken.objects.filter(user=user).first()
    if not token:
        return None
    try:
        return Credentials.from_authorized_user_info(json.loads(token.token_json), SCOPES)
    except Exception as e:
        logger.error(f"Error loading credentials from DB: {str(e)}", exc_info=True)
        return None

def _save_creds_to_db(creds: Credentials, user=None):
    """
    Save credentials to database
    """
    try:
        payload = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }
        
        # Handle expiry safely
        if hasattr(creds, "expiry") and creds.expiry:
            payload["expiry"] = creds.expiry.isoformat()
        
        with transaction.atomic():
            # Update or create token record
            token, created = GmailToken.objects.update_or_create(
                user=user,
                defaults={
                    'token_json': json.dumps(payload),
                    'updated_at': timezone.now()
                }
            )
            logger.info(f"Credentials {'saved' if created else 'updated'} for user: {user}")
            
    except Exception as e:
        logger.error(f"Error saving credentials to DB: {str(e)}", exc_info=True)
        raise

def save_credentials(creds: Credentials, user=None):
    """Public wrapper to save credentials."""
    _save_creds_to_db(creds, user)

def get_gmail_service(user=None):
    creds = _load_creds_from_db(user=user)
    if not creds:
        logger.warning("No credentials found in database")
        return None
    try:
        if creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials")
            creds.refresh(Request())
            _save_creds_to_db(creds, user=user)
        service = build("gmail", "v1", credentials=creds)
        logger.info("Successfully created Gmail service")
        return service
    except Exception as e:
        logger.error(f"Error getting Gmail service: {str(e)}", exc_info=True)
        return None

# In services/gmail.py
import time  # Add this import at the top

def fetch_unread(service, q: str = "is:unread in:inbox", max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Returns a lightweight list of unread emails using sequential requests to avoid rate limiting
    """
    # Create a unique cache key based on the query and max_results
    cache_key = f"gmail_unread_{hash(q)}_{max_results}"
    
    # Try to get cached results
    cached_emails = cache.get(cache_key)
    if cached_emails is not None:
        logger.info(f"Returning {len(cached_emails)} cached emails for query: {q}")
        return cached_emails
    
    # If not in cache, fetch from Gmail API
    try:
        logger.info(f"Fetching unread emails with query: {q}")
        results = service.users().messages().list(
            userId="me",
            q=q,
            maxResults=max_results,
        ).execute()
        logger.info(f"Gmail API response keys: {results.keys()}")
        messages = results.get("messages", [])
        logger.info(f"Found {len(messages)} unread messages")
        out: List[Dict[str, Any]] = []
        if not messages:
            logger.info("No unread messages found")
            # Cache empty result for 2 minutes
            cache.set(cache_key, out, 120)
            return out
        
        # Process messages sequentially to avoid rate limiting
        for i, m in enumerate(messages):
            try:
                # Add a small delay between requests to avoid rate limiting
                if i > 0:
                    time.sleep(0.1)  # 100ms delay between requests
                
                logger.info(f"Fetching message with ID: {m['id']}")
                full = service.users().messages().get(
                    userId="me", 
                    id=m["id"], 
                    format="metadata",
                    metadataHeaders=["Subject", "From", "Date", "To"]
                ).execute()
                
                payload = full.get("payload", {}) or {}
                headers = payload.get("headers", []) or []
                hmap = {h.get("name", "").lower(): h.get("value", "") for h in headers}
                out.append({
                    "id": full.get("id", ""),
                    "threadId": full.get("threadId", ""),
                    "snippet": full.get("snippet", "") or "",
                    "subject": hmap.get("subject", "") or "(no subject)",
                    "from": hmap.get("from", "") or "",
                    "to": hmap.get("to", "") or "",
                    "date": hmap.get("date", "") or "",
                    "body_text": "",  # We are not fetching the body in batch
                })
            except Exception as e:
                logger.error(f"Error processing message {m['id']}: {str(e)}", exc_info=True)
                continue
        
        logger.info(f"Successfully processed {len(out)} unread messages")
        
        # Cache the results for 5 minutes (300 seconds)
        cache.set(cache_key, out, 300)
        logger.info(f"Cached {len(out)} emails for {300} seconds")
        
        return out
    except Exception as e:
        logger.error(f"Error fetching unread emails: {str(e)}", exc_info=True)
        return []

def extract_plain_text(payload) -> str:
    try:
        # nested multiparts
        if "parts" in payload:
            for part in payload["parts"]:
                # recurse first
                if part.get("parts"):
                    t = extract_plain_text(part)
                    if t:
                        return t
                if part.get("mimeType") == "text/plain":
                    data = (part.get("body") or {}).get("data")
                    if data:
                        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        # single part
        if payload.get("mimeType") == "text/plain":
            data = (payload.get("body") or {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"Error extracting plain text: {str(e)}", exc_info=True)
    return ""

def create_gmail_draft(service, to_email: str, subject: str, body_text: str) -> str:
    try:
        msg = MIMEText(body_text)
        msg["to"] = to_email
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        draft = service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw}}
        ).execute()
        return draft.get("id", "")
    except Exception as e:
        logger.error(f"Error creating Gmail draft: {str(e)}", exc_info=True)
        return ""

def mark_as_read(service, message_id: str):
    """
    Mark an email as read by removing the UNREAD label
    """
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Error marking message {message_id} as read: {str(e)}", exc_info=True)
        return False

def get_email_details(service, message_id: str) -> Optional[Dict[str, Any]]:
    """
    Get full details of a specific email
    """
    # Create a cache key for this specific email
    cache_key = f"gmail_email_details_{message_id}"
    
    # Try to get cached result
    cached_email = cache.get(cache_key)
    if cached_email is not None:
        logger.info(f"Returning cached email details for message ID: {message_id}")
        return cached_email
    
    try:
        message = service.users().messages().get(
            userId="me", 
            id=message_id, 
            format="full"
        ).execute()
        
        payload = message.get("payload", {}) or {}
        headers = payload.get("headers", []) or []
        hmap = {h.get("name", "").lower(): h.get("value", "") for h in headers}
        
        email_details = {
            "id": message.get("id", ""),
            "threadId": message.get("threadId", ""),
            "snippet": message.get("snippet", "") or "",
            "subject": hmap.get("subject", "") or "(no subject)",
            "from": hmap.get("from", "") or "",
            "to": hmap.get("to", "") or "",
            "date": hmap.get("date", "") or "",
            "body_text": extract_plain_text(payload),
            "labels": message.get("labelIds", []),
        }
        
        # Cache the email details for 10 minutes (600 seconds)
        cache.set(cache_key, email_details, 600)
        logger.info(f"Cached email details for message ID: {message_id} for {600} seconds")
        
        return email_details
    except Exception as e:
        logger.error(f"Error getting email details for {message_id}: {str(e)}", exc_info=True)
        return None
    
# In services/gmail.py, add this function
def execute_with_retry(service_func, max_retries=3, initial_delay=0.5):
    """Execute a Gmail API function with retry logic"""
    for attempt in range(max_retries):
        try:
            return service_func()
        except Exception as e:
            if "rateLimitExceeded" in str(e) or "quotaExceeded" in str(e):
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Rate limited. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
            raise  # Re-raise the exception if it's not a rate limit error or we've exhausted retries
        
# In services/gmail.py
def is_email_available(service, message_id: str) -> bool:
    """
    Check if an email is still available (not deleted or moved)
    """
    try:
        # Try to get just the metadata to check if the email exists
        service.users().messages().get(
            userId="me", 
            id=message_id, 
            format="metadata",
            metadataHeaders=["Subject"]
        ).execute()
        return True
    except Exception as e:
        if hasattr(e, 'resp') and e.resp.status == 404:
            return False
        # For other errors, assume it might be available
        return True

def mark_as_read(service, message_id: str) -> bool:
    """
    Mark an email as read by removing the UNREAD label
    """
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        logger.info(f"Successfully marked message {message_id} as read")
        return True
    except Exception as e:
        logger.error(f"Error marking message {message_id} as read: {str(e)}", exc_info=True)
        return False