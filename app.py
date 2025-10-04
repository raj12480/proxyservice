from flask import Flask, request, make_response, jsonify
from authlib.oauth2.rfc6750 import BearerTokenValidator, InvalidTokenError, InsufficientScopeError
from authlib.oauth2.rfc6749 import OAuth2Token
from authlib.integrations.requests_client import OAuth2Session
from authlib.integrations.flask_client import OAuth
from authlib.integrations.flask_oauth2 import ResourceProtector, current_token
from werkzeug.exceptions import HTTPException
from authlib.jose import jwt, jwk, JsonWebKey, JoseError

import json
import requests

"""--- Steup Flask start ---"""

app = Flask(__name__)
app.config.from_prefixed_env()

"""--- Steup Flask end ---"""


"""--- Keycloak OAuth Resource Protector start ---"""

# env: FLASK_KEYCLOAK_AUTH_URL
KEYCLOAK_AUTH_URL = app.config["KEYCLOAK_AUTH_URL"]
KEYCLOAK_CERTS_URL = f'{KEYCLOAK_AUTH_URL}/protocol/openid-connect/certs'

class KeycloakTokenValidator(BearerTokenValidator):
    def __init__(self):
        super().__init__()
        self.public_keys = self.fetch_public_keys()

    def fetch_public_keys(self):
        response = requests.get(KEYCLOAK_CERTS_URL,verify=False)
        if response.status_code != 200:
            raise Exception('Failed to fetch public keys from Keycloak', response.text)

        jwks = response.json()
        return JsonWebKey.import_key_set(jwks)

    def authenticate_token(self, token_string):
        try:
            # Decode and verify the JWT token using the public keys
            claims = jwt.decode(token_string, self.public_keys)
            claims.validate()
            return OAuth2Token(claims)
        except JoseError:
            return None

    def validate_token(self, token, scopes, request):
        if not token:
            raise InvalidTokenError()
        if token.is_expired():
            raise InvalidTokenError()
        if self.scope_insufficient(token.get("scope"), scopes):
            print("scope_insufficient: required", scopes, ", but given", token.get("scope"))
            raise InsufficientScopeError()

require_keycloak = ResourceProtector()
require_keycloak.register_token_validator(KeycloakTokenValidator())

"""--- Keycloak OAuth Server Protector end ---"""


"""--- ZoHo OAuth Client start ---"""

ZOHO_DEFAULT_SCOPE = "AAAServer.profile.Read"

oauth = OAuth(app)
zoho = oauth.register('zoho',
    # env: FLASK_ZOHO_CLIENT_ID
    # env: FLASK_ZOHO_CLIENT_SECRET
    api_base_url="https://sdpondemand.manageengine.com",
    access_token_url="https://accounts.zoho.com/oauth/v2/token",
    scope=ZOHO_DEFAULT_SCOPE,
)

TOKEN_CACHE_BY_SCOPE = {}

def get_scope(scope = None):
    if scope == None:
        return [ZOHO_DEFAULT_SCOPE]

    return [ZOHO_DEFAULT_SCOPE, scope]

def get_token(scope = None):
    """Get token by scope, will try find form cache first"""

    scope = get_scope(scope)
    cache_key = ', '.join(scope)

    token = TOKEN_CACHE_BY_SCOPE.get(cache_key)
    if token and not token.is_expired():
        return token

    token = zoho.fetch_access_token(scope=scope)
    TOKEN_CACHE_BY_SCOPE[cache_key] = token

    return token

"""--- ZoHo OAuth Client end ---"""


"""--- Rest APIs start ---"""

@app.get('/api/v3/requests/<id>')
@require_keycloak(['tickets.read_only', 'tickets.write'])
def get_request_by_id(id):
    """Get request by ID"""

    scope = "SDPOnDemand.requests.READ"
    return proxy_zoho_api(scope)

@app.get('/api/v3/requests')
@require_keycloak(['tickets.read_only', 'tickets.write'])
def get_requests():
    """Get list requests"""

    scope = "SDPOnDemand.requests.READ"
    return proxy_zoho_api(scope)

@app.post('/api/v3/requests')
@require_keycloak('tickets.write')
def create_request():
    """Create a request"""

    scope = "SDPOnDemand.requests.WRITE"
    return proxy_zoho_api(scope)

@app.put('/api/v3/requests/<id>')
@require_keycloak('tickets.write')
def update_request(id):
    """Update a request by ID"""

    scope = "SDPOnDemand.requests.WRITE"
    return proxy_zoho_api(scope)

def proxy_zoho_api(scope):
    """Proxy the request by using OAuth2 client to request the ZoHo API"""

    print("proxy_zoho_api", request)

    token = get_token(scope)

    forwardHeaders = ['Content-Type', 'Accept']
    headers = {key: request.headers.get(key) for key in forwardHeaders}

    # request to ZoHo API with token
    resp = zoho.request(
                request.method,
                request.full_path,
                request=request,
                token=token,
                data=request.data or request.form,
                headers=headers
            )

    # make Flask response
    flask_resp = make_response(
            resp.content,
            resp.status_code,
    )

    # set header without content header
    for name, value in resp.headers.items():
        if name.lower() in ['content-encoding', 'transfer-encoding', 'content-length']:
            continue
        flask_resp.headers[name] = value

    return flask_resp

@app.errorhandler(HTTPException)
def handle_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    # start with the correct headers and status code from the error
    response = e.get_response()
    # replace the body with JSON
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    return response

"""--- Rest APIs end ---"""
