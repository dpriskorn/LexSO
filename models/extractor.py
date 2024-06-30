import gzip
import os
import re
import uuid
from typing import List

from bs4 import BeautifulSoup
from jsonlines import jsonlines
from pydantic import BaseModel
from tqdm import tqdm

import config


class DictionaryElement(BaseModel):
    prefix: str = ""  # prefix for the unique id number
    id_: str = str(uuid.uuid4())[6:]
    value: str

    @property
    def check_id(self):
        if self.prefix:
            return self.prefix in self.id_


class Inflection(DictionaryElement):
    prefix: str = "boj"

    @classmethod
    def from_soup(cls, soup):
        if soup is None:
            return None
        id_ = soup.get("id", "")
        value = soup.find("span", class_="bojning").text.strip() if soup.find("span", class_="bojning") else ""
        return cls(id_=id_, value=value)


class Lemvar(DictionaryElement):
    """This contains inflections"""
    prefix: str = "lnr"
    inflections: List[Inflection] = []

    @classmethod
    def from_soup(cls, soup):
        if soup is None:
            return None
        element = soup.find("span", class_="lemvarhuvud")
        if element:
            id_ = element.get("id", "")
        else:
            raise ValueError("no lemvarhuvud found")
        value = soup.find("span", class_="orto").text.strip() if soup.find("span", class_="orto") else ""
        inflection_soup = soup.find("span", class_="bojning_inline")
        inflections = [Inflection.from_soup(inflection_soup)] if inflection_soup else []
        return cls(id_=id_, value=value, inflections=inflections)


class Pronounciation(BaseModel):
    """Id and url for a pronounciation"""
    id_: str
    url: str

    @staticmethod
    def mp3_url(id_: str) -> str:
        """
        Generates the URL for the MP3 file for this identifier.

        :return: URL string for the MP3 file
        """
        base_url = 'https://isolve-so-service.appspot.com/pronounce?id='
        return f"{base_url}{id_}.mp3"


class Kernel(DictionaryElement):
    prefix: str = "kcnr"

    @classmethod
    def from_soup(cls, soup):
        if soup is None:
            return None
        id_ = soup.get("id", "")
        value = soup.text.strip() if soup else ""
        return cls(id_=id_, value=value)


class Etymology(DictionaryElement):
    prefix: str = "etynr"

    @classmethod
    def from_soup(cls, soup):
        if soup is None:
            return None
        id_ = soup.get("id", "")
        value = soup.find("span", class_="fb").text.strip() if soup.find("span", class_="fb") else ""
        return cls(id_=id_, value=value)


class SeeAlso(DictionaryElement):
    prefix: str = "xnr"

    @classmethod
    def from_soup(cls, soup):
        if soup is None:
            return None
        id_ = soup.get("id", "")
        value = soup.text.strip() if soup else ""
        return cls(id_=id_, value=value)

class Idiom(DictionaryElement):
    """Idioms that have a link are duplicate references to other pages where the data is found"""
    prefix: str = "inr"
    definition: str = ""
    example: str = ""
    has_link: bool = False

    def __hash__(self):
        return hash(self.id_)

    def __eq__(self, other):
        return self.id_ == other.id_

    @classmethod
    def from_soup(cls, soup):
        if soup is None:
            return None
        # print(soup)
        # print(soup.find("div"))
        # exit()
        id_ = soup.get("id", "")
        has_link = bool(soup.find("a"))
        value = soup.find("span", class_="fras").text.strip() if soup.find("span", class_="fras") else ""
        definition = soup.find("span", class_="idiomdef").text.strip() if soup.find("span", class_="idiomdef") else ""
        example = soup.find("span", class_="idiomex").text.strip() if soup.find("span", class_="idiomex") else ""
        return cls(id_=id_, value=value, definition=definition, example=example, has_link=has_link)


class Sentence(DictionaryElement):
    @classmethod
    def from_soup(cls, soup):
        if soup is None:
            return None
        id_ = soup.get("id", "")
        value = soup.text.strip() if soup else ""
        return cls(id_=id_, value=value)

