from __future__ import print_function, unicode_literals
import re
import requests
from collections import OrderedDict
from contextlib import closing
from datetime import datetime
from json import JSONEncoder

# regular expressions for replacing Dokuwiki formatting
h1_re = re.compile(r'====== (.*?) ======', re.UNICODE)
h2_re = re.compile(r'===== (.*?) =====', re.UNICODE)
h3_re = re.compile(r'==== (.*?) ====', re.UNICODE)
h4_re = re.compile(r'=== (.*?) ===', re.UNICODE)
h5_re = re.compile(r'== (.*?) ==', re.UNICODE)
italic_re = re.compile(r'[^:]//(.*?)//', re.UNICODE)
bold_re = re.compile(r'\*\*(.*?)\*\*', re.UNICODE)
image_re = re.compile(r'\{\{(http[s]*:.*?)\}\}', re.UNICODE)
link_re = re.compile(r'\[\[(http[s]*:[^:]*)\|(.*?)\]\]', re.UNICODE)
li_re = re.compile(r'[ ]{1,3}(\*)', re.UNICODE)
li_space_re = re.compile(r'^(\*.*\n)\n(?=\*)', re.UNICODE + re.MULTILINE)


def quiet_print(quiet, message, end='\n'):

    if not quiet:
        print(message, end=end)


def dokuwiki_to_markdown(text):
    """
    Cleans up text from possible DokuWiki and HTML tag pollution.
    :param str text:
    :return: str
    """
    text = text.replace('\r', '')
    text = text.replace('\n\n\n\n\n', '\n\n')
    text = text.replace('\n\n\n\n', '\n\n')
    text = text.replace('\n\n\n', '\n\n')
    text = h1_re.sub(r'# \1 #', text)
    text = h2_re.sub(r'## \1 ##', text)
    text = h3_re.sub(r'### \1 ###', text)
    text = h4_re.sub(r'#### \1 ####', text)
    text = h5_re.sub(r'##### \1 #####', text)
    text = italic_re.sub(r'_\1_', text)
    text = bold_re.sub(r'__\1__', text)
    text = image_re.sub(r'![Image](\1)', text)
    text = link_re.sub(r'[\2](\1)', text)
    text = li_re.sub(r'\1', text)
    text = li_space_re.sub(r'\1', text)

    return text


def post_url(url, data):
    """
    :param str|unicode url: URL to open
    :param dict data: The post data
    """

    headers = {'User-Agent': 'Mozilla/5.0',
               'Accept': 'application/json, text/javascript, */*; q=0.01',
               'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
               'X-Requested-With': 'XMLHttpRequest'}

    with closing(requests.Session()) as session:
        response = session.post(url, data=data, headers=headers).content

    # convert bytes to str (Python 3.5)
    if type(response) is bytes:
        return response.decode('utf-8')
    else:
        return response


class ResourceManifest(object):
    def __init__(self, slug, name):
        """
        Class constructor. Optionally accepts the name of a file to deserialize.
        :param unicode slug:
        :param unicode name:
        """

        self.syntax_version = '1.0'
        self.type = 'book'
        self.content_mime_type = 'text/markdown'
        self.slug = slug
        self.name = name
        self.versification_slug = 'ufw'
        self.finished_chunks = []
        self.language = {'slug': 'en', 'name': 'English', 'dir': 'ltr'}
        self.status = {'translate_mode': 'all', 'checking_entity': [], 'checking_level': '1', 'version': '4',
                       'comments': '', 'contributors': [], 'pub_date': datetime.today().strftime('%Y-%m-%d'),
                       'license': 'CC BY-SA', 'checks_performed': [],
                       'source_translations': []}

    def __contains__(self, item):
        return item in self.__dict__

    def to_serializable(self):
        return_val = OrderedDict([
            ('syntax_version', self.syntax_version),
            ('type', self.type),
            ('content_mime_type', self.content_mime_type),
            ('language', self.language),
            ('slug', self.slug),
            ('name', self.name),
            ('versification_slug', self.versification_slug),
            ('status', self.status),
            ('finished_chunks', self.finished_chunks)
        ])

        return return_val


class ResourceManifestEncoder(JSONEncoder):
    def default(self, o):
        """
        :param OBSManifest o:
        :return:
        """
        return o.to_serializable()
