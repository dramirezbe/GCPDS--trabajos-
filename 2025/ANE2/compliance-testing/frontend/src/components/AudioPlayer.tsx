import { useEffect, useRef, useState } from 'react';
import { Volume2, VolumeX, Play, Pause } from 'lucide-react';

interface AudioPlayerProps {
  isActive: boolean;
  demodType: 'AM' | 'FM';
}

export function AudioPlayer({ isActive, demodType }: AudioPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(0.7);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!isActive) {
      stopAudio();
      return;
    }

    // Inicializar AudioContext
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext();
      gainNodeRef.current = audioContextRef.current.createGain();
      gainNodeRef.current.connect(audioContextRef.current.destination);
      gainNodeRef.current.gain.value = volume;
    }

    // Conectar WebSocket para audio streaming
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsPort = window.location.protocol === 'https:' ? ':12443' : ':3000';
    const wsUrl = `${wsProtocol}//${window.location.hostname}${wsPort}/ws`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('🎵 AudioPlayer WebSocket connected');
      // Suscribirse al audio streaming
      ws.send(JSON.stringify({
        type: 'subscribe_audio',
        demodType: demodType
      }));
    };

    ws.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'audio_data' && audioContextRef.current && isPlaying) {
          // Decodificar y reproducir audio
          // El audio viene en formato base64 PCM
          const audioData = atob(data.audio);
          const audioArray = new Float32Array(audioData.length);
          
          for (let i = 0; i < audioData.length; i++) {
            audioArray[i] = (audioData.charCodeAt(i) - 128) / 128.0;
          }
          
          const audioBuffer = audioContextRef.current.createBuffer(
            1, // mono
            audioArray.length,
            audioContextRef.current.sampleRate
          );
          
          audioBuffer.copyToChannel(audioArray, 0);
          
          // Crear source y reproducir
          if (audioSourceRef.current) {
            audioSourceRef.current.stop();
          }
          
          const source = audioContextRef.current.createBufferSource();
          source.buffer = audioBuffer;
          source.connect(gainNodeRef.current!);
          source.start();
          audioSourceRef.current = source;
        }
      } catch (error) {
        console.error('Error processing audio data:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('AudioPlayer WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('🎵 AudioPlayer WebSocket disconnected');
    };

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [isActive, demodType, isPlaying]);

  useEffect(() => {
    if (gainNodeRef.current) {
      gainNodeRef.current.gain.value = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  const stopAudio = () => {
    if (audioSourceRef.current) {
      audioSourceRef.current.stop();
      audioSourceRef.current = null;
    }
    setIsPlaying(false);
  };

  const togglePlay = () => {
    if (!isActive) return;
    setIsPlaying(!isPlaying);
  };

  const toggleMute = () => {
    setIsMuted(!isMuted);
  };

  if (!isActive) {
    return null;
  }

  return (
    <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg p-3 border border-purple-200">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={togglePlay}
            className={`p-2 rounded-full transition-colors ${
              isPlaying 
                ? 'bg-purple-600 text-white hover:bg-purple-700' 
                : 'bg-white text-purple-600 hover:bg-purple-100 border border-purple-300'
            }`}
            title={isPlaying ? 'Pausar' : 'Reproducir'}
          >
            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
          </button>
          
          <div className="flex flex-col">
            <span className="text-xs font-medium text-gray-700">
              Audio en vivo - {demodType}
            </span>
            <span className="text-xs text-gray-500">
              {isPlaying ? 'Reproduciendo...' : 'Pausado'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={toggleMute}
            className="p-1.5 rounded hover:bg-white/60 transition-colors"
            title={isMuted ? 'Activar sonido' : 'Silenciar'}
          >
            {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
          </button>
          
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={volume}
            onChange={(e) => setVolume(parseFloat(e.target.value))}
            className="w-20 h-1 bg-gray-300 rounded-lg appearance-none cursor-pointer accent-purple-600"
            disabled={isMuted}
          />
          
          <span className="text-xs text-gray-600 w-8 text-right">
            {Math.round(volume * 100)}%
          </span>
        </div>
      </div>
    </div>
  );
}
