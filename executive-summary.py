
""" Check for new papers on arXiv by Monash researchers. """

__author__ = 'Andy Casey <andrew.casey@monash.edu>'

# Example usage:    python paperboy.py           (to run previous month)
#                   python paperboy.py 2015 8    (to run for August, 2015)

import os
import requests
import re
import sys
from time import localtime
from pdfrw import PdfReader, PdfWriter, PdfParseError


import ads

paper_format = "{count}. {title}\n{authors}, {pub}, {vol}{issue}{page} ({year}).\n\n"

strip_affiliation = lambda _: _.replace(",", "").replace(";", "").lower()


def parse_arxiv_number(identifier):
    number = re.sub("\D$", "", identifier.split("arXiv")[1].lstrip(":"))
    return number if "." in number else int(number)/100000.0
    

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

    articles = ads.SearchQuery(q=query,
        fl=["id", "first_author", "author", "aff", "title", "year", "bibcode", "identifier", "journal", "volume", "pub", "page", "issue", "pubdate"])

    executive_summary = []

    accept_affiliations = [
        "imperial college london united kingdom monash university faculty of science clayton australia", # for the dean
    ]
    original_affiliations = {}
    skipped_matches = {}
    missing_urls = []
    paths = []
    skipped = []
    counter = 1
    for i, article in enumerate(articles):
        for affiliation in article.aff:
            if "monash" in affiliation.lower():
                stripped_affiliation = strip_affiliation(affiliation)
                    
                if "physics" in affiliation.lower() or stripped_affiliation in accept_affiliations:
                    break
                else:
                    original_affiliations.setdefault(stripped_affiliation, [])
                    original_affiliations[stripped_affiliation].append(affiliation)

                    skipped_matches.setdefault(stripped_affiliation, [])
                    skipped_matches[stripped_affiliation].append(article.bibcode)

        else:
            skipped.append(article)
            continue

        # Retrieve article from arXiv.
        arxiv_version_found = False
        for identifier in article.identifier:
            if "arXiv" in identifier: 
                arxiv_version_found = True

                number = parse_arxiv_number(identifier)
                basename = "{0}.pdf".format(number)

                # arXiv/ADS gets this *wrong*
                #url = "https://arxiv.org/pdf/{0}".format(basename)

                path = os.path.join(folder, basename)
                paths.append(path)

                if not os.path.exists(path):

                    url = f"http://adsabs.harvard.edu/cgi-bin/nph-data_query?bibcode={article.bibcode}&link_type=PREPRINT"
                    r = requests.get(url)

                    if not r.ok:
                        raise a

                    url = r.url.replace("abs", "pdf")
                    print("({}) Downloading {} to {}".format(i, url, path))

                    response = requests.get(url)
                    with open(path, "wb") as fp:
                        fp.write(response.content)

                else:
                    print(f"({i}) Found {path} -- skipping")

                break

        if not arxiv_version_found:
            missing_urls.append("http://adsabs.harvard.edu/abs/{}".format(article.bibcode))

        is_monash = lambda aff: "monash" in aff.lower()
        format_author = lambda auth, aff: "*{}*".format(auth) if is_monash(aff) else auth

        skip = 0
        total_skip = 0
        if len(article.author) > 50:
            authors = []

            for j, (auth, aff) in enumerate(zip(article.author, article.aff)):
                if j < 1:
                    authors.append(format_author(auth, aff))

                else:
                    if is_monash(aff):
                        if skip > 0:
                            authors.append("...")
                            skip = 0
                        authors.append(format_author(auth, aff))

                    else:
                        skip += 1
                        total_skip += 1

            if skip > 0:
                authors.append("et al.")

            authors = "; ".join(authors) + f"({total_skip} authors not shown)"

        else:

            authors = "; ".join([format_author(auth, aff) for auth, aff in zip(article.author, article.aff)])

        executive_summary.append(paper_format.format(count=counter,
                                    title=article.title[0],
                                  authors=authors,
                                  pub=article.pub,
                                  vol="in press" if article.volume is None else "{}".format(article.volume), 
                                  issue=", {}".format(article.issue) if article.issue is not None else "",
                                  page=", {}".format(article.page[0]) if (article.page is not None and article.page[0] is not None) else "",
                                  year=article.pubdate.split("-")[0]))
        counter += 1



# Join PDFs.
summary_path = os.path.join(folder, "summary.pdf")

summary = PdfWriter()

from glob import glob

paths = glob(os.path.join(folder, "*.pdf"))
paths = [p for p in paths if not p.endswith("summary.pdf")]

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

print("Executive summary:\n{}".format("\n".join(executive_summary)))

with open(os.path.join(folder, "executive-summary.txt"), "w") as fp:
    fp.write("\n".join(executive_summary))


print("Missing these urls:")
for i, missing_url in enumerate(missing_urls):
    print(missing_url)

for affiliation, skipped_bibcodes in skipped_matches.items():
    bibcodes = list(set(skipped_bibcodes))
    print("Skipped affiliation ({}):\n\t{}".format(bibcodes, "\n".join(original_affiliations[affiliation])))



"""
Kinematic evidence for an embedded protoplanet in a circumstellar disc
Pinte, Christophe; Price, D. J.; Menard, F.; Duchene, G.; Dent, W.; Hill, T.; de Gregorio-Monsalvo, I.; Hales, A; Mentiplay, D., ApJ Letters, 860, L13 (2018).
"""