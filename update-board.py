
""" 
Monthly publications board script for the School of Physics & Astronomy, 
Monash University 


This script is expected to be run about once a month.
"""

OUTPUT_PATH_PREFIX = "{here}/{now:%Y-%B}"
LOCAL_RULES_PATH = "{here}/rules.yml"
LOCAL_RECORDS_PATH = "{here}/records.csv"
ADS_QUERY = "aff:\"Monash\""
EXECUTIVE_SUMMARY_ARTICLE_FORMAT = "{count}. {article.title[0]}\n{formatted_authors}, {article.pub}, {formatted_volume}{formatted_issue}{formatted_page} ({formatted_year}).\n\n"

EMAIL_PREFIX = ""
EMAIL_TO = "andrew.casey@monash.edu, andycasey@gmail.com"


def matching_author(author, aff):

    is_dean = lambda au, sa: \
            au == "Nash, J." \
        and sa == "monash university faculty of science clayton australia"

    stripped_affiliations = utils.stripped_affiliations(aff)

    for j, sa in enumerate(stripped_affiliations):
        if ("monash" in sa and "physics" in sa) or is_dean(author, sa):
            return (True, [j, author, aff])

    return (False, [])


def format_author(author, aff):
    is_matching_author, meta = matching_author(author, aff)
    return f"*{author.upper()}*" if is_matching_author else author


def formatted_summary(article, long_author_list=50):

    if len(article.author) > long_author_list:
        skip, total_skip = (0, 0)

        authors = []
        for j, (author, aff) in enumerate(zip(article.author, article.aff)):
            if j < 1:
                authors.append(format_author(author, aff))

            else:
                is_matching_author, meta = matching_author(author, aff)

                if is_matching_author:
                    if skip > 0:
                        authors.append("...")
                        skip = 0
                    authors.append(format_author(author, aff))

                else:
                    skip += 1
                    total_skip += 1

        if skip > 0:
            authors.append("et al.")

        formatted_authors = "; ".join(authors) + f" ({total_skip} authors not shown)"

    else:
        formatted_authors = "; ".join([format_author(auth, aff) for auth, aff in zip(article.author, article.aff)])

    kwds = dict(article=article, formatted_authors=formatted_authors,
                formatted_volume="in press" if article.volume is None else article.volume,
                formatted_issue="" if article.issue is None else f", {article.issue}",
                formatted_page=f", {article.page[0]}" if (article.page is not None and article.page[0] is not None) else "",
                formatted_year=article.pubdate.split("-")[0])

    return kwds


# That's it. We'll take it from here.

import base64
import email.encoders
import numpy as np
import os
import requests
import re
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase

import fitz
from pdfrw import PdfReader, PdfWriter, PdfParseError

import ads
from googleapiclient.discovery import build
from httplib2 import Http
from apiclient import errors
from oauth2client import file, client, tools

import utils


if __name__ != "__main__": 
    sys.exit()

# Be in the here and now.
now = datetime.now()
here = os.path.dirname(os.path.realpath(__file__))

# Load in the records.
local_records_path = LOCAL_RECORDS_PATH.format(here=here)
records = utils.load_records(local_records_path)

# Build the query.
if len(sys.argv) >= 3:
    year, month = map(int, (sys.argv[1:3]))

else:
    year, month = (now.year, now.month - 1)

    if 1 > month:
        year, month = (year - 1, 12)


query = f"""
    {ADS_QUERY} 
    AND (
            (property:refereed AND pubdate:{year}-{month:02d})
        OR  identifier:\"{year % 100}{month:02d}.*\"
        )
    """

# Clean up whitespace.
query = re.sub("\s{2,}", " ", query).strip()
fields = ["id", "first_author", "author", "aff", "title", "year", "bibcode", 
          "identifier", "journal", "volume", "pub", "page", "issue", "pubdate"]

articles = ads.SearchQuery(q=query, fl=fields)

new_articles = []

for i, article in enumerate(articles):

    print(f"Checking article {i} ({article})")

    # Check to see if already posted.
    if int(article.id) in records["id"]:
        print(f"  Skipping article {i} ({article}) because already posted")
        continue

    # Get the matching authors.
    matching_authors = []
    for i, (is_matching_author, meta) \
    in enumerate(map(matching_author, *(article.author, article.aff))):

        if is_matching_author:
            matching_authors.append([i] + meta)

    if len(matching_authors) == 0:
        print(f"  Skipping article ({article}) because no matched authors")
        continue

    # OK, this is new.
    new_articles.append((article, matching_authors))
    records.add_row(utils.prepare_record(article))

print(f"{len(new_articles)} new articles found")

# Save the records.
records.write(local_records_path, overwrite=True)

# Sort the new records to have first authors at front.
author_index = [ma[0][0] for a, ma in new_articles]
na_indices = np.argsort(author_index)
new_articles = [new_articles[idx] for idx in na_indices]

# Create an executive summary of the new records.
executive_summary = []

