# image-based-granule-detection
Image-Based Granule Detection for Fertilizer Distribution Monitoring

This repository contains a computer vision-based system for detecting and counting fertilizer granules from images, supporting spreader calibration in precision agriculture.

Overview

The method uses classical image processing techniques to automate granule quantification, reducing the need for manual tray-based evaluation.

The pipeline includes:

Geometric correction
HSV-based segmentation
Contour-based granule detection
Usage

Clone the repository and install dependencies:

git clone https://github.com/your-username/granule-detection.git
cd granule-detection
pip install -r requirements.txt

Run the pipeline:

python scripts/run_pipeline.py
Structure
app/        # GUI and application scripts  
src/        # Core processing modules  
scripts/    # Execution scripts  
data/       # Sample images  
