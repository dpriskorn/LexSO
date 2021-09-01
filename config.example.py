import os

# Add your credentials from the botpasswords page to your ~/.bashrc or below as
# strings:
username = ""
password = ""

# Global variables
count_only = False
add_no_value = False
tool_url = "Wikidata:Tools/LexSO"
user_agent = f"LexSO (WikidataIntegrator/0.11.0) User:So9q " + tool_url
wd_prefix = "http://www.wikidata.org/entity/"
foreign_id_property = "P9837"
source_item_id = "Q108312794"

login_instance = None
