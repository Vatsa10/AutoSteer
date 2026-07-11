"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// Single auth page at /sign-in with toggle — redirect sign-up users there
export default function SignUpRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace("/sign-in"); }, [router]);
  return null;
}
