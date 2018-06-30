try:
    import winxpgui as win32gui
except ImportError:
    import win32gui
import win32gui_struct
import urllib.request
import subprocess
import itertools
import win32api
import win32con
import glob
import sys
import re
import os


class SysTrayIcon(object):
    '''TODO'''
    QUIT = 'QUIT'
    SPECIAL_ACTIONS = [QUIT]

    FIRST_ID = 1023

    def __init__(self,
                 icon,
                 hover_text,
                 menu_options,
                 on_quit=None,
                 default_menu_index=None,
                 window_class_name=None, ):

        self.icon = icon
        self.hover_text = hover_text
        self.on_quit = on_quit

        menu_options = menu_options + (('Quit', None, self.QUIT),)
        self._next_action_id = self.FIRST_ID
        self.menu_actions_by_id = set()
        self.menu_options = self._add_ids_to_menu_options(list(menu_options))
        self.menu_actions_by_id = dict(self.menu_actions_by_id)
        del self._next_action_id

        self.default_menu_index = (default_menu_index or 0)
        self.window_class_name = window_class_name or "SysTrayIconPy"

        message_map = {win32gui.RegisterWindowMessage("TaskbarCreated"): self.restart,
                       win32con.WM_DESTROY: self.destroy,
                       win32con.WM_COMMAND: self.command,
                       win32con.WM_USER + 20: self.notify, }
        # Register the Window class.
        window_class = win32gui.WNDCLASS()
        hinst = window_class.hInstance = win32gui.GetModuleHandle(None)
        window_class.lpszClassName = self.window_class_name
        window_class.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW;
        window_class.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        window_class.hbrBackground = win32con.COLOR_WINDOW
        window_class.lpfnWndProc = message_map  # could also specify a wndproc.
        classAtom = win32gui.RegisterClass(window_class)
        # Create the Window.
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = win32gui.CreateWindow(classAtom,
                                          self.window_class_name,
                                          style,
                                          0,
                                          0,
                                          win32con.CW_USEDEFAULT,
                                          win32con.CW_USEDEFAULT,
                                          0,
                                          0,
                                          hinst,
                                          None)
        win32gui.UpdateWindow(self.hwnd)
        self.notify_id = None
        self.refresh_icon()

        win32gui.PumpMessages()

    def _add_ids_to_menu_options(self, menu_options):
        result = []
        for menu_option in menu_options:
            option_text, option_icon, option_action = menu_option
            if callable(option_action) or option_action in self.SPECIAL_ACTIONS:
                self.menu_actions_by_id.add((self._next_action_id, option_action))
                result.append(menu_option + (self._next_action_id,))
            elif non_string_iterable(option_action):
                result.append((option_text,
                               option_icon,
                               self._add_ids_to_menu_options(option_action),
                               self._next_action_id))
            else:
                print('Unknown item', option_text, option_icon, option_action)
            self._next_action_id += 1
        return result

    def refresh_icon(self):
        # Try and find a custom icon
        hinst = win32gui.GetModuleHandle(None)
        if os.path.isfile(self.icon):
            icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
            hicon = win32gui.LoadImage(hinst,
                                       self.icon,
                                       win32con.IMAGE_ICON,
                                       0,
                                       0,
                                       icon_flags)
        else:
            print("Can't find icon file - using default.")
            hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

        if self.notify_id:
            message = win32gui.NIM_MODIFY
        else:
            message = win32gui.NIM_ADD
        self.notify_id = (self.hwnd,
                          0,
                          win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
                          win32con.WM_USER + 20,
                          hicon,
                          self.hover_text)
        win32gui.Shell_NotifyIcon(message, self.notify_id)

    def restart(self, hwnd, msg, wparam, lparam):
        self.refresh_icon()

    def destroy(self, hwnd, msg, wparam, lparam):
        if self.on_quit: self.on_quit(self)
        nid = (self.hwnd, 0)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        win32gui.PostQuitMessage(0)  # Terminate the app.

    def notify(self, hwnd, msg, wparam, lparam):
        if lparam == win32con.WM_LBUTTONDBLCLK:
            self.execute_menu_option(self.default_menu_index + self.FIRST_ID)
        elif lparam == win32con.WM_RBUTTONUP:
            self.show_menu()
        elif lparam == win32con.WM_LBUTTONUP:
            pass
        return True

    def show_menu(self):
        menu = win32gui.CreatePopupMenu()
        self.create_menu(menu, self.menu_options)
        # win32gui.SetMenuDefaultItem(menu, 1000, 0)

        pos = win32gui.GetCursorPos()
        # See http://msdn.microsoft.com/library/default.asp?url=/library/en-us/winui/menus_0hdi.asp
        win32gui.SetForegroundWindow(self.hwnd)
        win32gui.TrackPopupMenu(menu,
                                win32con.TPM_LEFTALIGN,
                                pos[0],
                                pos[1],
                                0,
                                self.hwnd,
                                None)
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)

    def create_menu(self, menu, menu_options):
        for option_text, option_icon, option_action, option_id in menu_options[::-1]:
            if option_icon:
                option_icon = self.prep_menu_icon(option_icon)

            if option_id in self.menu_actions_by_id:
                item, extras = win32gui_struct.PackMENUITEMINFO(text=option_text,
                                                                hbmpItem=option_icon,
                                                                wID=option_id)
                win32gui.InsertMenuItem(menu, 0, 1, item)
            else:
                submenu = win32gui.CreatePopupMenu()
                self.create_menu(submenu, option_action)
                item, extras = win32gui_struct.PackMENUITEMINFO(text=option_text,
                                                                hbmpItem=option_icon,
                                                                hSubMenu=submenu)
                win32gui.InsertMenuItem(menu, 0, 1, item)

    def prep_menu_icon(self, icon):
        # First load the icon.
        ico_x = win32api.GetSystemMetrics(win32con.SM_CXSMICON)
        ico_y = win32api.GetSystemMetrics(win32con.SM_CYSMICON)
        hicon = win32gui.LoadImage(0, icon, win32con.IMAGE_ICON, ico_x, ico_y, win32con.LR_LOADFROMFILE)

        hdcBitmap = win32gui.CreateCompatibleDC(0)
        hdcScreen = win32gui.GetDC(0)
        hbm = win32gui.CreateCompatibleBitmap(hdcScreen, ico_x, ico_y)
        hbmOld = win32gui.SelectObject(hdcBitmap, hbm)
        # Fill the background.
        brush = win32gui.GetSysColorBrush(win32con.COLOR_MENU)
        win32gui.FillRect(hdcBitmap, (0, 0, 16, 16), brush)
        # unclear if brush needs to be feed.  Best clue I can find is:
        # "GetSysColorBrush returns a cached brush instead of allocating a new
        # one." - implies no DeleteObject
        # draw the icon
        win32gui.DrawIconEx(hdcBitmap, 0, 0, hicon, ico_x, ico_y, 0, 0, win32con.DI_NORMAL)
        win32gui.SelectObject(hdcBitmap, hbmOld)
        win32gui.DeleteDC(hdcBitmap)

        return hbm

    def command(self, hwnd, msg, wparam, lparam):
        id = win32gui.LOWORD(wparam)
        self.execute_menu_option(id)

    def execute_menu_option(self, id):
        menu_action = self.menu_actions_by_id[id]
        if menu_action == self.QUIT:
            win32gui.DestroyWindow(self.hwnd)
        else:
            menu_action(self, str(id))


