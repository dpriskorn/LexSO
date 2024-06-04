import uuid
from pprint import pprint
from typing import List
from bs4 import BeautifulSoup
from pydantic import BaseModel


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
    prefix: str = "lnr"
    inflections: List[Inflection] = []

    @classmethod
    def from_soup(cls, soup):
        if soup is None:
            return None
        id_ = soup.get("id", "")
        value = soup.find("span", class_="orto").text.strip() if soup.find("span", class_="orto") else ""
        inflection_soup = soup.find("span", class_="bojning_inline")
        inflections = [Inflection.from_soup(inflection_soup)] if inflection_soup else []
        return cls(id_=id_, value=value, inflections=inflections)


class Pronounciation(BaseModel):
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


class Lexem(DictionaryElement):
    """This equals a sense in the Wikidata lexicographic model"""
    prefix: str = "xnr"
    kernels: List[Kernel]
    see_alsos: List[SeeAlso]

    @classmethod
    def from_soup(cls, soup):
        if soup is None:
            return None
        id_ = soup.get("id", "")
        kernels_soup = soup.find_all("span", class_="kbetydelse")
        kernels = [Kernel.from_soup(kernel) for kernel in kernels_soup if kernel is not None]
        see_alsos_soup = soup.find_all("a", class_="hvtag")
        see_alsos = [SeeAlso.from_soup(see_also) for see_also in see_alsos_soup if see_also is not None]
        return cls(id_=id_, value=id_, kernels=kernels, see_alsos=see_alsos)


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


class Extractor(BaseModel):
    html_content: str
    articles: List[Article] = []

    def extract_articles(self):
        # Parse the HTML content
        soup = BeautifulSoup(self.html_content, 'lxml')

        # Find all div elements with class="artikel so"
        article_divs = soup.find_all('div', class_='artikel so')

        for article_div in article_divs:
            # Extract the article
            article = Article.from_soup(article_div)
            if article:
                self.articles.append(article)


# Example usage:
html_content = '''
<!DOCTYPE html>
<section class="post_content clearfix" itemprop="articleBody">
    <div class="panel-layout" id="pl-18">
        <div class="panel-grid panel-no-style" id="pg-18-0">
            <div class="panel-grid-cell" id="pgc-18-0-0">
                <div class="so-panel widget_execphp panel-first-child panel-last-child" data-index="0"
                     id="panel-18-0-0-0">
                    <div class="execphpwidget">
                        <div class="treval"><span class="flik ovald"><a class="t_val"
                                                                        href="/saol/?sok=homografi&amp;pz=4"
                                                                        onclick="tracklink('tabb','saol','/saol/?sok=homografi&amp;pz=4'); return false;">   SAOL   </a> </span><span
                                class="flik vald">   SO   </span><span class="flik ovald"><a class="t_val"
                                                                                             href="/saob/?sok=homografi&amp;pz=4"
                                                                                             onclick="tracklink('tabb','saob','/saob/?sok=homografi&amp;pz=4'); return false;">   SAOB   </a> </span><span
                                class="flik ovald treo"><a class="t_val" href="/tre/?sok=homografi&amp;pz=8"
                                                           onclick="tracklink('tabb', 'tre', '/tre/?sok=homografi&amp;pz=8'); return false;">   Alla tre   </a></span><span
                                class="homelink"></span></div>
                        <div class="bldtxt"><img class="third" src="/img/b2.png"/><span> SO </span></div>
                        <div class="pid_left"><span class="long h2">Svensk ordbok</span></div>
                    </div>
                </div>
            </div>
        </div>
        <div class="panel-grid panel-no-style" id="pg-18-1">
            <div class="panel-grid-cell" id="pgc-18-1-0">
                <div class="so-panel widget_execphp panel-first-child panel-last-child" data-index="1"
                     id="panel-18-1-0-0">
                    <div class="execphpwidget">
                        <div class="artikel so">
                            <div class="spaltnr"><span class="tryck">publicerad: 2021   </span></div>
                            <div class="lemmalista">
                                <div class="superlemma" id="snr173308">
                                    <div class="lemvar">
<span class="lemvarhuvud" id="lnr800182">
<span class="orto">homografi</span>
<span class="bojning_inline" id="boj800182"><span class="bojning">homografin</span></span>
</span>
                                    </div>
                                    <span class="avstav">homo·grafin</span>
                                    <div class="ordklass">substantiv</div>
                                    <div class="uttalblock">
                                        <span class="uttal">homografi<span class="condensed_accent">´</span><a
                                                class="ljudfil" href="#!" onclick="playAudioForLemma('800182_1');"> <img
                                                class="unicode_img" src="/speaker.png"/> </a></span>
                                    </div>
                                    <div class="lexemdiv">
                                        <div class="lexem" id="xnr800183">
<span class="kernel">
<span class="kbetydelse" id="kcnr800184"><span class="punkt">●</span>
<span class="def">det att ord (lemman) har samma stavning</span> <span class="deft">men olika ut­tal och (vanligen) olika betydelse</span>
</span>
<div class="hv"><span class="hvtyp">JFR</span>
<a class="hvtag" href="/so/?id=131071&amp;ref=xnr800180" target="_parent">homofoni 2</a>
</div>
</span>
                                            <span class="expansion collapsed"
                                                  onclick="jQuery(this).toggleClass('collapsed')"></span><span
                                                class="detaljer">
<div class="etymologiblock"><span class="etymologi" id="etynr812303">
<span class="fb">belagt sedan 1960-talet</span>
</span>
</div>
</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>
'''

extractor = Extractor(html_content=html_content)
extractor.extract_articles()

for article in extractor.articles:
    pprint(article.model_dump())
    print("Year of Publication:", article.year_of_publication)
    for superlemma in article.lemmalist:
        print("Superlemma ID:", superlemma.id_)
        print("Superlemma Value:", superlemma.value)
        print("Hyphenation:", superlemma.hyphenation)
        print("Lexical Category:", superlemma.lexical_category)
        print("Pronounciation url:", superlemma.pronunciation.url)
        for inflection in superlemma.lemvar.inflections:
            print("Inflection ID:", inflection.id_)
            print("Inflection Value:", inflection.value)
