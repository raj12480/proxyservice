# ProxyService Production - Detailed Technical Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Authentication & Authorization](#authentication--authorization)
4. [API Endpoints](#api-endpoints)
5. [Configuration](#configuration)
6. [OAuth2 Scope Management](#oauth2-scope-management)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)

---

## Overview

**ProxyService Production** is a Flask-based OAuth2 proxy service that acts as an intermediary between clients and two OAuth2-protected services:

1. **Keycloak** - Identity and Access Management (IAM) provider
2. **Zoho ServiceDesk** - IT Service Management platform (via ManageEngine SDP OnDemand)

### Key Features

- **Dual OAuth2 Integration**: Manages authentication with both Keycloak and Zoho
- **Scope-Based Access Control**: Implements fine-grained permission control using OAuth2 scopes
- **Token Caching**: Caches Zoho tokens by scope to reduce API calls
- **Request Proxying**: Transparently forwards API requests to Zoho while handling authentication
- **File Upload Support**: Handles multi-file uploads with automatic chunking
- **Swagger Documentation**: Built-in API documentation and testing interface

---

## Architecture

### System Components

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────┐
│      ProxyService (Flask Application)    │
│  - Keycloak OAuth2 Token Validator      │
│  - Zoho OAuth2 Client                   │
│  - Request/Response Proxying            │
│  - Token Caching                        │
└──────┬──────────────────────┬───────────┘
       │                      │
       ▼                      ▼
   ┌────────────┐      ┌──────────────────────┐
   │ Keycloak   │      │ Zoho ServiceDesk     │
   │ (Auth)     │      │ ManageEngine SDP     │
   └────────────┘      └──────────────────────┘
```

### Technology Stack

- **Framework**: Flask (Python web framework)
- **Authentication**: Authlib (OAuth2 library)
- **Token Validation**: JWT (JSON Web Tokens) with public key verification
- **HTTP Client**: Requests library
- **Deployment**: Gunicorn (WSGI server)
- **Containerization**: Docker & Docker Compose

---

## Authentication & Authorization

### 1. Keycloak OAuth2 Flow (Token Acquisition)

#### Flow Overview

```
Client Request
    │
    ▼
POST /api/token
(with client credentials + optional scope)
    │
    ▼
ProxyService forwards to Keycloak
    │
    ▼
Keycloak validates credentials
    │
    ▼
Returns JWT token with claims
    │
    ▼
ProxyService returns token to client
```

#### How It Works

1. **Client sends token request** to `POST /api/token` with:
   - `grant_type`: OAuth2 grant type (e.g., `client_credentials`)
   - `client_id`: Client identifier
   - `client_secret`: Client secret
   - `scope` (optional): Requested permission scopes

2. **ProxyService forwards** the request to Keycloak's token endpoint

3. **Keycloak returns** a JWT token containing:
   - `access_token`: The JWT bearer token
   - `token_type`: "Bearer"
   - `expires_in`: Token validity period (seconds)
   - `scope`: Granted scopes (if Full Scope Allowed is disabled)

#### Important: Full Scope Allowed Setting

**Keycloak Configuration Impact:**

- **If "Full Scope Allowed" is ON** (default):
  - Keycloak grants ALL scopes assigned to the client
  - Ignores the `scope` parameter in token requests
  - Example: Client with both `tickets.read_only` and `tickets.write` always gets both scopes regardless of request

- **If "Full Scope Allowed" is OFF** (recommended):
  - Keycloak grants ONLY the requested scopes
  - Must explicitly pass `scope` parameter
  - Example: Requesting `scope=tickets.read_only` returns only that scope

**Configuration Steps:**
1. Go to Keycloak Admin Console
2. Navigate to: Clients → [Your Client] → Settings
3. Find "Full Scope Allowed" toggle
4. Turn it **OFF** for proper scope control

### 2. Token Validation (Protected Endpoints)

#### Validation Flow

```
Client sends API request
    │
    ├─ Header: Authorization: Bearer <jwt_token>
    │
    ▼
@require_keycloak decorator checks:
    ├─ Token exists?
    ├─ Token valid (JWT signature)?
    ├─ Token not expired?
    ├─ Token contains required scopes?
    │
    ▼
If all checks pass ✓
    → Request proceeds to handler
If any check fails ✗
    → Return 401/403 error
```

#### Token Validator Implementation

The `KeycloakTokenValidator` class handles validation:

```python
class KeycloakTokenValidator(BearerTokenValidator):
    
    def authenticate_token(token_string):
        # Decodes and validates JWT signature using public keys from Keycloak
        # Returns OAuth2Token object if valid, None if invalid
    
    def validate_token(token, scopes, request):
        # Checks if token is valid, not expired, and has required scopes
        # Raises InvalidTokenError or InsufficientScopeError if validation fails
```

#### Scope Validation

The validator checks if token scopes include the required scopes:

```python
# Example: Endpoint requires 'tickets.write' scope
@app.post('/api/v3/requests')
@require_keycloak('tickets.write')
def create_request():
    ...

# Token validation: token.scope must include 'tickets.write'
# If token only has 'tickets.read_only', validation fails with InsufficientScopeError
```

---

## API Endpoints

### 1. Token Endpoint

**Purpose**: Obtain OAuth2 access token from Keycloak

```http
POST /api/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&
client_id=YOUR_CLIENT_ID&
client_secret=YOUR_CLIENT_SECRET&
scope=tickets.read_only
```

**Response** (Success - 200):
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "refresh_expires_in": 3600,
  "token_type": "Bearer",
  "scope": "tickets.read_only"
}
```

**Response** (Error - 500):
```json
{
  "error": "token_error",
  "error_description": "Connection timeout or Keycloak error message"
}
```

---

### 2. Get Requests (Read)

**Purpose**: Retrieve list of all service desk requests

```http
GET /api/v3/requests
Authorization: Bearer <access_token>
```

**Required Scope**: `tickets.read_only` OR `tickets.write`

**Response** (Success - 200):
```json
{
  "response_code": 2000,
  "response_status": "success",
  "requests": [
    {
      "id": "1001",
      "title": "Access Request",
      "status": "Open",
      "created_time": "2026-01-27 10:30:00",
      "updated_time": "2026-01-27 15:45:00"
    }
  ]
}
```

**Response** (Insufficient Scope - 403):
```json
{
  "code": 403,
  "name": "Forbidden",
  "description": "InsufficientScopeError"
}
```

---

### 3. Get Request by ID (Read)

**Purpose**: Retrieve details of a specific service desk request

```http
GET /api/v3/requests/{id}
Authorization: Bearer <access_token>
```

**Parameters**:
- `id` (path): The request ID (e.g., 1001)

**Required Scope**: `tickets.read_only` OR `tickets.write`

**Response** (Success - 200):
```json
{
  "response_code": 2000,
  "response_status": "success",
  "request": {
    "id": "1001",
    "title": "Access Request",
    "status": "Open",
    "description": "Need access to project X",
    "created_time": "2026-01-27 10:30:00",
    "assignee": {"id": "3", "name": "John Doe"},
    "requester": {"id": "5", "name": "Jane Smith"}
  }
}
```

---

### 4. Create Request (Write)

**Purpose**: Create a new service desk request

```http
POST /api/v3/requests
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "subject": "New Access Request",
  "description": "I need access to the development server",
  "request_type": "Service Request",
  "category": "Access Management",
  "priority": "2",
  "is_urgent": false
}
```

**Required Scope**: `tickets.write` (ONLY)

**Note**: Attempting this endpoint with only `tickets.read_only` will fail with 403 Forbidden.

**Response** (Success - 201/200):
```json
{
  "response_code": 2000,
  "response_status": "success",
  "request": {
    "id": "1002",
    "title": "New Access Request",
    "status": "Open",
    "created_time": "2026-01-28 09:15:00"
  }
}
```

**Response** (Insufficient Scope - 403):
```json
{
  "code": 403,
  "name": "Forbidden",
  "description": "InsufficientScopeError"
}
```

---

### 5. Update Request (Write)

**Purpose**: Update an existing service desk request

```http
PUT /api/v3/requests/{id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "status": "On Hold",
  "notes": "Waiting for additional information from requester"
}
```

**Parameters**:
- `id` (path): The request ID to update

**Required Scope**: `tickets.write` (ONLY)

**Response** (Success - 200):
```json
{
  "response_code": 2000,
  "response_status": "success",
  "request": {
    "id": "1001",
    "title": "Access Request",
    "status": "On Hold",
    "updated_time": "2026-01-28 11:20:00"
  }
}
```

---

### 6. Upload Request Attachment (Write)

**Purpose**: Attach files to a service desk request

```http
POST /api/v3/requests/{id}/_uploads
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

Files: [file1.pdf, file2.docx]
addtoattachment: true
```

**Parameters**:
- `id` (path): The request ID
- `filename` (form files): One or more files to upload
- `addtoattachment` (form field): Whether to add to request attachments (true/false)

**Required Scope**: `tickets.write` (ONLY)

**Response** (Success - 200):
```json
{
  "uploaded": [
    {
      "response_code": 2000,
      "response_status": "success",
      "attachment": {
        "id": "5001",
        "file_name": "document.pdf",
        "file_type": "pdf"
      }
    },
    {
      "response_code": 2000,
      "response_status": "success",
      "attachment": {
        "id": "5002",
        "file_name": "screenshot.png",
        "file_type": "png"
      }
    }
  ],
  "count": 2
}
```

---

### 7. Swagger Documentation

**Purpose**: View interactive API documentation

```http
GET /
or
GET /api/docs
```

Returns Swagger UI for testing all endpoints interactively.

---

## Configuration

### Environment Variables

Configure the service using environment variables prefixed with `FLASK_`:

```bash
# Keycloak Configuration
FLASK_KEYCLOAK_AUTH_URL=https://keycloak.example.com/auth/realms/your-realm

# Zoho OAuth2 Configuration
FLASK_ZOHO_CLIENT_ID=your_zoho_client_id
FLASK_ZOHO_CLIENT_SECRET=your_zoho_client_secret

# Flask Configuration (optional)
FLASK_ENV=production
FLASK_DEBUG=False
```

### Docker Compose Setup

```yaml
version: '3.8'
services:
  proxyservice:
    build: .
    ports:
      - "5000:5000"
    environment:
      FLASK_KEYCLOAK_AUTH_URL: https://keycloak.example.com/auth/realms/my-realm
      FLASK_ZOHO_CLIENT_ID: ${ZOHO_CLIENT_ID}
      FLASK_ZOHO_CLIENT_SECRET: ${ZOHO_CLIENT_SECRET}
    volumes:
      - ./app.py:/app/app.py
      - ./static:/app/static
```

### Gunicorn Configuration (gunicorn.conf.py)

```python
import multiprocessing

bind = "0.0.0.0:5000"
workers = multiprocessing.cpu_count() * 2 + 1
wsgi_app = "app:app"
timeout = 120  # Worker timeout in seconds
```

---

## OAuth2 Scope Management

### Understanding Scopes

Scopes are permission strings that define what actions a token can perform. They follow the pattern:
```
resource.action
```

### Available Scopes

| Scope | Description | Allows |
|-------|-------------|--------|
| `tickets.read_only` | Read-only access to service requests | GET /api/v3/requests, GET /api/v3/requests/{id} |
| `tickets.write` | Full write access to service requests | POST, PUT, file uploads |

### Scope Permission Matrix

| Endpoint | Method | tickets.read_only | tickets.write |
|----------|--------|-------------------|---------------|
| /api/v3/requests | GET | ✓ | ✓ |
| /api/v3/requests/{id} | GET | ✓ | ✓ |
| /api/v3/requests | POST | ✗ | ✓ |
| /api/v3/requests/{id} | PUT | ✗ | ✓ |
| /api/v3/requests/{id}/_uploads | POST | ✗ | ✓ |

### Keycloak Scope Configuration

**Step 1: Create Client Scopes**
1. Keycloak Admin Console → Client Scopes → Create
2. Create two scopes:
   - Name: `tickets.read_only`
   - Name: `tickets.write`

**Step 2: Assign to Client**
1. Go to your client → Client Scopes tab
2. Add both scopes as "Assigned Default" or "Assigned Optional"

**Step 3: Disable Full Scope Allowed**
1. Go to client → Settings tab
2. Turn OFF "Full Scope Allowed"
3. Now Keycloak will respect the `scope` parameter in token requests

**Step 4: Test Scope Enforcement**

Create two test clients to verify scope control:

**Test Client 1** (Read-Only):
```
- Client ID: test-client-read
- Assigned Scopes: tickets.read_only
```

Token request:
```bash
curl -X POST https://keycloak.example.com/auth/realms/my-realm/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=test-client-read&client_secret=secret&scope=tickets.read_only"
```

Result: Token has only `tickets.read_only` scope → Can read, cannot write

**Test Client 2** (Write Access):
```
- Client ID: test-client-write
- Assigned Scopes: tickets.read_only tickets.write
```

Token request:
```bash
curl -X POST https://keycloak.example.com/auth/realms/my-realm/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=test-client-write&client_secret=secret&scope=tickets.write"
```

Result: Token has only `tickets.write` scope → Cannot read, can write

---

## Deployment

### Prerequisites

- Docker & Docker Compose
- Keycloak server running and accessible
- Zoho ManageEngine SDP OnDemand credentials

### Local Development

```bash
# Set environment variables
export FLASK_KEYCLOAK_AUTH_URL=https://your-keycloak/auth/realms/your-realm
export FLASK_ZOHO_CLIENT_ID=your_client_id
export FLASK_ZOHO_CLIENT_SECRET=your_secret

# Run with Flask development server
python app.py

# Access at http://localhost:5000
```

### Production Deployment (Docker)

```bash
# Build Docker image
docker build -t proxyservice:1.0 .

# Run container
docker run -d \
  -p 5000:5000 \
  -e FLASK_KEYCLOAK_AUTH_URL=https://keycloak.example.com/auth/realms/my-realm \
  -e FLASK_ZOHO_CLIENT_ID=your_client_id \
  -e FLASK_ZOHO_CLIENT_SECRET=your_secret \
  proxyservice:1.0
```

### Production Deployment (Docker Compose)

```bash
# Create .env file
cat > .env << EOF
ZOHO_CLIENT_ID=your_client_id
ZOHO_CLIENT_SECRET=your_secret
KEYCLOAK_AUTH_URL=https://keycloak.example.com/auth/realms/my-realm
EOF

# Start services
docker-compose up -d

# View logs
docker-compose logs -f proxyservice
```

### Production Checklist

- [ ] "Full Scope Allowed" disabled in Keycloak client
- [ ] Client scopes created and assigned
- [ ] Environment variables configured
- [ ] HTTPS enabled in production
- [ ] Proper error logging configured
- [ ] Token caching verified (improve performance)
- [ ] Rate limiting configured (if needed)
- [ ] Firewall rules restrict access to Keycloak/Zoho APIs

---

## Troubleshooting

### Issue 1: "Insufficient Scope" Error (403)

**Symptom**: 
```
403 Forbidden - InsufficientScopeError
```

**Causes & Solutions**:

1. **Token lacks required scope**
   - Check token scopes: Decode JWT at https://jwt.io
   - Verify "Full Scope Allowed" is OFF in Keycloak
   - Explicitly pass `scope` parameter in token request

2. **Endpoint requires different scope**
   - Read operations need: `tickets.read_only` OR `tickets.write`
   - Write operations need: `tickets.write` ONLY
   - Verify correct scope was requested

**Example**:
```bash
# Wrong: Only requesting read scope for write operation
curl -X POST /api/v3/requests \
  -H "Authorization: Bearer <token_with_read_only>"
  # Will fail with 403

# Correct: Request write scope
curl -X POST /api/token \
  -d "scope=tickets.write" \
  # Use returned token for POST /api/v3/requests
```

---

### Issue 2: Token Request Timeout

**Symptom**: 
```
Worker timeout error / 31-second response time
```

**Causes & Solutions**:

1. **Keycloak is slow/unresponsive**
   - Check Keycloak server health
   - Monitor Keycloak CPU/memory usage
   - Check network latency to Keycloak

2. **Network connectivity issue**
   - Verify firewall rules allow connection to Keycloak
   - Test DNS resolution for Keycloak URL
   - Check if Keycloak is behind a load balancer

3. **Configuration issue**
   - Verify `FLASK_KEYCLOAK_AUTH_URL` is correct
   - Ensure HTTPS certificates are valid

**Quick Fix**: Increase Gunicorn timeout in `gunicorn.conf.py`:
```python
timeout = 120  # Increase from default 30 seconds
```

---

### Issue 3: Invalid Token / JWT Validation Error

**Symptom**:
```
401 Unauthorized - InvalidTokenError
```

**Causes & Solutions**:

1. **Token is expired**
   - Check token expiry: Decode at https://jwt.io
   - Request new token from `/api/token`

2. **Token signature invalid**
   - Keycloak public keys may have rotated
   - ProxyService fetches keys once on startup
   - Restart service to refresh public keys

3. **Token format incorrect**
   - Ensure header format is: `Authorization: Bearer <token>`
   - Not: `Authorization: <token>`
   - Not: `Authorization: token <token>`

**Debug**: Enable verbose logging:
```python
# In app.py validate_token method
print(f"Token claims: {token}")
print(f"Token scope: {token.get('scope')}")
print(f"Required scopes: {scopes}")
```

---

### Issue 4: Zoho API Error

**Symptom**:
```
Zoho API returns error or empty response
```

**Causes & Solutions**:

1. **Zoho credentials invalid**
   - Verify `FLASK_ZOHO_CLIENT_ID` and `FLASK_ZOHO_CLIENT_SECRET`
   - Test credentials directly with Zoho API
   - Ensure client has proper permissions in Zoho

2. **Zoho API scope issue**
   - ProxyService requests `SDPOnDemand.requests.READ` or `SDPOnDemand.requests.WRITE`
   - Verify these scopes are assigned to Zoho OAuth2 client
   - Check Zoho API documentation for required scopes

3. **Invalid request data**
   - Verify request body matches Zoho API schema
   - Check field names and data types
   - Review Zoho API documentation

**Debug**: Check console logs:
```bash
# In Docker
docker-compose logs proxyservice | grep -i zoho

# See what's being sent to Zoho
# Look for "proxy_zoho_api" debug prints
```

---

### Issue 5: File Upload Fails

**Symptom**:
```
413 Request Entity Too Large / Upload fails silently
```

**Causes & Solutions**:

1. **File size too large**
   - Check Flask max upload size: `MAX_CONTENT_LENGTH`
   - Check Zoho API file size limits
   - Split large files before upload

2. **Wrong content type**
   - Ensure form data includes `Content-Type: multipart/form-data`
   - File field must be named `filename`

**Example Upload**:
```bash
curl -X POST /api/v3/requests/1001/_uploads \
  -H "Authorization: Bearer <token>" \
  -F "filename=@/path/to/file.pdf" \
  -F "addtoattachment=true"
```

---

## Support & Additional Resources

- **Keycloak Documentation**: https://www.keycloak.org/documentation
- **Zoho ServiceDesk API**: https://www.zoho.com/servicedesk/api/
- **Authlib Documentation**: https://docs.authlib.org/
- **Flask Documentation**: https://flask.palletsprojects.com/
- **OAuth2 RFC 6749**: https://tools.ietf.org/html/rfc6749

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-28 | Initial production release |

---

**Last Updated**: January 28, 2026  
**Document Version**: 1.0  
**Status**: Production Ready
