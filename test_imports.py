try:
    from fastapi import FastAPI, File, Form, HTTPException, UploadFile
    print("FastAPI ok")
    from fastapi.middleware.cors import CORSMiddleware
    print("FastAPI CORS ok")
    import spacy
    print("spacy ok")
    from rapidfuzz import fuzz
    print("rapidfuzz ok")
    import pikepdf
    print("pikepdf ok")
    import numpy as np
    print("numpy ok")
    from PIL import Image, ImageChops
    print("PIL ok")
    import fitz
    print("fitz ok")
    import pdfplumber
    print("pdfplumber ok")
    from rapidocr_onnxruntime import RapidOCR
    print("RapidOCR ok")
    from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification, LayoutLMv3Model
    print("Transformers ok")
    from cryptography.fernet import Fernet
    print("Cryptography ok")
    from dotenv import load_dotenv
    print("Dotenv ok")
    from celery import Celery
    print("Celery ok")
    import torch
    print("Torch ok")
    print('All imports successful!')
except Exception as e:
    import traceback
    traceback.print_exc()
