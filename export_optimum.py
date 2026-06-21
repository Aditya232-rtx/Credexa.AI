from optimum.onnxruntime import ORTModelForTokenClassification
from transformers import LayoutLMv3Processor
from onnxruntime.quantization import quantize_dynamic, QuantType
import json
import os

def main():
    print("Loading processor to save id2label...")
    processor = LayoutLMv3Processor.from_pretrained("nielsr/layoutlmv3-finetuned-funsd", apply_ocr=False)
    
    print("Exporting with Optimum...")
    model = ORTModelForTokenClassification.from_pretrained("nielsr/layoutlmv3-finetuned-funsd", export=True)
    model.save_pretrained("./layoutlmv3_onnx")
    
    with open("layoutlmv3_id2label.json", "w") as f:
        json.dump(model.config.id2label, f)
        
    print("Quantizing ONNX model...")
    onnx_path = "./layoutlmv3_onnx/model.onnx"
    quantized_path = "layoutlmv3_quantized.onnx"
    
    quantize_dynamic(onnx_path, quantized_path, weight_type=QuantType.QUInt8)
    
    print(f"Done! Saved {quantized_path} (Size: {os.path.getsize(quantized_path) / (1024*1024):.2f} MB)")

if __name__ == "__main__":
    main()
