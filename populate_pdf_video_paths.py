"""
ADASS authors can upload a PDF and/or an MP4 file in their contribution
directory (named after their contribution PID) in out FTP site.

We have added two new columns in the database to keep track of these files and
we want to periodically update these. Also, we publish a conference schedule
and HTML pages for all contributions. We want to add and update links to the
PFD and MP4 in there as well.
"""
import argparse
import logging
from pathlib import Path
from bs4 import BeautifulSoup, Tag
import psycopg2


# Configuration
FTP_ROOT = '/var/www/html/static/ftp'
HTML_ROOT = '/var/www/schedule/adass2020/talk'
MEDIA_ROOT = '/var/www/schedule/media'
MEDIA_URL_ROOT = 'https:\/\/adass2020.es/static/ftp'

SQL = '''\
SELECT
    code,
    paper_id,
    pdf_path,
    video_path
FROM
    submission_submission
WHERE
    state = 'confirmed'
ORDER BY
    paper_id
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ftp_root', type=str, default=FTP_ROOT)
    parser.add_argument('--html_root', type=str, default=HTML_ROOT)
    parser.add_argument('--media_root', type=str, default=MEDIA_ROOT)
    parser.add_argument('--media_url_root', type=str, default=MEDIA_URL_ROOT)
    args = parser.parse_args()

    ftp_root = Path(args.ftp_root)
    html_root = Path(args.html_root)
    media_root = Path(args.media_root)
    media_url_root = Path(args.media_url_root)

    contribution_files = {}

    with psycopg2.connect(database="pretalx", user="pretalx", password="",
                          host="localhost", port="5432") as conn:
        cur = conn.cursor()
        cur.execute(SQL)

        for row in cur:
            (code, paper_id, pdf_path, video_path) = row
            if paper_id is None:
                logging.warning(f'Talk code {code} has no paper_id!')
                continue

            ftp_path = ftp_root / paper_id
            if not ftp_path.is_dir():
                logging.warning(f'Directory {ftp_path} MISSING')
                continue
            index_path = html_root / code / 'index.html'
            if not index_path.is_file():
                logging.warning(f'HTML file {index_path} MISSING')
                continue

            # Understand which pdf/mp4 file to use: probably the most recemt.
            files = sorted(
                [p for p in ftp_path.iterdir()
                 if p.suffix.lower() in ('.pdf', '.mp4')
                    and paper_id in p.name],
                key=lambda path: path.stat().st_ctime,
                reverse=True
            )
            if not files:
                # See if the PDF/MP4 was in the DB and just disappeared
                if pdf_path or video_path:
                    logging.warning(f'!!!!! {code}: PDF/MP4 DISAPPEARED!!!!!!')
                # else:
                #     logging.warning(f'{code} has not uploaded a PDF/MP4')
                continue

            newest_pdf = None
            newest_video = None
            while files:
                path = files.pop()
                ext = path.suffix.lower()
                if ext == '.pdf' and not newest_pdf:
                    newest_pdf = path
                elif ext == '.mp4' and not newest_video:
                    newest_video = path
                if newest_video and newest_pdf:
                    break

            # We store the file url, not the absolute path
            # Also, make sure that we can actually serve the files via HTTP(S)
            if newest_pdf:
                newest_pdf.chmod(0o644)
                newest_pdf = media_url_root / paper_id / newest_pdf.name
            if newest_video:
                newest_video.chmod(0o644)
                newest_video = media_url_root / paper_id / newest_video.name

            # if str(newest_pdf) == str(pdf_path) and \
            #         str(newest_video) == str(video_path):
            #     # Nothing to do!
            #     logging.warning(f'{code} is already up to date! SKIPPED')
            #     continue

            d = {'pdf_path': newest_pdf, 'video_path': newest_video}

            # Update the database
            # FIXME: do all these updates in a single transaction!
            with conn.cursor() as update_cur:
                update = 'UPDATE submission_submission SET'
                where = f"WHERE code = '{code}'"
                values = ', '.join(
                    f"{k} = '{v}'" for k, v in d.items() if v is not None
                )
                sql = f'{update} {values} {where}'
                update_cur.execute(sql)

            with open(index_path) as f:
                data = f.read()
            soup = BeautifulSoup(data, 'html.parser')

            aside = soup.find('aside')
            if not aside or not isinstance(aside, Tag):
                logging.warning(f'!!!! {code}: malformed HTML!!!!')
                continue

            existing = aside.find('section', 'resources')

            start = '''\
<section class="resources">
  <div class="speaker-header">
    <strong>From the FTP</strong>
  </div>
  <div>
'''
            links = ' | '.join(
                f'    <a href="{v}">{v.name}</a>' for v in d.values()
                if v is not None
            )
            end = '''
  </div>
</section>
'''
            html = f'{start}{links}{end}'
            new_tag = BeautifulSoup(html, 'html.parser').section
            if not existing:
                aside.contents.append(new_tag)
            else:
                existing.replace_with(new_tag)

            with open(index_path, 'w') as f:
                f.write(soup.prettify())
                logging.warning(f'{code} was updated')
            # print(soup.prettify())
