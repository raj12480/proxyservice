#!/bin/sh

export FLASK_KEYCLOAK_AUTH_URL="http://13.51.237.239:8080/realms/service_desk"
export FLASK_ZOHO_CLIENT_ID="1000.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export FLASK_ZOHO_CLIENT_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxx"


#gunicorn
exec gunicorn app:app \
    -b 0.0.0.0:5000 \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --log-level debug