for count, (article, matching_authors) in enumerate(new_articles, start=1):

    kwds = formatted_summary(article)
    kwds.update(count=count)

    executive_summary.append(EXECUTIVE_SUMMARY_ARTICLE_FORMAT.format(**kwds))

executive_summary = "\n".join(executive_summary)

executive_summary_path = OUTPUT_PATH_PREFIX.format(now=now, here=here) + ".txt"
with open(executive_summary_path, "w") as fp:
    fp.write(executive_summary)

print(executive_summary)

# Download the new articles.
paths = []
new_articles_with_errors = []
for i, (article, matching_authors) in enumerate(new_articles):

    print(f"Downloading PDF for article {i}: {article}\n{matching_authors}")

    response, path = utils.retrieve_pdf(article)

    if not response:
        new_articles_with_errors.append((article, matching_authors))
        continue

    # Search/replace for author names.
    doc = fitz.open(path)
    page = doc[0]

    for _, __, author_name, ___ in matching_authors:
        last_name = author_name.split(",")[0]

        for instance in page.searchFor(last_name):
            # TODO: search around to highlight full name?
            page.addHighlightAnnot(instance)

    new_path = f"{path}.pdf"
    doc.save(new_path, garbage=4, deflate=True, clean=True)

    paths.append([new_path, article, matching_authors])


if new_articles_with_errors:
    print("Failed to get these:")
    for article, matching_authors in new_articles_with_errors:
        print(f"{article}: {matching_authors}")

# Create a summary page.
summary = PdfWriter()
summary_path = OUTPUT_PATH_PREFIX.format(now=now, here=here) + ".pdf"

failed_to_add_page_errors = []
for path, article, matching_authors in paths:

    try:
        with open(path, "rb") as rp:
            summary.addpage(PdfReader(rp).getPage(0))

    except PdfParseError:
        print(f"Failed to add page from {path}")
        failed_to_add_page_errors.append((path, article, matching_authors))

with open(summary_path, "wb") as fp:
    summary.write(fp)

if failed_to_add_page_errors or new_articles_with_errors:
    failure_summary = "However, there were some errors that occurred.\n\n"

    for count, (article, matching_authors) in enumerate(new_articles_with_errors, start=1):
        kwds = formatted_summary(article)
        kwds.update(count=count)

        summary = EXECUTIVE_SUMMARY_ARTICLE_FORMAT.format(**kwds)

        failure = f"""{count}. Could not find PDF for this article:

        {summary}

        URL: http://adsabs.harvard.edu/cgi-bin/nph-data_query?bibcode={article.bibcode}&link_type=PREPRINT
        
        """

        failure_summary += "\n".join([ea.lstrip() for ea in ea.split("\n")])


    for count, (_, article, matching_authors) \
    in enumerate(failed_to_add_page_errors, start=count):
        kwds = formatted_summary(article)
        kwds.update(count=count)

        summary = EXECUTIVE_SUMMARY_ARTICLE_FORMAT.format(**kwds)

        failure = f"""{count}. Could not add first page of this article's PDF:

        {summary}

        URL: http://adsabs.harvard.edu/cgi-bin/nph-data_query?bibcode={article.bibcode}&link_type=PREPRINT
        
        """

        failure_summary += "\n".join([ea.lstrip() for ea in ea.split("\n")])


# TODO: Remove temporary files?


# Send an email with the summary PDF and executive summary.

SCOPES = 'https://www.googleapis.com/auth/gmail.send'

store = file.Storage(os.path.join(here, 'token.json'))
creds = store.get()
if not creds or creds.invalid:
    flow = client.flow_from_clientsecrets(os.path.join(here, 'gmail-credentials.json'), SCOPES)
    creds = tools.run_flow(flow, store)
service = build('gmail', 'v1', http=creds.authorize(Http()))


message = MIMEMultipart()
message["to"] = EMAIL_TO
message["from"] = "andrew.casey@monash.edu"
message["subject"] = f"Publications for {now:%B}"

email_body = f"""
Dear colleague,

Attached you will find a summary of publications in {now:%B} by Monash researchers in the School of Physics and Astronomy.

{executive_summary}

{failure_summary}

Best wishes,
Andy
"""

msg = MIMEText(email_body)
message.attach(msg)

content_type = "application/pdf"
main_type, sub_type = content_type.split('/', 1)

with open(summary_path, "rb") as fp:
    msg = MIMEBase(main_type, sub_type)
    msg.set_payload(fp.read())

    filename = os.path.basename(summary_path)
    msg.add_header('Content-Disposition', 'attachment', filename=filename)
    email.encoders.encode_base64(msg)

    message.attach(msg)

    raw = base64.urlsafe_b64encode(message.as_string().encode()).decode()

    status = service.users().messages().send(userId=EMAIL_TO, body={"raw": raw})

    failures = []
    try:
        result = status.execute()

    except errors.HttpError as error:
        failures.append(error)

if failures:
    print("Failed to send email:")
    print(failures[0])

else:
    print("Fin")
