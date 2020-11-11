import datetime
import json

class ExtendedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime)):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)
