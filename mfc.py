import warnings
warnings.filterwarnings('ignore', '.*hashlib.*',
                        DeprecationWarning)

import gdata.docs.service
import gdata.spreadsheet.service
import keychain, paramiko, sys
from getpass import getpass

GMAIL  = 'nriley' + '@gmail.com'
HOST   = 'ainaz.pair.com'
USER   = 'nriley'
PATH   = 'web/temp/flashcards/'

google_password, keychain_item = \
    keychain.FindInternetPassword(serverName='google.com',
                                  accountName=GMAIL)
if not google_password:
    google_password = getpass('Password for Google Account %s: ' % GMAIL)
    keychain_item = None

print >> sys.stderr, 'Connecting to Google'
gd = gdata.docs.service.DocsService()
gd.ClientLogin(GMAIL, google_password)

spreadsheets = gdata.spreadsheet.service.SpreadsheetsService()
spreadsheets.email = GMAIL
spreadsheets.password = google_password
spreadsheets.ProgrammaticLogin()

if google_password and not keychain_item:
    keychain.AddInternetPassword(serverName='google.com',
                                 accountName=GMAIL, password=google_password)

def sheet_as_text(docID):
    # strip 'spreadsheet:' from docID to produce key
    key = docID.split(':', 1)[-1]
    return spreadsheets.Get('https://spreadsheets.google.com/feeds/download/spreadsheets/Export?key=%s&exportFormat=tsv' % key,
                         converter=lambda x: x)

if __name__ == '__main__':
    query = gdata.docs.service.DocumentQuery()
    query.AddNamedFolder(GMAIL, 'Flash cards')
    docs = gd.Query(query.ToUri())

    num_docs = len(docs.entry)

    ssh_password, keychain_item = \
        keychain.FindInternetPassword(serverName=HOST, accountName=USER)
    if not ssh_password:
        ssh_password = getpass('Password for SSH account %s on %s: ' % (USER, HOST))
        keychain_item = None

    print >> sys.stderr, 'Connecting to', HOST
    transport = paramiko.Transport((HOST, 22))
    transport.connect(username=USER, password=ssh_password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    if ssh_password and not keychain_item:
        keychain.AddInternetPassword(serverName=HOST, accountName=USER,
                                     password=ssh_password)

    for idx, doc in enumerate(docs.entry):
        print >> sys.stderr, 'PROGRESS:%d' % (idx * 100. / num_docs)
        if doc.GetDocumentType() != 'spreadsheet':
            continue
        docID = doc.resourceId.text
        title = doc.title.text
        print >> sys.stderr, 'Uploading:', title
        header_row, sheet = sheet_as_text(docID).split('\n', 1)
        if 'Text 1' in header_row: # new format; retain header row
            sheet = '\n'.join((header_row, sheet))
        path = '%s/%s.txt' % (PATH, title)
        sftp.open(path, 'w').write(sheet)
        sftp.chmod(path, 0644)

    sftp.close()
    print >> sys.stderr, 'PROGRESS:100'

    transport.close()
