import os
import requests
import pandas as pd
import smartsheet
from io import StringIO

# Configuration - Pulling from GitHub Secrets
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
    url = "https://api.servicechannel.com/v3/odata/workorders?$select=Id,Number,Status,Priority,Trade,Location,CallDate"
    headers = {'Authorization': f'Bearer {token}'}
    all_orders = []
    while url:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        all_orders.extend(data.get('value', []))
        url = data.get('@odata.nextLink')
    return all_orders

def main():
    try:
        # 1. Fetch Data
        token = get_servicechannel_token()
        orders = get_work_orders(token)
        
        if not orders:
            return

        # 2. Prep CSV in-memory
        df = pd.json_normalize(orders)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()

        # 3. Initialize Smartsheet
        ss_client = smartsheet.Smartsheet(SS_TOKEN)
        sheet_id = int(SS_SHEET_ID)
        filename = "service_channel_orders.csv"

        # 4. Find existing attachment
        attachments_obj = ss_client.Attachments.list_all_attachments(sheet_id)
        attachments = attachments_obj.data
        
        existing_attachment = next((a for a in attachments if a.name == filename), None)

        if existing_attachment:
            # UPLOAD AS NEW VERSION
            ss_client.Attachments.attach_new_version(
                sheet_id,
                existing_attachment.id,
                (filename, csv_content, 'text/csv')
            )
        else:
            # FIRST TIME UPLOAD 
            # Note: Using ss_client.Attachments.attach_to_sheet
            ss_client.Attachments.attach_to_sheet(
                sheet_id,
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
