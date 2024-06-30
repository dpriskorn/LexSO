import asyncio
import gzip
import os
import time
from typing import List

import httpx
import pandas as pd
from bs4 import SoupStrainer, BeautifulSoup
from httpx import Limits, ConnectTimeout, ReadTimeout, ConnectError, HTTPStatusError
from pydantic import BaseModel, Field, ValidationError
from tqdm.asyncio import tqdm

import config
from config import max_ids_to_scrape


class Identifier(BaseModel):
    id_: int
    entry: str

    def __eq__(self, other):
        if isinstance(other, Identifier):
            return self.id_ == other.id_
        return False

    def __hash__(self):
        return hash(self.id_)

    # @property
    # def mp3_url(self) -> str:
    #     """
    #     Generates the URL for the MP3 file for this identifier.
    #
    #     :return: URL string for the MP3 file
    #     """
    #     base_url = 'https://isolve-so-service.appspot.com/pronounce?id='
    #     return f"{base_url}{self.id_}.mp3"

    @property
    def url(self):
        return f"https://svenska.se/so/?id={self.id_}"


class IdentifierModel(BaseModel):
    fetched: int = 0
    timeout: int = 0
    identifiers: List[Identifier] = Field(..., description="List of Identifier objects")

    @classmethod
    def from_csv(cls, csv_file: str) -> 'IdentifierModel':
        """
        Reads a list of identifiers from a CSV file.

        :param csv_file: Path to the CSV file
        :return: An instance of IdentifierModel
        """
        try:
            # Read the CSV file, only the first two columns
            df = pd.read_csv(csv_file, delimiter='\t', header=None, usecols=[0, 1], names=['id_', 'entry'])

            # Ensure the columns have been read correctly
            if df.shape[1] < 2:
                raise ValueError("The CSV file does not contain at least two columns")

            # Create a set of unique Identifier instances from the DataFrame
            unique_identifiers = {Identifier(id_=row['id_'], entry=row['entry']) for _, row in df.iterrows()}

            # Create an instance of IdentifierModel
            return cls(identifiers=list(unique_identifiers))
        except Exception as e:
            raise ValueError(f"Failed to read identifiers from CSV: {e}")

    async def fetch_url(self, identifier: Identifier) -> str:
        """
        Fetch the URL and save the HTML for a given identifier.

        :param identifier: Identifier object containing the id and entry
        :return: Path to the saved HTML file
        """
        # Ensure the output directory exists
        output_dir = 'data/html'
        os.makedirs(output_dir, exist_ok=True)

        # File path for the gzipped HTML file
        file_path = os.path.join(output_dir, f"{identifier.id_}.html.gz")

        if not os.path.exists(file_path):
            """They seem to have some kind of blocking against scraping. 
            When I ask for 1000 pages I get ~900 timeouts the first try
            Then if I ask immediately again I get 100% timeouts.
            Then I wait 20 seconds and ask again and then I get 100 pages and the rest is blocked
            
            So the best cause of action is to fetch 100, wait 15-20 seconds then fetch the next 100 and so forth"""
            async with httpx.AsyncClient(limits=Limits(max_connections=5, #max_keepalive_connections=2
                                                       )) as client:
                try:
                    response = await client.get(identifier.url)
                    response.raise_for_status()

                    # HTML content as string
                    html_content = response.text
                    # Define the tag and attributes you want to extract
                    strainer = SoupStrainer(attrs={"itemprop": "articleBody"})

                    # Parse the HTML content with BeautifulSoup
                    soup = BeautifulSoup(html_content, 'lxml', parse_only=strainer)
                    html = str(soup)
                    # Write the HTML content gzipped to the file
                    with gzip.open(file_path, 'wt', encoding='utf-8') as f:
                        f.write(html)
                    self.fetched += 1
                    return file_path
                except (ConnectTimeout, ReadTimeout,
                        HTTPStatusError
                        ):
                    # print("got timeout")
                    self.timeout += 1

    async def fetch_all_html(self, start, stop):
        """
        Fetch and save HTML for all identifiers.
        """
        ids = self.identifiers[start:stop]
        tasks = [self.fetch_url(id_) for id_ in ids]
        return await tqdm.gather(*tasks)


# Example usage:
# Assuming you have a CSV file named 'P9837.csv' in the 'data' directory
try:
    print("Loading identifiers from file")
    identifier_model = IdentifierModel.from_csv('data/P9837.csv')
    print(f"Starting fetch of html for all {len(identifier_model.identifiers)} identifiers")
    # Fetch and save all HTML pages asynchronously
    run = True
    start = 100
    stop = 200
    fetched = 0
    timeout = 0
    while run:
        print(f"Start = {start}, stop = {stop}")
        asyncio.run(identifier_model.fetch_all_html(start=start, stop=stop))
        new_fetched = identifier_model.fetched
        new_timeout =  identifier_model.timeout
        print(f"Fetched {new_fetched - fetched} pages and got {new_timeout - timeout} timouts")
        if new_fetched > fetched:
            print("Sleeping 15 sec to avoid timeouts")
            time.sleep(15)
        start += 100
        stop = start + 100
        fetched = new_fetched
        timeout = new_timeout
        if start >= config.max_ids_to_scrape:
            run = False
            print(f"Stopped at {config.max_ids_to_scrape}")

except ValidationError as e:
    print("Validation error:", e)
except ValueError as e:
    print("Error:", e)
