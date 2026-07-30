# Dataset Sources

This project is prepared for YOLOv8 fine-tuning with the four existing road-damage
classes:

```text
0 = Longitudinal Crack
1 = Transverse Crack
2 = Alligator Crack
3 = Potholes
```

The online dataset selected for the starter fine-tuning dataset is RDD2022 from the
Crowdsensing-based Road Damage Detection Challenge (CRDDC'2022).

Source:

```text
https://github.com/sekilab/RoadDamageDetector
https://figshare.com/articles/dataset/RDD2022_-_The_multi-national_Road_Damage_Dataset_released_through_CRDDC_2022/21431547
```

Subset used by default:

```text
RDD2022_China_MotorBike.zip
https://bigdatacup.s3.ap-northeast-1.amazonaws.com/2022/CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/RDD2022_China_MotorBike.zip
```

Class mapping:

```text
D00 -> 0 Longitudinal Crack
D10 -> 1 Transverse Crack
D20 -> 2 Alligator Crack
D40 -> 3 Potholes
```

The original RDD2022 train annotations are Pascal VOC XML files. Use
`scripts/prepare_rdd2022_dataset.py` to download the source data and convert it to
YOLO label files.

Fast streamed starter source:

```text
https://huggingface.co/datasets/TamAko783/Unified_Road_Defect_Dataset
```

This Hugging Face dataset is already arranged for Ultralytics YOLO and uses the
same four-class CRDDC schema. Use `scripts/prepare_hf_unified_dataset.py` to stream
a practical subset without downloading the multi-gigabyte archives.
