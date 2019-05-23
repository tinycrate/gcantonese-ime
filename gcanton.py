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
from input_methods.gcantonese.gretrieve import GWordRetrievalService
import concurrent.futures
import os.path
import time

class GCommit:
    def __init__(self, selected_suggestion, matched_string):
        self.selected_suggestion = selected_suggestion # Selected GSuggestion
        self.matched_string = matched_string

class GCantoneseTextService(TextService):
    def __init__(self, client):
        TextService.__init__(self, client)
        self.icon_dir = os.path.abspath(os.path.dirname(__file__))
        self.retriever = None
        self.commiting = []
        self.composition_buffer = ""
        self.selected_page = None

    def onActivate(self):
        TextService.onActivate(self)
        icon_name = "eng.ico"
        # Windows 8 以上已取消語言列功能，改用 systray IME mode icon
        if self.client.isWindows8Above:
            self.addButton("windows-mode-icon",
                icon=os.path.join(self.icon_dir, icon_name),
                tooltip="Google 粵語輸入法"
            )
        if self.retriever == None:
            self.retriever = GWordRetrievalService()

    def onDeactivate(self):
        TextService.onDeactivate(self)
        if self.client.isWindows8Above:
            self.removeButton("windows-mode-icon")
        if self.retriever != None:
            self.retriever.close()
            self.retriever = None

    def filterKeyDown(self, keyEvent):
        if not self.isComposing():
            if keyEvent.keyCode >= ord('A') and keyEvent.keyCode <= ord('Z') and not keyEvent.isKeyDown(VK_CONTROL):
                return True
            else:
                return False
        return True

    def update_composition(self):
        composition = ""
        for commit in self.commiting:
            composition += commit.selected_suggestion.word
        composition += self.composition_buffer
        self.setCompositionString(composition)
        self.setShowCandidates(False)

    def commit_composition(self):
        self.update_composition()
        self.setCommitString(self.compositionString)
        self.clear_composition()

    def clear_composition(self):
        self.setShowCandidates(False)
        self.setCompositionString("")
        self.commiting.clear()
        self.composition_buffer = ""

    def on_candidate_select(self, index):
        if self.selected_page == None:
            return
        index = max(min(index, len(self.selected_page.suggestions) - 1), 0)
        selected = self.selected_page.suggestions[index]
        matched_string = self.composition_buffer[:selected.matched_length]
        self.composition_buffer = self.composition_buffer[selected.matched_length:]
        self.commiting.append(GCommit(selected, matched_string))
        self.update_composition()
        if len(self.composition_buffer) == 0:
            self.commit_composition()

    def update_page(self):
        if self.selected_page == None:
            return
        cursor = max(min(self.candidateCursor, len(self.selected_page.suggestions) - 1), 0)
        self.setCandidateCursor(cursor)
        words = list(map(lambda x: x.word, self.selected_page.suggestions))
        self.setCandidateList(words)
        
    def onKeyDown(self, keyEvent):
        if self.retriever == None:
            print("Error: retriever not ready!!")
        if keyEvent.keyCode != VK_CONTROL and keyEvent.isKeyDown(VK_CONTROL):
            self.composition_buffer = ""
            self.commit_composition()
            return True
        if keyEvent.keyCode == VK_ESCAPE:
            self.clear_composition()
            return True
        if keyEvent.keyCode == VK_RETURN:
            self.commit_composition()
            return True
        if keyEvent.keyCode >= ord('1') and keyEvent.keyCode <= ord('9'):
            index = keyEvent.keyCode - ord('1')
            if self.selected_page != None and \
               self.showCandidates and \
               index < len(self.selected_page.suggestions):
                self.on_candidate_select(index)
            return True
        if keyEvent.keyCode == VK_BACK:
            if len(self.composition_buffer) > 0:
                self.composition_buffer = self.composition_buffer[:-1]
            elif len(self.commiting) > 0:
                last_commit = self.commiting.pop()
                self.composition_buffer = last_commit.matched_string
            self.update_composition()
            return True
        if keyEvent.keyCode == VK_SPACE:
            if self.selected_page != None and self.showCandidates:
                self.on_candidate_select(self.candidateCursor)
                return True
            if len(self.composition_buffer) > 0:
                for i in range(1,100):
                    page = self.retriever.get_page(self.composition_buffer, 0)
                    if page != None:
                        break
                    time.sleep(0.001)
                if page != None:
                    self.setCandidateCursor(0)
                    self.selected_page = page
                    self.update_page()
                    self.setShowCandidates(True)
                else:
                    print("[{}]: Page not ready!".format(self.compositionString))
                return True
            self.commit_composition()
            return True
        if keyEvent.keyCode >= ord('A') and keyEvent.keyCode <= ord('Z'):
            caps = False
            if keyEvent.isKeyDown(VK_SHIFT):
                caps = not caps
            if keyEvent.isKeyToggled(VK_CAPITAL):
                caps = not caps
            self.composition_buffer = self.composition_buffer + \
                                      chr(keyEvent.keyCode+(0 if caps else 32))
            self.retriever.register_input(self.compositionString)
            self.update_composition()
            return True
        return True

    # 鍵盤開啟/關閉時會被呼叫 (在 Windows 10 Ctrl+Space 時)
    def onKeyboardStatusChanged(self, opened):
        # Windows 8 systray IME mode icon
        if self.client.isWindows8Above:
            # 若鍵盤關閉，我們需要把 widnows 8 mode icon 設定為 disabled
            self.changeButton("windows-mode-icon", enable=opened)
