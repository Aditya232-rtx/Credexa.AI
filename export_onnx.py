import sys
import torch
import onnx
from transformers import LayoutLMv3ForTokenClassification, LayoutLMv3Processor
from onnxruntime.quantization import quantize_dynamic, QuantType
import PIL.Image
import os

def export_to_onnx():
    try:
        processor = LayoutLMv3Processor.from_pretrained("nielsr/layoutlmv3-finetuned-funsd", apply_ocr=False)
        model = LayoutLMv3ForTokenClassification.from_pretrained("nielsr/layoutlmv3-finetuned-funsd")
        model.eval()

        image = PIL.Image.new("RGB", (224, 224), (255, 255, 255))
        words = ["hello", "world"]
        boxes = [[0, 0, 10, 10], [10, 10, 20, 20]]

        encoding = processor(image, text=words, boxes=boxes, return_tensors="pt")

        input_names = list(encoding.keys())
        output_names = ["logits"]

        onnx_path = "layoutlmv3.onnx"
        quantized_path = "layoutlmv3_quantized.onnx"

        torch.onnx.export(
            model,
            args=tuple(encoding.values()),
            f=onnx_path,
            input_names=input_names,
            output_names=output_names,
            dynamic_axes={name: {0: "batch_size", 1: "sequence_length"} for name in input_names + output_names},
            opset_version=14,
        )

        quantize_dynamic(onnx_path, quantized_path, weight_type=QuantType.QUInt8)

        print(f"ONNX export complete: {quantized_path} ({os.path.getsize(quantized_path) / (1024 * 1024):.2f} MB)")
    except Exception as e:
        print(f"Export failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    export_to_onnx()
