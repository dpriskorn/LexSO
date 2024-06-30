from unittest import TestCase

from models.extractor import Extractor


class TestExtractor(TestCase):
    def test_extract_articles(self):
        with open('/home/dpriskorn/src/python/LexSO/test_data/test1.html', 'r', encoding='utf-8') as file:
            html = file.read()
        e = Extractor(html=html)
        e.__extract_articles__()
        assert len(e.articles) > 0
        # print(e.articles)
        first_super_lemma = e.articles[0].lemmalist[0]
        assert first_super_lemma.prefix == "snr"
        assert first_super_lemma.hyphenation == "honung·en"
        assert first_super_lemma.lexical_category == "substantiv"
        lemvar = first_super_lemma.lemvar
        assert lemvar.value == "honung"
        assert lemvar.id_ == "lnr183635"
        infl = lemvar.inflections[0]
        assert infl.value == "honungen"
        lexem = first_super_lemma.lexem
        assert lexem is not None
        assert len(lexem.idioms) == 1
        first_idiom = lexem.idioms[0]
        assert first_idiom.value == "len som honung"
        assert first_idiom.id_ == "inr908304"

    def test_extract_articles_2(self):
        with open('/home/dpriskorn/src/python/LexSO/test_data/test2.html', 'r', encoding='utf-8') as file:
            html = file.read()
        e = Extractor(html=html)
        e.__extract_articles__()
        assert len(e.articles) > 0
        # print(e.articles)
        first_super_lemma = e.articles[0].lemmalist[0]
        # assert first_super_lemma.prefix == "snr"
        # assert first_super_lemma.hyphenation == "honung·en"
        # assert first_super_lemma.lexical_category == "substantiv"
        lemvar = first_super_lemma.lemvar
        # assert lemvar.value == "honung"
        # assert lemvar.id_ == "lnr183635"
        # infl = lemvar.inflections[0]
        # assert infl.value == "honungen"
        lexem = first_super_lemma.lexem
        assert lexem is not None
        assert len(lexem.idioms) == 2
        first_idiom = lexem.idioms[0]
        assert first_idiom.value == "len som en barn­rumpa/persika"
        assert first_idiom.id_ == "inr907973"
        assert first_idiom.definition == "mycket len"
        assert first_idiom.example == "efter rakningen var han len som en barn\xadrumpa om hakan"