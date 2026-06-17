"use client";

import { WorkflowList } from "@/components/workflow-list";

export default function WorkflowsPage() {
  return (
    <div className="h-full overflow-y-auto bg-[#F4F4F0]">
      <div className="max-w-3xl mx-auto px-6 py-8">
        <h1 className="font-display text-3xl md:text-5xl mb-8">WORKFLOWS</h1>
        <WorkflowList />
      </div>
    </div>
  );
}
