#! python3
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import os
import re
import math
import json
import time
import shutil
import threading
import urllib.parse
import urllib.request
import concurrent.futures
from input_methods.gcantonese.sqlitedict import SqliteDict
from input_methods.gcantonese.gtypes import *

PAGE_SIZE = 6
REQUEST_URL = "https://inputtools.google.com/request"
REQUEST_LANG = "yue-hant-t-i0-und"
REQUEST_PAGE_MIN = 2
REQUEST_TRIAL_MAX = 7

class GWordRetrievalService:
    def __init__(self):
        folder = os.path.join(os.getenv('APPDATA'), 'gcantonese')
        if not os.path.exists(folder):
            os.makedirs(folder)
        self.cache = SqliteDict(os.path.join(folder, "cache.sqlite"), autocommit=True)
        self.requesting = {}
        self.threadlock = threading.Lock()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=20)

    def request(self, input_str, pages):
        print("[{}, {}]: Request scheduled!".format(ascii(input_str), pages))
        with self.threadlock:
            requested_time = time.time()
            requesting_pages = self.requesting.get(input_str, 0)
            if pages <= requesting_pages:
                print("[{}, {}]: Request dropped for existing request".format(ascii(input_str), pages))
                return
            self.requesting[input_str] = pages
        request_num = PAGE_SIZE * pages
        print("[{}, {}]: Requesting {} items from Google Input!".format(ascii(input_str), pages, request_num))
        params = {}
        params['text'] = input_str
        params['itc'] = REQUEST_LANG
        params['num'] = request_num
        params['ie'] = 'utf-8'
        params['oe'] = 'utf-8'
        params_str = urllib.parse.urlencode(params, encoding='utf-8')
        trials = 0
        backoff = 0.1
        while True:
            print("[{}, {}]: Request trail {}...".format(ascii(input_str), pages, trials))
            successful = False
            try:
                response = urllib.request.urlopen("{}?{}".format(REQUEST_URL, params_str), timeout=1)
                response = json.loads(response.read().decode('utf-8'), encoding='utf-8')
                if response[0] != "SUCCESS":
                    print("[{}, {}]:".format(ascii(input_str), pages),
                          "Google input tools reported an error: {}".format(response[0]))
                else:
                    successful = True
            except (ValueError, urllib.error.URLError) as e:
                print("[{}, {}]: Word suggestion retrieval error: {}".format(ascii(input_str), pages, e))
            if not successful:
                if trials >= REQUEST_TRIAL_MAX:
                    print("[{}, {}]: Retrieval failed after {} retries.".format(ascii(input_str), pages, trials))
                    return
                print("[{}, {}]: Retrying in {backoff} seconds...".format(ascii(input_str), pages))
                time.sleep(backoff)
                backoff *= 2
                trials += 1
            else:
                break
        print("[{}, {}]: Got a response! forging GRequest...".format(ascii(input_str), pages))
        # Extract real input from queries like "|{committing},{real_input}"
        real_input = re.sub(r"^\|.+,", "", input_str)
        word_suggestions = response[1][0][1]
        word_info = response[1][0][3]
        grequest = GRequest()
        grequest.request = input_str
        grequest.suggestions = []
        if len(word_suggestions) <= 0:
            grequest.suggestions = [GSuggestion(real_input, "", len(real_input))]
            grequest.requested_pages = 1
            grequest.max_pages = 1
        else:
            grequest.requested_pages = math.ceil(len(word_suggestions)/PAGE_SIZE)
            if len(word_suggestions) < request_num:
                grequest.max_pages = grequest.requested_pages
            for i, word in enumerate(word_suggestions):
                annotation = word_info['annotation'][i]
                if 'matched_length' in word_info:
                    matched_length = word_info['matched_length'][i]
                else:
                    matched_length = len(real_input)
                grequest.suggestions.append(GSuggestion(word, annotation,
                                                        matched_length))
        grequest.requested_time = requested_time
        print("[{}, {}]: Saving to cache...".format(ascii(input_str), pages))
        with self.threadlock:
            if input_str in self.cache:
                if self.cache[input_str].requested_time > grequest.requested_time:
                    print("[{}, {}]: Skipping save, cache is newer!".format(ascii(input_str), pages))
                    return
            self.cache[input_str] = grequest
            self.requesting.pop(input_str, 0)
        print("[{}, {}]: Request completed!".format(ascii(input_str), pages))

    def register_input(self, input_str):
        if len(input_str) <= 0:
            return
        cached = self.cache.get(input_str, None)
        if cached != None:
            if cached.requested_pages == cached.max_pages or \
               cached.requested_pages >= REQUEST_PAGE_MIN:
                return
        if input_str in self.requesting:
            return
        self.executor.submit(self.request, input_str, REQUEST_PAGE_MIN)

    def get_page(self, input_str, page):
        cached = self.cache.get(input_str, None)
        if cached != None and cached.requested_pages > 0:
            if page >= cached.requested_pages / 2 and \
               cached.requested_pages < cached.max_pages:
                # Request more pages in advance
                requesting_pages = min(cached.requested_pages * 2, cached.max_pages)
                self.executor.submit(self.request, input_str, requesting_pages)
            page_num = max(min(page, cached.requested_pages - 1), 0)
            suggestions = cached.suggestions[page_num*PAGE_SIZE:(page_num+1)*PAGE_SIZE]
            page = GPage(input_str, page_num, suggestions)
            return page
        else:
            # Page not ready
            self.register_input(input_str) # Trigger word retrieval just in case
            return None

    def close(self):
        self.executor.shutdown(wait=False)
        self.cache.close()

