### how to set up Dagu via DigitalOcean

1. Log into the DigitalOcean dashboard
2. Go to the Droplet page and get the public ip
3. Open up PowerShell on my local machine
4. Make sure that Dagu is running on the Droplet and is listening on port 8080
5. Create a SSH tunnel
   - ssh -L 8080:localhost:8080 jmiao@publicIpAddress
   - the public IP will change often

### dependencies
- pip install --upgrade 
- python 3.13
- pandas
- numpy
- yfinance
- google-api-python-client 
- google-auth-httplib2 
- google-auth-oauthlib