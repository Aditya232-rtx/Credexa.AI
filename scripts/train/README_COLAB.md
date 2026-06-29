# Colab Training Instructions

## What to upload to Colab

1. **Dataset** — Upload `casia_combined.zip` to your Google Drive
2. **Notebook** — Upload `colab_train_visual_forensics.ipynb` to Colab

## Steps

### 1. Package the dataset
```bash
# From Credexa.AI root:
cd data
zip -r casia_combined.zip casia_combined/
```
Then upload `casia_combined.zip` to `/content/drive/MyDrive/` in Colab.

### 2. Run the notebook
- Open `colab_train_visual_forensics.ipynb` in Colab
- Runtime → Change runtime type → T4 GPU
- Run all cells
- Training takes ~45-75 min for 75 epochs on a T4 GPU

### 3. Download the model
After training completes, the model `efficientnet_b4_tamper.pth` will automatically download.
Place it in: `models/trained/efficientnet_b4_tamper/efficientnet_b4_tamper.pth`

### Expected results
- **75 epochs, batch=32, T4 GPU:** 93-96% validation accuracy
- **50 epochs:** 91-94%
- **100-150 epochs:** 94-97% (diminishing returns after ~75)
