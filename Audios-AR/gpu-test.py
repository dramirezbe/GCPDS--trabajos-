import torch

print(f"Versión de PyTorch: {torch.__version__}")
print(f"CUDA está disponible: {torch.cuda.is_available()}")
print(f"Nombre del dispositivo CUDA: {torch.cuda.get_device_name(0)}")

# Verifica si un tensor se puede mover a la GPU
x = torch.rand(5, 3)
if torch.cuda.is_available():
    device = "cuda"
    x = x.to(device)
    print(f"Tensor creado en: {x.device}")