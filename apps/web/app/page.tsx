"use client";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

type Mode = "address" | "listing_url" | "query";
type Profile = { id: string; name: string };
const examples = {
  address: "123 County Road, Ames, Iowa",
  listing_url: "https://example.com/agricultural-listing",
  query:
    "I'm considering an 85-acre farm near Ames, IA listed for $1.2M. The seller says 70 acres are tillable with excellent drainage. I care about row-crop productivity and low flood risk.",
};
export default function Home() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("query");
  const [input, setInput] = useState(examples.query);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [profile, setProfile] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    api<Profile[]>("/buyer-profiles")
      .then(setProfiles)
      .catch(() => {});
  }, []);
  function switchMode(value: Mode) {
    setMode(value);
    setInput(examples[value]);
    setError("");
  }
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api<{ investigation_id: string }>(
        "/investigations",
        {
          method: "POST",
          body: JSON.stringify({
            input_type: mode,
            input,
            buyer_profile_id: profile || null,
          }),
        },
      );
      router.push(`/investigation/${result.investigation_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="shell">
      <section className="hero">
        <div>
          <p className="eyebrow">Agricultural acquisition intelligence</p>
          <h1>
            Know the land.
            <br />
            Question the story.
          </h1>
        </div>
        <p className="lede">
          An autonomous evidence investigation for agricultural property
          decisions—physical reality, crop history, contradictions, valuation,
          and your next move.
        </p>
      </section>
      <section className="panel">
        <div className="modebar">
          <button
            className={mode === "address" ? "active" : ""}
            onClick={() => switchMode("address")}
          >
            Property address
          </button>
          <button
            className={mode === "listing_url" ? "active" : ""}
            onClick={() => switchMode("listing_url")}
          >
            Listing URL
          </button>
          <button
            className={mode === "query" ? "active" : ""}
            onClick={() => switchMode("query")}
          >
            Describe the deal
          </button>
        </div>
        <form onSubmit={submit}>
          <label>
            {mode === "query"
              ? "Property and acquisition question"
              : mode === "address"
                ? "Property address"
                : "Public listing URL"}
          </label>
          {mode === "query" ? (
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
          ) : (
            <input
              type={mode === "listing_url" ? "url" : "text"}
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
          )}
          <div className="columns" style={{ marginTop: 16 }}>
            <div>
              <label>Buyer context</label>
              <select
                value={profile}
                onChange={(e) => setProfile(e.target.value)}
              >
                <option value="">No saved profile</option>
                {profiles.map((p) => (
                  <option value={p.id} key={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="actions">
              <span className="fine">
                Claims are investigated, never assumed true.
              </span>
              <button className="button" disabled={busy || input.length < 3}>
                {busy ? "Starting…" : "Begin investigation →"}
              </button>
            </div>
          </div>
          {error && <p className="error">{error}</p>}
        </form>
      </section>
      <section className="grid" style={{ marginTop: 22 }}>
        <div className="card">
          <h3>Evidence, not a score</h3>
          <p>
            Every conclusion traces back to source, field, vintage, spatial
            scope, and known limitations.
          </p>
        </div>
        <div className="card">
          <h3>Investigation that adapts</h3>
          <p>
            The orchestrator chooses the next question according to materiality
            and expected decision impact.
          </p>
        </div>
        <div className="card">
          <h3>A decision you can act on</h3>
          <p>
            A binary verdict, bounded value, prioritized diligence, and
            evidence-linked negotiation strategy.
          </p>
        </div>
      </section>
    </div>
  );
}
