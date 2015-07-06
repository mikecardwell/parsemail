from django.conf import settings

import base64
import datetime
import email
import json
import random
import re
import os
import string
import subprocess
import time
import urllib.parse
import wand.image
import zipfile

trusted_image_types = [
    'image/jpeg',
    'image/gif',
    'image/png',
    'image/tiff',
]

class Image:

    def __init__(self, part):
        self._part = part

    def body(self):
        with open(self.path(), 'rb') as fh:
            return fh.read()

    def content_type(self):
        return self.meta('mimetype')

    def error(self):
        return self.meta('error')

    def width(self):
        return self.meta('width')

    def height(self):
        return self.meta('height')

    def meta(self, name=None):
        meta = self._part.meta('image')

        mimetype = meta.get('mimetype').lower()
        if mimetype and mimetype not in trusted_image_types:
            meta['mimetype'] = self._part.content_type()

        if name == None:
            return meta
        return meta.get(name)

    def path(self):
        path = self._part.path() + '-body'

        if self._part.is_html():
            path += '.gif'
        return path

class Header:

    def __init__(self, name, value):
        self._name  = name.strip()
        self._value = value.strip()

    def name(self):
        return self._name

    def name_is(self, name):
        return name.lower() == self._name.lower()

    def value(self):
        """\
        Returns the header value, fully decoded
        """
        raw = self.raw_value()

        header = []
        for part in email.header.decode_header(raw):
            if isinstance(part[0], str):
                header.append(part[0])
            else:
                charset = part[1] or 'us-ascii'
                header.append(part[0].decode(charset, errors='replace'))

        header = re.sub('\n\s+', '\n', ''.join(header))
        if self.name_is('content-type'):
            header = re.sub('\s*[\r\n]+\s*', ' ', header)

        return header

    def raw_value(self):
        """\
        Returns the raw value of the header, prior to decoding
        """
        return self._value

    def freeze(self):
        return [self._name, self._value]
                
    @staticmethod
    def thaw(frozen):
        return Header(*frozen)

class Headers:

    def __init__(self, headers):
        self._headers = headers

    def __iter__(self):
        for header in self.get_all():
            yield header

    def __str__(self):
        return "\n".join([
            header.name() + ': ' + header.value().replace("\n", "\n\t")
            for header in self.get_all()
        ])

    def raw(self):
        return "\n".join([
            header.name() + ': ' + header.raw_value()
            for header in self.get_all()
        ])

    def count(self):
        return len(self.get_all())

    def get(self, name):
        headers = self.get_all(name)
        if len(headers) == 0:
            return None
        return headers[0]

    def get_all(self, name=None):
        if name == None:
            return self._headers

        headers = []
        for header in self._headers:
            if header.name().lower() == name.lower():
                headers.append(header)
        return headers

    def to_storage(self, path_dir, id):
        with open(path_dir + '/' + id + '-headers', 'w') as fh:
            json.dump(self.freeze(), fh)

    def freeze(self):
        return list(map(lambda h: h.freeze(), self.get_all()))

    @staticmethod
    def thaw(frozen):
        headers = list(map(lambda h: Header.thaw(h), frozen))
        return Headers(headers)

    @staticmethod
    def from_message(msg):
        headers = list(map(lambda t: Header(*t), msg.items()))
        return Headers(headers)

