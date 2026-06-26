from pathlib import Path
import soundfile as sf
import numpy as np
import torch
import torch.nn as nn
from torch.nn.utils.parametrizations import weight_norm
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import gc
import optuna

# --- Module 1: Data Loading ---
class AudioProcessor:
    """Processes a folder of .wav audio files for the model."""
    def __init__(self, audio_folder_path: str):
        self.audio_folder_path = Path(audio_folder_path)
        self.audio_files, self.audio_names, self.max_length = [], [], 0

    def _get_wav_files(self):
        for file_path in sorted(self.audio_folder_path.glob("*.wav")):
            self.audio_files.append(file_path)
            self.audio_names.append(file_path.name)

    def _find_max_length(self):
        for file_path in self.audio_files:
            try:
                with sf.SoundFile(str(file_path), 'r') as f:
                    if f.frames > self.max_length: self.max_length = f.frames
            except Exception as e: print(f"Could not read {file_path}: {e}")

    def process_audios(self):
        self._get_wav_files()
        if not self.audio_files: return np.array([]), []
        self._find_max_length()
        processed_audios = []
        for file_path in self.audio_files:
            try:
                audio_data, _ = sf.read(str(file_path), dtype="float32", always_2d=True)
                mono_audio = np.mean(audio_data, axis=1) if audio_data.shape[1] > 1 else audio_data[:, 0]
                padded_data = np.pad(mono_audio, (0, self.max_length - mono_audio.shape[0]), 'constant')
                processed_audios.append(padded_data)
            except Exception as e: print(f"Failed to process {file_path}: {e}")
        return np.vstack(processed_audios), self.audio_names if processed_audios else (np.array([]), [])

# --- Module 2: TCN Model Definition (from scratch) ---
class Chomp1d(nn.Module):
    def __init__(self, chomp_size): super(Chomp1d, self).__init__(); self.chomp_size = chomp_size
    def forward(self, x): return x[:, :, :-self.chomp_size].contiguous()

class TemporalBlock(nn.Module):
    def __init__(self, n_inputs, n_outputs, kernel_size, stride, dilation, padding, dropout=0.2):
        super(TemporalBlock, self).__init__()
        self.conv1 = weight_norm(nn.Conv1d(n_inputs, n_outputs, kernel_size, stride=stride, padding=padding, dilation=dilation))
        self.chomp1 = Chomp1d(padding); self.relu1 = nn.ReLU(); self.dropout1 = nn.Dropout(dropout)
        self.conv2 = weight_norm(nn.Conv1d(n_outputs, n_outputs, kernel_size, stride=stride, padding=padding, dilation=dilation))
        self.chomp2 = Chomp1d(padding); self.relu2 = nn.ReLU(); self.dropout2 = nn.Dropout(dropout)
        self.net = nn.Sequential(self.conv1, self.chomp1, self.relu1, self.dropout1, self.conv2, self.chomp2, self.relu2, self.dropout2)
        self.downsample = nn.Conv1d(n_inputs, n_outputs, 1) if n_inputs != n_outputs else None
        self.relu = nn.ReLU(); self.init_weights()
    def init_weights(self):
        self.conv1.weight.data.normal_(0, 0.01); self.conv2.weight.data.normal_(0, 0.01)
        if self.downsample is not None: self.downsample.weight.data.normal_(0, 0.01)
    def forward(self, x):
        out = self.net(x); res = x if self.downsample is None else self.downsample(x)
        return self.relu(out + res)

class TemporalConvNet(nn.Module):
    def __init__(self, num_inputs, num_channels, kernel_size=2, dropout=0.2):
        super(TemporalConvNet, self).__init__()
        layers = []
        for i, out_channels in enumerate(num_channels):
            dilation_size = 2 ** i; in_channels = num_inputs if i == 0 else num_channels[i-1]
            layers.append(TemporalBlock(in_channels, out_channels, kernel_size, stride=1, dilation=dilation_size, padding=(kernel_size-1) * dilation_size, dropout=dropout))
        self.network = nn.Sequential(*layers)
    def forward(self, x): return self.network(x)

