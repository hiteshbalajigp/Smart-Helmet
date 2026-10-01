import { useEffect, useRef, useState } from "react";

export default function LiveCamera() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [active, setActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active || !videoRef.current) return;

    let stream: MediaStream | null = null;
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "environment" }, audio: false })
      .then((media) => {
        stream = media;
        if (videoRef.current) {
          videoRef.current.srcObject = media;
        }
      })
      .catch(() => setError("Camera access denied or unavailable"));

    return () => {
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, [active]);

  return (
    <div className="card">
      <div className="card-header">
        <h2>Live Camera</h2>
        <button className="btn secondary" onClick={() => setActive((v) => !v)}>
          {active ? "Stop" : "Start"}
        </button>
      </div>
      {error && <p className="muted">{error}</p>}
      <div className="camera-frame">
        {active ? (
          <video ref={videoRef} autoPlay playsInline muted />
        ) : (
          <div className="camera-placeholder">Camera preview inactive</div>
        )}
      </div>
    </div>
  );
}
