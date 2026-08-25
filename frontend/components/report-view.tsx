import type { Report } from "@/lib/types";

function healthClass(health: string): string {
  const key = health.toLowerCase();
  if (key === "alarm") return "health-alarm";
  if (key === "advisory") return "health-advisory";
  return "health-normal";
}

export function ReportView({ report }: { report: Report }) {
  return (
    <div className="report-card">
      <p className="report-summary">{report.summary}</p>

      {report.verdicts.length > 0 && (
        <table className="verdict-table">
          <thead>
            <tr>
              <th>Parameter</th>
              <th>Value</th>
              <th>Health</th>
            </tr>
          </thead>
          <tbody>
            {report.verdicts.map((v) => (
              <tr key={v.parameter}>
                <td>{v.parameter}</td>
                <td>{v.value}</td>
                <td className={healthClass(v.health)}>{v.health}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {report.diagnosis && (
        <dl className="diagnosis">
          <dt>What the data shows</dt>
          <dd>{report.diagnosis.what_data_shows}</dd>
          <dt>What the guidance says</dt>
          <dd>{report.diagnosis.what_guidance_says}</dd>
          <dt>Combined finding</dt>
          <dd>{report.diagnosis.combined_finding}</dd>
          <dt>Recommendation</dt>
          <dd>
            {report.diagnosis.recommendation.next_step}
            <br />
            <em>— {report.diagnosis.recommendation.fault_signature}, {report.diagnosis.recommendation.citation}</em>
          </dd>
          <dt>Caveats</dt>
          <dd>{report.diagnosis.caveats}</dd>
        </dl>
      )}
    </div>
  );
}
