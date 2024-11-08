import argparse
import urllib3
import json
import datetime as DT
import os
import urllib3

http = urllib3.PoolManager()

BRIGHTDATA_RESULT_ADDRESS = "https://api.brightdata.com/datasets/v3/snapshot"
BRIGHTDATA_API_KEY = os.environ["BRIGHTDATA_API_TOKEN"]
BRIGHTDATA_DATASET_ID = os.environ["BRIGHTDATA_DATASET_ID"]
BRIGHTDATA_TRIGGER_API_ADDRESS = f"https://api.brightdata.com/datasets/v3/trigger?dataset_id={BRIGHTDATA_DATASET_ID}&type=discover_new&discover_by=profile_url"
AWS_BUCKET_NAME = os.environ["AWS_BUCKET_NAME"]
AWS_ACCESS_KEY = os.environ["BUCKET_ACCESS_KEY"]
AWS_SECRET_KEY = os.environ["BUCKET_SECRET_KEY"]

def clean_handle_list(input_list):
    """
    Helper function for removing white space and @s from handles
    """
    stripped_list = [handle.rstrip() for handle in input_list]
    no_ats_list = [handle.replace("@", "") for handle in stripped_list]
    return no_ats_list


def todays_date():
    """
    Helper function to return today's date in YYYY-MM-DD format
    """
    return DT.date.today().strftime("%Y-%m-%d")


def yesterdays_date():
    """
    Helper function to return yesterday's date in YYYY-MM-DD format
    """
    return (DT.date.today() - DT.timedelta(days=1)).strftime("%Y-%m-%d")


def week_ago_date():
    """
    Helper function to return a week ago's date in YYYY-MM-DD format
    """
    return (DT.date.today() - DT.timedelta(days=7)).strftime("%Y-%m-%d")

def aws_delivery_block():
    return {"type":"s3","filename":{"template":"{[datetime]}_{[snapshot_id]}","extension":"csv"},"bucket":AWS_BUCKET_NAME,"credentials":{"aws-access-key":AWS_ACCESS_KEY,"aws-secret-key":AWS_SECRET_KEY},"directory":"daily-tweets"}
    
def date_range_request_body(start_date, end_date, handle_list):
    """
    Generate the body of the API request for triggering collection through
    BrightData API.
    start_date and end_date format should be YYYY-MM-DD (i.e. "2024-10-15")
    handle_list should be a list of twitter handles
    """
    
    request_block = []
    for handle in handle_list:
        request_block.append(
            {
                "url": f"https://x.com/{handle}",
                "start_date": start_date,
                "end_date": end_date,
            }
        )
    return request_block

def trigger_brightdata_snapshot(start_date, end_date, handles_list):
    """
    Pass in a start_date and end_date in "YYYY-MM-DD" format and a list of twitter handles
    """
    response = http.request(
        'POST',
        url=BRIGHTDATA_TRIGGER_API_ADDRESS,
        headers={
            "Authorization": f"Bearer {BRIGHTDATA_API_KEY}",
            "Content-Type": "application/json",
        },
        body=json.dumps({"deliver": aws_delivery_block(),
               "input": date_range_request_body(start_date,end_date, handles_list)})
    )
    print(response)
    return response

def collect_tweets(start_date, end_date, handles_list):
    trigger_brightdata_snapshot(start_date, end_date, handles_list)

with open("handles.csv", 'r') as file:
    handles = clean_handle_list(file.read().split('\n'))

print(f"start date: {yesterdays_date()}, end date: {todays_date()}, handles_list: {handles}")
    
def lambda_handler(event, context):
    collect_tweets(start_date=yesterdays_date(), end_date=todays_date(), handles_list=handles)
    print(f"Started collection of tweets from {len(handles)} accounts, starting {yesterdays_date()} and ending {todays_date()}")
    