class Lexem(DictionaryElement):
    """This equals a sense in the Wikidata lexicographic model"""
    prefix: str = "xnr"
    kernels: List[Kernel]
    see_alsos: List[SeeAlso]
    idioms: List[Idiom]
    sentences: List[Sentence]

    @classmethod
    def from_soup(cls, soup):
        if soup is None:
            return None
        id_ = soup.get("id", "")
        kernels_soup = soup.find_all("span", class_="kbetydelse")
        kernels = [Kernel.from_soup(kernel) for kernel in kernels_soup if kernel is not None]
        see_alsos_soup = soup.find_all("a", class_="hvtag")
        see_alsos = [SeeAlso.from_soup(see_also) for see_also in see_alsos_soup if see_also is not None]
        idioms_soup = soup.find_all("div", class_="idiom")
        # print(idioms_soup)
        # exit()
        idioms = [Idiom.from_soup(idiom) for idiom in idioms_soup if idiom is not None]
        # if idioms:
        #     pprint(idioms)
        #     exit()
        # Extract sentences
        sentences_soup = soup.find_all("span",
                                       class_="sentence-class")  # Adjust the class as per actual HTML structure
        sentences = [Sentence.from_soup(sentence) for sentence in sentences_soup if sentence is not None]

        return cls(id_=id_, value=id_, kernels=kernels, see_alsos=see_alsos, idioms=idioms, sentences=sentences)


class Superlemma(DictionaryElement):
    prefix: str = "snr"
    lemvar: Lemvar
    hyphenation: str  # called 'avstav' # P5279
    lexical_category: str  # called 'ordklass'
    pronunciation: Pronounciation | None = None
    lexem: Lexem|None = None

    def __eq__(self, other):
        return self.id_ == other.id_

    def __hash__(self):
        return hash(self.id_)

    @classmethod
    def from_soup(cls, soup):
        if soup is None:
            return None
        id_ = soup.get("id", "")
        if id_ == "":
            raise ValueError("id cannot be empty")
        lemvar_soup = soup.find("div", class_="lemvar")
        if lemvar_soup is None:
            raise ValueError("Lemvar_soup cannot be None")
        lemvar = Lemvar.from_soup(lemvar_soup)
        if lemvar is None:
            raise ValueError("Lemvar cannot be None")
        hyphenation = soup.find("span", class_="avstav").text.strip() if soup.find("span", class_="avstav") else ""
        lexical_category = soup.find("div", class_="ordklass").text.strip() if soup.find("div",
                                                                                         class_="ordklass") else ""

        # Extract pronunciation if available
        pronunciation_tag = soup.find("a", class_="ljudfil")
        pronunciation = pronunciation_tag.get('onclick').split('\'')[1] if pronunciation_tag else None
        if pronunciation is not None:
            # Generate pronunciation URL using mp3_url property
            pronunciation_url = Pronounciation.mp3_url(pronunciation)

            # Create Pronounciation instance
            pronunciation_instance = Pronounciation(id_=pronunciation, url=pronunciation_url)
        else:
            pronunciation_instance=None

        # Extract lexem
        lexem_soup = soup.find("div", class_="lexemdiv")
        lexem = Lexem.from_soup(lexem_soup) if lexem_soup else None

        return cls(id_=id_, value=lemvar.value if lemvar else "", lemvar=lemvar, hyphenation=hyphenation,
                   lexical_category=lexical_category, pronunciation=pronunciation_instance, lexem=lexem)

class Article(BaseModel):
    """Entry with year of publication and list of lemmas"""
    year_of_publication: str  # called 'tryck'
    lemmalist: List[Superlemma]  # lemmalista

    def __eq__(self, other):
        return self.lemmalist == other.lemmalist

    def __hash__(self):
        """We join the ids to get a unique id"""
        ids = []
        for lemma in self.lemmalist:
            ids.append(lemma.id_)
        return hash("".join(ids))

    @classmethod
    def from_soup(cls, soup):
        if soup is None:
            return None
        year_of_publication = soup.find("span", class_="tryck").text.replace("publicerad: ", "").strip() if soup.find("span", class_="tryck") else ""
        lemmalist_soup = soup.find_all("div", class_="superlemma")
        if lemmalist_soup is None:
            raise ValueError("lemmalist_soup cannot be None")
        lemmalist = [Superlemma.from_soup(lemma) for lemma in lemmalist_soup if lemma is not None]
        return cls(year_of_publication=year_of_publication, lemmalist=lemmalist)


