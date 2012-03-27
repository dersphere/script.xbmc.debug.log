import os
import re
import sys
import urllib
import urllib2
import xbmc
import xbmcaddon
import xbmcgui

ADDON_ID = 'script.xbmc_log_uploader'
Addon = xbmcaddon.Addon(id=ADDON_ID)
ADDON_TITLE = Addon.getAddonInfo('name')

DEBUG = True


class LogUploader(object):

    STR_DO_UPLOAD = 30000
    STR_UPLOADED_ID = 30001
    STR_UPLOADED_URL = 30002
    STR_UPLOAD_LINK = 'http://xbmclogs.com/show.php?id=%s'

    def __init__(self):
        self.__log('started')
        self.first_run()
        self.get_settings()
        found_logs = self.__get_logs()
        uploaded_logs = []
        for logfile in found_logs:
            if self.ask_upload(logfile['title']):
                paste_id = self.upload_file(logfile['path'])
                if paste_id:
                    uploaded_logs.append({'paste_id': paste_id,
                                          'title': logfile['title']})
                    self.report_msg(paste_id)
        if uploaded_logs and self.email_address:
            self.report_mail(self.email_address, uploaded_logs)
            pass

    def get_settings(self):
        self.email_address = Addon.getSetting('email')
        self.__log('settings: email address=%s' % self.email_address)
        self.skip_oldlog = Addon.getSetting('skip_oldlog') == 'true'
        self.__log('settings: skip_oldlog=%s' % self.skip_oldlog)

    def first_run(self):
        if not Addon.getSetting('already_shown') == 'true':
            Addon.openSettings()
            Addon.setSetting('already_shown', 'true')

    def upload_file(self, filepath):
        url = 'http://xbmclogs.com/'
        self.__log('reading log...')
        file_content = open(filepath, 'r').readlines()
        self.__log('starting upload "%s"...' % filepath)
        post_dict = {'paste_data': file_content,
                     'api_submit': True,
                     'mode': 'xml'}
        if filepath.endswith('.log'):
            post_dict['paste_lang'] = 'xbmc'
        elif filepath.endswith('.xml'):
            post_dict['paste_lang'] = 'advancedsettings'
        post_data = urllib.urlencode(post_dict)
        req = urllib2.Request(url, post_data)
        response = urllib2.urlopen(req).read()
        if DEBUG:
            print response
        self.__log('upload done.')
        r_id = re.compile('<id>([0-9]+)</id>', re.DOTALL)
        m_id = re.search(r_id, response)
        paste_id = None
        if m_id:
            paste_id = m_id.group(1)
        self.__log('paste_id=%s' % paste_id)
        return paste_id

    def ask_upload(self, logfile):
        Dialog = xbmcgui.Dialog()
        msg = Addon.getLocalizedString(self.STR_DO_UPLOAD) % logfile
        return Dialog.yesno(ADDON_TITLE, msg)

    def report_msg(self, paste_id):
        url = self.STR_UPLOAD_LINK % paste_id
        Dialog = xbmcgui.Dialog()
        msg1 = Addon.getLocalizedString(self.STR_UPLOADED_ID) % paste_id
        msg2 = Addon.getLocalizedString(self.STR_UPLOADED_URL) % url
        return Dialog.ok(ADDON_TITLE, msg1, msg2)

    def report_mail(self, mail_address, uploaded_logs):
        url = 'http://xbmclogs.com/xbmc-addon.php'
        if not mail_address:
            raise Exception('No Email set!')
        post_dict = {'email': mail_address}
        for logfile in uploaded_logs:
            if logfile['title'] == 'xbmc.log':
                post_dict['xbmclog_id'] = logfile['paste_id']
            elif logfile['title'] == 'xbmc.old.log':
                post_dict['oldlog_id'] = logfile['paste_id']
            elif logfile['title'] == 'crash.log':
                post_dict['chrashlog_id'] = logfile['paste_id']
        post_data = urllib.urlencode(post_dict)
        if DEBUG:
            print post_data
        req = urllib2.Request(url, post_data)
        response = urllib2.urlopen(req).read()
        if DEBUG:
            print response


    def __get_logs(self):
        if sys.platform == 'darwin':
            if os.path.join(os.path.exists(os.path.expanduser('~'), 'Library', 'Logs', 'xbmc.log')):
                # we are on OSX or ATV1
                platform = 'OSX'
                log_path = os.path.join(os.path.expanduser('~'), 'Library', 'Logs')
            else:
                # we are on IOS
                platform = 'IOS'
                log_path = '/var/mobile/Library/Preferences'
            crashlog_path = os.path.join(os.path.expanduser('~'), 'Library', 'Logs', 'CrashReporter')
            crashfile_prefix = 'XBMC'
        elif sys.platform.startswith('linux'):
            # we are on Linux
            platform = 'Linux'
            log_path = xbmc.translatePath('special://home/temp')
            crashlog_path = os.path.expanduser('~')
            crashfile_prefix = 'xbmc_crashlog'
        elif sys.platform.startswith('win'):
            # we are on Windows
            platform = 'Win'
            log_path = xbmc.translatePath('special://home')
            crashlog_path = ''
            crashfile_prefix = ''
        else:
            # we are on an unknown OS and need to fix that here
            raise Exception('UNHANDLED OS')
        # get filename and path for xbmc.log and xbmc.old.log
        log = os.path.join(log_path, 'xbmc.log')
        log_old = os.path.join(log_path, 'xbmc.old.log')
        # check for XBMC crashlogs
        log_crash = None
        if crashlog_path and crashfile_prefix:
            crashlog_files = [s for s in os.listdir(crashlog_path)
                              if os.path.isfile(os.path.join(crashlog_path, s))
                              and s.startswith(crashfile_prefix)]
            if crashlog_files:
                # we have crashlogs, use the last one by time
                crashlog_files.sort(key=lambda s: os.path.getmtime(os.path.join(crashlog_path, s)))
                log_crash = os.path.join(crashlog_path, crashlog_files[-1])
        found_logs = []
        if log and os.path.isfile(log):
            found_logs.append({'title': 'xbmc.log',
                               'path': log})
        if not self.skip_oldlog and log_old and os.path.isfile(log_old):
            found_logs.append({'title': 'xbmc.old.log',
                               'path': log_old})
        if log_crash and os.path.isfile(log_crash):
            found_logs.append({'title': 'crash.log',
                               'path': log_crash})
        return found_logs
        
    def __log(self, msg):
        xbmc.log('%s: %s' % (ADDON_TITLE, msg))


if (__name__ == '__main__'):
    Uploader = LogUploader()
