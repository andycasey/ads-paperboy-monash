
import os
import re
import requests
from datetime import datetime
from tempfile import NamedTemporaryFile
from astropy.table import Table

def parse_arxiv_number(identifier):
    number = re.sub("\D$", "", identifier.split("arXiv")[1].lstrip(":"))
    return number if "." in number else int(number)/100000.0
    


def stripped_affiliations(aff):

    aff = aff.replace("&amp;", "&")

    return [ea.replace(",", "").replace(":", "").lower().strip() for ea in aff.split(";")]



def load_records(path):

    if os.path.exists(path):
        try:
            return Table.read(path, encoding="latin-1")
        except:
            return Table.read(path, encoding="utf-8")

    # Return an empty Table with the expected columns.
    return Table(rows=None,
                 names=('id', 'updated', 'title', 'bibcode', 'pubdate'),
                 dtype=('i4', 'S26', 'S500', 'S100', 'S100'))


def prepare_record(article):
    return (int(article.id), f"{datetime.now()}", str(article.title[0].encode()), article.bibcode, article.pubdate)





def download_pdf_to_path(url, path=None):

    path = path or NamedTemporaryFile().name

    print(f"Downloading {url} to {path}")

    r = requests.get(url)
    with open(path, "wb") as fp:
        fp.write(r.content)

    return path


def eprint_pdf_uri(bibcode):
    return f"https://ui.adsabs.harvard.edu/link_gateway/{bibcode}/EPRINT_PDF"

def retrieve_pdf(article, path=None):

    if "JHEP" == article.bibcode[4:8]:
        # Special case for JHEP, because it always fails on arXiv search.
        url = f"https://link.springer.com/content/pdf/10.1007%2FJHEP{article.issue}%28{article.year}%29{int(article.page[0]):03d}.pdf"
        path = download_pdf_to_path(url, path)

    else:

        # Search arXiv.
        arxiv_version_found = False
        for identifier in article.identifier:

            if "arxiv" not in str(identifier).lower(): continue

            number = parse_arxiv_number(identifier)
            basename = "{0}.pdf".format(number)

            # arXiv/ADS gets this *wrong*
            #url = "https://arxiv.org/pdf/{0}".format(basename)

            # Ask ADS to send us to the right place.
            #url = f"http://adsabs.harvard.edu/cgi-bin/nph-data_query?bibcode={article.bibcode}&link_type=PREPRINT"
            url = eprint_pdf_uri(article.bibcode)

            r = requests.get(url)

            if not r.ok:
                raise

            url = r.url.replace("abs", "pdf")

            path = download_pdf_to_path(url, path)

            break

        else:

            return (False, path, )

    return (True, path)

