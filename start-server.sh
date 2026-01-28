#!/bin/sh

export FLASK_KEYCLOAK_AUTH_URL="http://51.21.81.193:8080/realms/service_desk"
export FLASK_ZOHO_CLIENT_ID="1000.xxxxxxxxxxxxxxxxxxxxxxxxxx"
export FLASK_ZOHO_CLIENT_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxx"


#export FLASK_ZOHO_CLIENT_ID="1000.W2JC936IJ8CYROPR4VCLNOCBU51XBC"
#export FLASK_ZOHO_CLIENT_SECRET="faf99b00ecacab08bc635b5f5e1df9301dc5795dd1"

#gunicorn
exec gunicorn app:app \
    -b 0.0.0.0:5000 \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --log-level debug
