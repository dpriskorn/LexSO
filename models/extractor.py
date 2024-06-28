import gzip
import os
import re
import uuid
from pprint import pprint
from typing import List

from bs4 import BeautifulSoup
from jsonlines import jsonlines
from pydantic import BaseModel
from tqdm import tqdm


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


class Superlemma(DictionaryElement):
    prefix: str = "snr"
    lemvar: Lemvar
    hyphenation: str  # called 'avstav' # P5279
    lexical_category: str  # called 'ordklass'
    pronunciation: Pronounciation | None = None

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

        # Generate pronunciation URL using mp3_url property
        pronunciation_url = Pronounciation.mp3_url(pronunciation)

        # Create Pronounciation instance
        pronunciation_instance = Pronounciation(id_=pronunciation, url=pronunciation_url)

        return cls(id_=id_, value=lemvar.value if lemvar else "", lemvar=lemvar, hyphenation=hyphenation,
                   lexical_category=lexical_category, pronunciation=pronunciation_instance)


class Article(BaseModel):
    """Entry with year of publication and list of lemmas"""
    year_of_publication: str  # called 'tryck'
    lemmalist: List[Superlemma]  # lemmalista

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
    prefix: str = "inr"

    @classmethod
    def from_soup(cls, soup):
        if soup is None:
            return None
        id_ = soup.get("id", "")
        value = soup.find("span", class_="fras").text.strip() if soup.find("span", class_="fras") else ""
        return cls(id_=id_, value=value)


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
        idioms_soup = soup.find_all("a", class_="idiom")
        idioms = [Idiom.from_soup(idioms_soup) for idiom in idioms_soup if idiom is not None]
        if idioms:
            pprint(idioms)
            exit()
        # todo support sentences also
        return cls(id_=id_, value=id_, kernels=kernels, see_alsos=see_alsos, idioms=idioms)




class Extractor(BaseModel):
    html: str = ""
    articles: List[Article] = []

    def extract_articles(self):
        # Parse the HTML content
        soup = BeautifulSoup(self.html, 'lxml')

        # Find all div elements with class="artikel so"
        article_divs = soup.find_all('div', class_='artikel so')

        for article_div in article_divs:
            # Extract the article
            article = Article.from_soup(article_div)
            if article:
                self.articles.append(article)

    def extract_from_gzip_files(self, directory_path="data/html"):
        extractor = Extractor()
        file_list = [file for file in os.listdir(directory_path) if file.endswith(".gz")]
        with tqdm(total=len(file_list), desc="Processing files") as pbar:
            for file_name in file_list:
                file_path = os.path.join(directory_path, file_name)
                with gzip.open(file_path, 'rt') as f:
                    extractor.html = f.read()
                    # if "idiom" in extractor.html_content:
                    #     print(extractor.html_content)
                    #     exit()
                    extractor.extract_articles()
                    self.articles.extend(extractor.articles)
                pbar.update(1)

    @staticmethod
    def remove_special_characters(obj):
        if isinstance(obj, str):
            return re.sub('\u00ad', '', obj)
        elif isinstance(obj, dict):
            return {k: Extractor.remove_special_characters(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [Extractor.remove_special_characters(item) for item in obj]
        else:
            return obj

    def dump_articles_to_jsonl(self, output_file="data/articles_v1.jsonl"):
        if os.path.exists(output_file):
            os.remove(output_file)
        with jsonlines.open(output_file, mode='w') as writer:
            for article in self.articles:
                article_dict = article.model_dump()
                cleaned_article = Extractor.remove_special_characters(article_dict)
                writer.write(cleaned_article)

