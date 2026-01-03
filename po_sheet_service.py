import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

class POSheetService:
    def __init__(self, json_keyfile, spreadsheet_id, sheet_name):
        creds = Credentials.from_service_account_file(
            json_keyfile, scopes=SCOPE
        )
        client = gspread.authorize(creds)
        self.ws = client.open_by_key(spreadsheet_id).worksheet(sheet_name)

    def get_df(self):
        return pd.DataFrame(self.ws.get_all_records())

    def append_po(self, data: dict):
        self.ws.append_row(list(data.values()))

    def update_cell(self, row, col_name, value, df):
        col = df.columns.get_loc(col_name) + 1
        self.ws.update_cell(row, col, value)

    def get_row_number(self, df, po_id):
        return df[df["PO ID"] == po_id].index[0] + 2
