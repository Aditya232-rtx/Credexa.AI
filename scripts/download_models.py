import os
import sys

def download_models():
    # If HF_HUB_OFFLINE is set, assume models are already downloaded, so don't attempt download unless forced
    if os.environ.get("HF_HUB_OFFLINE") == "1":
        print("HF_HUB_OFFLINE=1, skipping download.")
        return

    print("Downloading HuggingFace models for offline use...")
    try:
        from transformers import AutoModel, AutoTokenizer
        
        # 1. LayoutLMv3
        print("Downloading nielsr/layoutlmv3-finetuned-funsd...")
        AutoModel.from_pretrained("nielsr/layoutlmv3-finetuned-funsd")
        AutoTokenizer.from_pretrained("nielsr/layoutlmv3-finetuned-funsd")

        # 2. MiniLM (Sentence Transformers) - if used anywhere
        print("Downloading all-MiniLM-L6-v2...")
        AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
        AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

        print("Models downloaded successfully to HuggingFace cache.")
    except Exception as e:
        print(f"Error downloading models: {e}")
        sys.exit(1)

if __name__ == "__main__":
    download_models()
