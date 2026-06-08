from scraper import ContentPipeline
from data import SUBJECTS
import sys

pipeline = ContentPipeline()

target_ids = {"social-science", "hindi", "sanskrit", "french", "ai", "it"}

for subject in SUBJECTS:
    if subject["id"] in target_ids:
        print(f"Importing {subject['name']}...")
        pipeline.import_from_data_module([subject], board_id="cbse", board_name="CBSE Class X")

print("Done.")
