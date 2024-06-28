

class SOEntry:
    # TODO support idiom
    # TODO support sentence
    id: str = None
    lemma: str = None
    lexical_category: str = None
    number: int = None

    def __init__(self,
                 id: str = None,
                 lemma: str = None,
                 lexical_category: str = None,
                 number: int = None):
        self.id = id
        self.lemma = lemma
        self.lexical_category = lexical_category
        self.number = number

    def scrape_details(self):
        """Scrape details from SO"""
        pass

    def url(self):
        return f"https://svenska.se/so/?id={self.id}"

    def search_url(self):
        return f"https://svenska.se/so/?sok={self.lemma}"