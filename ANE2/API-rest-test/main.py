from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

from pymongo import MongoClient

db = MongoClient('mongodb://localhost:27017/')

