import pandas as pd
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient import discovery
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import pickle

def get_values(tab: str, spreadsheet_id: str, cells: str):
    '''Returns a specific range of values from a given spreadsheet

    Parameters
    ----------
    tab: The sheet tab that the function gets values from
    spreadsheet_id: The spreadsheet id in the sheet URL
    cells: The cell range to be returned
    '''
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    SERVICE_ACCOUNT_FILE = os.environ.get('SERVICE_ACCT_FILE') #service account file here
    global values_input, service
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=scope)
    service = discovery.build('sheets', 'v4', credentials=creds)

    range_ = tab+"!"+cells

    sheet = service.spreadsheets()
    result_input = sheet.values().get(spreadsheetId=spreadsheet_id,
                                      range=range_).execute()
    values_input = result_input.get('values', [])

    if not values_input:
        print('No data found.')

    return values_input

class StatError(Exception):
    pass

def write_player(tab: str, spreadsheet_id: str, gid: str, uid: str, player: str, clan: str):
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    SERVICE_ACCOUNT_FILE = os.environ.get('SERVICE_ACCT_FILE') #service account file here
    global values_input, service
    gs = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=scope)
    service = discovery.build('sheets', 'v4', credentials=creds)
    sheet = gs.open("clanwarsDATA")
    worksheet = sheet.worksheet(tab)
    sheet_id = spreadsheet_id 
    sheet_gid = gid

    index = 1
    cell = worksheet.acell('A'+str(index)).value
    while cell != None: #Determine row to write on based on the first row without any values
        index = index+1
        cell = worksheet.acell('A' + str(index)).value

    request_body = {
        'requests': [
            {
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_gid,

                        'startRowIndex': 1,
                        'endRowIndex': 1,

                        'startColumnIndex': 1,
                        'endColumnIndex': 3
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {
                                'fontSize': 10,
                                'fontFamily': "Arial",
                            }
                        }
                    },
                    'fields': 'userEnteredFormat'
                }
                
            }
        ]
    }   
    
    worksheet.update('A'+str(index), [[uid, player, clan]])
    response = service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body=request_body
    ).execute()
    return



