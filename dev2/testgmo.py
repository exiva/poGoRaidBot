from google.protobuf.json_format import MessageToJson
from protos.pogoprotos.networking.responses.fort_search_response_pb2 import FortSearchResponse
from protos.pogoprotos.networking.responses.encounter_response_pb2 import EncounterResponse
from protos.pogoprotos.networking.responses.get_map_objects_response_pb2 import GetMapObjectsResponse
from protos.pogoprotos.networking.responses.gym_get_info_response_pb2 import GymGetInfoResponse
from protos.pogoprotos.networking.responses.fort_details_response_pb2 import FortDetailsResponse

import json
from base64 import b64decode

gmo = "CiAwMTI5MDExMjBjY2NkNzc0NmQ3MTk4MzQ0YjM3MjM3NiIJU3RhcmJ1Y2tzKnVodHRwOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS9NSENib1paaXI2OEJCNGZqTVpCaGNSNzBqMEZnUWZWUlR6aWl5VEFNblFqWkVJa184dlMwRVh2NEEtclJ1R0xTNFJ6bGdGNlhGM2lYNFNoR0cyc0VIAVH/c/tZaghFQFm6gq/g5SBSwGJqVGhlIFBva8OpbW9uIEdPIEZyYXBwdWNjaW5vwq4gYmxlbmRlZCBiZXZlcmFnZSDigJMgYXNrIHlvdXIgU3RhcmJ1Y2tzIGJhcmlzdGEgYWJvdXQgcHJpY2luZyAmIGF2YWlsYWJpbGl0eYIBAA=='"

dec = b64decode(gmo)

gmo = FortDetailsResponse()
gmo.ParseFromString(dec)
gmo_response_json = json.loads(MessageToJson(gmo))

print(gmo_response_json)