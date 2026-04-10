import os
import requests
import pandas as pd
import smartsheet
from io import StringIO, BytesIO

# 1. Configuration
SC_CLIENT_ID = os.getenv('SC_CLIENT_ID')
SC_CLIENT_SECRET = os.getenv('SC_CLIENT_SECRET')
SC_USERNAME = os.getenv('SC_USERNAME')
SC_PASSWORD = os.getenv('SC_PASSWORD')

SS_TOKEN = os.getenv('SS_TOKEN')
SS_SHEET_ID = int(os.getenv('SS_SHEET_ID'))

FILENAME = "service_channel_orders.csv"


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


def get_all_sheet_attachments(ss_client, sheet_id):
    """Handles pagination and returns ALL attachments"""
    attachments = []

    result = ss_client.Attachments.list_all_attachments(sheet_id)
    attachments.extend(result.data)

    while result.page_number < result.total_pages:
        result = ss_client.Attachments.list_all_attachments(
            sheet_id,
            page=result.page_number + 1
        )
        attachments.extend(result.data)

    return attachments


def main():
    try:
        print("=== SCRIPT START ===")

        # 1. Fetch data
        token = get_servicechannel_token()
        print("Token acquired")

        orders = get_work_orders(token)
        print(f"Orders retrieved: {len(orders)}")

        if not orders:
            print("No orders found. Exiting.")
            return

        # 2. Convert to CSV (in memory)
        df = pd.json_normalize(orders)

        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()

        # Convert to BytesIO (critical for versioning)
        csv_bytes = BytesIO(csv_content.encode('utf-8'))

        # 3. Initialize Smartsheet
        ss_client = smartsheet.Smartsheet(SS_TOKEN)
        sheet_id = SS_SHEET_ID

        print("Fetching existing attachments...")

        attachments = get_all_sheet_attachments(ss_client, sheet_id)

        print(f"Total attachments found: {len(attachments)}")

        # Filter to sheet-level only
        sheet_attachments = [
            a for a in attachments if str(a.parent_type) == 'SHEET'
        ]

        print(f"Sheet-level attachments: {len(sheet_attachments)}")

        # Find matching file
        existing_attachment = next(
            (a for a in sheet_attachments if a.name == FILENAME),
            None
        )

        print(f"Matching attachment: {existing_attachment}")

        file_tuple = (FILENAME, csv_bytes, 'text/csv')

        # 4. Upload logic
        if existing_attachment:
            print("=== ATTEMPTING VERSION UPLOAD ===")
            print(f"Attachment ID: {existing_attachment.id}")

            try:
                response = ss_client.Attachments.attach_new_version(
                    sheet_id,
                    existing_attachment.id,
                    file_tuple
                )
                print("Version upload SUCCESS")
                print(response)

            except Exception as e:
                print("Version upload FAILED, falling back to new upload")
                print(e)

                ss_client.Attachments.attach_file_to_sheet(
                    sheet_id,
                    file_tuple
                )
                print("Fallback upload SUCCESS")

        else:
            print("=== NO EXISTING FILE, CREATING NEW ===")

            ss_client.Attachments.attach_file_to_sheet(
                sheet_id,
                file_tuple
            )

            print("Initial upload SUCCESS (Version 1 created)")

        print("=== SCRIPT COMPLETE ===")

    except Exception as e:
        print("Automation failed.")
        print(f"Error details: {e}")
        raise e


if __name__ == "__main__":
    main()
