# LexSO
**Note: [a bot request has been filed](https://www.wikidata.org/wiki/Wikidata:Requests_for_permissions/Bot#So9qBot_6)**

Add SO identifier to Wikidata Lexemes [Wikidata Property:P9837](https://www.wikidata.org/wiki/Property:P9837). 

This script is maybe not that useful to run for anyone else besides the author in its current form. It is shared here to help others get started writing scripts to improve Wikidata.

It would be interesting to edit it to monitor the SO website for newly published articles/words.

This script can easily be modified to create new lexemes for every word found in the list from SO. Unfortunately that is not legal because of the database protection law.

## Thanks
Big thanks to Magnus Sälgö for reverse engineering of the SAOB website to make this possible. <3

## Requirements
See the requirements file

Install using pip:
`$ sudo pip install -r

If pip fails with errors related to python 2.7 you need to upgrade your OS. E.g. if you are using an old version of Ubuntu like 18.04.

## Getting started
Please create a bot password for running the script for
safety reasons here: https://www.wikidata.org/wiki/Special:BotPasswords

Copy config.example.py to config.py yourself and adjust the following
content:

username = "username"
password= "password"

# License
All code except get_so_list.py is GPLv3+