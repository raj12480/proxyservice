# Step 0 Install python

```
apt install python3 python3-pip
```

# Step 1 Download

```
wget -O ProxyService.zip "https://tmpfiles.org/dl/8300625/zohoproxyservice.zip"
unzip ProxyService.zip
```

# Step 2 Setup python env
```
cd target

python -m venv .venv & . .venv/bin/activate
pip3 install -r requirements.txt
```

# Step 3 Pre-configure (IF you can use VIM)

update the environment variables in the start-server.sh file:
- KEYCLOAK_AUTH_URL
- ZOHO_CLIENT_ID
- ZOHO_CLIENT_SECRET
```
vim start-server.sh
```

# Step 3 Pre-configure (IF you can't use VIM)

```
export KEYCLOAK_AUTH_URL="REPLACE_ME"
export ZOHO_CLIENT_ID="REPLACE_ME"
export ZOHO_CLIENT_SECRET="REPLACE_ME"
```

# Step 4 Run

```
# If you updated the start-server.sh file
sh start-server.sh


# If you updated the environment variables
gunicorn
```

# Step 5 Test

