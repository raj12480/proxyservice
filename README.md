

Step 0 Prerequisite

Finish the running Keycloak by Keycloak installation
Setup scopes for Keycloak
We need create two scopes globally in Keycloak:
tickets.read_only
tickets.write
Add those scopes to our client in Keycloak
test_client
Test_write_client

Enable client authentication and select “Service access roles”


Step1 Build the Keycloak Auth URL
Assuming we have:
KEYCLAOK_REALM_ID : service_desk
KEYCLOAK_LOCATION : link point to the Keycloak EC2 host
So, we have
KECYLOAK_AUTH_URL = KEYCLOAK_LOCATION + /realms/ + KEYCLAOK_REALM_ID


For example: 
KEYCLOAK_LOCATION = http://example.compute-1.amazonaws.com/
KEYCLAOK_REALM_ID = service_desk
Then:
KECYLOAK_AUTH_URL = http://example.compute-1.amazonaws.com/realms/service_desk

KECYLOAK_AUTH_URL = http://100.27.2.203/realms/service_desk

http://ec2-3-19-32-8.us-east-2.compute.amazonaws.com/realms/service_desk
Step 2 	Install python
```
sudo yum install python3 python3-pip -y
```

Step 3 Download the source code
```



unzip ProxyService.zip
```

Step 4 Setup python env
```
cd target

python3 -m venv .venv

. .venv/bin/activate

pip3 install -r requirements.txt
```
Step 5 Pre-configure
You should replace with 
KEYCLOAK_AUTH_URL : from Step1
ZOHO_CLIENT_ID : ZoHo self-client client ID
ZOHO_CLIENT_SECRET : ZoHo self-client client secret
```
export FLASK_KEYCLOAK_AUTH_URL=KEYCLOAK_AUTH_URL

export FLASK_KEYCLOAK_AUTH_URL=http://ec2-3-19-32-8.us-east-2.compute.amazonaws.com/realms/service_desk

export FLASK_ZOHO_CLIENT_ID=ZOHO_CLIENT_ID

export FLASK_ZOHO_CLIENT_ID=1000.LRVHSQWB49D266Y3WUW4ZLRIG24ADB

export FLASK_ZOHO_CLIENT_SECRET=ZOHO_CLIENT_SECRET

export FLASK_ZOHO_CLIENT_SECRET=2adcb69c487d18ef24d93380956e4b87b7f158597d
```
Step 6 Run in the Background
```
nohup gunicorn &
```
Step 7 Export the port for EC2 5000
Back to your EC2 Security group configuration.
Allow the inbound rule: TCP 5000

Step 8 Testing
Change the URL in the Swagger, then start testing
ProxyService API
servers.url
change to the ProxyService location, keep 8000 as the same

OAuth2 Provider
clientCredentials.tokenUrl
change to Keycloak token Endpoint, should double-check the realm.




openapi: 3.0.0
info:
  title: SDP
  version: 1.0.0
components:
  securitySchemes:
    Zoho-oauthtoken:
      type: apiKey
      in: header
      name: Authorization
security:
  - Zoho-oauthtoken: []         
paths:
  /realms/service_desk/protocol/openid-connect/token:	
    servers:
     - url: http://100.27.2.203
    post:
      tags:
        - default
      summary: Access Token
      requestBody:
        content:
          application/x-www-form-urlencoded:
            schema:
              properties:
                client_id:
                  type: string
                client_secret:
                  type: string
                grant_type:
                  type: string
                  example: client_credentials
                scope:
                  type: string
                  example: SDPOnDemand.requests.CREATE
      responses:
        '200':
          description: Successful response
          content:
            application/json: {}
  /api/v3/requests:
    servers:
     - url: https://ec2-3-129-209-246.us-east-2.compute.amazonaws.com:8000
    post:
      tags:
        - default
      summary: Create Request
      requestBody:
        content:
          application/x-www-form-urlencoded:
            schema:
              properties:
                input_data:
                  #type: string
                  type: object
                  # example: {"request":{"template":{"id":""},"subject":""}}
                  example: {
    "request": {
      "template": {
        "id": "189190000000930045"
      },
      "subject": "Updating ticket api functionality",
      "description": "Be able to update status of ticket after and update is made",
      "requester": {
        "email_id": "testemail@gmail.com"
      },
      "impact": {
        "name": "EN3 - 10-30 Customers"
      },
      "urgency": {
        "name": "4 - Low"
      },
      "priority": {
        "name": "4 - Low"
      }
    }
  }

      responses:
        '200':
          description: Successful response
          content:
            application/vnd.manageengine.sdp.v3+json: {}
servers:
  # Added by API Auto Mocking Plugin
  - description: SwaggerHub API Auto Mocking

Keycloak configuration
Step1 Disable SSL for new Realm
Set Require SSL to none
