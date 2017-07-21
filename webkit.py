#!/usr/bin/env python

import os
import sys
import urllib

from PyQt5.QtCore import QUrl, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QStackedLayout
from PyQt5.QtNetwork import QTcpServer, QHostAddress
from PyQt5.QtWebKitWidgets import QWebView

app = QApplication(sys.argv)


class Site(QWebView):
    def __init__(self, parent, url, time, zoom=1):
        super(Site, self).__init__(parent)
        parent.layout.addWidget(self)

        self.page().networkAccessManager().sslErrors.connect(self.on_ssl_errors)
        
        self.url = url
        self.time = time
        self.zoom = zoom

        self.hide()
        self.load(url)
        self.setZoomFactor(zoom)

    def set_zoom(self, zoom):
        self.zoom = zoom
        self.setZoomFactor(zoom)

    @pyqtSlot()
    def on_ssl_errors(self, reply, errors):
        reply.ignoreSslErrors()


class Command(object):
    commands = dict()

    def __init__(self, name):
        self.name = name

    def __call__(self, f):
        def wrapped_f(self, *args):
            f(self, *args)
        Command.commands[self.name] = wrapped_f
        return wrapped_f


class RemoteShell(QTcpServer):
    commands = dict()

    def __init__(self, browser):
        super(RemoteShell, self).__init__(browser)
        self.browser = browser

        self.socket = False
        self.newConnection.connect(self._on_connection)
        self.listen(QHostAddress.Any, 4242)

    def print_message(self, text):
        self.socket.write(text + '\n')

    def print_commands(self):
        self.print_message('avaible commands:')
        for command in Command.commands.keys():
            self.print_message('  ' + command)

    @Command('help')
    def help(self, args):
        self.print_message('>> help')
        self.print_commands()

    @Command('refresh')
    def refresh(self, args):
        self.print_message('>> refresh ' + self.url.toString().encode())
        self.current_page.reload()

    @Command('add')
    def add(self, args):
        self.print_message('>> add ' + args[1] + ' ' + args[2] + ' ' + args[3])
        self.browser.sites.append(Site(self, QUrl(args[1]), int(args[2], int(args[3]))))

    @Command('delete')
    def delete(self, args):
        self.print_message('>> del ' + args[1])
        self.browser.sites.pop(int(args[1]))

    @Command('ls')
    def ls(self, args):
        self.print_message('>> list')
        self.print_message('current list:')
        i = 0
        for site in self.browser.sites:
            self.print_message('%1c[%1d] %2ds : %3s' % (
                (site == browser.current_site) and '*' or ' ', i, site.time, site.url.toString().encode()))
            i += 1

    @Command('zoom')
    def zoom(self, args):
        self.print_message('>> zoom ' + args[1])
        self.browser.current_site.set_zoom(float(args[1]))

    @Command('fullscreen')
    def fullscreen(self, args):
        self.print_message('>> fullscreen ' + args[1])
        if args[1] == '1':
            self.browser.showFullScreen()
        else:
            self.browser.showNormal()

    @Command('exit')
    def exit(self, args):
        self.print_message('>> exit')
        self.socket.close()

    @Command('next')
    def next(self, args):
        self.browser.show_next()
        self.print_message('>> next ' + self.browser.current_site.url.toString().encode())

    @Command('restart')
    def restart(self, args):
        self.print_message('>> restart')
        self.browser.close()

    @Command('upgrade')
    def upgrade(self, args):
        self.print_message('>> upgrade')
        update = urllib.urlopen('https://raw.github.com/pol51/monitoring_browser/master/webkit.py').read()
        script = file('webkit.py', 'w')
        script.write(update)
        script.close()
        self.close()

    @pyqtSlot()
    def _on_connection(self):
        self.socket = self.nextPendingConnection()
        self.socket.write(self.browser.hostname + ' % ')
        self.socket.readyRead.connect(self._on_data_received)

    @pyqtSlot()
    def _on_data_received(self):
        data = self.socket.readAll().data().strip()
        try:
            args = data.split(' ')
            map(lambda x: x.strip(), args)
            Command.commands[args[0]](self, args)
        except Exception as e:
            print(e)
            self.print_message('>> syntax error')
            self.print_commands()
        if self.socket.isOpen():
            self.socket.write(self.browser.hostname + ' % ')


class Browser(QWidget):
    def __init__(self):
        super(Browser, self).__init__()

        self.layout = QStackedLayout(self)
        self.layout.setStackingMode(QStackedLayout.StackAll)

        self.hostname = os.uname()[1]

        self.timer = QTimer()
        self.timer.setSingleShot(False)
        self.timer.start(2000)

        self._init_sites()

        self.remote_shell = RemoteShell(self)

        self.timer.timeout.connect(self.show_next)
        self.show_next()

    def _init_sites(self):
        self.sites = list()
        self.site_id = -1

        url = QUrl("https://www.qt.io/developers/")
        self.sites.append(Site(self, url, 5, 1))

        url = QUrl("https://www.riverbankcomputing.com/software/pyqt/intro")
        self.sites.append(Site(self, url, 5, 1))

        url = QUrl("https://www.python.org/")
        self.sites.append(Site(self, url, 5, 1))

    @property
    def current_site(self):
        return self.sites[self.site_id]

    @pyqtSlot()
    def show_next(self):
        self.timer.stop()
        previous_id = self.site_id
        self.site_id = (self.site_id + 1) % len(self.sites)
        current_site = self.current_site
        self.timer.start(current_site.time * 1000)
        current_site.show()
        print('show ' + current_site.url.toString())
        if previous_id >= 0:
            self.sites[previous_id].hide()

# main
browser = Browser()
browser.showFullScreen()

sys.exit(app.exec_())
