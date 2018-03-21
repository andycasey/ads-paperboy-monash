
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
    query = 'aff:"Monash" AND ((property:refereed AND pubdate:20{0}-{1:02d})'\
            ' OR identifier:"{0}{1:02d}.*")'.format(str(year)[-2:], month)

    articles = list(ads.SearchQuery(q=query,
        fl=["id", "author", "aff", "title", "year", "bibcode", "identifier"]))

    print("Found {0} articles. Downloading PDFs..".format(len(articles)))
    
    # Retrieve articles from arXiv.
    paths = []
    N = len(articles)
    for i, article in enumerate(articles):

        for identifier in article.identifier:
            if "arXiv" in identifier: break
        else:
            print("No arXiv identifier found for {}:\nTitle: {}\nAuthors: {}"\
                .format(article, article.title, article.author))
            continue

        number = int(identifier.split("arXiv")[1][:-1])/100000.0
        basename = "{0}.pdf".format(number)

        url = "https://arxiv.org/pdf/{0}".format(basename)

        path = os.path.join(folder, basename)
        paths.append(path)

        if not os.path.exists(path):
            print("({}/{}) Downloading {} to {}".format(i, N, url, path))

            response = requests.get(url)
            with open(path, "wb") as fp:
                fp.write(response.content)

    # Join PDFs.
    summary_path = os.path.join(folder, "summary.pdf")

    summary = PdfWriter()

    files = []
    for i, path in enumerate(paths):
        print("Adding first page from {}".format(path))
        try:
            with open(path, "rb") as rp:
                summary.addpage(PdfReader(rp).getPage(0))

        except PdfParseError:
            print("failed to add page from {}".format(path))

    with open(summary_path, "wb") as fp:
        summary.write(fp)

    print("Created {}".format(summary_path))

    # Send to printer.
    os.system("lp {}".format(os.path.abspath(summary_path))
