""" Retrieve all articles authored by IoA researchers in the previous month. """

__author__ = 'Andy Casey <andrew.casey@monash.edu>'

SENDER = __author__
RECIPIENT = __author__

# Example usage:    python paperboy.py           (to run previous month)
#                   python paperboy.py 2015 8    (to run for August, 2015)

import os
import sys
from StringIO import StringIO
from time import localtime

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.MIMEBase import MIMEBase
from email import Encoders

import ads
import requests
from PyPDF2 import (PdfFileReader, PdfFileWriter)
requests.packages.urllib3.disable_warnings()


def get_pdf(article, debug=False):
    """
    Download an article PDF from arXiv.

    :param article:
        The ADS article to retrieve.

    :type article:
        :class:`ads.search.Article`

    :returns:
        The binary content of the requested PDF.
    """

    print('Retrieving {0}'.format(article))

    identifier = [_ for _ in article.identifier if 'arXiv' in _]
    if identifier:
        # Increase 13 to 15 in the year 10000 AD
        N = 13
        url = 'http://arXiv.org/pdf/{0}.{1}'.format(identifier[0][N-4:N],
            ''.join(_ for _ in identifier[0][N:] if _.isdigit()))
    else:
        # No arXiv version. Ask ADS to redirect us to the journal article.
        params = {
            'bibcode': article.bibcode,
            'link_type': 'ARTICLE',
            'db_key': 'AST'
        }
        url = requests.get('http://adsabs.harvard.edu/cgi-bin/nph-data_query', 
            params=params).url
    article.__url = url
    q = requests.get(url)
    if not q.ok:
        print('Error retrieving {0}: {1} for {2}'.format(
            article, q.status_code, url))
        if debug: q.raise_for_status()
        else: return None

    # Check if the journal has given back forbidden HTML.
    if q.content.endswith('</html>'):
        print('Error retrieving {0}: 200 (access denied?) for {1}'.format(
            article, url))
        return None
    return q.content


def summarise_pdfs(pdfs, articles):
    """
    Collate the first page from each of the PDFs provided into a single PDF.

    :param pdfs:
        The contents of several PDF files.

    :type pdfs:
        list of str

    :returns:
        The contents of single PDF, which can be written directly to disk.
    """

    summary = PdfFileWriter()
    message = []
    for pdf, article in zip(pdfs, articles):
        if pdf is None:
            message.append("Failed to download article {0} from {1}".format(article, article.__url))
        else:
            try:
                summary.addPage(PdfFileReader(StringIO(pdf)).getPage(0))
            except:
                message.append("Article {0} from {1} appears to be corrupted! Skipping,..".format(article, article.__url))
            

    N_total = len(pdfs)
    N_failed = len(message)
    stacktrace = "" if N_failed == 0 else "\n\t".join(message)

    return (summary, N_total, N_failed, stacktrace)


def email_summary_pdf(recipients, attachments, message):
    """
    Email the summary PDF to the given address.
    """

    if isinstance(recipients, str):
        recipients = [recipients]

    contents = "Attached are the 1-page summary papers for all articles "\
        "published by researchers at the Institute of Astronomy last month."
    contents += "\n\n{0}".format(message)

    message = MIMEMultipart()
    message["From"] = SENDER
    message["To"] = ", ".join(recipients)
    message["Subject"] = "Papers board"
    message.attach(MIMEText(contents))

    # Load the attachment.
    for filename in attachments:
        with open(filename, "r") as fp:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(fp.read())

        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="{}"'\
            .format(os.path.basename(filename)))
        message.attach(part)

    server = smtplib.SMTP("localhost")
    server.sendmail(SENDER, recipients + [__author__], message.as_string())
    code, message = server.quit()

    return (code, message)



if __name__ == '__main__':

    # Use year/month if given, otherwise query the previous month.
    if len(sys.argv) >= 3:
        year, month = map(int, (sys.argv[1:3]))
    else:
        now = localtime()
        year, month = (now.tm_year, now.tm_mon - 1)
        if 1 > month: year, month = (year - 1, 12)

    print('Querying {0} / {1}'.format(year, month))

    # Retrieve all the articles published last month (by post code).
    articles = list(ads.SearchQuery(
        q='(aff:"Monash")'\
          'database:astronomy property:refereed pubdate:{0}-{1}'.format(year, month),
        fl=['id', 'first_author', 'year', 'bibcode', 'identifier'],
        sort='read_count desc'))

    print("Found {0} articles. Downloading PDFs..".format(len(articles)))
    
    # Download all articles from ArXiv.
    pdfs = map(get_pdf, articles)

    # Collate the first page of each PDF into a summary PDF.
    folder = os.path.dirname(__file__)
    basename = '{0:d}-{1:02d}.pdf'.format(year, month)
    summary_pdf_filename = os.path.join(folder, basename)
    with open(summary_pdf_filename, 'wb') as fp:
        contents, N_total, N_failed, stacktrace = summarise_pdfs(pdfs, articles)
        contents.write(fp)

    # Prepare the message and attachments for our email.
    attachments = [summary_pdf_filename]
    message = "I found {0} articles".format(N_total)
    if N_failed == 0:
        message = "I successfully found and downloaded {0} articles.".format(N_total)

    else:
        message = "I found {0} articles, and encountered errors when trying to"\
                  "download {1} of them:\n\n{2}".format(N_total, N_failed, stacktrace)

    """
    # Sometimes authors can get their own affiliation wrong (e.g., post code)
    # so we will search by Madingley, but exclude papers that do match by post.

    # Retrieve all the articles published last month (by street name).
    additional_articles = list(ads.SearchQuery(
        q='(aff:"Madingley" -(aff:"CB3 0HA" or aff:"CB3 OHA")) '\
          'database:astronomy property:refereed pubdate:{0}-{1}'.format(year, month),
        fl=['id', 'first_author', 'year', 'bibcode', 'identifier'],
        sort='read_count desc'))

    if additional_articles:
        print("Found another {0} article(s) by searching for Madingley..".format(
            len(additional_articles)))

        additional_pdfs = map(get_pdf, additional_articles)

        filename = os.path.join(folder, '{0:d}-{1:02d}-madingley.pdf'.format(year, month))
        with open(filename, "wb") as fp:
            contents, N_total, N_failed, stacktrace \
                = summarise_pdfs(additional_pdfs, additional_articles)
            contents.write(fp)

        if N_failed > 0:
            message += "\n\nAnother {0} article(s) were found by searching for "\
                       "'Madingley' ({1} had errors, see below).\n\n{2}".format(
                            N_total, N_failed, stacktrace)
        else:
            message += "\n\nAnother {0} article(s) were found by searching for "\
                       "'Madingley' (none had errors).".format(N_total)

        attachments.append(filename)

    else:
        message += "\n\nNo additional articles were found by searching for "\
                   "'Madingley'."
    """

    # Print information.
    message += "\n\n\nComplaints, comments, and suggestions on how to improve "\
               "this script can be sent to {0}".format(__author__)

    print(message)

    # Email the summary PDF.
    email_summary_pdf([RECIPIENT], attachments, message)
    
