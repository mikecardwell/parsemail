from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    url(r'^$',        'parsemail.views.home',    name='home'),
   
    url(r'^csp$',     'parsemail.views.csp',     name='csp'),

    url(r'^about$',   'parsemail.views.about',   name='about'),
    
    url(r'^privacy$', 'parsemail.views.privacy', name='privacy'),
    
    # /msg/CODE
    url(r'^msg/(?P<code>[a-zA-Z0-9]+)$',
            'parsemail.views.msg',      name='msg'),

    # /msg/CODE/raw
    url(r'^msg/(?P<code>[a-zA-Z0-9]+)/raw$',
            'parsemail.views.msg_raw',  name='msg_raw'),

    # /msg/CODE/ID.headers
    url(r'^msg/(?P<code>[a-zA-Z0-9]+)/(?P<id>[0-9]+(?:\.[0-9]+)*)\.headers$',
            'parsemail.views.msg_headers', name='msg_part_headers'),

    # /msg/CODE.headers
    url(r'^msg/(?P<code>[a-zA-Z0-9]+)\.headers$',
            'parsemail.views.msg_headers', name='msg_headers'),

    # /msg/CODE/ID.txt (The .txt is ignored unless it's a HTML part)
    url(r'^msg/(?P<code>[a-zA-Z0-9]+)/(?P<id>[0-9]+(?:\.[0-9]+)*)\.(?P<ext>txt)$',
            'parsemail.views.msg_part', name='msg_part_ext'),

    # /msg/CODE/ID
    url(r'^msg/(?P<code>[a-zA-Z0-9]+)/(?P<id>[0-9]+(?:\.[0-9]+)*)$',
            'parsemail.views.msg_part', name='msg_part'),
)