class TCNAutoencoder(nn.Module):
    def __init__(self, input_channels, output_channels, num_channels, kernel_size, dropout):
        super(TCNAutoencoder, self).__init__()
        self.tcn = TemporalConvNet(input_channels, num_channels, kernel_size=kernel_size, dropout=dropout)
        self.decoder = nn.Conv1d(in_channels=num_channels[-1], out_channels=output_channels, kernel_size=3, padding='same')
    def forward(self, x):
        x = x.permute(0, 2, 1); encoded = self.tcn(x); decoded = self.decoder(encoded)
        return decoded.permute(0, 2, 1)

# --- Module 3: Performance Metrics ---
class PerformanceMetrics:
    @staticmethod
    def signal_to_noise_ratio(original, reconstructed):
        signal_power = torch.mean(original ** 2); noise_power = torch.mean((original - reconstructed) ** 2)
        return 10 * torch.log10(signal_power / noise_power) if noise_power > 0 else float('inf')
    @staticmethod
    def peak_signal_to_noise_ratio(original, reconstructed):
        max_signal = torch.max(torch.abs(original)); mse = torch.mean((original - reconstructed) ** 2)
        return 20 * torch.log10(max_signal / torch.sqrt(mse)) if mse > 0 else float('inf')

# --- Module 4: The Trainer Class ---
class TCNTrainer:
    def __init__(self, model, device, lr=0.001, epochs=100):
        self.model = model.to(device)
        self.device = device
        self.lr = lr
        self.epochs = epochs
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.lr)
        self.criterion = nn.MSELoss()
        self.history = {'train_loss': [], 'val_loss': [], 'val_mae': [], 'val_snr': [], 'val_psnr': []}

    def _create_dataloaders(self, X_train, X_val, chunk_size, batch_size):
        def _create_chunks(data_matrix, chunk_size):
            num_files, total_length = data_matrix.shape
            chunks_per_file = total_length // chunk_size
            return np.reshape(data_matrix, (num_files * chunks_per_file, chunk_size))

        train_chunks = _create_chunks(X_train, chunk_size)
        val_chunks = _create_chunks(X_val, chunk_size)
        X_train_t = torch.tensor(train_chunks, dtype=torch.float32).unsqueeze(-1)
        X_val_t = torch.tensor(val_chunks, dtype=torch.float32).unsqueeze(-1)
        train_dataset = TensorDataset(X_train_t, X_train_t.clone())
        val_dataset = TensorDataset(X_val_t, X_val_t.clone())
        return DataLoader(train_dataset, batch_size=batch_size, shuffle=True), DataLoader(val_dataset, batch_size=batch_size)

    def train(self, X_train, X_val, chunk_size, batch_size):
        train_loader, val_loader = self._create_dataloaders(X_train, X_val, chunk_size, batch_size)
        print(f"Starting training for {self.epochs} epochs...")
        for epoch in range(self.epochs):
            self.model.train()
            train_loss = 0
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(self.device), targets.to(self.device)
                self.optimizer.zero_grad(); outputs = self.model(inputs)
                loss = self.criterion(outputs, targets); loss.backward(); self.optimizer.step()
                train_loss += loss.item()
            
            self.model.eval()
            val_loss, val_mae, val_snr, val_psnr = 0.0, 0.0, 0.0, 0.0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(self.device), targets.to(self.device)
                    outputs = self.model(inputs)
                    val_loss += self.criterion(outputs, targets).item()
                    val_mae += nn.L1Loss()(outputs, targets).item()
                    val_snr += PerformanceMetrics.signal_to_noise_ratio(targets, outputs).item()
                    val_psnr += PerformanceMetrics.peak_signal_to_noise_ratio(targets, outputs).item()

            avg_train_loss = train_loss / len(train_loader)
            avg_val_loss = val_loss / len(val_loader)
            self.history['train_loss'].append(avg_train_loss)
            self.history['val_loss'].append(avg_val_loss)
            self.history['val_mae'].append(val_mae / len(val_loader))
            self.history['val_snr'].append(val_snr / len(val_loader))
            self.history['val_psnr'].append(val_psnr / len(val_loader))
            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch+1}/{self.epochs} - Train Loss: {avg_train_loss:.6f}, Val Loss: {avg_val_loss:.6f}")
        
        del train_loader, val_loader
        gc.collect(); torch.cuda.empty_cache()

    def evaluate(self, X_test, chunk_size):
        print("\nEvaluating model on the test set...")
        self.model.eval()
        original_audios, reconstructed_audios = [], []
        with torch.no_grad():
            for i in range(X_test.shape[0]):
                full_original = X_test[i, :]
                num_chunks = full_original.shape[0] // chunk_size
                test_chunks = np.reshape(full_original, (num_chunks, chunk_size))
                reconstructed_chunks = []
                for chunk in test_chunks:
                    chunk_tensor = torch.tensor(chunk, dtype=torch.float32).unsqueeze(0).unsqueeze(-1).to(self.device)
                    reconstructed_chunk = self.model(chunk_tensor).squeeze().cpu().numpy()
                    reconstructed_chunks.append(reconstructed_chunk)
                original_audios.append(full_original)
                reconstructed_audios.append(np.concatenate(reconstructed_chunks))
        original = np.array(original_audios); reconstructed = np.array(reconstructed_audios)
        results = {
            "MSE": np.mean((original - reconstructed) ** 2),
            "MAE": np.mean(np.abs(original - reconstructed)),
            "SNR": np.mean([PerformanceMetrics.signal_to_noise_ratio(torch.tensor(o), torch.tensor(r)) for o, r in zip(original, reconstructed)]),
            "PSNR": np.mean([PerformanceMetrics.peak_signal_to_noise_ratio(torch.tensor(o), torch.tensor(r)) for o, r in zip(original, reconstructed)])
        }
        return results

    def plot_history(self):
        fig, axs = plt.subplots(2, 2, figsize=(15, 10)); fig.suptitle('Model Training History')
        axs[0, 0].plot(self.history['train_loss'], label='Training Loss')
        axs[0, 0].plot(self.history['val_loss'], label='Validation Loss')
        axs[0, 0].set_title('Loss Over Epochs'); axs[0, 0].set_xlabel('Epochs'); axs[0, 0].set_ylabel('Loss (MSE)'); axs[0, 0].legend(); axs[0, 0].grid(True)
        axs[0, 1].plot(self.history['val_mae'], label='Validation MAE', color='orange')
        axs[0, 1].set_title('Validation MAE Over Epochs'); axs[0, 1].set_xlabel('Epochs'); axs[0, 1].set_ylabel('Mean Absolute Error'); axs[0, 1].legend(); axs[0, 1].grid(True)
        axs[1, 0].plot(self.history['val_snr'], label='Validation SNR', color='green')
        axs[1, 0].set_title('Validation SNR Over Epochs'); axs[1, 0].set_xlabel('Epochs'); axs[1, 0].set_ylabel('Signal-to-Noise Ratio (dB)'); axs[1, 0].legend(); axs[1, 0].grid(True)
        axs[1, 1].plot(self.history['val_psnr'], label='Validation PSNR', color='red')
        axs[1, 1].set_title('Validation PSNR Over Epochs'); axs[1, 1].set_xlabel('Epochs'); axs[1, 1].set_ylabel('Peak Signal-to-Noise Ratio (dB)'); axs[1, 1].legend(); axs[1, 1].grid(True)
        plt.tight_layout(rect=[0, 0.03, 1, 0.95]); plt.show()

