from django.http                  import Http404, HttpResponse
from django.shortcuts             import (render, redirect)
from django.conf                  import settings
from django.views.decorators.csrf import csrf_exempt

import os
import re

from .message import ( Message, MIMEPart )

# Routes:

def home(request):
    """\
    Present/Process a form for uploading emails
    """

    params = {}

    delete_after_options = [
        { 'value':     5, 'name': '5 mins'  },
        { 'value':    60, 'name': '1 hour'  },
        { 'value':  1440, 'name': '1 day'   },
        { 'value': 10080, 'name': '1 week'  },
        { 'value': 43200, 'name': '1 month' },
    ]
    default_delete_after_index = 3

    if request.method == 'POST':
        try:
            # Was remote_content checked?
            remote_content = request.POST.get('remote_content')
            remote_content = True if remote_content == 'on' else False
            if remote_content:
                params['remote_content'] = True

            # Delete after
            found_delete_after = False
            delete_after = request.POST.get('delete_after')
            for option in delete_after_options:
                if str(option['value']) == delete_after:
                    option['selected'] = True
                    found_delete_after = True
            if not found_delete_after:
                delete_after = delete_after_options[ default_delete_after_index ]['value']

            # Get the email raw source (as binary, and the probable encoding)
            encoding = request.encoding or settings.DEFAULT_CHARSET
            msg = None
            for part in request.body.decode(encoding=encoding,errors='ignore').split('&'):
                if part.startswith('email_source='):
                    msg = part[13:]

            if msg == None:
                raise Exception("Empty email")

            msg = Message.create(msg, encoding=encoding,
                        remote_content=remote_content,
                        delete_after=int(delete_after))
            return redirect('/msg/' + msg.code())

        except Exception as err:
            print("ERROR", err)
            params['error'] = 'Invalid email source'

    delete_after_selected = False
    for option in delete_after_options:
        if option.get('selected'):
            delete_after_selected = True
    if not delete_after_selected:
        delete_after_options[ default_delete_after_index ][ 'selected' ] = True

    params['delete_after_options'] = delete_after_options

    return render(request, 'index.html', params)

def about(request):
    return render(request, 'about.html')

def privacy(request):
    return render(request, 'privacy.html')

@csrf_exempt
def csp(request):
    print('CSP Report:' + request.body.decode())
    return HttpResponse('Content-Security-Policy FTW!',
            content_type='text/plain; charset=utf-8')

def msg(request, code):
    """\
    Display information about a message previously uploaded
    """
    try:
        msg = Message(code)
    except FileNotFoundError:
        return render(request, '404.html', status=404, dictionary={
            "msg":"No such email. Either it expired, or it never existed"
        })

    # Extract a bunch of information from the message. 
    urls      = []
    emails    = []
    ips       = []
    hostnames = []

    for part in msg.parts():
        urls.extend(part.find_urls())
        emails.extend(part.find_emails())
        ips.extend(part.find_ips())
        hostnames.extend(part.find_hostnames())

    # Dedupe and sort
    urls      = list(set(urls))
    urls.sort()
    emails    = list(set(emails))
    emails.sort()
    ips       = list(set(ips))
    ips.sort(key=ip_sort)
    hostnames = list(set(hostnames))
    hostnames.sort()

    ips = list(filter(lambda ip: ip != '::', ips))

    return render(request, 'msg.html', {
        'msg':       msg,
        'urls':      urls,
        'emails':    emails,
        'ips':       ips,
        'hostnames': hostnames
    })

def ip_sort (ip):
    """\
    Helper for alphanumeric IP sorting where IPv4 always comes first
    So:  1.2.3.4, 2.3.4.5, 1::2
    Not: 1.2.3.4, 1::2, 2.3.4.5
    """
    return 'z' + ip if ':' in ip else ip

def msg_raw(request, code):
    """\
    Display original raw content of this message as text
    """

    try:
        msg = Message(code)
    except FileNotFoundError:
        raise Http404()

    return HttpResponse(msg.raw(), content_type='text/plain; charset=utf-8')

def msg_headers(request, code, id='1'):

    try:
        part = MIMEPart(code, id)
    except FileNotFoundError:
        raise Http404()

    return HttpResponse(part.headers().raw(), content_type='text/plain; charset=utf-8')

def msg_part(request, code, id, ext=None):
    """\
    Displays the body of a particular mime part
    """

    try:
        part = MIMEPart(code, id)
    except FileNotFoundError:
        raise Http404()

    referrer = request.META.get('HTTP_REFERER')
    if referrer and not \
            re.search(r'^(?i)https?://www\.parsemail\.org(/.*)?$', referrer):
        return render(request, 'msg/referrer.html', { 'part': part })

    if ext == 'txt' and not part.is_html():
        return redirect('/msg/' + part.code() + '/' + part.id())

    as_attachment = False
    if part.is_image():
        image = part.image()
        content_type = image.content_type()
        body = image.body()
    elif part.is_html() and ext != 'txt':
        image = part.image()
        content_type = image.content_type()
        body = image.body()
    elif part.is_text():
        content_type = 'text/plain; charset=utf-8'
        body = part.body_text()
    elif part.is_zipfile():
        content_type = part.content_type()
        body = part.body()
        as_attachment = True
    elif part.content_type() in [
            'application/msword',
            'application/pkcs7-signature',
            'application/pdf',
        ]:
        content_type = part.content_type()
        body = part.body()
        as_attachment = True
    else:
        content_type = 'application/octet-stream'
        body = part.body()
        as_attachment = True

    res = HttpResponse(body, content_type=content_type)

    if as_attachment:
        res['Content-Disposition'] = 'attachment; filename="' + part.escaped_filename() + '"'

    return res
