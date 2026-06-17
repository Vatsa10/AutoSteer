"use client";

import { useParams } from "next/navigation";
import { WorkflowDetail } from "@/components/workflow-detail";

export default function WorkflowDetailPage() {
  const { name } = useParams<{ name: string }>();
  return (
    <div className="h-full overflow-y-auto bg-[#F4F4F0]">
      <div className="max-w-3xl mx-auto px-6 py-8">
        <WorkflowDetail name={name} />
      </div>
    </div>
  );
}
