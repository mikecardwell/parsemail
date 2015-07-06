#!/usr/bin/env python3

import glob
import json
import os
import shutil
import sys
import time
from django.conf import settings

# Add parent directory to path for parsemail modules
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + '/..')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "parsemail.settings")

for path in glob.glob(settings.EMAIL_DIR + '/*'):
    if not os.path.isdir(path):
        continue

    with open(path + '/1-meta') as fh:
        meta = json.load(fh)

    delete_after = meta['ctime'] + int(meta['delete_after']) * 60

    if time.time() >= delete_after:
        print("Expiring " + path)
        shutil.rmtree(path)
