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

import json
import zlib
import time
import sqlite3
import threading
from input_methods.gcantonese.gtypes import *

class GCacheService:
    def __init__(self, cache_path):
        self.threadlock = threading.Lock()
        self.cache_path = cache_path
        self.prepare_db()

    def prepare_db(self):
        # Creates the table if not already existing, called on init
        # Validations / version checking should be done here in the future
        with sqlite3.connect(self.cache_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request TEXT NOT NULL UNIQUE,
                    suggestions BLOB NOT NULL,
                    cached_pages INTEGER NOT NULL,
                    max_pages INTEGER NOT NULL,
                    requested_time REAL NOT NULL,
                    last_retrieved REAL NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS request_idx ON requests(request);
            """)
            conn.commit()

    def is_request_in_cache(self, query):
        with self.threadlock:
            with sqlite3.connect(self.cache_path) as conn:
                cur = conn.execute("SELECT 1 FROM requests WHERE request = ?;", (query,))
                return cur.fetchone() != None

    def put(self, grequest):
        with self.threadlock:
            with sqlite3.connect(self.cache_path) as conn:
                suggestions = list(map(lambda x: (x.word, x.annotation, x.matched_length),
                                   grequest.suggestions))
                conn.execute("""
                    INSERT OR REPLACE INTO requests(request, suggestions, cached_pages,
                                                    max_pages, requested_time, last_retrieved)
                    VALUES(?,?,?,?,?,?)
                """, (
                        grequest.request,
                        sqlite3.Binary(
                            zlib.compress(json.dumps(
                                    suggestions, separators=(',', ':')
                                ).encode('utf-8')
                            )
                        ),
                        grequest.requested_pages,
                        grequest.max_pages,
                        grequest.requested_time,
                        grequest.requested_time
                     )
                )
                conn.commit()

    def get(self, query):
        with self.threadlock:
            with sqlite3.connect(self.cache_path) as conn:
                cur = conn.execute("""
                    SELECT id, suggestions, cached_pages, max_pages, requested_time
                    FROM requests
                    WHERE request = ?;
                """, (query,))
                row = cur.fetchone()
                if row == None:
                    return None
                id = row[0]
                result = GRequest()
                result.request = query
                result.suggestions = list(map(lambda x: GSuggestion(x[0],x[1],x[2]),
                                          json.loads(zlib.decompress(row[1]).decode('utf-8'))))
                result.requested_pages = row[2]
                result.max_pages = row[3]
                result.requested_time = row[4]
                conn.execute("""
                    UPDATE requests SET last_retrieved = ? WHERE id = ?
                """, (time.time(), id))
                conn.commit()
                return result

    def close(self):
        # Cleans up old entries
        with sqlite3.connect(self.cache_path) as conn:
            current_time = time.time()
            conn.execute("""
                DELETE FROM requests WHERE
                    /* Remove super large requests */
                    length(request) > 50 OR
                    /* Remove entries older than 30 days */
                    last_retrieved < (? - 2592000) OR
                    /* Remove large entries older than 7 days */
                    (length(request) > 20 AND last_retrieved < (? - 604800));
            """, (current_time, current_time))
            conn.commit()