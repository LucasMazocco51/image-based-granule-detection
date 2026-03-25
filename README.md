# 🌱 Image-Based Granule Detection

Computer vision-based system for detecting and counting fertilizer granules from images, supporting spreader calibration in precision agriculture.

---

## 📖 Overview

This project introduces an automated approach using classical image processing techniques to quantify fertilizer granules from images.

---

## 🧠 Methodology

The processing pipeline consists of three main steps:

* **Geometric correction** — corrects image perspective
* **HSV-based segmentation** — isolates granules from the background
* **Contour detection** — identifies and counts individual granules

---

## 🚀 Usage

### Clone the repository

```bash
git clone https://github.com/LucasMazocco51/image-based-granule-detection.git
cd image-based-granule-detection
```

### Install dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Run (CLI pipeline)

Run the processing pipeline using input images:

```bash
python scripts/run_pipeline.py --images "data/SD FC 10.jpg" "data/SD FC 10_2.jpg"
```

> Provide between 2 and 6 images for comparison.

---

## 🖥️ Run GUI (optional)

Launch the graphical interface:

```bash
python app/App_gui.py
```

---

## 🗂️ Project Structure

```
app/        # GUI and application scripts  
src/        # Core processing modules  
scripts/    # Pipeline execution (CLI)  
data/       # Sample images  
```

---

## 📌 Notes

* Includes sample images for testing
* Full datasets are not included
---
