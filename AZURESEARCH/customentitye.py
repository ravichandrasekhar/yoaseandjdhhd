import logging
import azure.functions as func
import csv
import json
import re
import os

def main(req: func.HttpRequest) -> func.HttpResponse:
    print('Python HTTP trigger function processed a request.')

    try:
        body = json.dumps(req.get_json())
    except ValueError:
        return func.HttpResponse(
             "Invalid body",
             status_code=400
        )
    
    if body:
        result = compose_response(body)
        return func.HttpResponse(result, mimetype="application/json")
    else:
        return func.HttpResponse(
             "Invalid body",
             status_code=400
        )


def compose_response(json_data):
    values = json.loads(json_data)['values']
    
    # Prepare the Output before the loop
    results = {}
    results["values"] = []

    # Get reference data - csv file. Any platform, any OS. 
    __location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))
    myFile = os.path.join(__location__, 'C:\\Users\\ravichandrav\\Desktop\\csv\\demo.csv')
    myFile = os.path.normpath(myFile)
    with open(myFile, 'r', encoding='latin-1') as csvList:
        myList = list(csv.reader(csvList))
    
    for value in values:
        outputRecord = transform_value(value, myList)
        if outputRecord is not None:
            results["values"].append(outputRecord)
    # Keeping the original accentuation with ensure_ascii=False
    return json.dumps(results, ensure_ascii=False)

## Perform an operation on a record
def transform_value(value, myList):
    try:
        recordId = value['recordId']
    except KeyError:
        return None

    # Validate the inputs
    try:         
        assert 'data' in value, "'data' field is required."
        data = value['data']        
        assert 'text' in data, "'text' field is required in 'data' object."
    except AssertionError as error:
        return {
            "recordId": recordId,
            "data":{},
            "errors": [{"message": "Error: " + str(error)}]
        }

    try:                
        # Preparing the data output, reading the data
        outputList = []
        recordId = value['recordId']
        text = value['data']['text']

        # Adding extra white spaces because I also add one for the terms
        text = ' ' + text + ' '

        # Removing punctuation, also because of the white spaces. 
        # A term followed by a comma or other punctuation would not be extracted because of the white spaces
        text = re.sub(r'[^\w\s]', '', text)

        # Now let's process for each term in the CSV
        for term in myList:
            # Convert to string and add spaces to avoid things like 'Africa' being extracted from 'African'
            myStr = ' ' + str(term[0]) + ' '
            if text.lower().find(myStr.lower()) >= 0:
                # Remove the white spaces
                myStr = myStr.strip()
                outputList.append(myStr)

    except Exception as e:
        return {
            "recordId": recordId,
            "errors": [{"message": "Could not complete operation for record. Error: " + str(e)}]
        }

    return {
        "recordId": recordId,
        "data": {
            "text": outputList
        }
    }


# Testing the function, forcing one error for the second record. 
# Third record is an empty string. It will work.
# The sample csv content is:
# FLAMENGO
# BARCELONA
# REAL MADRID
# MANCHESTER UNITED
# LIVERPOOL
# MILAN
# JUVENTUS

myInput = {
    "values": [
      {
        "recordId": "0",
        "data": {
             "text": "Flamengo is the new champion"
           }
      },   
      {
        "recordId": "1",
        "data": {
            "text": "Flamengo beat Liverpool in the 1981 World Cup final."
            }
      },
      {
        "recordId": "2",
        "data": {
            "text": ""
          }
      }
    ]
}

inputTest = json.dumps(myInput)
compose_response(inputTest)