class MIMEPart:

    def __init__(self, code, id):
        self._code = code
        self._id   = id
        meta_path  = self.path() + '-meta'
        if not os.path.isfile(meta_path):
            raise FileNotFoundError(meta_path)

    def id(self):
        return self._id

    def id_underscored(self):
        return self.id().replace('.', '_')

    def code(self):
        return self._code

    def url(self):
        return '/msg/' + self.code() + '/' + self.id()

    def content_type(self):
        return self.meta('content_type')

    def charset(self):
        charset = self.meta('charset')
        if charset == None and self.is_text():
            charset = 'us-ascii'
        return charset

    def has_filename(self):
        return self.meta('filename') != None

    def filename(self):
        filename = self.meta('filename')
        if filename:
            fileparts = []
            for part in email.header.decode_header(filename):
                if isinstance(part[0], str):
                    fileparts.append(part[0])
                else:
                    charset = part[1] or 'us-ascii'
                    fileparts.append(part[0].decode(charset, errors='replace'))
            filename = re.sub(r'[\s\t\r\n]+', ' ', ''.join(fileparts)).strip()
        
        return filename or self.code() + '_' + self.id() + '.raw'

    def escaped_filename(self):
        return email.header.Header(self.filename()).encode()

    def content_id(self):
        header = self.header('Content-Id')
        if header == None: return None
        return re.sub(r'^\s*<\s*(.*?)\s*>\s*$', r'\1', header.value())

    def content_ids(self):
        cids = {}
        cid = self.content_id()
        if cid: cids[cid] = self
        for child in self.children():
            for (cid, part) in child.content_ids().items():
                cids[cid] = part
        return cids

    def search_by_cid(self, cid):
        return self.content_ids().get(cid)

    def is_zipfile(self):
        return self.content_type() in ['application/zip',
                'application/x-zip-compressed']

    def is_image(self):
        # Be very careful. Don't want to include e.g image/svg+xml here
        return self.content_type() in trusted_image_types

    def is_html(self):
        return self.content_type() == 'text/html'

    def is_text(self):
        return self.content_type().startswith('text/') \
                or self.content_type() in [
                    'image/svg+xml',
                    'application/xml',
                    'application/javascript',
                    'application/x-javascript',
                    'application/pgp-signature',
                ]

    def is_previewable(self):
        return self.is_text() or self.is_image() or self.is_zipfile()

    def msg(self):
        """\
        Return the top level MIME part/Message
        """
        return Message(self.code())

    def parent_or_self(self):
        return self.parent() if self.has_parent() else self

    def has_parent(self):
        return self.id() != '1'

    def parent(self):
        if not self.has_parent(): return None
        parent_id = re.sub('\.[0-9]+$', '', self.id())
        return MIMEPart(self.code(), parent_id)

    def next(self):
        ids = list(map(lambda c: c.id(), self.msg().parts()))
        try:
            next_id = ids[ ids.index(self.id()) + 1 ]
            return MIMEPart(self.code(), next_id)
        except IndexError:
            return None

    def prev(self):
        ids = list(map(lambda c: c.id(), self.msg().parts()))
        idx = ids.index(self.id()) - 1
        if idx < 0: return None
        return MIMEPart(self.code(), ids[ idx ])

    def has_children(self):
        return os.path.isfile(self.path() + '.1-meta')

    def children(self):
        children = []
        for n in range(1,100):
            if not os.path.isfile(self.path() + '.' + str(n) + '-meta'): break
            children.append(self.id() + '.' + str(n))
        return map(lambda id: MIMEPart(self.code(), id), children)

    def ancestors(self):
        ancestors = []
        for child in self.children():
            ancestors.append(child)
            ancestors.extend(child.ancestors())
        return ancestors

    def meta(self, name=None, value=None):
        if not hasattr(self, '_meta'):
            with open(self.path() + '-meta') as fh:
                self._meta = json.load(fh)

        if value != None:
            if name == None:
                raise Exception("Can't set a meta value without name")
            self._meta[ name ] = value
            with open(self.path() + '-meta', 'w') as fh:
                json.dump(self._meta, fh)
        elif name == None:
            return self._meta

        return self._meta.get(name)

    def header(self, name):
        return self.headers().get(name)

    def headers(self, name=None):
        if not hasattr(self, '_headers'):
            with open(self.path() + '-headers') as fh:
                self._headers = Headers.thaw(json.load(fh))
        return self._headers if name == None else self._headers.get_all(name)

    def has_preamble(self):
        return os.path.isfile(self.path() + '-preamble')

    def preamble(self):
        with open(self.path() + '-preamble') as fh:
            return fh.read()

    def has_epilogue(self):
        return os.path.isfile(self.path() + '-epilogue')

    def epilogue(self):
        with open(self.path() + '-epilogue') as fh:
            return fh.read()

    def has_body(self):
        return os.path.isfile(self.path() + '-body')

    def body(self):
        with open(self.path() + '-body', 'rb') as fh:
            return fh.read()

    def body_size(self):
        return os.stat(self.path() + '-body').st_size if self.has_body() else 0

    def body_text(self):
        return self.body().decode().strip()

    def body_datauri(self):
        ct = self.content_type()
        if self.charset():
            ct += ';charset=' + self.charset()
        body = base64.b64encode(self.body()).decode()
        return 'data:' + ct + ';base64,' + body

    def image(self):
        if self.is_image() or self.is_html():
            return Image(self)
        else:
            raise Exception('No image available')

    def zipfile_contents(self):
        return self._parse_zipfile().get('infolist')

    def zipfile_error(self):
        return self._parse_zipfile().get('error')

    def _parse_zipfile(self):
        if not hasattr(self, '_zipdata'):
            try:
                with zipfile.ZipFile(self.path() + '-body') as zip:

                    items = []
                    for item in zip.infolist():
                        items.append({
                            'filename':        item.filename,
                            'date_time':       datetime.datetime(*item.date_time),
                            'file_size':       item.file_size,
                        })

                    items = sorted(items, key=lambda item: item['filename'])
                    self._zipdata = { "infolist": items }
            except zipfile.BadZipFile as err:
                self._zipdata = { "error": str(err) }

        return self._zipdata

    def html_image_content_type(self):
        return self.meta('image').get('mimetype')

    def gen_html_image(self, cids, remote_content=False):
        html = self.body_text()
        # Figure out paths
        path = self.path() + '-body'

        html_path  = path + '.html' # tmpfile for modified html content
        wk_path    = path + '.png'  # generated by wk
        image_path = path + '.gif'  # image preview file

        # Crude method to replace content id URIs with data URIs
        # TODO: Make this work much more nicely. Deal with uri encoding
        # and make sure it's actually an attribute we're replacing etc
        for (cid, datauri) in cids.items():
            html = re.sub(r'(?i)=([\'"]?)cid:' + re.escape(cid) + '[\'"\s>]', r'=\1' + datauri, html)

        # Add MIME type charset to the HTML so Webkit knows what to use
        if not re.search('(?i)charset=', html):
            html = '<meta charset="' + self.charset() + '">' + html

        # Write out the temporary html file which we will use as input
        # for webkit
        with open(html_path, 'w') as fh:
            fh.write(html)

        # Generate image using webkit
        cmd = [
            '/usr/bin/xvfb-run', '--',
            '/usr/bin/wkhtmltoimage',
            '--disable-local-file-access',
            '--disable-javascript',
            '--disable-plugins',
            '--encoding', 'utf-8',
        ]
        if not remote_content:
            cmd.extend([ '--proxy', '127.0.0.1:1' ])
        cmd.append(html_path)
        cmd.append(wk_path)
 
        print('Running: ' + ' '.join(cmd))
        return_code = subprocess.call(cmd, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)

        if not return_code in [0, 1]:
            raise Exception('Failed to generate image from HTML - ' \
                    + str(return_code))

        # Remove temporary html file. We no longer need it after generating
        # the image using webkit
        os.remove(html_path)

        # Now we use image magick to resize and convert to a gif. Not using
        # wand here as I can't see how to use "1024x>" with wands resize func
        cmd = [ '/usr/bin/convert', wk_path, '-sample', '1024x>', image_path ]
        print('Running: ' + ' '.join(cmd))
        return_code = subprocess.call(cmd, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)

        if return_code != 0:
            raise Exception('Failed to convert wk image to gif')
        os.remove(wk_path)

        # Get some meta data about the image and store it with the main meta
        # file for the part
        with wand.image.Image(filename=image_path) as img:
            self.meta('image', {
                "mimetype": img.mimetype,
                "width":    img.width,
                "height":   img.height,
            })

    @staticmethod
    def create(code, msg, id='1', delete_after=None):
        path = MIMEPart.id_path(code, id)

        written_something = False

        # Write meta file last as it may be updated as we go along
        meta = {
            'content_type': msg.get_content_type(),
            'charset':      msg.get_content_charset(),
            'filename':     msg.get_filename(),
        }

        if id == '1':
            meta['ctime'] = time.time()

        if delete_after:
            meta['delete_after'] = int(delete_after)

        headers = Headers.from_message(msg)

        if msg.preamble:
            preamble = msg.preamble.strip()
            if preamble:
                with open(path + '-preamble', 'w') as fh:
                    fh.write(preamble)
                written_something = True

        if msg.epilogue:
            epilogue = msg.epilogue.strip()
            if epilogue:
                with open(path + '-epilogue', 'w') as fh:
                    fh.write(epilogue)
                written_something = True

        if msg.is_multipart():
            n = 0
            for child_msg in msg.get_payload():
                n += 1
                child_id = id + '.' + str(n)
                if MIMEPart.create(code, child_msg, child_id):
                    written_something = True
        else:
            msg.set_charset('utf-8')
            body = msg.get_payload(decode=True)
            if len(body):

                body_mode = 'wb'
                if meta['content_type'].startswith('text/'):
                    body_mode = 'w'
                    try:
                        body = body.decode(meta['charset'])
                    except:
                        body = body.decode(errors='replace')

                with open(path + '-body', body_mode) as fh:
                    fh.write(body)

                written_something = True
                if meta['content_type'] in trusted_image_types:
                    try:
                        with wand.image.Image(blob=body) as img:
                            info = {
                                "mimetype": img.mimetype,
                                "width":    img.width,
                                "height":   img.height,
                                "meta":     list(map(lambda i: i, img.metadata.items())),
                            }
                    except:
                        info = {
                            "mimetype": meta['content_type'],
                            "error":    "Failed to parse with ImageMagick"
                        }

                    meta['image'] = info
            elif headers.count() == 0 and not written_something:
                return False

        with open(path + '-headers', 'w') as fh:
            json.dump(headers.freeze(), fh)

        with open(path + '-meta', 'w') as fh:
            json.dump(meta, fh)

        return True

    def path(self):
        return MIMEPart.id_path(self.code(), self.id())

    @staticmethod
    def id_path(code, id):
        return MIMEPart.code_path(code) + '/' + id

    @staticmethod
    def code_path(code):
        return settings.EMAIL_DIR + '/' + code

