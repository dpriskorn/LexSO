#!/usr/bin/env python3
# Licensed under GPLv3+ i.e. GPL version 3 or later.
import logging
from csv import reader
from time import sleep
from typing import List, Dict
from urllib.parse import urlparse, parse_qsl

from wikibaseintegrator import wbi_login
from wikibaseintegrator import wbi_config

import config
from models import wikidata, so
from modules.console import console

# Constants
from models.wikidata import LexemeLanguage, ForeignID

wd_prefix = "http://www.wikidata.org/entity/"
count_only = False

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Pseudo code
# first it gets all swedish lexemes
# opens the list of entries in dictionary
# tries to match each lexeme to an entry
# if match found
## uploads
# else
# add no-value to the lexeme


def match_lexical_category(lexeme: wikidata.Lexeme = None,
                           entry: so.SOEntry = None) -> bool:
    logger = logging.getLogger(__name__)
    if lexeme is None or entry is None:
        raise ValueError("Did not get the arguments needed")
    # TODO find out what the number means and how it affects the matching
    logger.debug(f"dictionary number: {entry.number}")
    # if not count_only:
    #     logger.info(f"found match: category: {dictionary_entry.lexical_category} id: {dictionary_entry.id}")
    # check if categories match
    category = None
    if entry.lexical_category == "" or entry.lexical_category is None:
        if not count_only:
            logging.info("No category found")
    elif "verb" in entry.lexical_category:
        category = "Q24905"
    elif "subst" in entry.lexical_category:
        if "-" in entry.lemma:
            # handle affixes like -fil also being marked as subst in dictionary
            category = "Q62155"
        else:
            category = "Q1084"
    elif "adj" in entry.lexical_category:
        category = "Q34698"
    elif "adv" in entry.lexical_category:
        category = "Q380057"
    elif "konj" in entry.lexical_category:
        category = "Q36484"
    elif "interj" in entry.lexical_category:
        category = "Q83034"
    elif "prep" in entry.lexical_category:
        category = "Q4833830"
    elif "räkn" in entry.lexical_category:
        category = "Q63116"
    elif "artikel" in entry.lexical_category:
        category = "Q103184"
    elif "pron" in entry.lexical_category:
        category = "Q36224"
    elif (
            entry.lexical_category == "prefix" or
            entry.lexical_category == "suffix" or
            entry.lexical_category == "affix"
    ):
        category = "Q62155"
    elif (
        # this covers all special cases like this one: https://svenska.se/dictionary/?id=O_0283-0242.Qqdq&pz=5
        "(" in entry.lexical_category or
        "ssgled" in entry.lexical_category
    ):
        # ignore silently
        return False
    else:
        if not count_only:
            logging.error(f"Did not recognize category "
                          f"{entry.lexical_category} on "
                          f"{entry.url()}, skipping")
            return False
    if category is not None:
        if category == lexeme.lexical_category:
            return True
        else:
            if not count_only:
                logging.info("Categories did not match, skipping")
            return False


def load_dictionary_into_memory():
    # load all saab words into a list that can be searched
    # load all saab ids into a list we can lookup in using the index.
    # the two lists above have the same index.
    # load all dictionary lines into a dictionary with count as key and list in the value
    #list[0] = dictionary_category
    #list[1] = number
    #list[2] = id
    #list[3] = word
    with console.status("Loading dictionary into memory..."):
        dictionary_lemma_list = []
        dictionary_data = {}
        # open file in read mode
        with open('so_2021-09-01.csv', 'r', encoding="UTF-8") as read_obj:
            # pass the file object to reader() to get the reader object
            csv_reader = reader(read_obj)
            count = 0
            # Iterate over each row in the csv using reader object
            for row in csv_reader:
                # row variable is a list that represents a row in csv
                #row0 is null
                word = row[1]
                dictionary_category = row[2]
                if row[3] == '':
                    dictionary_number = 0
                else:
                    dictionary_number = int(row[3])
                url = urlparse(row[4])
                # print(url.query)
                dictionary_id = dict(parse_qsl(url.query))["id"]
                if "_" in dictionary_id:
                    logger.debug(f"Detected underscore id {dictionary_id}")
                    # We hardcode to always return 1 after the underscore
                    dictionary_id = dictionary_id[0:dictionary_id.find("_")] + "_1"
                    logger.debug(f"Hardcoded to {dictionary_id}")
                # Create object
                entry = so.SOEntry(
                    id=dictionary_id,
                    lexical_category=dictionary_category,
                    number=dictionary_number,
                    lemma=word
                )
                dictionary_data[count] = entry #[dictionary_category, dictionary_number, dictionary_id, word]
                dictionary_lemma_list.append(word)
                count += 1
    print(f"Finished loading {count} dictionary lines")
    return dictionary_lemma_list, dictionary_data