def non_string_iterable(obj):
    try:
        iter(obj)
    except TypeError:
        return False
    else:
        return not isinstance(obj, basestring)

if __name__ == '__main__':
    def resource_path(relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)
    playerController = resource_path("controlPlayer.exe")
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    icons = itertools.cycle(glob.glob(resource_path("main_ico.ico")))
    mute_ico = itertools.cycle(glob.glob(resource_path("mute_ico.ico")))
    hover_text = "Youtube Music Streamer"
    muted = False
    already_streaming = False   # Used to only have one ongoing stream even when changing from one stream to another
    good_urls = []

    try:
        live_urls = open(resource_path("url.config"), "r")
        for i in live_urls:
            if i.startswith('http'):
                good_urls.append(i)
    except:    #In case file does not exist, or no urls are added
        good_urls.append('https://www.youtube.com/watch?v=dyLV6gnu-wg')


    def get_stream_title(url):
        with urllib.request.urlopen(url) as source:
            s = source.read()
            s = s.decode('utf-8')

        result = re.search('<title>(.*)</title>', s)
        full_title = result.group(1).replace(' - YouTube', '').split(' ')
        try:
            if 'radio' not in result.group(1).lower():
                menu_title = full_title[0] + ' ' + full_title[1] + ' ' + full_title[2]
            else:
                menu_title = ''
                for i in full_title:
                    menu_title = menu_title + ' ' + i
                    if 'radio' in i.lower():
                        break
        except:
            menu_title = 'LINK UNAVAILABLE'
        return str(menu_title.strip())


    def live1(sysTrayIcon, linkselect):
        configLocation = resource_path("player.config")
        streamlinkLocation = resource_path(r"streamlink\streamlink.exe")
        global good_urls
        global already_streaming
        if linkselect == 'initial':
            idx = 0
        else:
            idx = int(linkselect) - 1023
        if not already_streaming:
            #subprocess.Popen(['streamlink', '--config', configLocation, good_urls[idx], 'best'], startupinfo=startupinfo)
            subprocess.Popen([streamlinkLocation, '--config', configLocation, good_urls[idx], 'best'], startupinfo=startupinfo)
            already_streaming = True
        else:
            #os.system(r'echo quit >\\.\pipe\mpvyoutubeskt')
            subprocess.Popen([playerController, 'quit'], startupinfo=startupinfo)
            #subprocess.Popen(['streamlink', '--config', configLocation, good_urls[idx], 'best'], startupinfo=startupinfo)
            subprocess.Popen([streamlinkLocation, '--config', configLocation, good_urls[idx], 'best'], startupinfo=startupinfo)


    def mute(sysTrayIcon, button_id):
        global muted
        if not muted:
            sysTrayIcon.icon = next(mute_ico)
            sysTrayIcon.refresh_icon()
            muted = True
        else:
            sysTrayIcon.icon = next(icons)
            sysTrayIcon.refresh_icon()
            muted = False
        #os.system(r'echo cycle mute >\\.\pipe\mpvyoutubeskt')   # TCP Socket declared in streamlink config file
        subprocess.Popen([playerController, 'mute'], startupinfo=startupinfo)


    def volumeup(sysTrayIcon, button_id):
        #os.system(r'echo cycle volume +5 >\\.\pipe\mpvyoutubeskt')
        subprocess.Popen([playerController, 'volUp'], startupinfo=startupinfo)

    def volumedown(sysTrayIcon, button_id):
        #os.system(r'echo cycle volume -5 >\\.\pipe\mpvyoutubeskt')
        subprocess.Popen([playerController, 'volDown'], startupinfo=startupinfo)


    def quit(sysTrayIcon):
        #os.system(r'echo quit >\\.\pipe\mpvyoutubeskt')
        subprocess.Popen([playerController, 'quit'], startupinfo=startupinfo)

    menu_options = []
    for i in good_urls:
        livestream_title = get_stream_title(i)
        menu_options.append((livestream_title, None, live1))
    menu_options.append(('Volume Up', None, volumeup))
    menu_options.append(('Volume Down', None, volumedown))
    menu_options.append(('Mute/Unmute', None, mute))
    menu_options = tuple(menu_options)
    live1(None, 'initial')
    SysTrayIcon(next(icons), hover_text, menu_options, on_quit=quit, default_menu_index=(len(good_urls) + 2))