class Message(MIMEPart):

    def __init__(self, code):
        super().__init__(code, '1')

    def url(self):
        return '/msg/' + code

    def raw(self):
        with open(Message.code_path(self.code()) + '/raw') as fh:
            return fh.read()

    def ctime(self):
        return datetime.datetime.fromtimestamp(self.meta('ctime'))

    def dtime(self):
        return datetime.datetime.fromtimestamp(self.meta('ctime') + self.meta('delete_after') * 60)

    def parts(self):
        parts = [self.part('1')]
        parts.extend(self.ancestors())
        return parts

    def part(self, id='1'):
        return MIMEPart(self.code(), id)

    @staticmethod
    def create(raw, delete_after, encoding='utf-8', remote_content=False):

        # Try and decode the message using the encoding supplied. If fails,
        # try and get the encoding from the message source it's self
        try:
            data = urllib.parse.unquote_plus(raw, encoding=encoding, errors='strict')
        except Exception as err:
            print("Failed to strict decode message using " + encoding + ": " + str(err))
            data = urllib.parse.unquote_plus(raw, encoding=encoding, errors='replace')
            data = email.message_from_string(data)
            encoding = data.get_content_charset()
            print("Looks like message is using " + encoding + ", so we'll forcibly decode with that instead")
            data = urllib.parse.unquote_plus(raw, encoding=encoding, errors='replace')

        msg = email.message_from_string(data)

        # No headers = empty email
        if len(msg.items()) == 0:
            raise Exception('Empty email')

        code = Message._mkdir_code()
        if not MIMEPart.create(code, msg, delete_after=delete_after):
            os.remove(Message.code_path(code) + '/raw')
            os.rmdir(Message.code_path(code))
            raise Exception('Unexpected parsing failure')

        msg = Message(code)

        with open(Message.code_path(code) + '/raw', 'w') as fh:
            fh.write(data)

        # Trigger generation of the image previews of the html parts
        cids = msg.content_ids().items()
        cids = dict(map(lambda i: [i[0], i[1].body_datauri()], cids))
        for part in msg.parts():
            if not part.is_html():  continue
            if not part.has_body(): continue
            part.gen_html_image(cids=cids, remote_content=remote_content)

        return msg

    @staticmethod
    def _mkdir_code():
        while True:
            code = Message._random_code()
            path = Message.code_path(code)
            try:
                os.mkdir(path)
                return code
            except FileExistsError:
                pass

    @staticmethod
    def _random_code(rnd=random.SystemRandom(),
              choices=string.ascii_letters + string.digits):
        return ''.join([rnd.choice(choices) for l in range(6)]) # ~56b poss
