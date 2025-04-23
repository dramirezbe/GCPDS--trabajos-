# Mathods Used

## 1. Backbone

- In the context of convolutional NN (works better with images)

Backbone is a feature extractor used in the input of a Convolutional NN, the backbone extracts a certain feature of an image, and then we use the extraction to train more easily the NN (specific architecture).

#### Type of models used to backbone:

- VGGs: Effective in image classification and detection.
- ResNets: Object detection and semantic segmentation
- Inception v1: Most used ConvNN, GoogleNet, used in vode summarization

## 2. Nest Architecture

- Used to fusion different low and high level feature extraction from backbone NN

The neck models are composed of several top-down paths and several bottom-up paths. The idea behind this feature aggregation existing in this model is to allow low-level features to interact more directly with high-level features, by mixing information from this high-level feature with the low-level feature. They reach aggregation and feature interaction across many layers, since the distance between the two feature maps is large.

#### Often used Neck NN:

- PAN
- FPN