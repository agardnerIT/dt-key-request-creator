import csv
import requests
import os

# Assumes an input file like:
# entitySelector|request_name
# type(SERVICE),tag(app:frontend)|/pageOne.html
# type(SERVICE),tag(app:frontend),tag(environment: production)|/pageTwo.html
#
# request_name must match what is shown visually in Dynatrace
# so if request naming rules are used, use the visual output to match whatever is shown in DT
#
# Requests can be marked as key BEFORE traffic arrives
# This code standardises on uppercase SERVICE-1234, even if the CSV contains lower or camelcase
#
# Usage:
# docker run --rm ^
# -v $pwd:/app ^
# -e dt_filename=input.csv ^
# -e dt_url=https://abc12345.live.dynatrace.com ^
# -e dt_api_token=dt0c01.********** ^
# gardnera/dt-key-request-creator:0.1.0

dt_url = os.environ.get('dt_url','')
dt_api_token = os.environ.get('dt_api_token','') # needs read entities and write settings v2
input_filename = os.environ.get('dt_filename','input.csv')
logging = os.environ.get('dt_logging','') # Set to enable debug logging mode
SCHEMA_ID = "builtin:settings.subscriptions.service"

if dt_url == '':
    print('Environment variable dt_url is missing. Should be like: https://abc12345.live.dynatrace.com. Please set. Exiting')
    exit()

if dt_api_token == '':
    print('Environment variable dt_api_token is missing. API token requires v2 read entities and write settings permission. Please set. Exiting')
    exit()

if logging:
    print('dt_logging environment variable is set. Enabling debug logging mode.')
    print(f"DT URL: {dt_url}")
    print(f"Input Filename: {input_filename}")

headers = {
    "Authorization": f"Api-Token {dt_api_token}"
}

# master_list = [
#     {
#        "entitySelector": "type(SERVICE),tag(app:frontend),tag(environment:production)",
#        "request_names": [
#          "/pageOne.html",
#          "/pageTwo.html"
#         ]
#     }
# ]

def build_master_list(csv_reader):

    first_row = True
    master_list = []

    for row in csv_reader:
        # Skip header row
        if first_row:
            first_row = False

            if logging:
                print("Header row should be: \"entitySelector|request_name\"")
                print(f"Header Row: {row}")
            continue

        # row[0] is entitySelector
        # row[1] is the URL
        #print(f"Marking \"{row[1]}\" as a KR for services matching: \"{row[0]}\"")

        # Build master list
        # If this entitySelector is already in the master_list, add the URL to that item
        if logging:
            print(f"Checking: {row[0]} for {row[1]} in master list")

        create_new_master_list_item = True
        for master_list_item in master_list:
            if row[0] == master_list_item['entitySelector']:
                create_new_master_list_item = False
                print(f"found a new url for existing entity id: {row[0]}. adding it.")
                master_list_item['request_names'].append(row[1])

        # If existing entitySelector not found, create a new master_list_item
        if create_new_master_list_item:
            master_list_item = {
                "entitySelector": row[0],
                "request_names": [row[1]]
            }
            master_list.append(master_list_item)

    return master_list

def get_and_add_service_ids(master_list):
    # Get services for each entity ID and add to master list
    for master_list_item in master_list:
        entity_selector = master_list_item['entitySelector']

        if logging:
            print(f"Entity Selector: {entity_selector}")

        # Get SERVICE IDs for this entitySelector
        get_service_ids_response = requests.get(
            url=f"{dt_url}/api/v2/entities",
            headers=headers,
            params= {
              'entitySelector': entity_selector
            }
        )

        if get_service_ids_response.status_code != 200:
          print('Got a non 200 OK code from Dynatrace. Something went wrong. Exiting')
          print(get_service_ids_response.text)
          continue

        dt_payload_response = get_service_ids_response.json()

        # If DT has returned SERVICE IDs, add to the master_list_item
        if dt_payload_response['totalCount'] > 0:
            entities_ids = []
            for item in dt_payload_response['entities']:
                entity_id = item['entityId']

                if logging:
                    print(f"Got entityId: {entity_id}")

                # Add entity_id to list
                entities_ids.append(entity_id)

            master_list_item['service_entity_ids'] = entities_ids
    return master_list

with open(input_filename, newline='') as input_csv_file:

    if logging:
        print("Remember: CSV file must use | as a seperator!")

    csv_reader = csv.reader(input_csv_file, delimiter='|')
    master_list = build_master_list(csv_reader)
    master_list = get_and_add_service_ids(master_list)

    if logging:
        print('printing master list...')
        print(master_list)

    # For each entity in master list, put the key requests
    payload = []
    for entity in master_list:
        # scope is one service ID so for each service ID, create a new object
        if 'service_entity_ids' in entity:
            for service_entity_id in entity['service_entity_ids']:
                item = {
                    "schemaId": SCHEMA_ID,
                    "scope": service_entity_id,
                    "value": {
                        "keyRequestNames": entity['request_names']
                    }
                }

                # Add to payload
                payload.append(item)

    if logging:
        print('Printing payload')
        print(payload)

#####################
# POST to Dynatrace #
#####################
response = requests.post(
    url=f"{dt_url}/api/v2/settings/objects",
    headers=headers,
    json=payload)

if response.status_code != 200:
    print(f"Error POSTing to Dynatrace. Response Code: {response.status_code}. Text: {response.text}")