class Extractor(BaseModel):
    html: str = ""
    articles: List[Article] = []
    superlemmas: List[Superlemma] = []
    idioms: List[Idiom] = []
    articles_jsonl: str = "data/jsonl/articles_{}.jsonl"
    superlemmas_jsonl: str = "data/jsonl/superlemmas_{}.jsonl"
    idioms_jsonl: str = "data/jsonl/idioms_{}.jsonl"

    def __extract_articles__(self):
        """Parse the HTML content and extract articles."""
        soup = BeautifulSoup(self.html, 'lxml')
        article_divs = soup.find_all('div', class_='artikel so')

        for article_div in article_divs:
            article = Article.from_soup(article_div)
            if article and len(article.lemmalist) > 0:
                self.articles.append(article)

    def __extract_superlemmas(self):
        """Extract superlemmas from articles."""
        for article in self.articles:
            self.superlemmas.extend(article.lemmalist)
        self.superlemmas = list(set(self.superlemmas))  # Deduplicate superlemmas

    def __extract_idioms(self):
        """Extract idioms from superlemmas."""
        for lemma in self.superlemmas:
            self.idioms.extend(lemma.lexem.idioms)
        self.idioms = list(set(self.idioms))  # Deduplicate idioms

    def __process_gzip_file(self, file_path):
        """Process a single gzip file and extract articles."""
        with gzip.open(file_path, 'rt') as f:
            self.html = f.read()
            self.__extract_articles__()
            self.__extract_superlemmas()
            self.__extract_idioms()

    # def process_gzip_files(self, directory_path="data/html"):
    #     """Process all gzip files in the directory one by one."""
    #     file_list = [file for file in os.listdir(directory_path) if file.endswith(".gz")]
    #     with tqdm(total=len(file_list), desc="Processing files") as pbar:
    #         for file_name in file_list:
    #             file_path = os.path.join(directory_path, file_name)
    #             self.process_gzip_file(file_path)
    #             pbar.update(1)

    def __remove_existing_jsonl_files(self):
        """remove existing """

    def process_and_dump_individual_files(self, directory_path="data/html"):
        """Process gzip files one by one and dump results to JSONL to avoid memory issues."""
        self.__remove_existing_jsonl_files()
        file_list = [file for file in os.listdir(directory_path) if file.endswith(".gz")]
        with tqdm(total=len(file_list), desc="Processing and dumping files") as pbar:
            for file_name in file_list:
                file_path = os.path.join(directory_path, file_name)
                self.__process_gzip_file(file_path)
                self.__dump_articles_to_jsonl()
                self.__dump_superlemmas_to_jsonl()
                self.__dump_idioms_to_jsonl()
                self.__reset_extracted_data()  # Clear data to free up memory
                pbar.update(1)
                # raise Exception("debug exit")

    def __reset_extracted_data(self):
        """Reset extracted data to free up memory."""
        self.articles = []
        self.superlemmas = []
        self.idioms = []

    @staticmethod
    def remove_special_characters(obj):
        """Remove special characters from strings within the given object."""
        if isinstance(obj, str):
            return re.sub('\u00ad', '', obj)
        elif isinstance(obj, dict):
            return {k: Extractor.remove_special_characters(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [Extractor.remove_special_characters(item) for item in obj]
        return obj

    def __dump_articles_to_jsonl(self):
        """Dump articles to a JSONL file."""
        with jsonlines.open(self.articles_jsonl.format(config.version), mode='a') as writer:
            for article in self.articles:
                article_dict = article.model_dump()
                cleaned_article = Extractor.remove_special_characters(article_dict)
                writer.write(cleaned_article)

    def __dump_superlemmas_to_jsonl(self):
        """Dump superlemmas to a JSONL file."""
        with jsonlines.open(self.superlemmas_jsonl.format(config.version), mode='a') as writer:
            for superlemma in self.superlemmas:
                dict_ = superlemma.model_dump()
                cleaned_dict = Extractor.remove_special_characters(dict_)
                writer.write(cleaned_dict)

    def __dump_idioms_to_jsonl(self):
        """Dump idioms to a JSONL file.
        We only dump idioms that does not have a link"""
        with jsonlines.open(self.idioms_jsonl.format(config.version), mode='a') as writer:
            for idiom in self.idioms:
                if not idiom.has_link:
                    dict_ = idiom.model_dump()
                    cleaned_dict = Extractor.remove_special_characters(dict_)
                    writer.write(cleaned_dict)
