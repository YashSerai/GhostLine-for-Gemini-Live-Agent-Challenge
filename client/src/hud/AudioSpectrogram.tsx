import React, { useEffect, useRef } from "react";

export interface AudioSpectrogramProps {
  operatorAnalyser: AnalyserNode | null;
  userAnalyser: AnalyserNode | null;
}

export const AudioSpectrogram: React.FC<AudioSpectrogramProps> = ({
  operatorAnalyser,
  userAnalyser,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    // Fast decay helps the waveform snap back down to show "silence" immediately.
    const DECAY_FACTOR = 0.85; 

    // Internal data arrays to hold smoothed frequency blocks
    const operatorData = new Uint8Array(128);
    const smoothedOperator = new Float32Array(128);

    const userData = new Uint8Array(128);
    const smoothedUser = new Float32Array(128);

    const draw = () => {
      animationId = window.requestAnimationFrame(draw);

      // Match canvas logical size to physical pixels
      const width = canvas.width;
      const height = canvas.height;
      const halfHeight = height / 2;

      ctx.clearRect(0, 0, width, height);

      // Read real data if available
      if (operatorAnalyser) {
        // limit bars to standard visual range (lower half of FFT)
        const binCount = Math.min(operatorAnalyser.frequencyBinCount, 128);
        const temp = new Uint8Array(binCount);
        operatorAnalyser.getByteFrequencyData(temp);
        for (let i = 0; i < binCount; i++) {
          operatorData[i] = temp[i];
        }
      } else {
        operatorData.fill(0);
      }

      if (userAnalyser) {
        const binCount = Math.min(userAnalyser.frequencyBinCount, 128);
        const temp = new Uint8Array(binCount);
        userAnalyser.getByteFrequencyData(temp);
        for (let i = 0; i < binCount; i++) {
          userData[i] = temp[i];
        }
      } else {
        userData.fill(0);
      }

      // Smooth the data so it doesn't flicker violently
      for (let i = 0; i < 128; i++) {
        smoothedOperator[i] =
          smoothedOperator[i] * DECAY_FACTOR + operatorData[i] * (1 - DECAY_FACTOR);
        smoothedUser[i] =
          smoothedUser[i] * DECAY_FACTOR + userData[i] * (1 - DECAY_FACTOR);
      }

      // Render configuration
      const barCount = 48; // How many bars to draw horizontally
      const barWidth = Math.floor(width / barCount);
      const gap = 2; // Spacing between bars

      // Helper to draw the mirrored bars
      const drawBars = (
        data: Float32Array,
        color: string,
        yOrigin: number,
        direction: 1 | -1
      ) => {
        ctx.fillStyle = color;
        // Map 48 bars across the 128 data points (skip high invisible frequencies)
        const step = Math.floor(64 / barCount); 
        
        for (let i = 0; i < barCount; i++) {
          // Average a few bins to get a more stable bar height
          const dataIndex = Math.max(0, i * step);
          // Scale 0-255 down to half height, keep a tiny 2px bar minimum
          const magnitude = Math.max(2, (data[dataIndex] / 255) * halfHeight * 0.9);
          
          const x = i * barWidth;
          // Direction 1 draws down, -1 draws up from origin
          const y = direction === 1 ? yOrigin : yOrigin - magnitude;
          
          // Use rounded bars if possible, otherwise standard fillRect
          ctx.beginPath();
          ctx.roundRect(x + gap, y, barWidth - gap * 2, magnitude, 2);
          ctx.fill();
        }
      };

      // Draw User (Microphone) in the top half, painting UPWARDS from center
      drawBars(smoothedUser, "#7FA9CA", halfHeight, -1);
      
      // Draw Operator (Gemini) in the bottom half, painting DOWNWARDS from center
      drawBars(smoothedOperator, "#D67E4A", halfHeight, 1);

      // Center Divider line
      ctx.fillStyle = "rgba(255, 255, 255, 0.1)";
      ctx.fillRect(0, halfHeight - 1, width, 2);
    };

    draw();

    return () => {
      window.cancelAnimationFrame(animationId);
    };
  }, [operatorAnalyser, userAnalyser]);

  return (
    <section className="panel" aria-label="Audio Bridge Diagnostics">
      <div className="panel-heading" style={{ marginBottom: "8px" }}>
        <div>
          <h2>Audio Spectrogram</h2>
        </div>
      </div>
      <div style={{ position: "relative", width: "100%", height: "120px" }}>
        <canvas
          ref={canvasRef}
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%"
          }}
          // Canvas internal rendering coordinates
          width={800}
          height={240}
        />
        
        {/* Channel Labels overlaying the canvas corners */}
        <div style={{
          position: "absolute", 
          top: 0, 
          right: 0, 
          fontFamily: "'Courier New', monospace",
          fontSize: "0.65rem",
          color: "#7FA9CA",
          padding: "4px 8px",
          background: "rgba(12, 22, 31, 0.8)",
          borderRadius: "0 0 0 8px"
        }}>
          UPSTREAM (MIC)
        </div>
        <div style={{
          position: "absolute", 
          bottom: 0, 
          right: 0, 
          fontFamily: "'Courier New', monospace",
          fontSize: "0.65rem",
          color: "#D67E4A",
          padding: "4px 8px",
          background: "rgba(36, 22, 17, 0.8)",
          borderRadius: "8px 0 0 0"
        }}>
          DOWNSTREAM (HOST)
        </div>
      </div>
    </section>
  );
};
