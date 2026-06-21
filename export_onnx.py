import torch
import onnx
from transformers import LayoutLMv3ForTokenClassification, LayoutLMv3Processor
from onnxruntime.quantization import quantize_dynamic, QuantType
import PIL.Image
import os

def export_to_onnx():
    print("Loading processor and model...")
    processor = LayoutLMv3Processor.from_pretrained("nielsr/layoutlmv3-finetuned-funsd", apply_ocr=False)
    model = LayoutLMv3ForTokenClassification.from_pretrained("nielsr/layoutlmv3-finetuned-funsd")
    model.eval()

    # Create dummy inputs
    image = PIL.Image.new("RGB", (224, 224), (255, 255, 255))
    words = ["hello", "world"]
    boxes = [[0, 0, 10, 10], [10, 10, 20, 20]]
    
    encoding = processor(image, text=words, boxes=boxes, return_tensors="pt")
    
    print("Encoding keys:", encoding.keys())
    
    # Some older transformers versions don't return bbox for layoutlmv3 if apply_ocr=False? No, they should.
    
    input_names = list(encoding.keys())
    output_names = ["logits"]

    onnx_path = "layoutlmv3.onnx"
    quantized_path = "layoutlmv3_quantized.onnx"

    print("Exporting to ONNX...")
    inputs = tuple(encoding[k] for k in input_names)
    
    dynamic_axes = {k: {0: "batch_size", 1: "sequence_length"} for k in input_names if k != "pixel_values"}
    if "pixel_values" in input_names:
        dynamic_axes["pixel_values"] = {0: "batch_size"}
    dynamic_axes["logits"] = {0: "batch_size", 1: "sequence_length"}

    torch.onnx.export(
        model,
        inputs,
        onnx_path,
        input_names=input_names,
        output_names=output_names,
        dynamic_axes=dynamic_axes,
        opset_version=14,
        do_constant_folding=True
    )
    
    # Save id2label
    import json
    with open("layoutlmv3_id2label.json", "w") as f:
        json.dump(model.config.id2label, f)
    
    print("Quantizing ONNX model...")
    quantize_dynamic(onnx_path, quantized_path, weight_type=QuantType.QUInt8)
    
    print(f"Done! Saved {quantized_path} (Size: {os.path.getsize(quantized_path) / (1024*1024):.2f} MB)")

if __name__ == "__main__":
    export_to_onnx()
