import os
import re
import urllib
import urllib2
from xbmc import getCondVisibility as condtition, translatePath as translate
import xbmcaddon
import xbmcgui

addon = xbmcaddon.Addon(id='script.xbmc.debug.log')

ADDON_TITLE = addon.getAddonInfo('name')
ADDON_VERSION = addon.getAddonInfo('version')
UPLOAD_LINK = 'http://xbmclogs.com/show.php?id=%s'
UPLOAD_URL = 'http://xbmclogs.com/'

STRINGS = {
    'upload_id': 30001,
    'upload_url': 30002,
    'no_email_set': 30003,
    'you_would_get_an_email': 30005,
    'with_a_link_to_your': 30006,
    'uploaded_xbmc_logfile': 30007,
    'dont_want': 30008,
    'open_settings': 30009,
    'you_would_get_an_email': 30010,
    'with_a_link_to_your': 30011,
    'uploaded_xbmc_logfile': 30012,
    'dont_want': 30013,
    'open_settings': 30014,
    'wont_get_mail': 30015,
    'do_you_want_to_upload': 30016,
    'logfile_to_xbmclogs_com': 30017,
    'will_receive_email_to': 30018,
}

REPLACES = (
    ('//.+?:.+?@', '//USER:PASSWORD@'),
    ('<user>.+?</user>', '<user>USER</user>'),
    ('<pass>.+?</pass>', '<pass>PASSWORD</pass>'),
)


class NetworkError(Exception):
    pass


def get_email_address():
    if addon.getSetting('dont_ask_email') == 'true':
        log('dont_ask_email enabled')
        return
    email_address = addon.getSetting('email')
    while not email_address:
        try_again = xbmcgui.Dialog().yesno(
            heading=_('no_email_set'),
            line1=_('you_would_get_an_email'),
            line2=_('with_a_link_to_your'),
            line3=_('uploaded_xbmc_logfile'),
            nolabel=_('dont_want'),
            yeslabel=_('open_settings')
        )
        if not try_again:
            return
        addon.openSettings()
        email_address = addon.getSetting('email')
    log('got email address')
    return email_address


def ask_upload(email_address):
    if email_address:
        line3 = _('will_receive_email_to') % email_address
    else:
        line3 = _('wont_get_mail')
    ok = xbmcgui.Dialog().yesno(
        heading=ADDON_TITLE,
        line1=_('do_you_want_to_upload'),
        line2=_('logfile_to_xbmclogs_com'),
        line3=line3,
    )
    return ok


def get_log_content():
    log_path = translate('special://logpath')
    log_file_path = os.path.join(log_path, 'xbmc.log')
    with open(log_file_path, 'r') as f:
        log_content = f.read()
    for pattern, repl in REPLACES:
        log_content = re.sub(pattern, repl, log_content)
    return log_content


def upload_log_content(log_content):
    post_dict = {
        'paste_data': log_content,
        'api_submit': True,
        'mode': 'xml',
        'paste_lang': 'xbmc'
    }
    response = _post_data(UPLOAD_URL, post_dict)
    upload_re = re.compile('<id>([0-9]+)</id>', re.DOTALL)
    match = re.search(upload_re, response)
    if match:
        return match.group(1)
    else:
        log('Upload failed with response: %s' % repr(response))


def report_mail(email_address, paste_id):
    url = 'http://xbmclogs.com/xbmc-addon.php'
    post_dict = {
        'email': email_address,
        'xbmclog_id': paste_id
    }
    response = _post_data(url, post_dict)


def report_dialog(paste_id):
    url = UPLOAD_LINK % paste_id
    Dialog = xbmcgui.Dialog()
    msg1 = _('upload_id') % paste_id
    msg2 = _('upload_url') % url
    return Dialog.ok(ADDON_TITLE, msg1, '', msg2)


def _post_data(url, post_dict):
    headers = {'User-Agent': '%s-%s' % (ADDON_TITLE, ADDON_VERSION)}
    post_data = urllib.urlencode(post_dict)
    req = urllib2.Request(url, post_data, headers)
    try:
        response = urllib2.urlopen(req).read()
    except urllib2.HTTPError, error:
        raise NetworkError('HTTPError: %s' % error)
    return response


def log(msg):
    xbmc.log(u'%s: %s' % (ADDON_TITLE, msg))


def _(string_id):
    if string_id in STRINGS:
        return addon.getLocalizedString(STRINGS[string_id])
    else:
        log('String is missing: %s' % string_id)
        return string_id


def main():
    email_address = get_email_address()
    if not ask_upload(email_address):
        log('aborted, user doesn\'t want')
        return
    log_content = get_log_content()
    paste_id = upload_log_content(log_content)
    if email_address:
        report_mail(email_address, paste_id)
    report_dialog(paste_id)


if __name__ == '__main__':
    main()
