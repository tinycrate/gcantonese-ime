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
from input_methods.gcantonese.sqlitedict import SqliteDict

class GWordRetrievalService():
    def __init__(self):
        folder = os.path.join(os.getenv('APPDATA'), 'gcantonese')
        if not os.path.exists(folder):
            os.makedirs(folder)
        self.cache = SqliteDict(os.path.join(folder, "cache.sqlite"), autocommit=True)
    def close(self):
        self.cache.close()
    
