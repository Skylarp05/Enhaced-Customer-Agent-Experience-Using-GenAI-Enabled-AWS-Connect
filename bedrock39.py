import sys
import json
from pip._internal import main

main(['install', '-I', '-q', 'boto3', '--target', '/tmp/', '--no-cache-dir', '--disable-pip-version-check'])
sys.path.insert(0,'/tmp/')

import boto3
from botocore.exceptions import ClientError
kendra_client = boto3.client('kendra')
s3_client = boto3.client('s3')

def getKendraString(query):
    # TODO implement
    
    #query = "What is the refund policy"
    kendra_index = '079e20c7-a5f4-4df0-836a-d0090f0899b1'
    
    response = kendra_client.query(
        IndexId=kendra_index,
        QueryText=query
        )
        
    results = response.get('ResultItems', [])
    first_document = results[0] if results else {}
    second_document = results[1] if len(results) > 1 else {}
    
    response_data = {
        'first_document': {
            'document_title': first_document.get('DocumentTitle', {}).get('Text', ''),
            'document_excerpt': first_document.get('DocumentExcerpt', {}).get('Text', '')
        },
        'second_document': {
            'document_title': second_document.get('DocumentTitle', {}).get('Text', ''),
            'document_excerpt': second_document.get('DocumentExcerpt', {}).get('Text', '')
        }
    }
    
    #printing the objects in S3
    s3_objects = s3_client.list_objects(Bucket='wisdomconnect-testdata')
    s3_list = [item['Key'] for item in s3_objects.get('Contents', [])]
    
    text_string = ''
    for key, value in response_data.items():
        title = value['document_title']
        excerpt = value['document_excerpt']
        if title in s3_list:
            text_string += excerpt
    
    return text_string

def get_generate_text(modelId, response):
    provider = modelId.split(".")[0]
    generated_text = None
    if provider == "anthropic":
        response_body = json.loads(response.get("body").read().decode())
        generated_text = response_body.get("completion")
    elif provider == "ai21":
        response_body = json.loads(response.get("body").read())
        generated_text = response_body.get("completions")[0].get("data").get("text")
    elif provider == "amazon":
        response_body = json.loads(response.get("body").read())
        generated_text = response_body.get("results")[0].get("outputText")
    else:
        raise Exception("Unsupported provider: ", provider)
    return generated_text



def lambda_handler(event, context):
    print(boto3.__version__)
    bedrock = boto3.client('bedrock')
    bedrock_runtime = boto3.client('bedrock-runtime')
    
    #query = "What is the refund policy"
    query  = event['inputTranscript']
    text_string = getKendraString(query)
    print("+++++++++ Printing the text string +++++++++++++")
    print(text_string)
    print("++++++++++++++++++++++++++++++++++++++++++++++++")
    
    if not text_string:
        prompt = f"My customer asked this {query} Respond to this:"
    else:
        prompt = f"My customer asked {query}, my response needs to use the following statements {text_string}. Please provide a possible response"
    
    request_body = {
            "prompt": prompt,
            "maxTokens": 100
    } 
    
    event1 = {
    "prompt": "\n\nHuman:Why is the sky blue?\n\nAssistant:",
    "parameters": {
    "temperature": 0
        }
    }
    request_body.update(event1["parameters"])
    r_body = json.dumps(request_body)

    response = bedrock_runtime.invoke_model(
    contentType='application/json',
    body=r_body,
    accept='*/*',
    modelId='ai21.j2-mid-v1'
    )
    
    modelId='ai21.j2-mid-v1'
    
    generated_text = get_generate_text(modelId, response)
    print(generated_text)
    
    lex_response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
                "contentType": "PlainText",
                "content": generated_text
            }
        }
    }
    
    return lex_response


