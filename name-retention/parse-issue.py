from urllib.request import urlopen
import urllib.error
import argparse
import re
import json
import string
from pprint import pp
from textwrap import dedent

from textual.app import App
from textual.widgets import Header, Footer, OptionList, TextArea, Button
from textual import on
import pyperclip

# Useful links:
# - https://github.com/pypi/support/tree/main/name-retention
# - https://github.com/pypi/support/projects/1
# - https://github.com/pypi/support/issues?q=is%3Aissue+is%3Aopen+label%3A%22PEP+541%22

CYAN = '\033[36m'
INTENSE = '\033[1m'
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
RESET = '\033[m'

parser = argparse.ArgumentParser(
    description='Extracts info from PEP-541 issues and formats templates',
)

parser.add_argument('issue_number', type=int)

args = parser.parse_args()

SUPPORT_ISSUE_URL = f'https://api.github.com/repos/pypi/support/issues/{args.issue_number}'
with urlopen(SUPPORT_ISSUE_URL) as page:
    info = json.load(page)
    request_text = info['body']

if match := re.search(r'`(.+)`:\s*https://pypi.org/project/\1', request_text, re.I):
    PROJECT = match[1]
if match := re.search(r'`PROJECT_NAME`:\s*https://pypi.org/project/([^ \n]+)/?', request_text):
    PROJECT = match[1]
elif match := re.search(r'`PROJECT_NAME`:\s*([-_a-zA-Z0-9]+)', request_text):
    PROJECT = match[1]

if match := re.search(r'`(.+)`:\s*https://pypi.org/user/\1', request_text, re.I):
    CANDIDATE = match[1]
if match := re.search(r'`USER_NAME`:\s*https://pypi.org/user/([^ \n]+)/?', request_text):
    CANDIDATE = match[1]
elif match := re.search(r'`USER_NAME`:\s*([-_a-zA-Z0-9]+)', request_text):
    CANDIDATE = match[1]

pypi_api_data = {}
pypi_api_info = {}
if 'PROJECT' in globals():
    PROJECT = PROJECT.strip()
    if not re.fullmatch('[a-zA-Z0-9_.-]+', PROJECT):
        raise ValueError(PROJECT)
    PYPI_URL = f'https://pypi.org/project/{PROJECT}/'
    try:
        with urlopen(f'https://pypi.org/pypi/{PROJECT}/json') as page:
            pypi_api_data = json.load(page)
            pypi_api_info = pypi_api_data.get('info', {})
    except urllib.error.HTTPError:
        pass
    PROJECT_AUTHOR_ADDRESS = pypi_api_info.get('author_email')

templates = {}
with open('README.md') as readme_file:
    for line in readme_file:
        if line.startswith('#'):
            current_section = line.strip()
            assert current_section not in templates
            templates[current_section] = []
        else:
            templates[current_section].append(line)
identifiers = set()
for section, lines in templates.items():
    templates[section] = string.Template(dedent(''.join(lines)))
    identifiers.update(templates[section].get_identifiers())

class Replacements:
    def __getitem__(self, name):
        if name.isupper() and (value := globals().get(name)):
            return f'{GREEN}{value}{RESET}'
        return f'{RED}{INTENSE}{name}{RESET}'

for section, template in templates.items():
    print(f'{CYAN}{section}{RESET}')
    content = template.safe_substitute(Replacements())
    content = re.sub('([{|}])', fr'{RED}{INTENSE}\1{RESET}', content)
    print(content)


try:
    url = f'https://pypistats.org/api/packages/{PROJECT}/recent'
except NameError:
    pass
else:
    print(f'{CYAN}{url}{RESET}')
    try:
        page = urlopen(url)
    except urllib.error.HTTPError as e:
        print(repr(e))
    else:
        with page:
            stats = json.load(page)
        pp(stats)

print('Home page:', pypi_api_info.get('home_page'))
try:
    last_upload_time = max(upload['upload_time_iso_8601']
                           for release in pypi_api_data['releases'].values()
                           for upload in release)
    print('Last upload:', last_upload_time)
except (IndexError, ValueError):
    pass


class SupportApp(App):
    def compose(self):
        yield Header()
        yield OptionList(*templates)
        yield Button("copy", id="copy")
        yield TextArea("foo bar", id='text')
        yield Footer()

    @on(OptionList.OptionHighlighted)
    @on(OptionList.OptionSelected)
    def selected(self, msg):
        template = templates[msg.option.prompt]
        content = template.safe_substitute(Replacements())
        content = re.sub('([{|}])', fr'{RED}{INTENSE}\1{RESET}', content)
        self.query_one("#text", TextArea).text = content

    @on(Button.Pressed)
    def clicked(self, msg):
        content = self.query_one("#text", TextArea).text
        pyperclip.copy(content)

if __name__ == "__main__":
    app = SupportApp()
    app.run()

# TODO Add to process diagram:
#
# https://github.com/pypi/support/issues/2554

# TODO: invalid project -- Initial Response -- no more details.
