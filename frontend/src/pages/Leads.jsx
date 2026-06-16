import { useEffect, useState } from "react";
import { api } from "../lib/api";

const STATUS = ["new", "contacted", "qualified", "won", "lost"];

export default function Leads() {
  const [items, setItems] = useState([]);
  const load = async () => {
    const { data } = await api.get("/leads");
    setItems(data);
  };
  useEffect(() => { load(); }, []);

  const updateStatus = async (id, status) => {
    await api.patch(`/leads/${id}?status=${status}`);
    await load();
  };

  return (
    <div className="p-6 md:p-10 max-w-[1400px]">
      <div className="overline text-muted-foreground">Pipeline</div>
      <h1 className="text-3xl lg:text-4xl font-black tracking-tight mt-1" style={{ fontFamily: "Chivo, sans-serif" }}>Leads</h1>

      <div className="mt-6 border border-border">
        <div className="grid grid-cols-12 px-5 py-3 border-b border-border bg-secondary overline text-muted-foreground">
          <div className="col-span-3">From</div>
          <div className="col-span-5">Intent</div>
          <div className="col-span-1">Score</div>
          <div className="col-span-2">Category</div>
          <div className="col-span-1 text-right">Status</div>
        </div>
        {items.length === 0 && <div data-testid="leads-empty" className="p-10 text-center text-sm text-muted-foreground">No leads yet.</div>}
        {items.map((l) => (
          <div key={l.comment_id} data-testid={`lead-${l.comment_id}`} className="grid grid-cols-12 px-5 py-4 border-b border-border last:border-0 items-center gap-2 text-sm">
            <div className="col-span-3 font-semibold truncate">{l.from_name}</div>
            <div className="col-span-5 line-clamp-2">{l.message}</div>
            <div className="col-span-1">
              <span className={`mono px-2 py-0.5 border ${l.score >= 75 ? "border-[#10B981] text-[#10B981] bg-[#10B981]/5" : "border-border"}`}>{l.score}</span>
            </div>
            <div className="col-span-2 text-muted-foreground capitalize">{l.category?.replaceAll("_", " ")}</div>
            <div className="col-span-1 text-right">
              <select
                data-testid={`lead-status-${l.comment_id}`}
                value={l.status}
                onChange={(e) => updateStatus(l.comment_id, e.target.value)}
                className="border border-border px-2 py-1 text-xs bg-white"
              >
                {STATUS.map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
