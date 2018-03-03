from flask import Flask, request
from flask_restful import Resource, Api
import urllib.parse
import requests
from subprocess import call
from requests.auth import HTTPBasicAuth
import json

app = Flask(__name__)
api = Api(app)


USER="167200a9-b2cd-4ef2-90b9-e0879b0e0a96"
PASSWORD="frO10ZyEGSig"
TMP_FILENAME = "test.wav"

ORION_SERVER_PRIVATE = "192.168.4.230"
ORION_SERVER_PUBLIC = "84.89.60.4"

ORION_SERVER=ORION_SERVER_PUBLIC
ORION_PORT = 80

registered_entities = {
        'bressol': {
            'aliases': [],
            'type': 'bebe',
            'actions': {
                'encen': {
                    "var": "estat",
                    "value": "on",
                },
                'para': {
                    "var": "estat",
                    "value": "off",
                }
            }
        },
        
        'persiana': {
            'aliases': ["persianes"],
            'type': 'blind_controller',
            'actions': {
                'puja': {
                    "var": "action",
                    "value": "puja",
                },
                'baixa': {
                    "var": "action",
                    "value": "baixa",
                },
                'para': {
                    "var": "action",
                    "value": "para",
                }
            },                
        },
    }


class Hub(Resource):
    """
    Return all configured entities and their related actions
    """

    def get(self):

        return registered_entities


class Fiware(Resource):

    def __init__(self, host=ORION_SERVER, port=ORION_PORT):
        self.host = host
        self.port = port

    @property
    def url(self):
        protocol = "http"
        if self.port == 443:
            protocol = "https"
            
        return f"{protocol}://{self.host}:{self.port}"

    def get(self, entity, action):

        values_to_update = registered_entities[entity]['actions'][action]
        entities_url = self.url + f"/v2/entities/{entity}/attrs"

        payload = {
            values_to_update['var']: {
                'value': values_to_update['value'],
                'type': "String",
            }
        }

        r = requests.patch(entities_url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload) )
        
        if r.status_code > 399:
            return {
                'error': True,
                'message': r.text,
                'code': r.status_code
            }

        return {
            'error': False,
            'message': f"Triggered action '{action}' at '{entity}'",
            'payload': payload,
        }


class Voice(Resource):
    """
    Process an incoming string trying to match with an entity and their possible actions
    """

    def identify_entity(self, text):
        for entity in registered_entities.keys():
            if entity in text.split(" "):
                return entity
        return False

    def identify_actions(self, entity, text):
        for action in registered_entities[entity]['actions'].keys():
            if action in text.split(" "):
                return action
        return False

    def process_voice(self, text):
        # Try to match the entity
        the_entity = self.identify_entity(text)

        # Try to match the action and notify fiware
        if the_entity:
            the_action = self.identify_actions(the_entity, text)

            if the_action:
                fiware = Fiware()
                return fiware.get(the_entity, the_action)

    def get(self, text):
        return self.process_voice(text)



class Speech(Resource):
    """
    Ask watson to reach a wav file with the provided text
    """
    def get(self, text):

        URL = "https://stream.watsonplatform.net/text-to-speech/api/v1/synthesize?accept=audio/wav&text={}&voice=es-ES_EnriqueVoice".format(urllib.parse.quote_plus(text))

        r = requests.get(URL, stream=True, auth=HTTPBasicAuth(USER, PASSWORD))
        open(TMP_FILENAME, 'wb').write(r.content)

        call(['aplay', TMP_FILENAME])

        return {
            'text': text,
            'URL': URL,
            'status': True,
        }


api.add_resource(Hub, '/hub/')
api.add_resource(Voice, '/voice/<string:text>')
api.add_resource(Fiware, '/fiware/<string:entity>/<string:action>')
api.add_resource(Speech, '/speech/<string:text>')

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
