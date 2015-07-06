#!/usr/bin/env python3

import datetime
import os
import re
import requests
import sys

# Config

url     = 'https://publicsuffix.org/list/effective_tld_names.dat'
path    = '../resources/effective_tld_names.dat'
min_age = 3600

# Abs path to the file is relative to this script

path = os.path.dirname(os.path.realpath(__file__)) + '/' + path

# Decide whether to download new version based on mtime of existing file

if os.path.isfile(path):
    mtime = os.stat(path).st_mtime
    age   = datetime.datetime.now().timestamp() - mtime
    if age < min_age:
        sys.exit(0)

# Download new version

print('Downloading')
res = requests.get(url)
if res.status_code != 200:
    raise Exception("Bad status code: " + str(res.status_code))

# Write out new data set

tlds = []
for line in map(lambda l: l.strip(), res.text.split("\n")):

    # Skip comments
    if line == '' or line.startswith("//"):
        continue

    # Strip all but the last label
    tld = re.sub(r'.+\.', '', line)

    # Encode using punycode
    tld = tld.encode('idna').decode()
    
    if tld not in tlds:
        tlds.append(tld)

tlds.sort(key=len)
tlds.reverse()

with open(path + '.tmp', 'w') as fh:
    fh.write("\n".join(tlds))
os.rename(path + '.tmp', path)
