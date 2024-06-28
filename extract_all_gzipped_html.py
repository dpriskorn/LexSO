from models.extractor import Extractor


def main():
    # Create an instance of the Extractor class
    extractor = Extractor()

    # Call the extract_from_gzip_files method
    extractor.extract_from_gzip_files()
    extractor.dump_articles_to_jsonl()

    # Print the extracted articles
    # for article in extractor.articles:
    #     # Print or process the articles as needed
    #     print(article.model_dump())
    #     print("Year of Publication:", article.year_of_publication)
    #     for superlemma in article.lemmalist:
    #         print("Superlemma ID:", superlemma.id_)
    #         print("Superlemma Value:", superlemma.value)
    #         print("Hyphenation:", superlemma.hyphenation)
    #         print("Lexical Category:", superlemma.lexical_category)
    #         print("Pronounciation url:", superlemma.pronunciation.url)
    #         for inflection in superlemma.lemvar.inflections:
    #             print("Inflection ID:", inflection.id_)
    #             print("Inflection Value:", inflection.value)


if __name__ == "__main__":
    main()
