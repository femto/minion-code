#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OAuth authentication module for minion-code ACP agent.

Handles OAuth PKCE flow with OpenRouter for user authentication.
Users sign in with their own OpenRouter account and use their own credits.
"""

import asyncio
import json
import logging
import os
import secrets
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

# Configuration
MINION_AUTH_DIR = Path.home() / ".minion"
CREDENTIALS_FILE = MINION_AUTH_DIR / "credentials.json"

# OpenRouter OAuth configuration
# OpenRouter uses a simple OAuth PKCE flow - no client_id required
OPENROUTER_AUTH_URL = "https://openrouter.ai/auth"
OPENROUTER_TOKEN_URL = "https://openrouter.ai/api/v1/auth/keys"
# API endpoint (OpenRouter is OpenAI-compatible)
DEFAULT_API_ENDPOINT = os.environ.get(
    "MINION_API_ENDPOINT",
    "https://openrouter.ai/api/v1"
)
# OpenRouter only allows localhost:3000 or https for callbacks
OAUTH_CALLBACK_PORT = int(os.environ.get("MINION_OAUTH_CALLBACK_PORT", "3000"))


class Credentials:
    """Stores authentication credentials (OpenRouter API key)."""

    def __init__(
        self,
        access_token: Optional[str] = None,  # OpenRouter API key (sk-or-...)
        refresh_token: Optional[str] = None,  # Not used by OpenRouter
        token_type: str = "Bearer",
        expires_at: Optional[int] = None,
        provider: str = "openrouter",
        api_keys: Optional[Dict[str, str]] = None,  # Legacy fallback
        api_endpoint: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = token_type
        self.expires_at = expires_at
        self.provider = provider
        # For direct API key storage (fallback)
        self.api_keys = api_keys or {}
        # API endpoint - OpenRouter is OpenAI-compatible
        self.api_endpoint = api_endpoint or DEFAULT_API_ENDPOINT
        # Default model to use (OpenRouter format: provider/model)
        self.default_model = default_model or "anthropic/claude-sonnet-4"

    def is_valid(self) -> bool:
        """Check if credentials are valid (have OpenRouter API key or legacy API keys)."""
        if self.access_token:
            return True
        if self.api_keys:
            return bool(self.api_keys.get("openai") or self.api_keys.get("anthropic"))
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_at": self.expires_at,
            "provider": self.provider,
            "api_keys": self.api_keys,
            "api_endpoint": self.api_endpoint,
            "default_model": self.default_model,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Credentials":
        return cls(
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            token_type=data.get("token_type", "Bearer"),
            expires_at=data.get("expires_at"),
            provider=data.get("provider", "openrouter"),
            api_keys=data.get("api_keys", {}),
            api_endpoint=data.get("api_endpoint"),
            default_model=data.get("default_model"),
        )


class CredentialStore:
    """Manages credential storage and retrieval."""

    def __init__(self, credentials_file: Path = CREDENTIALS_FILE):
        self.credentials_file = credentials_file
        self._credentials: Optional[Credentials] = None

    def _ensure_dir(self) -> None:
        """Ensure the credentials directory exists."""
        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Optional[Credentials]:
        """Load credentials from file."""
        if self._credentials:
            return self._credentials

        if not self.credentials_file.exists():
            logger.debug("No credentials file found")
            return None

        try:
            with open(self.credentials_file, "r") as f:
                data = json.load(f)
            self._credentials = Credentials.from_dict(data)
            logger.info("Loaded credentials from file")
            return self._credentials
        except Exception as e:
            logger.warning(f"Failed to load credentials: {e}")
            return None

    def save(self, credentials: Credentials) -> None:
        """Save credentials to file."""
        self._ensure_dir()
        try:
            with open(self.credentials_file, "w") as f:
                json.dump(credentials.to_dict(), f, indent=2)
            # Set restrictive permissions
            os.chmod(self.credentials_file, 0o600)
            self._credentials = credentials
            logger.info("Saved credentials to file")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            raise

    def clear(self) -> None:
        """Clear stored credentials."""
        self._credentials = None
        if self.credentials_file.exists():
            try:
                self.credentials_file.unlink()
                logger.info("Cleared credentials")
            except Exception as e:
                logger.warning(f"Failed to delete credentials file: {e}")

    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        creds = self.load()
        return creds is not None and creds.is_valid()


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""

    # Class-level storage for the received data
    auth_code: Optional[str] = None
    auth_state: Optional[str] = None
    error: Optional[str] = None
    received_event: Optional[asyncio.Event] = None
    event_loop: Optional[asyncio.AbstractEventLoop] = None  # Store event loop reference

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default HTTP logging."""
        logger.debug(f"OAuth callback: {format % args}")

    def do_GET(self) -> None:
        """Handle GET request (OAuth callback)."""
        parsed = urlparse(self.path)

        # Ignore non-callback requests (e.g., /favicon.ico)
        if not parsed.path.startswith("/callback"):
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)

        # Extract code and state
        if "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            OAuthCallbackHandler.auth_state = params.get("state", [None])[0]
            self._send_success_response()
            logger.info(f"OAuth callback received with code")
        elif "error" in params:
            OAuthCallbackHandler.error = params.get("error_description", params["error"])[0]
            self._send_error_response(OAuthCallbackHandler.error)
            logger.error(f"OAuth callback received with error: {OAuthCallbackHandler.error}")
        else:
            # No code or error - might be a pre-flight or other request
            self.send_response(400)
            self.end_headers()
            return

        # Signal that we received the callback
        if OAuthCallbackHandler.received_event and OAuthCallbackHandler.event_loop:
            # Use call_soon_threadsafe since we're in a different thread
            OAuthCallbackHandler.event_loop.call_soon_threadsafe(
                OAuthCallbackHandler.received_event.set
            )

    def _send_success_response(self) -> None:
        """Send success HTML response."""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Successful</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                       display: flex; justify-content: center; align-items: center; height: 100vh;
                       margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
                .card { background: white; padding: 40px; border-radius: 16px; text-align: center;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.2); }
                h1 { color: #22c55e; margin-bottom: 16px; }
                p { color: #666; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Authentication Successful</h1>
                <p>You can close this window and return to your editor.</p>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def _send_error_response(self, error: str) -> None:
        """Send error HTML response."""
        self.send_response(400)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Failed</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                       display: flex; justify-content: center; align-items: center; height: 100vh;
                       margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
                .card {{ background: white; padding: 40px; border-radius: 16px; text-align: center;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.2); }}
                h1 {{ color: #ef4444; margin-bottom: 16px; }}
                p {{ color: #666; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Authentication Failed</h1>
                <p>{error}</p>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode())


class OAuthFlow:
    """Handles the OpenRouter OAuth PKCE authentication flow."""

    def __init__(
        self,
        callback_port: int = OAUTH_CALLBACK_PORT,
        credential_store: Optional[CredentialStore] = None,
    ):
        self.callback_port = callback_port
        self.credential_store = credential_store or CredentialStore()
        self._http_server: Optional[HTTPServer] = None
        self._server_thread: Optional[Thread] = None
        # PKCE: code_verifier will be generated per auth flow
        self._code_verifier: Optional[str] = None

    def _generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code_verifier and code_challenge."""
        import hashlib
        import base64

        # Generate random code_verifier (43-128 characters)
        code_verifier = secrets.token_urlsafe(64)[:128]

        # Generate code_challenge = BASE64URL(SHA256(code_verifier))
        digest = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode()

        return code_verifier, code_challenge

    def get_authorization_url(self, code_challenge: str) -> str:
        """Generate the OpenRouter OAuth authorization URL with PKCE."""
        from urllib.parse import urlencode

        callback_url = f"http://localhost:{self.callback_port}/callback"
        params = {
            "callback_url": callback_url,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{OPENROUTER_AUTH_URL}?{urlencode(params)}"

    async def start_auth_flow(self, timeout: float = 300.0) -> Optional[Credentials]:
        """
        Start the OpenRouter OAuth PKCE flow.

        1. Generate PKCE code_verifier and code_challenge
        2. Start local HTTP server for callback
        3. Open browser to OpenRouter authorization URL
        4. Wait for callback with authorization code
        5. Exchange code for API key (with code_verifier)
        6. Store and return credentials

        Args:
            timeout: Maximum time to wait for auth completion (seconds)

        Returns:
            Credentials if successful, None otherwise
        """
        # Generate PKCE pair
        self._code_verifier, code_challenge = self._generate_pkce_pair()

        # Reset callback handler state
        OAuthCallbackHandler.auth_code = None
        OAuthCallbackHandler.auth_state = None
        OAuthCallbackHandler.error = None
        OAuthCallbackHandler.event_loop = asyncio.get_running_loop()
        OAuthCallbackHandler.received_event = asyncio.Event()

        # Start local HTTP server
        try:
            self._http_server = HTTPServer(
                ("localhost", self.callback_port),
                OAuthCallbackHandler
            )
        except OSError as e:
            logger.error(f"Failed to start callback server on port {self.callback_port}: {e}")
            return None

        # Run server in background thread - handle multiple requests until we get the callback
        def serve_until_callback():
            while not OAuthCallbackHandler.auth_code and not OAuthCallbackHandler.error:
                if self._http_server:
                    self._http_server.handle_request()

        self._server_thread = Thread(target=serve_until_callback)
        self._server_thread.daemon = True
        self._server_thread.start()

        logger.info(f"Started OAuth callback server on port {self.callback_port}")

        # Open browser with PKCE code_challenge
        auth_url = self.get_authorization_url(code_challenge)
        logger.info(f"Opening browser for OpenRouter authentication: {auth_url}")

        try:
            webbrowser.open(auth_url)
        except Exception as e:
            logger.warning(f"Failed to open browser: {e}")
            logger.info(f"Please open this URL manually: {auth_url}")

        # Wait for callback
        try:
            await asyncio.wait_for(
                OAuthCallbackHandler.received_event.wait(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error("OAuth flow timed out")
            self._cleanup_server()
            return None

        self._cleanup_server()

        # Check for errors
        if OAuthCallbackHandler.error:
            logger.error(f"OAuth error: {OAuthCallbackHandler.error}")
            return None

        # Exchange code for API key
        auth_code = OAuthCallbackHandler.auth_code
        if not auth_code:
            logger.error("No authorization code received")
            return None

        credentials = await self._exchange_code_for_api_key(auth_code)

        if credentials:
            self.credential_store.save(credentials)

        return credentials

    async def _exchange_code_for_api_key(self, code: str) -> Optional[Credentials]:
        """Exchange authorization code for OpenRouter API key using PKCE."""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    OPENROUTER_TOKEN_URL,
                    json={
                        "code": code,
                        "code_verifier": self._code_verifier,
                        "code_challenge_method": "S256",
                    },
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"API key exchange failed: {response.status} - {error_text}")
                        return None

                    data = await response.json()
                    logger.info(f"OpenRouter response keys: {list(data.keys())}")

                    # OpenRouter returns: { "key": "sk-or-..." }
                    api_key = data.get("key")
                    if not api_key:
                        logger.error("No API key in OpenRouter response")
                        return None

                    logger.info("Successfully obtained OpenRouter API key")

                    return Credentials(
                        access_token=api_key,  # Store as access_token for compatibility
                        provider="openrouter",
                        api_endpoint=DEFAULT_API_ENDPOINT,
                        default_model="anthropic/claude-sonnet-4",
                    )
        except Exception as e:
            logger.error(f"API key exchange error: {e}")
            return None

    def _cleanup_server(self) -> None:
        """Clean up the HTTP server."""
        if self._http_server:
            try:
                self._http_server.server_close()
            except Exception:
                pass
            self._http_server = None

        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=1.0)
        self._server_thread = None


# Global instances
credential_store = CredentialStore()
oauth_flow = OAuthFlow(credential_store=credential_store)


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return credential_store.is_authenticated()


def get_credentials() -> Optional[Credentials]:
    """Get stored credentials."""
    return credential_store.load()


async def start_authentication(timeout: float = 300.0) -> Optional[Credentials]:
    """Start the OAuth authentication flow."""
    return await oauth_flow.start_auth_flow(timeout=timeout)


def logout() -> None:
    """Clear stored credentials."""
    credential_store.clear()


__all__ = [
    "Credentials",
    "CredentialStore",
    "OAuthFlow",
    "credential_store",
    "oauth_flow",
    "is_authenticated",
    "get_credentials",
    "start_authentication",
    "logout",
]
