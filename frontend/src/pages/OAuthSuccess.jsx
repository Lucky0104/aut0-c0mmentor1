import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function OAuthSuccess() {
  const navigate = useNavigate();
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    if (token) {
      localStorage.setItem("dashai_token", token);
      localStorage.removeItem("dashai_tid");
      window.location.href = "/dashboard";
    } else {
      navigate("/login");
    }
  }, [navigate]);
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="overline text-muted-foreground">Authenticating…</div>
    </div>
  );
}
