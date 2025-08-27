import os
import json
import logging
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.urls import resolve, reverse
from django.contrib import messages
from .services.gmail import (
    build_flow, get_gmail_service, create_gmail_draft, save_credentials,
    _save_creds_to_db, _load_creds_from_db, fetch_unread  # Added fetch_unread import
)
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator, EmptyPage
from .serializers import EmailSerializer
from .services import gemini


# Logging
logger = logging.getLogger(__name__)

########################################
# Helper Functions
########################################
def credentials_to_dict(credentials):
    """Convert credentials object to dictionary"""
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes,
    }

def is_authenticated(user=None):
    """Check if user has valid Gmail credentials"""
    try:
        # Try to get service - if it works, we're authenticated
        service = get_gmail_service(user=user)
        return service is not None
    except:
        return False

########################################
# Debug URLs
########################################
def debug_urls(request):
    path_info = request.path_info
    try:
        resolver_match = resolve(path_info)
        return JsonResponse({
            "status": "matched",
            "view_name": resolver_match.view_name,
            "app_name": resolver_match.app_name,
            "namespace": resolver_match.namespace,
            "url_name": resolver_match.url_name,
            "function": str(resolver_match.func)
        })
    except Exception as e:
        return JsonResponse({
            "status": "not_matched",
            "error": str(e),
            "path": path_info
        })

########################################
# Home page
########################################
def home_view(request):
    service = get_gmail_service(user=request.user if request.user.is_authenticated else None)
    authed = service is not None
    return render(request, "inbox/home.html", {"authed": authed})

########################################
# OAuth status
########################################
def auth_status(request):
    service = get_gmail_service(user=request.user if request.user.is_authenticated else None)
    
    # Test the service by trying to fetch the user's profile
    profile = None
    if service:
        try:
            profile = service.users().getProfile(userId="me").execute()
            logger.info(f"Successfully fetched Gmail profile: {profile.get('emailAddress')}")
        except Exception as e:
            logger.error(f"Error fetching Gmail profile: {str(e)}", exc_info=True)
            service = None
    
    return JsonResponse({
        "authenticated": service is not None,
        "django_authenticated": request.user.is_authenticated,
        "email": request.user.email if request.user.is_authenticated else None,
        "username": request.user.username if request.user.is_authenticated else None,
        "gmail_profile": profile,
    })
    
########################################
# OAuth start
########################################
def oauth_start(request):
    try:
        redirect_uri = request.build_absolute_uri("/oauth/callback/")
        logger.info(f"OAuth start with redirect_uri: {redirect_uri}")
        
        flow = build_flow(redirect_uri)
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        request.session["oauth_state"] = state
        logger.info(f"OAuth redirecting to: {auth_url}")
        return redirect(auth_url)
        
    except Exception as e:
        logger.error(f"OAuth start error: {str(e)}")
        return HttpResponseBadRequest(f"OAuth initialization failed: {str(e)}")

########################################
# OAuth callback (FIXED)
########################################
def oauth_callback(request):
    try:
        expected_state = request.session.get("oauth_state")
        returned_state = request.GET.get("state")
        
        if not expected_state or expected_state != returned_state:
            logger.error(f"State mismatch. Expected: {expected_state}, Got: {returned_state}")
            return HttpResponseBadRequest("Invalid OAuth state. Please try again.")
            
        redirect_uri = request.build_absolute_uri("/oauth/callback/")
        logger.info(f"OAuth callback with redirect_uri: {redirect_uri}")
        
        flow = build_flow(redirect_uri)
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        creds = flow.credentials
        
        # Save credentials to database
        _save_creds_to_db(creds, user=request.user if request.user.is_authenticated else None)
        request.session.pop("oauth_state", None)
        logger.info("OAuth successful. Credentials saved to database.")
        return redirect("home")
        
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}", exc_info=True)
        error_message = f"OAuth authentication failed: {str(e)}"
        
        # Check for common OAuth errors
        if "invalid_grant" in str(e):
            error_message += ". This may be due to an expired or invalid authorization code. Please try authenticating again."
        elif "redirect_uri_mismatch" in str(e):
            error_message += ". Redirect URI mismatch. Check your Google Cloud Console configuration."
        
        return HttpResponseBadRequest(error_message)

