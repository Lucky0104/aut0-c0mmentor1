import { useEffect, useState } from "react";
import { api } from "../lib/api";

const SENT = ["", "positive", "neutral", "negative"];

const sentClass = (s) =>
  s === "positive" ? "text-[#10B981] border-[#10B981]/40 bg-[#10B981]/5"
  : s === "negative" ? "text-destructive border-destructive/40 bg-destructive/5"
  : "text-muted-foreground border-border bg-secondary";

export default function Comments() {
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState({ sentiment: "", status: "" });

  const load = async () => {
    const q = new URLSearchParams();
    if (filter.sentiment) q.append("sentiment", filter.sentiment);
    if (filter.status) q.append("status", filter.status);
    const { data } = await api.get(`/comments?${q.toString()}`);
    setItems(data);
  };

  useEffect(() => { load(); }, [filter]);

  return (
    <div className="p-6 md:p-10 max-w-[1400px]">
      <div className="overline text-muted-foreground">Inbox</div>
      <h1 className="text-3xl lg:text-4xl font-black tracking-tight mt-1" style={{ fontFamily: "Chivo, sans-serif" }}>
        Comments
      </h1>

      <div className="flex gap-3 mt-6 flex-wrap">
        <div>
          <div className="overline text-muted-foreground mb-1">Sentiment</div>
          <select
            data-testid="filter-sentiment"
            value={filter.sentiment}
            onChange={(e) => setFilter({ ...filter, sentiment: e.target.value })}
            className="border border-border px-3 py-2 bg-white text-sm"
          >
            {SENT.map((s) => <option key={s} value={s}>{s || "all"}</option>)}
          </select>
        </div>
        <div>
          <div className="overline text-muted-foreground mb-1">Status</div>
          <select
            data-testid="filter-status"
            value={filter.status}
            onChange={(e) => setFilter({ ...filter, status: e.target.value })}
            className="border border-border px-3 py-2 bg-white text-sm"
          >
            {["", "pending", "pending_approval", "replied", "rejected"].map((s) => <option key={s} value={s}>{s || "all"}</option>)}
          </select>
        </div>
      </div>

      <div className="mt-6 border border-border">
        <div className="grid grid-cols-12 px-5 py-3 border-b border-border bg-secondary overline text-muted-foreground">
          <div className="col-span-3">From</div>
          <div className="col-span-5">Comment</div>
          <div className="col-span-2">Category</div>
          <div className="col-span-1">Sentiment</div>
          <div className="col-span-1 text-right">Status</div>
        </div>
        {items.length === 0 && (
          <div className="p-10 text-center text-sm text-muted-foreground" data-testid="comments-empty">No comments yet — run a Page sync.</div>
        )}
        {items.map((c) => (
          <div key={c.comment_id} data-testid={`comment-row-${c.comment_id}`} className="grid grid-cols-12 px-5 py-4 border-b border-border last:border-0 items-start gap-2 text-sm hover:bg-secondary/40">
            <div className="col-span-3">
              <div className="font-semibold truncate">{c.from_name}</div>
              <div className="overline text-muted-foreground">{c.platform}</div>
            </div>
            <div className="col-span-5"><div className="line-clamp-3 leading-relaxed">{c.message}</div></div>
            <div className="col-span-2 capitalize text-muted-foreground">{c.category?.replaceAll("_", " ")}</div>
            <div className="col-span-1"><span className={`px-2 py-0.5 text-[10px] border ${sentClass(c.sentiment)}`}>{c.sentiment}</span></div>
            <div className="col-span-1 text-right mono text-[10px] text-muted-foreground">{c.status}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
