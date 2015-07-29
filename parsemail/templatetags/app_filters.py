from django import template
from django.utils.safestring import mark_safe
from django.contrib.gis.geoip import GeoIP

import html
import os
import parsemail
import parsemail.re
import re

register = template.Library()

geoip = GeoIP()

@register.filter(name='bytes_to_human')
def bytes_to_human(bytes):
    """\
    Converts a size in bytes to one in a more human readable format.
    """
    bytes = int(bytes)
    if bytes < 1024:               return "{:,}".format(bytes) + 'B'
    if bytes < 1024 * 1024:        return "{:,}".format(int(bytes/1024)) + 'KB'
    if bytes < 1024 * 1024 * 1024: return "{:,.1f}".format(bytes/1024/1024) + 'MB'
    return "{:,.1f}".format(bytes/1024/1024/1024) + 'GB'

@register.filter(name='wbr')
def wbr(value, max=35):
    """\
    Injects zero-width word break characters in long blocks of text that have
    no natural word break points.
    """
    value = re.sub(r'([^\s\u200b]{' + str(max) + r'})', '\\1\u200b', value)
    value = re.sub('\u200b$', '', value)
    return value

@register.filter(name='wbr_path')
def wbr_path(value, max=35):
    """\
    Like wbr, except injects extra word break points after slashes
    """
    value = value.replace('/',  '/\u200b')
    value = value.replace('\\', '\\\u200b')
    return wbr(value, max)

def add_wbr_to_html(t):
    parts = []
    for part in re.split(r'(<[^>]*>)', t):
        if part == '': continue
        if part.startswith('<'):
            parts.append(part)
        else:
            part = html.unescape(part)
            part = re.sub(r'([^\s\u200b]{35})', '\\1\u200b', part)
            parts.append(html.escape(part))

    return ''.join(parts)

@register.filter(name='ip_html')
def ip_html(ip):
    if ip in ['::']:
        return ip

    rfc1918 = re.match(r'(?:127|192|10|172\.(?:1[6-9]|2[0-9]|3[01]))\.', ip)

    h = '<span class="ip'

    c = geoip.city(ip)
    if c and c.get('country_code'):
        cc = c.get('country_code').lower()
        h += ' cc-' + cc
        if os.path.isfile(parsemail.__path__[0] + \
                '/../htdocs/images/flags/' + cc + '.gif'):
            h += ' flag'
    elif rfc1918:
        h += ' rfc1918'
    h += '"'

    if c and c.get('country_name'):
        title = c.get('country_name')
        if c.get('city'):
            title += ' (' + c.get('city') + ')'
        h += ' title="' + html.escape(title) + '"'
    elif rfc1918:
        h += ' title="RFC 1918 Private Network"'

    return h + '>' + ip + '</span>'

@register.filter(name='url_html')
def url_html(data, className='link'):
    url = data
    if not re.match('^[a-zA-Z]+://', url):
        url = 'http://' + url

    h = '<a rel="nofollow noreferrer" href="' + \
            html.escape(url) + '"'
    if className:
        h += ' class="' + className + '"'
    return h + '>' + html.escape(data) + '</a>'

@register.filter(name='hostname_html')
def hostname_html(data):
    return url_html(data, className='hostname')

@register.filter(name='email_html')
def email_html(data, keepBrackets=False):
    m = re.fullmatch('<(.+)>', data)
    email = m.group(1) if m else data
    return '<a href="mailto:' + html.escape(email) + '" class="email">' \
            + html.escape(data if keepBrackets else email) + '</a>'

@register.filter(name='text_to_nice_html')
def text_to_nice_html(t):

    parts = []
    for part in parsemail.re.RX_all.split(t):

        if parsemail.re.RX_url.fullmatch(part):
            parts.append(url_html(part))
        elif parsemail.re.RX_email.fullmatch(part):
            parts.append(email_html(part, keepBrackets=True))
        elif parsemail.re.RX_ip.fullmatch(part):
            parts.append(ip_html(part))
        elif parsemail.re.RX_hostname.fullmatch(part):
            parts.append(hostname_html(part))
        else:
            parts.append(html.escape(part))

    t = ''.join(parts)
    t = add_wbr_to_html(t)
    t = t.replace('\n', '<br>')

    return mark_safe(t)