def process_lexemes(lexeme_lemma_list: List = None,
                    lexemes_data: Dict = None,
                    dictionary_lemma_list: List = None,
                    dictionary_data: Dict = None):
    """Go though each lexeme and try to match with SO"""
    if (
        lexeme_lemma_list is None or
        lexemes_data is None or
        dictionary_lemma_list is None or
        dictionary_data is None
    ):
        logger.exception("Did not get what we need")
    lexemes_count = len(lexeme_lemma_list)
    # go through all lexemes missing dictionary identifier
    match_count = 0
    processed_count = 0
    skipped_multiple_matches = 0
    no_value_count = 0
    if count_only:
        print("Counting all matches that can be uploaded")
    for lemma in lexeme_lemma_list:
        if processed_count > 0 and processed_count % 1000 == 0:
            print(f"Processed {processed_count} lexemes out of "
                  f"{lexemes_count} ({round(processed_count * 100 / lexemes_count)}%)")
        lexeme: wikidata.Lexeme = lexemes_data[lemma]
        if not count_only:
            logging.info(f"Working on {lexeme.id}: {lexeme.lemma} {lexeme.lexical_category}")
        if lexeme.lemma in dictionary_lemma_list:
            for index, dictionary_lemma in enumerate(dictionary_lemma_list):
                if lexeme.lemma == dictionary_lemma:
                    # We found a lemma-match!
                    entry = dictionary_data[index]
                    # Check if the lexical categories match also
                    result = match_lexical_category(lexeme=lexeme,
                                                    entry=entry)
                    if result:
                        match_count += 1
                        if not count_only:
                            lexeme.upload_foreign_id_to_wikidata(foreign_id=ForeignID(
                                id=entry.id,
                                property=config.foreign_id_property,
                                source_item_id=config.source_item_id
                            ))
                        # Pick only the first search result in the dictionary wordlist
                        break
        else:
            if not count_only:
                console.print(f"[red]{lexeme.lemma} not found in dictionary wordlist, "
                                f"see 'https://svenska.se/so/?sok={lexeme.lemma}'")
                if config.add_no_value:
                    # Add dictionary=no_value to lexeme
                    lexeme.upload_foreign_id_to_wikidata(foreign_id=ForeignID(
                        property=config.foreign_id_property,
                        no_value=True
                    ))
                else:
                    # sleep to give the user time to read the warning above
                    sleep(3)
            no_value_count += 1
        processed_count += 1
    print(f"Processed {processed_count} lexemes. "
          f"Found {match_count} matches "
          f"out of which {skipped_multiple_matches} "
          f"was skipped because they had multiple entries "
          f"with the same lexical category. {no_value_count} "
          f"entries with no main entry in dictionary was found")


def main():
    if not count_only:
        with console.status("Logging in with WikibaseIntegrator..."):
            config.login_instance = wbi_login.Login(
                user=config.username, pwd=config.password
            )
            # Set User-Agent
            wbi_config.config["USER_AGENT_DEFAULT"] = config.user_agent
    language = LexemeLanguage("sv")
    language.fetch_all_lexemes_without_so_id()
    lexemes_list = language.lemma_list()
    lexemes_data = language.data_dictionary_with_lemma_as_key()
    dictionary_list, dictionary_data = load_dictionary_into_memory()
    process_lexemes(lexeme_lemma_list=lexemes_list, lexemes_data=lexemes_data, dictionary_lemma_list=dictionary_list,
                    dictionary_data=dictionary_data)


if __name__ == "__main__":
    main()
