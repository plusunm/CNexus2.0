"use client";

import { useEffect } from "react";

/** Legacy path — keep bookmarks working inside the shell. */
export default function MissionControlRedirectPage() {
  useEffect(() => {
    window.location.replace("/shell/?layout=overview&view=network");
  }, []);
  return (
    <main className="min-h-screen flex items-center justify-center text-sm text-slate-400">
      正在进入网络驾驶舱…
    </main>
  );
}
