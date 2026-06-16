import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Sparkle, Trash } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Campaigns() {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    const { data } = await api.get("/campaigns");
    setItems(data);
  };
  useEffect(() => { load(); }, []);

  const generate = async () => {
    setBusy(true);
    try {
      await api.post("/campaigns/generate");
      toast.success("Campaign ideas generated");
      await load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Generation failed");
    } finally { setBusy(false); }
  };

  const del = async (id) => {
    await api.delete(`/campaigns/${id}`);
    await load();
  };

  return (
    <div className="p-6 md:p-10 max-w-[1400px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="overline text-muted-foreground">Growth</div>
          <h1 className="text-3xl lg:text-4xl font-black tracking-tight mt-1" style={{ fontFamily: "Chivo, sans-serif" }}>Campaigns</h1>
        </div>
        <button
          data-testid="campaigns-generate"
          onClick={generate}
          disabled={busy}
          className="bg-primary text-white px-4 py-2 text-sm font-semibold flex items-center gap-2 hover:bg-foreground transition disabled:opacity-60"
        >
          <Sparkle size={16} weight="fill" /> {busy ? "Generating…" : "Generate ideas with AI"}
        </button>
      </div>

      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {items.length === 0 && (
          <div data-testid="campaigns-empty" className="md:col-span-2 lg:col-span-3 border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
            No campaigns yet — click "Generate ideas with AI".
          </div>
        )}
        {items.map((c) => (
          <div key={c.id} data-testid={`campaign-${c.id}`} className="grid-card p-5">
            <div className="flex items-start justify-between gap-2">
              <div className="font-bold text-lg">{c.name}</div>
              <button data-testid={`campaign-delete-${c.id}`} onClick={() => del(c.id)} className="border border-border p-1 hover:bg-destructive hover:text-white hover:border-destructive">
                <Trash size={12} />
              </button>
            </div>
            <div className="overline text-muted-foreground mt-2">{c.audience}</div>
            <p className="mt-3 text-sm leading-relaxed">{c.ad_copy}</p>
            <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
              <div><span className="overline text-muted-foreground block">Budget</span><span className="mono">${c.budget_usd?.toLocaleString()}</span></div>
              <div><span className="overline text-muted-foreground block">Reach</span><span className="mono">{c.expected_reach?.toLocaleString()}</span></div>
              <div className="col-span-2"><span className="overline text-muted-foreground block">Schedule</span><span>{c.schedule}</span></div>
              <div className="col-span-2"><span className="overline text-muted-foreground block">Creative</span><span className="text-muted-foreground">{c.creative_idea}</span></div>
              {c.hashtags?.length > 0 && (
                <div className="col-span-2 flex flex-wrap gap-1 mt-1">
                  {c.hashtags.map((h, i) => (
                    <span key={i} className="text-[10px] border border-border px-2 py-0.5 mono">{h.startsWith("#") ? h : `#${h}`}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
