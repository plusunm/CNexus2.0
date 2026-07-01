"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import MindShell from "@/components/mind/MindShell";
import { parseShellLayout, parseShellPanel } from "@/cnexus-kernel";

function DesktopShellInner() {
  const searchParams = useSearchParams();
  const panel = parseShellPanel(searchParams.get("panel"));
  return <MindShell layout="float" desktop panel={panel} />;
}

export default function DesktopPage() {
  return (
    <Suspense fallback={<MindShell layout="float" desktop />}>
      <DesktopShellInner />
    </Suspense>
  );
}
