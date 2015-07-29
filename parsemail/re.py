# Define a load of regular expressions which will be useful for parsing
# html/text for things like ip addresess, hostnames, email address and so on

import os
import re

effective_tld_names_path = os.path.abspath(os.path.dirname(__file__)) \
        + '/../resources/effective_tld_names.dat'

# Regular expression string matching a top level label from the public suffix
# list (no unicode support)

with open(effective_tld_names_path) as fh:
    RXS_effective_tld_names = '(?:' + ('|'.join([t.strip() for t in fh])) + ')'

# Regular expression string matching a hostname (no unicode support)

RXS_hostname = r'(?:[a-zA-Z0-9](?:[-a-zA-Z0-9]*[a-zA-Z0-9])?\.)+' + \
    RXS_effective_tld_names

# Regular expression string matching an email address. Yes, this is much more
# limited than what reality allows.

RXS_email = r'[-\.a-zA-Z0-9#_~!&\'\+,=]{1,64}@' + RXS_hostname 

# Regular expression string matching a URL

RXS_pathname = r"(?:/" \
               + r"(?:" \
                  + r"(?:[-,a-zA-Z0-9\._~!\$&'\(\)*\+;=:@]|%[a-fA-F0-9]{2})*" \
                  + r"(?:[a-zA-Z0-9]|%[a-fA-F0-9]{2})" \
               + r")?" \
             + r")*"
RXS_qs   = r"(?:\?" + r"(?:[-a-zA-Z0-9._~=&;\+,!/@:?]|%[a-fA-F0-9]{2})*(?:[a-zA-Z0-9]|%[a-fA-F0-9]{2}))?"
RXS_hash = r"(?:#"  + r"(?:[-a-zA-Z0-9._~=&;\+,!/@:?]|%[a-fA-F0-9]{2})*(?:[a-zA-Z0-9]|%[a-fA-F0-9]{2}))?"
RXS_url  = r"(?:(?:ht|f)tp|gopher)s?://" + \
        RXS_hostname + RXS_pathname + RXS_qs + RXS_hash

# Regular expression strings matching IP addresses

RXS_ipv4_octet = r"(?:[1-9]?[0-9]|1[0-9]{2}|2(?:[0-4][0-9]|5[0-5]))"
RXS_ipv4       = r"(?:(?<![0-9]\.)" + \
        RXS_ipv4_octet + r"(?:\." + RXS_ipv4_octet + r"){3})(?!\.[0-9])"

RXS_ipv6 = r"(?:(?:[0-9A-Fa-f]{1,4}:){6}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|::(?:[0-9A-Fa-f]{1,4}:){5}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){4}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){3}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,2}[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){2}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,3}[0-9A-Fa-f]{1,4})?::[0-9A-Fa-f]{1,4}:(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,4}[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,5}[0-9A-Fa-f]{1,4})?::[0-9A-Fa-f]{1,4}|(?:(?:[0-9A-Fa-f]{1,4}:){,6}[0-9A-Fa-f]{1,4})?::)"

RXS_ip = r"(?:" + RXS_ipv6 + "|" + RXS_ipv4 + ")"

# Compile some useful regular expressions

RX_url      = re.compile(RXS_url)
RX_ip       = re.compile(RXS_ip)
RX_hostname = re.compile(RXS_hostname)
RX_email    = re.compile(RXS_email)
RX_all      = re.compile(r"(?i)(\b" + \
        r'\b|\b'.join([RXS_url, RXS_email, RXS_ip, RXS_hostname ]) + r"\b)")
