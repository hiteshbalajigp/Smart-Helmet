import { Violation, evidenceUrl } from "../services/api";

interface Props {
  violations: Violation[];
}

export default function ViolationHistory({ violations }: Props) {
  return (
    <div className="card">
      <h2>Violation History</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Type</th>
              <th>Plate</th>
              <th>Device</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody>
            {violations.map((v) => (
              <tr key={v.violation_id}>
                <td>{new Date(v.timestamp).toLocaleString()}</td>
                <td>{v.violation_type}</td>
                <td>{v.plate_text || "—"}</td>
                <td>{v.device_id}</td>
                <td>
                  <a href={evidenceUrl(v.violation_id, "snapshot")} target="_blank" rel="noreferrer">
                    JPEG
                  </a>
                  {" | "}
                  <a href={evidenceUrl(v.violation_id, "video")} target="_blank" rel="noreferrer">
                    MP4
                  </a>
                </td>
              </tr>
            ))}
            {violations.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  No violations recorded yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