########################################
# API: unread emails with pagination
########################################
@api_view(['GET'])
def unread_emails_view(request):
    page_number = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)  # Allow configurable items per page
    
    try:
        page_number = int(page_number)
        if page_number < 1:
            page_number = 1
    except ValueError:
        page_number = 1
        
    try:
        per_page = int(per_page)
        if per_page < 1:
            per_page = 10
        if per_page > 50:  # Limit max items per page
            per_page = 50
    except ValueError:
        per_page = 10
        
    try:
        user = request.user if request.user.is_authenticated else None
        service = get_gmail_service(user=user)
        
        if not service:
            logger.warning("Failed to get Gmail service - user not authenticated or no valid credentials")
            return Response({'ok': False, 'error': 'Failed to authenticate'}, status=status.HTTP_401_UNAUTHORIZED)
        
        logger.info(f"Fetching unread emails for user: {user if user else 'anonymous'}")
        
        # Use the fetch_unread from services.gmail
        emails = fetch_unread(service, max_results=100)  # Fetch more emails for pagination
        
        if not emails:
            logger.warning("No unread emails found")
            return Response({'ok': True, 'emails': [], 'total_pages': 0, 'current_page': 1})
        
        paginator = Paginator(emails, per_page)
        try:
            page_obj = paginator.page(page_number)
        except EmptyPage:
            logger.warning(f"Requested page {page_number} out of range. Returning last page.")
            page_obj = paginator.page(paginator.num_pages)
        
        serializer = EmailSerializer(page_obj.object_list, many=True)
        return Response({
            'ok': True,
            'emails': serializer.data,
            'total_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'per_page': per_page,
            'total_emails': len(emails),
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        })
    except Exception as e:
        logger.error(f"Error in unread_emails_view: {str(e)}", exc_info=True)
        return Response({'ok': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
########################################
# API: generate reply with Gemini
########################################
@csrf_exempt
@require_POST
def generate_reply_view(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        email_text = payload.get("email_text", "")
        if not email_text:
            return HttpResponseBadRequest("email_text is required")
        summary = gemini.summarize_email(email_text)
        draft = gemini.generate_reply(email_text, summary=summary)
        return JsonResponse({"ok": True, "summary": summary, "draft_reply": draft})
    except Exception as e:
        logger.error(f"Generate reply error: {str(e)}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

########################################
# API: save draft to Gmail
########################################
@csrf_exempt
@require_POST
def save_draft_view(request):
    service = get_gmail_service(user=request.user if request.user.is_authenticated else None)
    if not service:
        return JsonResponse({"ok": False, "error": "Not authorized. Connect Gmail first."}, status=401)
    try:
        payload = json.loads(request.body.decode("utf-8"))
        to_email = payload.get("to")
        subject = payload.get("subject")
        body = payload.get("body")
        if not all([to_email, subject, body]):
            return HttpResponseBadRequest("to, subject, body are required")
        draft_id = create_gmail_draft(service, to_email, subject, body)
        return JsonResponse({"ok": True, "draft_id": draft_id})
    except Exception as e:
        logger.error(f"Save draft error: {str(e)}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)



# In views.py, add this function

@api_view(['GET'])
def email_detail_view(request, message_id):
    try:
        service = get_gmail_service(user=request.user if request.user.is_authenticated else None)
        if not service:
            return Response({'ok': False, 'error': 'Failed to authenticate'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # First check if the email is available
        from .services.gmail import is_email_available, get_email_details
        
        if not is_email_available(service, message_id):
            return Response({'ok': False, 'error': 'Email not found or may have been deleted'}, status=status.HTTP_404_NOT_FOUND)
        
        email_details = get_email_details(service, message_id)
        if not email_details:
            return Response({'ok': False, 'error': 'Email not found or may have been deleted'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({'ok': True, 'email': email_details})
    except Exception as e:
        logger.error(f"Error fetching email details: {str(e)}", exc_info=True)
        return Response({'ok': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@csrf_exempt
def mark_as_read_view(request, message_id):
    try:
        service = get_gmail_service(user=request.user if request.user.is_authenticated else None)
        if not service:
            return Response({'ok': False, 'error': 'Failed to authenticate'}, status=status.HTTP_401_UNAUTHORIZED)
        
        from .services.gmail import mark_as_read
        
        success = mark_as_read(service, message_id)
        if success:
            # Clear the cache for unread emails to ensure fresh data
            from django.core.cache import cache
            # Clear all unread email caches
            cache.delete_many([key for key in cache.keys('*gmail_unread_*')])
            
            return Response({'ok': True})
        else:
            return Response({'ok': False, 'error': 'Failed to mark email as read'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"Error marking email as read: {str(e)}", exc_info=True)
        return Response({'ok': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


########################################
# Logout
########################################
def logout_view(request):
    request.session.flush()
    return redirect('oauth_start')


