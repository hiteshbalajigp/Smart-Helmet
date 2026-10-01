import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import { Violation } from "../services/api";

interface Props {
  violations: Violation[];
}

const DEFAULT_CENTER: [number, number] = [28.6139, 77.209];

export default function ViolationMap({ violations }: Props) {
  const geoViolations = violations.filter((v) => v.latitude && v.longitude);
  const center: [number, number] =
    geoViolations.length > 0
      ? [geoViolations[0].latitude!, geoViolations[0].longitude!]
      : DEFAULT_CENTER;

  return (
    <div className="card map-card">
      <h2>GPS Map</h2>
      <MapContainer center={center} zoom={12} scrollWheelZoom={false} className="map">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {geoViolations.map((v) => (
          <Marker key={v.violation_id} position={[v.latitude!, v.longitude!]}>
            <Popup>
              {v.violation_type} — {v.plate_text || "Unknown plate"}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
