import asyncio
import os
from argparse import ArgumentParser
import re
from pprint import pprint
from aiohttp import ClientSession
import aiofiles
import requests
from bs4 import BeautifulSoup

DOWNLOAD_FOLDER = "/Users/stevenjohn/Downloads"


async def get_page_links(link, session, sem=None):
    async with sem:
        async with session.get(link) as resp:
            soup = BeautifulSoup(await resp.text(), 'html.parser')
            return [
                li["href"] for li in soup.select("div.span3.compendious > a")
            ]


async def download_image(link,
                         session,
                         sem=None,
                         folder_name=None,
                         chunk_size=200):
    async with sem:
        async with session.get(link) as resp:
            soup = BeautifulSoup(await resp.text(), 'html.parser')
            image_url = soup.find("a", string="Full Resolution TIFF")["href"]

        async with session.get(image_url) as resp:
            os.chdir(DOWNLOAD_FOLDER)
            os.makedirs(folder_name, exist_ok=True)
            os.chdir(folder_name)
            file_name = os.path.split(image_url)[1]

            async with aiofiles.open(file_name, 'wb') as f:
                while True:
                    chunk = await resp.content.read(chunk_size)
                    if not chunk:
                        break
                    await f.write(chunk)


async def search_item(item):
    query_link = f"https://etc.usf.edu/clipart/home/search?q={item}&page="
    page_html = requests.get(query_link).text
    soup = BeautifulSoup(page_html, 'html.parser')
    page_links = []
    try:
        for page_li in soup.find("ul", class_="pull-right").children:
            try:
                if page_li["class"] == ["active"]:
                    continue
            except KeyError:
                page_links.append(page_li.find("a")["href"])

    except AttributeError:
        pass

    sem = asyncio.Semaphore(100)
    async with ClientSession() as session:
        tasks = [
            get_page_links(
                link,
                session,
                sem=sem,
            ) for link in [query_link] + page_links
        ]
        image_page_links = []
        for page in await asyncio.gather(*tasks):
            image_page_links.extend(page)

        tasks = [
            download_image(
                link,
                session,
                sem=sem,
                folder_name=item.title(),
            ) for link in image_page_links
        ]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = ArgumentParser(
        "Searches your term in Clipart ETC and downloads all the results")
    parser.add_argument("term", help="Searches this")
    args = parser.parse_args()
    asyncio.run(search_item(args.term))
