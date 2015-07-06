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

def ip_html(ip):
    if ip in ['::']:
        return ip

    h = '<span class="ip'

    c = geoip.city(ip)
    if c and c.get('country_code'):
        cc = c.get('country_code').lower()
        h += ' cc-' + cc
        if os.path.isfile(parsemail.__path__[0] + \
                '/../htdocs/images/flags/' + cc + '.gif'):
            h += ' flag'
    h += '"'

    if c and c.get('country_name'):
        title = c.get('country_name')
        if c.get('city'):
            title += ' (' + c.get('city') + ')'
        h += ' title="' + html.escape(title) + '"'

    return h + '>' + ip + '</span>'

def url_html(data, className=None):
    url = data
    if not re.match('^[a-zA-Z]+://', url):
        url = 'http://' + url

    h = '<a rel="nofollow noreferrer" href="' + \
            html.escape(url) + '"'
    if className:
        h += ' class="' + className + '"'
    return h + '>' + html.escape(data) + '</a>'

@register.filter(name='text_to_nice_html')
def text_to_nice_html(t):

    parts = []
    for part in parsemail.re.RX_all.split(t):

        if parsemail.re.RX_url.fullmatch(part):
            parts.append(url_html(part, className='link'))
        elif parsemail.re.RX_email.fullmatch(part):
            m = re.fullmatch('<(.+)>', part)
            email = m.group(1) if m else part
            parts.append('<a class="email" href="mailto:' + html.escape(email) + '">' +
                    html.escape(part) + '</a>')
        elif parsemail.re.RX_ip.fullmatch(part):
            parts.append(ip_html(part))
        elif parsemail.re.RX_hostname.fullmatch(part):
            parts.append(url_html(part, className='hostname'))
        else:
            parts.append(html.escape(part))

    t = ''.join(parts)
    t = add_wbr_to_html(t)
    t = t.replace('\n', '<br>')

    return mark_safe(t)

