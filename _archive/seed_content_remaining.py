import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from database import get_conn

SUMMARY_MAP = {}
def add_summary(subj, keywords, summary):
    for kw in keywords:
        SUMMARY_MAP[(subj, kw.lower())] = summary

CHUNK_MAP = {}
def add_chunks(subj, keywords, chunks):
    for kw in keywords:
        CHUNK_MAP[(subj, kw.lower())] = chunks
