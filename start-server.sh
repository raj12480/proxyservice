#!/bin/sh

# ==============================
# Environment Variables
# ==============================

# Keycloak authentication URL for the Flask app
# NOTE: 
#   - If you create a realm with a different name, replace 'service_desk' with your realm name.
#   - Update <keyclock-host-ip> with the actual IP or hostname of your Keycloak server.
#   - Change the port (8080) if your Keycloak server is running on a different port.
# Example URL format: http://127.0.0.1:8080/realms/my_custom_realm
export FLASK_KEYCLOAK_AUTH_URL="http://<keyclock-host-ip>:8080/realms/service_desk"

# Zoho OAuth2 Client ID
export FLASK_ZOHO_CLIENT_ID="1000.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Zoho OAuth2 Client Secret
export FLASK_ZOHO_CLIENT_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxx"


#gunicorn
exec gunicorn app:app \
    -b 0.0.0.0:5000 \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --log-level debug
