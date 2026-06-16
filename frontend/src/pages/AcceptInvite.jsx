import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../lib/api";

export default function AcceptInvite() {
  const { token } = useParams();
  const nav = useNavigate();
  const [status, setStatus] = useState("Joining…");

  useEffect(() => {
    if (!localStorage.getItem("dashai_token")) {
      localStorage.setItem("dashai_invite_pending", token);
      nav("/login");
      return;
    }
    api.post(`/team/accept/${token}`)
      .then(({ data }) => {
        localStorage.setItem("dashai_tid", data.tenant_id);
        setStatus("Joined! Redirecting…");
        setTimeout(() => { window.location.href = "/dashboard"; }, 600);
      })
      .catch((e) => setStatus(e.response?.data?.detail || "Invite invalid"));
  }, [token, nav]);

  return <div className="min-h-screen flex items-center justify-center"><span className="overline">{status}</span></div>;
}
