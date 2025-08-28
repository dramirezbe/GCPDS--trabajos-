# Cómo optimizar recursos

- HPO
- MultiHilo
- GPU
- Por lotes (chunks)

# Métodos Hmejora NN para ARNN (autoregressive NN)

- hpo
- tcnn
- lstm
- rn
- Representación 2D (CNN)

- Cargar audios
- Hacer una LARNN, como entrada una matriz de audios, (#audios, #data de audios), luego tratar de optimizar modelo (tcnn, lstm, rnn), que salga una representación 2D de los audio(el objetivo es utilizar características de la señal con una ARNN, que los clusters encontrados en la representacion 2D, se vean ordenados).


# MLP -> LSTM -> t-CNN