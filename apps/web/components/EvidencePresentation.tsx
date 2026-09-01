import type { EvidenceRecord, SignalRecord } from "@/lib/types";
import MarkdownView from "./MarkdownView";

export const humanize = (value: string) =>
  value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

const displayPrimitive = (value: unknown): string => {
  if (value == null || value === "") return "Not available";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return value.toLocaleString(undefined, { maximumFractionDigits: 3 });
  return String(value);
};

const parseStructuredString = (value: unknown): unknown => {
  if (typeof value !== "string" || !/^[\[{]/.test(value.trim())) return value;
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
};

const sanitizeTechnical = (value: unknown): unknown => {
  if (Array.isArray(value)) return value.map(sanitizeTechnical);
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>)
      .filter(([key]) => !["trace", "planner_reasoning", "cache_creation_input_tokens", "cache_read_input_tokens"].includes(key))
      .map(([key, item]) => [key, sanitizeTechnical(item)]),
  );
};

function MireyeIntelligence({ value }: { value: Record<string, unknown> }) {
  const fields = Array.isArray(value.fields_used) ? value.fields_used.map(String) : [];
  const citations = Array.isArray(value.citations) ? value.citations as Array<Record<string, unknown>> : [];
  const gaps = Array.isArray(value.data_gaps) ? value.data_gaps as Array<Record<string, unknown>> : [];
  const answer = typeof value.answer === "string" ? value.answer.trim() : "";
  return (
    <div className="mireye-intelligence">
      {answer ? <MarkdownView content={answer} /> : (
        <div className="provider-note">
          <b>Source-backed context retrieved</b>
          <p>Mireye returned field coverage and provenance, but no synthesized narrative. The evidence is organized below without filling the gap with generated claims.</p>
        </div>
      )}
      {fields.length > 0 && (
        <div className="evidence-section">
          <span className="fine">FIELD COVERAGE</span>
          <div className="field-chips">
            {fields.map((field) => <span key={field}>{humanize(field)}</span>)}
          </div>
        </div>
      )}
      {citations.length > 0 && (
        <div className="evidence-section">
          <span className="fine">SOURCE COVERAGE</span>
          <div className="source-grid">
            {citations.map((citation, index) => (
              <article className="source-card" key={`${String(citation.source)}-${index}`}>
                <b>{humanize(String(citation.source || "Provider source"))}</b>
                <span>{humanize(String(citation.confidence || "unrated"))} confidence</span>
                {Array.isArray(citation.fields) && <p>{citation.fields.map((field) => humanize(String(field))).join(", ")}</p>}
              </article>
            ))}
          </div>
        </div>
      )}
      {gaps.length > 0 && (
        <details className="technical-disclosure data-gaps">
          <summary>{gaps.length} data gaps and unavailable fields</summary>
          {gaps.map((gap, index) => (
            <div className="gap-row" key={`${String(gap.field)}-${index}`}>
              <b>{humanize(String(gap.field || "Field"))}</b>
              <span>{String(gap.reason || "No reason supplied")}</span>
            </div>
          ))}
        </details>
      )}
    </div>
  );
}

