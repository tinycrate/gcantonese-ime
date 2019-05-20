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

from keycodes import * # for VK_XXX constants
from textService import *
import concurrent.futures
import os.path
import time

class GCantoneseTextService(TextService):
    def __init__(self, client):
        TextService.__init__(self, client)
        self.icon_dir = os.path.abspath(os.path.dirname(__file__))

    def onActivate(self):
        TextService.onActivate(self)   
        icon_name = "eng.ico"
        # Windows 8 以上已取消語言列功能，改用 systray IME mode icon
        if self.client.isWindows8Above:
            self.addButton("windows-mode-icon",
                icon=os.path.join(self.icon_dir, icon_name),
                tooltip="Google 粵語輸入法"
            )

    def onDeactivate(self):
        TextService.onDeactivate(self)
        if self.client.isWindows8Above:
            self.removeButton("windows-mode-icon")

    def filterKeyDown(self, keyEvent):
        if not self.isComposing():
            if keyEvent.keyCode >= ord('A') and keyEvent.keyCode <= ord('Z') and not keyEvent.isKeyDown(VK_CONTROL):
                return True
            else:
                return False
        return True     
        
    def onKeyDown(self, keyEvent):
        if keyEvent.keyCode != VK_CONTROL and keyEvent.isKeyDown(VK_CONTROL):
            self.setCompositionString("")
            return True
        if keyEvent.keyCode == VK_ESCAPE:
            self.setCompositionString("")
            return True
        if keyEvent.keyCode == VK_BACK:
            self.setCompositionString(self.compositionString[:-1])
            return True
        if keyEvent.keyCode == VK_SPACE:
            commit = self.compositionString + ' '
            self.setCompositionString("")
            self.setCommitString(commit)
        if keyEvent.keyCode >= ord('A') and keyEvent.keyCode <= ord('Z'):
            self.setCompositionString(self.compositionString + chr(keyEvent.keyCode+32))
            return True
        return True
            
    # 鍵盤開啟/關閉時會被呼叫 (在 Windows 10 Ctrl+Space 時)
    def onKeyboardStatusChanged(self, opened):
        # Windows 8 systray IME mode icon
        if self.client.isWindows8Above:
            # 若鍵盤關閉，我們需要把 widnows 8 mode icon 設定為 disabled
            self.changeButton("windows-mode-icon", enable=opened)
        # FIXME: 是否需要同時 disable 其他語言列按鈕？