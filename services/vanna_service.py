import os

from dotenv import load_dotenv
from openai import OpenAI

from vanna.chromadb import ChromaDB_VectorStore
from vanna.openai import OpenAI_Chat

# from vanna.qdrant import Qdrant_VectorStore

load_dotenv()


class Vanna(ChromaDB_VectorStore, OpenAI_Chat):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(
            self,
            client=OpenAI(
                base_url=os.getenv("OPENAI_API_BASE"), api_key=os.getenv("OPENAI_API_KEY")
            ),
            config={"model": os.getenv("OPENAI_MODEL")},
        )