# --- Module 5: Hyperparameter Tuner ---
class HyperparameterTuner:
    def __init__(self, X_train, X_val, device, chunk_size, epochs_per_trial=20):
        self.X_train = X_train
        self.X_val = X_val
        self.device = device
        self.chunk_size = chunk_size
        self.epochs_per_trial = epochs_per_trial

    def objective(self, trial):
        # Suggest hyperparameters
        lr = trial.suggest_float("lr", 1e-4, 1e-2, log=True)
        dropout = trial.suggest_float("dropout", 0.05, 0.4)
        kernel_size = trial.suggest_categorical("kernel_size", [3, 5])
        batch_size = trial.suggest_categorical("batch_size", [8, 16])
        
        # Suggest a flexible TCN channel architecture
        num_layers = trial.suggest_int("num_layers", 2, 5)
        channels = []
        for i in range(num_layers):
            n_channels = trial.suggest_categorical(f"n_channels_l{i}", [16, 32, 64])
            channels.append(n_channels)

        # Create model with suggested hyperparameters
        model = TCNAutoencoder(
            input_channels=1, output_channels=1, num_channels=channels,
            kernel_size=kernel_size, dropout=dropout
        )
        
        # Create and run the trainer for a limited number of epochs
        trainer = TCNTrainer(model=model, device=self.device, lr=lr, epochs=self.epochs_per_trial)
        trainer.train(self.X_train, self.X_val, self.chunk_size, batch_size)
        
        # Return the last validation loss as the metric to minimize
        return trainer.history['val_loss'][-1]

    def tune(self, n_trials=50):
        study = optuna.create_study(direction="minimize")
        study.optimize(self.objective, n_trials=n_trials, timeout=1800) # e.g. 30-minute timeout

        print("\n--- Hyperparameter Optimization Finished ---")
        print(f"Number of finished trials: {len(study.trials)}")
        print("Best trial:")
        trial = study.best_trial
        print(f"  Value (Min. Val Loss): {trial.value:.6f}")
        print("  Best Parameters: ")
        for key, value in trial.params.items():
            print(f"    {key}: {value}")
        return study.best_params

