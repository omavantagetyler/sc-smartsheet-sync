def main():
    try:
        # 1. Authenticate and Fetch from ServiceChannel
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

        # 4. Search for an existing attachment by name
        # Note: list_all_attachments is the most compatible method
        attachments_result = ss_client.Attachments.list_all_attachments(sheet_id)
        existing_attachment = next((a for a in attachments_result.data if a.name == filename), None)

        # 5. Execute versioned or fresh upload
        file_tuple = (filename, csv_content.encode('utf-8'), 'text/csv')

        if existing_attachment:
            # Update the existing file
            ss_client.Attachments.attach_new_version(
                sheet_id,
                existing_attachment.id,
                file_tuple
            )
        else:
            # Create the file for the first time
            ss_client.Sheets.attach_to_sheet(
                sheet_id,
                file_tuple
            )

    except Exception as e:
        # Generic error to keep logs clean in a public repo
        print("Automation failed. Check API credentials or network status.")
        #print(f"Error details: {e}")
        # Optional: raise e if you want the GitHub Action to show a 'red' fail status
        raise e
