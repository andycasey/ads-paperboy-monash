
""" Check for new papers on arXiv by Monash researchers. """

__author__ = 'Andy Casey <andrew.casey@monash.edu>'

# Example usage:    python paperboy.py           (to run previous month)
#                   python paperboy.py 2015 8    (to run for August, 2015)

import os
import sys
from time import localtime

import ads
import requests
from pdfrw import PdfReader, PdfWriter, PdfParseError


paper_format = "{count}. {title}\n{authors}, {pub}, {vol}{issue}{page} ({year}).\n\n"

if __name__ == '__main__':

    # Use year/month if given, otherwise query the previous month.
    if len(sys.argv) >= 3:
        year, month = map(int, (sys.argv[1:3]))
    else:
        now = localtime()
        year, month = (now.tm_year, now.tm_mon - 1)
        if 1 > month: year, month = (year - 1, 12)

    folder = "{0}-{1:02d}".format(year, month)
    if not os.path.exists(folder):
        os.mkdir(folder)

    print('Querying {0} / {1}'.format(year, month))

    # Retrieve all the articles published last month (refereed or otherwise)
    query = 'aff:"Monash" AND ((property:refereed AND (pubdate:20{0}-{1:02d} OR pubdate:20{0}-{2:02d}))'\
            ' OR identifier:"{0}{1:02d}.*")'.format(str(year)[-2:], month, month + 1)

    articles = list(ads.SearchQuery(q=query,
        fl=["id", "first_author", "author", "aff", "title", "year", "bibcode", "identifier", "journal", "volumne", "pub", "page", "issue", "pubdate"]))

    skipped = []
    counter = 1
    for article in articles:
        for affiliation in article.aff:
            if "monash" in affiliation.lower() and "physics" in affiliation.lower():
                break
        else:
            skipped.append(article)
            continue

        authors = [("*{}*".format(auth, aff) if "monash" in aff.lower() else auth) for auth, aff in zip(article.author, article.aff)]

        print(paper_format.format(count=counter,
                                    title=article.title[0],
                                  authors="; ".join(authors),
                                  pub=article.pub,
                                  vol=article.volume,
                                  issue=", {}".format(article.issue) if article.issue is not None else "",
                                  page=", {}".format(article.page[0]) if article.page[0] is not None else "",
                                  year=article.pubdate.split("-")[0]))
        counter += 1

    # Send to printer.
    #os.system("lp {}".format(os.path.abspath(summary_path)))


"""
Kinematic evidence for an embedded protoplanet in a circumstellar disc
Pinte, Christophe; Price, D. J.; Menard, F.; Duchene, G.; Dent, W.; Hill, T.; de Gregorio-Monsalvo, I.; Hales, A; Mentiplay, D., ApJ Letters, 860, L13 (2018).
"""