if __name__ == '__main__':
    # --- 1. Configuration ---
    AUDIO_FOLDER = "/home/javastral/GIT/GCPDS--trabajos-/Audios-AR/PresenceANEAudios"
    CHUNK_SIZE = 8192
    EPOCHS = 50 
    
    # --- 2. Data Loading and Preparation ---
    processor = AudioProcessor(AUDIO_FOLDER)
    audio_matrix, _ = processor.process_audios()

    if audio_matrix.size == 0:
        print("No audio files found or processed. Exiting.")
    else:
        print(f"Shape of original audio matrix: {audio_matrix.shape}")
        if audio_matrix.shape[1] % CHUNK_SIZE != 0:
            new_length = (audio_matrix.shape[1] // CHUNK_SIZE) * CHUNK_SIZE
            audio_matrix = audio_matrix[:, :new_length]
            print(f"Trimmed audio matrix for chunking. New shape: {audio_matrix.shape}")

        X_train, X_temp = train_test_split(audio_matrix, test_size=0.30, random_state=42)
        X_test, X_val = train_test_split(X_temp, test_size=(10/30), random_state=42)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {device}")

        # --- 3. Hyperparameter Optimization ---
        tuner = HyperparameterTuner(X_train, X_val, device, chunk_size=CHUNK_SIZE, epochs_per_trial=15)
        best_params = tuner.tune(n_trials=30)
        
        # --- 4. Final Model Training with Best Hyperparameters ---
        print("\n--- Training Final Model with Best Hyperparameters ---")
        
        # Extract best parameters
        final_lr = best_params.pop('lr')
        final_dropout = best_params.pop('dropout')
        final_kernel_size = best_params.pop('kernel_size')
        final_batch_size = best_params.pop('batch_size')
        final_num_layers = best_params.pop('num_layers')
        final_channels = [best_params[f'n_channels_l{i}'] for i in range(final_num_layers)]

        final_model = TCNAutoencoder(
            input_channels=1, output_channels=1, num_channels=final_channels,
            kernel_size=final_kernel_size, dropout=final_dropout
        )

        final_trainer = TCNTrainer(model=final_model, device=device, lr=final_lr, epochs=EPOCHS)
        final_trainer.train(X_train, X_val, chunk_size=CHUNK_SIZE, batch_size=final_batch_size)
        final_trainer.plot_history()
        
        # --- 5. Final Evaluation ---
        performance_results = final_trainer.evaluate(X_test, chunk_size=CHUNK_SIZE)
        
        print("\n--- Final Model Performance on Test Data ---")
        print(f"Mean Squared Error (MSE): {performance_results['MSE']:.6f}")
        print(f"Mean Absolute Error (MAE): {performance_results['MAE']:.6f}")
        print(f"Average Signal-to-Noise Ratio (SNR): {performance_results['SNR']:.2f} dB")
        print(f"Average Peak Signal-to-Noise Ratio (PSNR): {performance_results['PSNR']:.2f} dB")