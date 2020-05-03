#!/usr/bin/python3
import hashlib
import json
data = {
    '123':123,
    '456':456
}
s = hashlib.sha256(json.dumps(data).encode('utf8')).hexdigest()
print(s)
data['s'] = s

data = json.dumps(data)
data = json.loads(data)
del data['s']
print(hashlib.sha256(json.dumps(data).encode('utf8')).hexdigest())


