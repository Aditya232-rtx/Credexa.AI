import sys
import torch
import os
from transformers import LayoutLMv3ForTokenClassification

def main():
    try:
        torch.backends.quantized.engine = 'qnnpack'
        model = LayoutLMv3ForTokenClassification.from_pretrained("nielsr/layoutlmv3-finetuned-funsd")

        torch.save(model.state_dict(), "original_model.pt")
        orig_size = os.path.getsize("original_model.pt") / (1024 * 1024)
        print(f"Original Model Size: {orig_size:.2f} MB")

        quantized_model = torch.quantization.quantize_dynamic(
            model,
            {torch.nn.Linear},
            dtype=torch.qint8
        )

        quantized_path = "layoutlmv3_quantized.pt"
        torch.save(quantized_model, quantized_path)

        q_size = os.path.getsize(quantized_path) / (1024 * 1024)
        print(f"Quantized Model Size: {q_size:.2f} MB ({(1 - q_size/orig_size)*100:.1f}% reduction)")
    except Exception as e:
        print(f"Export failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
