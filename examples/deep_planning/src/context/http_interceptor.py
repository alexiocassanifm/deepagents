"""
HTTP Request Interceptor for OpenRouter API Calls

This module provides logging interceptors that capture the exact HTTP requests
and responses made to OpenRouter API, allowing us to compare what we send
vs what OpenRouter reports for token usage.
"""

import logging
import json
import time
from typing import Dict, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)
http_logger = logging.getLogger('openrouter_http')

# Store original functions for restoration
_original_httpx_post = None
_original_requests_post = None
_patched = False


def log_request_details(url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> None:
    """Log detailed information about HTTP requests to OpenRouter."""
    
    if "openrouter.ai" not in url:
        return  # Only log OpenRouter requests
    
    timestamp = time.strftime('%H:%M:%S.%f')[:-3]  # Include milliseconds
    http_logger.info(f"🌐 OUTGOING REQUEST TO OPENROUTER AT {timestamp}")
    http_logger.info(f"📍 URL: {url}")
    
    # Log headers (excluding sensitive auth info)
    safe_headers = {k: v for k, v in headers.items() if 'auth' not in k.lower() and 'key' not in k.lower()}
    http_logger.info(f"📋 Headers: {json.dumps(safe_headers, indent=2)}")
    
    # Log the complete payload
    try:
        http_logger.info(f"📤 COMPLETE REQUEST PAYLOAD:")
        
        if isinstance(payload, dict):
            # Count tokens in the payload if possible
            messages = payload.get('messages', [])
            if messages:
                http_logger.info(f"  Model: {payload.get('model', 'unknown')}")
                http_logger.info(f"  Messages: {len(messages)}")
                http_logger.info(f"  Temperature: {payload.get('temperature', 'not set')}")
                http_logger.info(f"  Max tokens: {payload.get('max_tokens', 'not set')}")
                
                # Log message breakdown
                total_content_length = 0
                for i, msg in enumerate(messages):
                    content = msg.get('content', '')
                    role = msg.get('role', 'unknown')
                    content_len = len(str(content))
                    total_content_length += content_len
                    
                    # Log first few messages in detail
                    if i < 3:
                        preview = str(content)[:150] + "..." if len(str(content)) > 150 else str(content)
                        http_logger.info(f"    Message {i+1} ({role}): {content_len} chars - '{preview}'")
                    elif i == 3:
                        http_logger.info(f"    ... and {len(messages) - 3} more messages")
                
                http_logger.info(f"  Total content length: {total_content_length:,} characters")
                http_logger.info(f"  Estimated tokens (chars/4): {total_content_length // 4:,}")
            
            # Log the full JSON payload (truncated if too long)
            payload_json = json.dumps(payload, indent=2, default=str)
            if len(payload_json) > 5000:  # Truncate very long payloads
                http_logger.info(f"📄 Full payload (first 5000 chars):\n{payload_json[:5000]}...")
            else:
                http_logger.info(f"📄 Full payload:\n{payload_json}")
                
        else:
            http_logger.info(f"📄 Payload type: {type(payload)} - {str(payload)[:500]}")
            
    except Exception as e:
        http_logger.error(f"❌ Error logging payload: {e}")


def log_response_details(response: Any) -> None:
    """Log detailed information about HTTP responses from OpenRouter."""
    
    try:
        timestamp = time.strftime('%H:%M:%S.%f')[:-3]
        http_logger.info(f"📨 RESPONSE FROM OPENROUTER AT {timestamp}")
        http_logger.info(f"🔢 Status: {getattr(response, 'status_code', 'unknown')}")
        
        # Try to get response headers
        headers = getattr(response, 'headers', {})
        if headers:
            # Look for token usage in headers
            for key, value in headers.items():
                if 'token' in key.lower() or 'usage' in key.lower():
                    http_logger.info(f"📊 Header {key}: {value}")
        
        # Try to parse JSON response
        if hasattr(response, 'json'):
            try:
                json_data = response.json()
                
                # Look for usage information
                if 'usage' in json_data:
                    usage = json_data['usage']
                    http_logger.info(f"🎯 OPENROUTER REPORTED USAGE:")
                    http_logger.info(f"  Prompt tokens: {usage.get('prompt_tokens', 'not reported')}")
                    http_logger.info(f"  Completion tokens: {usage.get('completion_tokens', 'not reported')}")
                    http_logger.info(f"  Total tokens: {usage.get('total_tokens', 'not reported')}")
                
                # Log other relevant fields
                if 'model' in json_data:
                    http_logger.info(f"🤖 Model used: {json_data['model']}")
                    
                if 'id' in json_data:
                    http_logger.info(f"🆔 Request ID: {json_data['id']}")
                
                # Log choices/content length
                if 'choices' in json_data:
                    choices = json_data['choices']
                    if choices:
                        first_choice = choices[0]
                        if 'message' in first_choice:
                            content = first_choice['message'].get('content', '')
                            http_logger.info(f"📝 Response content: {len(str(content))} characters")
                            
                            # Show preview of response
                            preview = str(content)[:200] + "..." if len(str(content)) > 200 else str(content)
                            http_logger.info(f"📄 Response preview: '{preview}'")
                
            except Exception as e:
                http_logger.error(f"❌ Error parsing JSON response: {e}")
                # Try to log raw content
                if hasattr(response, 'text'):
                    text = response.text[:1000] + "..." if len(response.text) > 1000 else response.text
                    http_logger.info(f"📄 Raw response: {text}")
        
    except Exception as e:
        http_logger.error(f"❌ Error logging response: {e}")


def patch_httpx():
    """Patch httpx.post to intercept OpenRouter requests."""
    
    try:
        import httpx
        global _original_httpx_post
        
        if _original_httpx_post is None:
            _original_httpx_post = httpx.post
        
        def patched_post(*args, **kwargs):
            """Patched httpx.post with logging."""
            
            # Log the request
            url = args[0] if args else kwargs.get('url', 'unknown')
            
            # Try to extract payload from different formats
            payload = None
            if 'json' in kwargs:
                payload = kwargs['json']
            elif len(args) > 1:
                payload = args[1]
            elif 'data' in kwargs:
                try:
                    payload = json.loads(kwargs['data'])
                except:
                    payload = kwargs['data']
            
            headers = kwargs.get('headers', {})
            
            log_request_details(str(url), payload or {}, headers)
            
            # Make the actual request
            response = _original_httpx_post(*args, **kwargs)
            
            # Log the response
            if "openrouter.ai" in str(url):
                log_response_details(response)
            
            return response
        
        # Apply the patch
        httpx.post = patched_post
        return True
        
    except ImportError:
        http_logger.warning("httpx not available for patching")
        return False


def patch_requests():
    """Patch requests.post to intercept OpenRouter requests."""
    
    try:
        import requests
        global _original_requests_post
        
        if _original_requests_post is None:
            _original_requests_post = requests.post
        
        def patched_post(*args, **kwargs):
            """Patched requests.post with logging."""
            
            # Log the request
            url = args[0] if args else kwargs.get('url', 'unknown')
            
            # Try to extract payload
            payload = None
            if 'json' in kwargs:
                payload = kwargs['json']
            elif len(args) > 1:
                payload = args[1]
            elif 'data' in kwargs:
                try:
                    if isinstance(kwargs['data'], str):
                        payload = json.loads(kwargs['data'])
                    else:
                        payload = kwargs['data']
                except:
                    payload = kwargs['data']
            
            headers = kwargs.get('headers', {})
            
            log_request_details(str(url), payload or {}, headers)
            
            # Make the actual request
            response = _original_requests_post(*args, **kwargs)
            
            # Log the response
            if "openrouter.ai" in str(url):
                log_response_details(response)
            
            return response
        
        # Apply the patch
        requests.post = patched_post
        return True
        
    except ImportError:
        http_logger.warning("requests not available for patching")
        return False


def enable_openrouter_logging():
    """Enable comprehensive OpenRouter request/response logging."""
    
    global _patched
    
    if _patched:
        http_logger.info("🔄 OpenRouter logging already enabled")
        return
    
    http_logger.info("🚀 Enabling OpenRouter HTTP logging...")
    
    # Try to patch both httpx and requests
    httpx_patched = patch_httpx()
    requests_patched = patch_requests()
    
    if httpx_patched or requests_patched:
        _patched = True
        http_logger.info(f"✅ OpenRouter logging enabled (httpx: {httpx_patched}, requests: {requests_patched})")
    else:
        http_logger.error("❌ Could not enable OpenRouter logging - no HTTP library found")


def disable_openrouter_logging():
    """Disable OpenRouter logging by restoring original functions."""
    
    global _patched
    
    if not _patched:
        return
    
    try:
        # Restore original functions
        if _original_httpx_post:
            import httpx
            httpx.post = _original_httpx_post
            
        if _original_requests_post:
            import requests  
            requests.post = _original_requests_post
            
        _patched = False
        http_logger.info("🔄 OpenRouter logging disabled")
        
    except Exception as e:
        http_logger.error(f"❌ Error disabling OpenRouter logging: {e}")


# Auto-enable logging when module is imported
try:
    enable_openrouter_logging()
except Exception as e:
    logger.error(f"Failed to auto-enable OpenRouter logging: {e}")