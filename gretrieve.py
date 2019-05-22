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
import math
import json
import time
import shutil
import threading
import urllib.request
import urllib.parse
from input_methods.gcantonese.sqlitedict import SqliteDict

PAGE_SIZE = 6
REQUEST_URL = "https://inputtools.google.com/request"
REQUEST_LANG = "yue-hant-t-i0-und"
REQUEST_PAGE_MIN = 2
REQUEST_TRIAL_MAX = 7

class GSuggestion:
    word = ""
    annotation = ""
    matched_length = 0
    def __init__(self, word, annotation, matched_length):
        self.word = word
        self.annotation = annotation
        self.matched_length = matched_length
    
class GRequest:
    request = ""
    suggestions = []
    requested_pages = 0
    max_pages = 32
    requested_time = 0
    
class GPage:
    word = ""
    page_num = 0
    suggestions = []
    def __init__(self, word, page_num, suggestions):
        self.word = word
        self.page_num = page_num
        self.suggestions = suggestions
    
class GWordRetrievalService:
    def __init__(self):
        folder = os.path.join(os.getenv('APPDATA'), 'gcantonese')
        if not os.path.exists(folder):
            os.makedirs(folder)
        self.cache = SqliteDict(os.path.join(folder, "cache.sqlite"), autocommit=True)
        self.requesting = {}
        self.threadlock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=20)
    
    def request(self, input_str, pages):
        with self.threadlock:
            requested_time = time.time()
            requesting_pages = self.requesting.get(input_str, 0)
            if pages <= requesting_pages:
                return
            self.requesting[input_str] = pages
        request_num = PAGE_SIZE * pages
        params = {}
        params['text'] = input_str
        params['itc'] = REQUEST_LANG
        params['num'] = request_num
        params['ie'] = 'utf-8'
        params['oe'] = 'utf-8'
        params_str = urllib.parse.urlencode(params)
        trials = 0
        backoff = 0.1
        while True:
            successful = False
            try:
                response = urllib.request.urlopen(f"{REQUEST_URL}?{params_str}", timeout=1)
                response = json.loads(response.read(), encoding='utf-8')
                if response[0] != "SUCCESS":
                    print(f"[{input_str}, {pages}]:", 
                          f"Google input tools reported an error: {response[0]}")
                else:
                    successful = True
            except (ValueError, urllib.error.URLError) as e:
                print(f"[{input_str}, {pages}]: Word suggestion retrieval error: {e}")
            if not successful:
                if trials >= REQUEST_TRIAL_MAX:
                    print(f"[{input_str}, {pages}]: Retrieval failed after {trials} retries.")
                    return
                print(f"[{input_str}, {pages}]: Retrying in {backoff} seconds...")
                time.sleep(backoff)
                backoff *= 2
                trials += 1
            else:
                break
        word_suggestions = response[1][0][1]
        word_info = response[1][0][3]
        grequest = GRequest()
        grequest.request = input_str
        grequest.suggestions = []
        if len(word_suggestions) <= 0:
            grequest.suggestions = [GSuggestion(input_str, "", len(input_str))]
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
                    matched_length = len(input_str)
                grequest.suggestions.append(GSuggestion(word, annotation, 
                                                        matched_length))
        grequest.requested_time = requested_time
        with self.threadlock:
            if input_str in self.cache:
                if self.cache[input_str].requested_time > grequest.requested_time:
                    return
            self.cache[input_str] = grequest
            self.requesting.pop(input_str, 0)
    
    def register_input(self, input_str):
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
                requesting_pages = max(cached.requested_pages * 2, cached.max_pages)
                self.executor.submit(self.request, input_str, requesting_pages)
            page_num = max(min(page, cached.requested_pages - 1), 0)
            suggestions = cached.suggestions[page_num*PAGE_SIZE:(page_num+1)*PAGE_SIZE]
            page = GPage(input_str, page_num, suggestions)
            return page
        else:
            # Page not ready
            register_input(self, input_str) # Trigger word retrieval just in case
            return None
            
    def close(self):
        self.executor.shutdown(wait=False)
        self.cache.close()
        
