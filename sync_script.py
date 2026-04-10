import os
import requests
import pandas as pd
import smartsheet
from io import StringIO

# 1. Configuration - Pulling from GitHub Secrets
SC_CLIENT_ID = os.getenv('SC_CLIENT_ID')
SC_CLIENT_SECRET = os.getenv('SC_CLIENT_SECRET')
SC_USERNAME = os.getenv('SC_USERNAME')
SC_PASSWORD = os.getenv('SC_PASSWORD')

SS_TOKEN = os.getenv('SS_TOKEN')
SS_SHEET_ID = os.getenv('SS_SHEET_ID')

def get_servicechannel_token():
    auth_url = "https://login.servicechannel.com/oauth/token"
    data = {
        'grant_type': 'password',
        'username': SC_USERNAME,
        'password': SC_PASSWORD,
        'client_id': SC_CLIENT_ID,
        'client_secret': SC_CLIENT_SECRET
    }
    response = requests.post(auth_url, data=data)
    response.raise_for_status()
    return response.json().get('access_token')

def get_work_orders(token):
    # OData endpoint to get Work Orders
    # We select common fields; adjust the $select string if you need more columns
    url = "https://api.servicechannel.com/v3/odata/workorders?$select=Id,Number,Status,Priority,Trade,Location,CallDate"
    headers = {'Authorization': f'Bearer {token}'}
    
    all_orders = []
    while url:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        all_orders.extend(data.get('value', []))
        # Handle ServiceChannel pagination
        url = data.get('@odata.nextLink')
    
    return all_orders

def main():
    try:
        # Authenticate and Fetch
        token = get_servicechannel_token()
        orders = get_work_orders(token)
        
        if not orders:
            return

        # Convert to CSV in-memory to avoid leaving local file traces
        df = pd.json_normalize(orders)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()

        # Upload to Smartsheet as an attachment
        ss_client = smartsheet.Smartsheet(SS_TOKEN)
        
        # We name the file generically as discussed
        filename = "service_channel_orders.csv"
        
        # Attachment logic
        ss_client.Sheets.attach_file_to_sheet(
            SS_SHEET_ID, 
            (filename, csv_content, 'text/csv')
        )

    except Exception as e:
        # Generic error to keep logs clean in a public repo
        #print("Automation failed. Check API credentials or network status.")
        print(f"Error details: {e}")
        # Optional: raise e if you want the GitHub Action to show a 'red' fail status
        raise e

if __name__ == "__main__":
    main()