function StructuredValue({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (value == null || typeof value !== "object") {
    return <span>{displayPrimitive(value)}</span>;
  }
  if (Array.isArray(value)) {
    if (!value.length) return <span className="muted">No records returned</span>;
    if (
      Array.isArray(value[0]) &&
      (value[0] as unknown[]).every((item) => typeof item === "string")
    ) {
      const headers = value[0] as string[];
      const records = value.slice(1).filter(Array.isArray).map((row) =>
        Object.fromEntries(headers.map((header, index) => [header, (row as unknown[])[index]])),
      );
      return <StructuredValue value={records} depth={depth} />;
    }
    return (
      <div className="structured-list">
        {value.map((item, index) => (
          <div className="structured-item" key={index}>
            {typeof item === "object" && item !== null ? (
              <StructuredValue value={item} depth={depth + 1} />
            ) : (
              displayPrimitive(item)
            )}
          </div>
        ))}
      </div>
    );
  }
  const entries = Object.entries(value as Record<string, unknown>).filter(
    ([key, item]) => !["raw", "metadata"].includes(key) && item != null && item !== "",
  );
  if (!entries.length) return <span className="muted">No details returned</span>;
  return (
    <dl className={depth ? "fact-list nested" : "fact-list"}>
      {entries.map(([key, item]) => (
        <div className="fact" key={key}>
          <dt>{humanize(key)}</dt>
          <dd>
            {typeof item === "object" ? (
              <StructuredValue value={item} depth={depth + 1} />
            ) : (
              displayPrimitive(item)
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}

const normalizeEvidenceValue = (item: EvidenceRecord, value: unknown): unknown => {
  if (
    item.source_type === "USDA_CDL" &&
    value &&
    typeof value === "object" &&
    !Array.isArray(value)
  ) {
    const record = value as Record<string, unknown>;
    const category = String(record.category || "").toLowerCase();
    if (category.startsWith("developed/")) {
      return {
        ...record,
        is_agricultural: false,
        classification_note: "Developed land-cover classes are non-agricultural.",
      };
    }
  }
  return value;
};

const whyItMatters = (item: EvidenceRecord) => {
  const field = item.field_name.toLowerCase();
  if (field.includes("crop") || field.includes("cultivat"))
    return "Historical land use helps test agricultural continuity and seller acreage claims.";
  if (field.includes("soil") || field.includes("drain"))
    return "Soil and drainage conditions can change usable acreage, operating cost, and crop reliability.";
  if (field.includes("flood") || field.includes("hazard"))
    return "Hazard exposure matters only after translating it into consequences for the intended activity.";
  if (field.includes("value") || field.includes("price") || field.includes("market"))
    return "This evidence helps bound acquisition economics without treating a regional benchmark as an appraisal.";
  if (field.includes("location") || field.includes("boundary") || field.includes("area"))
    return "Location and geometry determine which physical evidence is applicable and whether acreage comparisons are valid.";
  if (item.source_type === "MIREYE")
    return "Physical-world context helps decide which property claims and operational risks deserve deeper investigation.";
  return "This observation contributes to the evidence graph and is used only when it can affect a material decision.";
};

export function EvidenceCard({ item, featured = false }: { item: EvidenceRecord; featured?: boolean }) {
  const normalizedValue = normalizeEvidenceValue(item, parseStructuredString(item.value));
  const isMarkdown = item.source_type === "MIREYE" && typeof normalizedValue === "string";
  const isStructured = typeof normalizedValue === "object" && normalizedValue !== null;
  const isMireyePayload = item.source_type === "MIREYE" && isStructured && !Array.isArray(normalizedValue);
  return (
    <article className={`evidence-card refined ${featured ? "featured-evidence" : ""}`}>
      <div className="evidence-card-head">
        <div>
          <p className="eyebrow">{humanize(item.source_type)}</p>
          <h3>{humanize(item.field_name)}</h3>
        </div>
        <span className={`materiality-chip confidence-${item.confidence >= 0.75 ? "high" : item.confidence >= 0.5 ? "medium" : "low"}`}>
          {Math.round(item.confidence * 100)}% confidence
        </span>
      </div>
      <div className="confidence-track" aria-label={`${Math.round(item.confidence * 100)}% confidence`}>
        <span style={{ width: `${Math.round(item.confidence * 100)}%` }} />
      </div>
      <div className="evidence-section">
        <span className="fine">OBSERVATION</span>
        {isMireyePayload ? (
          <MireyeIntelligence value={normalizedValue as Record<string, unknown>} />
        ) : isMarkdown ? (
          <MarkdownView content={normalizedValue as string} />
        ) : isStructured ? (
          <StructuredValue value={normalizedValue} />
        ) : (
          <p className="evidence-value">{displayPrimitive(item.value)} {item.unit || ""}</p>
        )}
      </div>
      <div className="evidence-explanation">
        <div>
          <span className="fine">WHY IT MATTERS</span>
          <p>{whyItMatters(item)}</p>
        </div>
        <div>
          <span className="fine">SOURCE & SCOPE</span>
          <p><b>{item.source.publisher}</b> · {item.source.dataset}{item.source.vintage ? ` · ${item.source.vintage}` : ""}</p>
          <p className="muted">{item.semantic_scope || "Scope not specified"}{item.spatial_resolution ? ` · ${item.spatial_resolution}` : ""}</p>
        </div>
      </div>
      {(item.limitations.length > 0 || isStructured) && (
        <details className="technical-disclosure">
          <summary>Limitations & technical data</summary>
          {item.limitations.map((limitation) => <p className="limitation" key={limitation}>{limitation}</p>)}
          {isStructured && <pre>{JSON.stringify(sanitizeTechnical(normalizedValue), null, 2)}</pre>}
        </details>
      )}
    </article>
  );
}

export function SignalCard({ signal }: { signal: SignalRecord }) {
  return (
    <article className="signal-card">
      <div className="evidence-card-head">
        <div>
          <p className="eyebrow">Derived signal</p>
          <h3>{signal.name}</h3>
        </div>
        <span className={`materiality-chip materiality-${signal.materiality.toLowerCase()}`}>
          {humanize(signal.materiality)} materiality
        </span>
      </div>
      <div className="signal-value">{displayPrimitive(signal.value)}</div>
      <p>{signal.interpretation}</p>
      {signal.method && (
        <details className="technical-disclosure">
          <summary>How this was derived</summary>
          <p>{signal.method}</p>
          {signal.limitations?.map((item) => <p className="limitation" key={item}>{item}</p>)}
        </details>
      )}
    </article>
  );
}
