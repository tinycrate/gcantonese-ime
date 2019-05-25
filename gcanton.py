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

COMMAND_TOGGLE_LANGUAGE = 10

class GCommit:
    def __init__(self, selected_suggestion, matched_string):
        self.selected_suggestion = selected_suggestion # Selected GSuggestion
        self.matched_string = matched_string

class GCantoneseTextService(TextService):
    def __init__(self, client):
        TextService.__init__(self, client)
        self.icon_dir = os.path.abspath(os.path.dirname(__file__))
        self.retriever = None
        self.committing = []
        self.composition_buffer = ""
        self.selected_page = None
        self.is_masking = False
        self.chinese_enabled = True

    def onActivate(self):
        TextService.onActivate(self)
        icon_name = "chi.ico"
        if self.client.isWindows8Above:
            self.addButton("windows-mode-icon",
                icon=os.path.join(self.icon_dir, icon_name),
                tooltip="Google 粵語輸入法",
                commandId=COMMAND_TOGGLE_LANGUAGE
            )
            self.update_button_display()
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
        self.last_pressed_key = keyEvent.keyCode
        self.last_pressed_time = time.time()
        if not self.chinese_enabled:
            return False
        # Chinese mode enabled
        if not self.isComposing():
            if keyEvent.keyCode >= ord('A') and keyEvent.keyCode <= ord('Z') and not keyEvent.isKeyDown(VK_CONTROL):
                return True
            else:
                return False
        return True

    def filterKeyUp(self, keyEvent):
        if keyEvent.keyCode == VK_SHIFT and \
           self.last_pressed_key == VK_SHIFT and \
           time.time() - self.last_pressed_time < 0.5:
            return True
        return False

    def onKeyUp(self, keyEvent):
        if keyEvent.keyCode == VK_SHIFT:
            self.toggle_language()

    def onCommand(self, commandId, commandType):
        if commandId == COMMAND_TOGGLE_LANGUAGE:
            self.toggle_language()

    def toggle_language(self):
        if self.isComposing:
                self.commit_composition()
        self.chinese_enabled = not self.chinese_enabled
        self.update_button_display()

    def update_button_display(self):
        icon_name = 'chi.ico' if self.chinese_enabled else 'eng.ico'
        if self.client.isWindows8Above:
            self.changeButton("windows-mode-icon", icon=os.path.join(self.icon_dir, icon_name))

    def update_composition(self):
        composition = ""
        for commit in self.committing:
            composition += commit.selected_suggestion.word
        composition += self.composition_buffer
        self.setCompositionString(composition)
        self.setShowCandidates(False)
        self.is_masking = False

    def commit_composition(self):
        self.setCommitString(self.compositionString)
        self.clear_composition()

    def clear_composition(self):
        self.setShowCandidates(False)
        self.setCompositionString("")
        self.committing.clear()
        self.composition_buffer = ""
        self.is_masking = False

    def mask_composition(self):
        if self.selected_page == None or not self.showCandidates:
            return
        if self.candidateCursor < 0 or \
           self.candidateCursor >= len(self.selected_page.suggestions):
            return
        composition = ""
        for commit in self.committing:
            composition += commit.selected_suggestion.word
        selected = self.selected_page.suggestions[self.candidateCursor]
        composition += selected.word
        leftovers = self.composition_buffer[selected.matched_length:]
        if len(leftovers) > 0:
            self.retriever.register_input("|{},{}".format(composition, leftovers))
            composition += leftovers
        self.setCompositionString(composition)
        self.is_masking = True

    def onCompositionTerminated(self, forced):
        self.commitString = ""
        # Only clears composition when the composition is forcefully terminated
        # This allow seamless continuous typing by allowing characters in
        # composition buffer right after a word is being committed
        if forced:
            self.compositionString = ""
            self.composition_buffer = ""
            self.committing.clear()
            self.is_masking = False

    def on_candidate_select(self, index, select_next_page=False):
        if self.selected_page == None or not self.showCandidates:
            return
        index = max(min(index, len(self.selected_page.suggestions) - 1), 0)
        selected = self.selected_page.suggestions[index]
        matched_string = self.composition_buffer[:selected.matched_length]
        self.composition_buffer = self.composition_buffer[selected.matched_length:]
        self.committing.append(GCommit(selected, matched_string))
        self.update_composition()
        if len(self.composition_buffer) == 0:
            self.commit_composition()
        else:
            self.retriever.register_input(self.get_input_query())
            if select_next_page:
                page = self.try_get_page(self.get_input_query(), 0)
                if page != None:
                    self.selected_page = page
                    self.update_page()
                    self.mask_composition()
                else:
                    print("[{}]: Page not ready!".format(ascii(self.get_input_query())))

    def update_page(self):
        if self.selected_page == None:
            return
        cursor = max(min(self.candidateCursor, len(self.selected_page.suggestions) - 1), 0)
        self.setCandidateCursor(cursor)
        words = list(map(lambda x: x.word, self.selected_page.suggestions))
        self.setCandidateList(words)
        self.setShowCandidates(True)
        self.setCandidateCursor(0)

    # Returns composition buffer if no pending commit
    # Use this to query retriever
    # Otherwise return in such format: "|{committing},{composition_buffer}"
    def get_input_query(self):
        if len(self.committing) == 0:
            return self.composition_buffer
        else:
            committing = "".join(map(lambda x:x.selected_suggestion.word, self.committing))
            return "|{},{}".format(committing, self.composition_buffer)

    def try_get_page(self, query, page_num):
        for i in range(0,200):
            page = self.retriever.get_page(query, page_num)
            if page != None:
                break
            time.sleep(0.001)
        return page

    def try_switch_page(self, page_num):
        # retriever should handle page_num higher than page size
        page_num = max(0, page_num)
        query = self.selected_page.word
        page = self.try_get_page(query, page_num)
        if page != None:
            self.selected_page = page
            self.update_page()
            self.mask_composition()
            return page.page_num
        return -1

    def onKeyDown(self, keyEvent):
        if self.retriever == None:
            print("Error: retriever not ready!!")
        # Ignore Ctrl-C / Ctrl-V interrupts composition
        if keyEvent.keyCode != VK_CONTROL and keyEvent.isKeyDown(VK_CONTROL):
            self.composition_buffer = ""
            self.commit_composition()
            return True
        # ESC cancels composition
        if keyEvent.keyCode == VK_ESCAPE:
            self.clear_composition()
            return True
        # ENTER commits composition including those still in buffer
        if keyEvent.keyCode == VK_RETURN:
            self.commit_composition()
            return True
        # Numeric input selects candidate
        if keyEvent.keyCode >= ord('1') and keyEvent.keyCode <= ord('9') and \
           not keyEvent.isKeyDown(VK_SHIFT):
            index = keyEvent.keyCode - ord('1')
            if self.selected_page != None and \
               self.showCandidates and \
               index < len(self.selected_page.suggestions):
                self.on_candidate_select(index)
            return True
        # Backspace reduces composition_buffer
        if keyEvent.keyCode == VK_BACK:
            if len(self.composition_buffer) > 0:
                if not self.is_masking:
                    self.composition_buffer = self.composition_buffer[:-1]
            elif len(self.committing) > 0:
                last_commit = self.committing.pop()
                self.composition_buffer = last_commit.matched_string
            self.update_composition()
            return True
        # UP/DOWN keys for page switching
        if keyEvent.keyCode == VK_UP or keyEvent.keyCode == VK_DOWN:
            if self.selected_page != None and self.showCandidates:
                offset = -1 if keyEvent.keyCode == VK_UP else 1
                self.try_switch_page(self.selected_page.page_num + offset)
            return True
        # LEFT/RIGHT keys for candidate selecting
        if keyEvent.keyCode == VK_LEFT or keyEvent.keyCode == VK_RIGHT:
            if self.selected_page != None and self.showCandidates:
                offset = -1 if keyEvent.keyCode == VK_LEFT else 1
                cursor = self.candidateCursor + offset
                current_page_num = self.selected_page.page_num
                if cursor < 0 and current_page_num > 0:
                    self.try_switch_page(current_page_num - 1)
                    cursor = len(self.selected_page.suggestions) - 1
                elif cursor >= len(self.selected_page.suggestions):
                    new_page_num = self.try_switch_page(current_page_num + 1)
                    if new_page_num > current_page_num:
                        cursor = 0
                cursor = max(min(cursor, len(self.selected_page.suggestions) - 1), 0)
                self.setCandidateCursor(cursor)
                self.mask_composition()
            return True
        # Space confirms selection
        if keyEvent.keyCode == VK_SPACE:
            if self.selected_page != None and self.showCandidates:
                self.on_candidate_select(self.candidateCursor, select_next_page=True)
                return True
            if len(self.composition_buffer) > 0:
                page = self.try_get_page(self.get_input_query(), 0)
                if page != None:
                    self.selected_page = page
                    self.update_page()
                    self.mask_composition()
                else:
                    print("[{}]: Page not ready!".format(ascii(self.get_input_query())))
                return True
            self.commit_composition()
            return True
        # Key presses from 'A' to 'Z'
        if keyEvent.keyCode >= ord('A') and keyEvent.keyCode <= ord('Z'):
            if self.selected_page != None and \
               self.showCandidates and \
               self.candidateCursor < len(self.selected_page.suggestions):
                # Seamless continuous typing
                self.on_candidate_select(self.candidateCursor)
            # Capital letters handling
            caps = False
            if keyEvent.isKeyDown(VK_SHIFT):
                caps = not caps
            if keyEvent.isKeyToggled(VK_CAPITAL):
                caps = not caps
            self.composition_buffer = self.composition_buffer + \
                                      chr(keyEvent.keyCode+(0 if caps else 32))
            self.retriever.register_input(self.get_input_query())
            self.update_composition()
            return True
        return True

    def onKeyboardStatusChanged(self, opened):
        if self.client.isWindows8Above:
            self.changeButton("windows-mode-icon", enable=opened)
